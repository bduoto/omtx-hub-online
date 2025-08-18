"""
Modal Subprocess Runner
Handles subprocess execution with Modal authentication isolation
"""

import asyncio
import json
import logging
import os
import tempfile
import time
from typing import Dict, Any, Optional
from pathlib import Path

from services.modal_auth_service import modal_auth_service

logger = logging.getLogger(__name__)

class ModalSubprocessRunner:
    """Generic subprocess runner for Modal predictions with auth isolation"""
    
    def __init__(self):
        self.max_retries = 3
        self.retry_delay = 5
        self.subprocess_timeout = 300  # 5 minutes default timeout
    
    async def execute_modal_function(
        self,
        app_name: str,
        function_name: str,
        parameters: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a Modal function in an isolated subprocess
        
        Args:
            app_name: Modal app name
            function_name: Modal function name  
            parameters: Function parameters
            timeout: Subprocess timeout in seconds
            
        Returns:
            Dict with execution result and metadata
        """
        execution_timeout = timeout or self.subprocess_timeout
        
        logger.info(f"Executing Modal function {app_name}.{function_name}")
        logger.debug(f"Parameters: {list(parameters.keys())}")
        
        # Validate authentication
        if not modal_auth_service.validate_credentials():
            raise Exception("Modal credentials not available or invalid")
        
        # Create subprocess script
        script_content = self._generate_subprocess_script(
            app_name, function_name, parameters
        )
        
        # Execute with retries
        for attempt in range(1, self.max_retries + 1):
            try:
                result = await self._execute_subprocess(
                    script_content, execution_timeout, attempt
                )
                logger.info(f"Modal function execution completed successfully")
                return result
                
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{self.max_retries} failed: {e}")
                
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)  # Exponential backoff
                else:
                    logger.error(f"All {self.max_retries} attempts failed")
                    raise Exception(f"Modal execution failed after {self.max_retries} attempts: {e}")
    
    def _generate_subprocess_script(
        self,
        app_name: str,
        function_name: str,
        parameters: Dict[str, Any]
    ) -> str:
        """Generate Python script for subprocess execution"""
        
        auth_snippet = modal_auth_service.get_auth_script_snippet()
        
        # Safely serialize parameters for script generation
        serialized_params = {}
        for key, value in parameters.items():
            # Store the JSON representation as a string for script generation
            serialized_params[key] = json.dumps(value, default=str)
        
        script = f'''
import json
import sys
import os
import time

def execute_modal_function():
    try:
        start_time = time.time()
        
        # Set Modal authentication credentials
        {auth_snippet}
        
        print("--- Modal Subprocess Debug ---")
        print(f"App: {app_name}")
        print(f"Function: {function_name}")
        print(f"Auth available: {{bool(os.environ.get('MODAL_TOKEN_ID'))}}")
        
        # Import Modal after setting credentials
        import modal
        
        # Load Modal function
        modal_function = modal.Function.from_name(
            "{app_name}",
            "{function_name}"
        )
        
        # Prepare parameters
        params = {{}}
'''
        
        # Add parameter assignments  
        for key, serialized_value in serialized_params.items():
            # Use repr() to properly escape all special characters including newlines
            escaped_value = repr(serialized_value)
            script += f"        params['{key}'] = json.loads({escaped_value})\n"
        
        script += f'''
        print(f"Calling Modal function with {{len(params)}} parameters...")
        
        # Execute Modal function
        # Execute Modal function synchronously for immediate results
        result = modal_function.remote(**params)

        print(f"Modal function executed successfully")

        # Ensure we have a proper result structure
        if not isinstance(result, dict):
            result = {{"raw_result": str(result)}}

        # Add success status
        result["status"] = "completed"
        
        execution_time = time.time() - start_time
        print(f"Modal execution completed in {{execution_time:.2f}} seconds")
        
        # Ensure result is serializable
        if not isinstance(result, dict):
            result = {{"raw_result": str(result)}}
        
        # Add execution metadata
        result["_execution_metadata"] = {{
            "execution_time": execution_time,
            "app_name": "{app_name}",
            "function_name": "{function_name}",
            "timestamp": time.time()
        }}
        
        print(json.dumps(result, default=str))
        
    except Exception as e:
        error_result = {{
            "error": str(e),
            "error_type": type(e).__name__,
            "app_name": "{app_name}",
            "function_name": "{function_name}",
            "timestamp": time.time()
        }}
        print(json.dumps(error_result), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    execute_modal_function()
'''
        
        return script
    
    async def _execute_subprocess(
        self,
        script_content: str,
        timeout: int,
        attempt: int
    ) -> Dict[str, Any]:
        """Execute the subprocess with the generated script"""
        
        # Create temporary script file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            script_path = f.name
        
        try:
            # Prepare environment with Modal credentials
            env = modal_auth_service.create_auth_env()
            
            logger.debug(f"Executing subprocess (attempt {attempt}): {script_path}")
            
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                'python3', script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise Exception(f"Subprocess timed out after {timeout} seconds")
            
            # Process results
            return self._process_subprocess_result(process, stdout, stderr, attempt)
            
        finally:
            # Cleanup temporary script
            try:
                os.unlink(script_path)
            except OSError:
                pass
    
    def _process_subprocess_result(
        self,
        process: asyncio.subprocess.Process,
        stdout: bytes,
        stderr: bytes,
        attempt: int
    ) -> Dict[str, Any]:
        """Process subprocess execution results"""
        
        stdout_str = stdout.decode().strip()
        stderr_str = stderr.decode().strip()
        
        # Log subprocess output
        if stdout_str:
            logger.debug(f"Subprocess stdout (attempt {attempt}): {stdout_str}")
        if stderr_str:
            logger.warning(f"Subprocess stderr (attempt {attempt}): {stderr_str}")
        
        if process.returncode == 0:
            try:
                # Parse JSON result from stdout
                lines = stdout_str.split('\n')
                result_line = None
                
                # Find the JSON result line (usually the last line)
                for line in reversed(lines):
                    if line.strip().startswith('{'):
                        result_line = line.strip()
                        break
                
                if not result_line:
                    raise Exception("No JSON result found in subprocess output")
                
                result = json.loads(result_line)
                
                # Extract Modal call ID if available
                modal_call_id = self._extract_modal_call_id(result)
                
                return {
                    "status": "success",
                    "result": result,
                    "modal_call_id": modal_call_id,
                    "subprocess_logs": stdout_str,
                    "attempt": attempt
                }
                
            except json.JSONDecodeError as e:
                raise Exception(f"Failed to parse subprocess result as JSON: {e}")
        
        else:
            # Process failed
            error_msg = stderr_str or "Unknown subprocess error"
            
            # Try to parse error JSON from stderr
            try:
                error_result = json.loads(stderr_str)
                error_msg = error_result.get('error', error_msg)
            except (json.JSONDecodeError, AttributeError):
                pass
            
            raise Exception(f"Subprocess failed (return code {process.returncode}): {error_msg}")
    
    def _extract_modal_call_id(self, result: Dict[str, Any]) -> Optional[str]:
        """Extract Modal call ID from result for job tracking"""
        if not isinstance(result, dict):
            return None
        
        # Try common Modal call ID field names
        id_fields = ['modal_call_id', 'call_id', 'id', 'job_id']
        
        for field in id_fields:
            if field in result and result[field]:
                return str(result[field])
        
        # Check in nested metadata
        metadata = result.get('_execution_metadata', {})
        for field in id_fields:
            if field in metadata and metadata[field]:
                return str(metadata[field])
        
        logger.debug("No Modal call ID found in result")
        return None

# Global instance
modal_subprocess_runner = ModalSubprocessRunner()