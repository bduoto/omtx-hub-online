#!/usr/bin/env python3
"""
Modal File Downloader for OMTX-Hub
Downloads .cif/.pdb files from Modal persistent volumes for completed prediction jobs.

Usage:
    python download_modal_files.py --jobs job1,job2,job3 --output-dir ./downloads
    python download_modal_files.py --all-completed --output-dir ./downloads
"""

import os
import json
import asyncio
import argparse
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModalFileDownloader:
    """Download files from Modal persistent volumes"""
    
    def __init__(self):
        self.modal_apps = {
            'boltz2': 'omtx-hub-boltz2-persistent',
            'chai1': 'omtx-hub-chai1', 
            'rfantibody': 'rfantibody-real-phase2'
        }
        self.setup_modal_auth()
    
    def setup_modal_auth(self):
        """Load Modal authentication credentials"""
        modal_config_path = os.path.expanduser("~/.modal.toml")
        
        if os.path.exists(modal_config_path):
            try:
                import toml
                with open(modal_config_path, 'r') as f:
                    config = toml.load(f)
                    # Find active profile
                    for profile_name, profile_data in config.items():
                        if profile_data.get('active', False):
                            os.environ['MODAL_TOKEN_ID'] = profile_data.get('token_id', '')
                            os.environ['MODAL_TOKEN_SECRET'] = profile_data.get('token_secret', '')
                            logger.info(f"Loaded Modal credentials from profile: {profile_name}")
                            return
                logger.warning("No active Modal profile found")
            except Exception as e:
                logger.error(f"Failed to read Modal config: {e}")
        else:
            logger.warning("Modal config file not found")
    
    async def get_job_info(self, job_ids: List[str]) -> Dict[str, Dict]:
        """Get job information from local database"""
        job_info = {}
        
        # Create subprocess to query database without auth conflicts
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            query_script = f"""
import sys
import os
# Add backend directory to path
backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
if os.path.exists(backend_path):
    sys.path.insert(0, backend_path)
else:
    # Try current directory if we're already in backend
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
import json
from database.unified_job_manager import unified_job_manager

async def get_jobs():
    try:
        jobs = {{}}
        for job_id in {job_ids}:
            job = await unified_job_manager.get_job(job_id)
            if job:
                jobs[job_id] = {{
                    'task_type': job.get('task_type', ''),
                    'status': job.get('status', ''),
                    'modal_call_id': job.get('modal_call_id', ''),
                    'modal_function': job.get('modal_function', ''),
                    'created_at': str(job.get('created_at', '')),
                    'result': job.get('result', {{}})
                }}
        print(json.dumps(jobs, default=str))
    except Exception as e:
        print(json.dumps({{"error": str(e)}}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(get_jobs())
"""
            f.write(query_script)
            script_path = f.name
        
        try:
            process = await asyncio.create_subprocess_exec(
                'python3', script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                job_info = json.loads(stdout.decode())
                logger.info(f"Retrieved info for {len(job_info)} jobs")
            else:
                logger.error(f"Failed to query jobs: {stderr.decode()}")
                
        except Exception as e:
            logger.error(f"Error querying job database: {e}")
        finally:
            os.unlink(script_path)
        
        return job_info
    
    async def download_job_files(self, job_id: str, job_info: Dict, output_dir: Path) -> bool:
        """Download files for a specific job"""
        logger.info(f"Downloading files for job: {job_id}")
        
        task_type = job_info.get('task_type', '')
        modal_call_id = job_info.get('modal_call_id', '')
        
        if not modal_call_id:
            logger.warning(f"No Modal call ID found for job {job_id}")
            return False
        
        # Determine app name based on task type
        app_name = None
        if 'boltz' in task_type.lower() or 'protein' in task_type.lower():
            app_name = self.modal_apps['boltz2']
        elif 'chai' in task_type.lower():
            app_name = self.modal_apps['chai1']
        elif 'antibody' in task_type.lower() or 'nanobody' in task_type.lower():
            app_name = self.modal_apps['rfantibody']
        
        if not app_name:
            logger.warning(f"Cannot determine Modal app for task type: {task_type}")
            return False
        
        # Create download script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            download_script = f"""
import modal
import json
import sys
import os
from pathlib import Path

def download_files():
    try:
        # Set Modal credentials
        if os.environ.get('MODAL_TOKEN_ID') and os.environ.get('MODAL_TOKEN_SECRET'):
            pass  # Already set
        
        # Connect to Modal app
        app = modal.App.lookup("{app_name}")
        
        # Get call object
        call = modal.FunctionCall.from_id("{modal_call_id}")
        
        # Check if call is completed
        if not call.finished:
            print(json.dumps({{"error": "Call not finished yet", "status": "running"}}))
            return
        
        # Get call result
        try:
            result = call.get()
            
            # Look for structure files in the result
            structure_files = {{}}
            
            # Check different possible file fields
            if isinstance(result, dict):
                # Look for structure file content
                if 'structure_file_content' in result and result['structure_file_content']:
                    structure_files['structure.pdb'] = result['structure_file_content']
                
                # Look for base64 encoded files
                if 'structure_file_base64' in result and result['structure_file_base64']:
                    import base64
                    try:
                        decoded = base64.b64decode(result['structure_file_base64'])
                        structure_files['structure_base64.pdb'] = decoded.decode('utf-8')
                    except Exception as e:
                        print(f"Warning: Could not decode base64 structure: {{e}}", file=sys.stderr)
                
                # Look for multiple structure files
                if 'structure_files' in result and isinstance(result['structure_files'], dict):
                    structure_files.update(result['structure_files'])
                
                # Look for all_structures array
                if 'all_structures' in result and isinstance(result['all_structures'], list):
                    for i, struct in enumerate(result['all_structures']):
                        if isinstance(struct, dict) and 'content' in struct:
                            filename = struct.get('filename', f'structure_{{i}}.pdb')
                            structure_files[filename] = struct['content']
            
            print(json.dumps({{
                "status": "success",
                "files": structure_files,
                "result_keys": list(result.keys()) if isinstance(result, dict) else []
            }}))
            
        except Exception as e:
            print(json.dumps({{"error": f"Failed to get call result: {{str(e)}}"}}), file=sys.stderr)
            
    except Exception as e:
        print(json.dumps({{"error": str(e)}}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    download_files()
"""
            f.write(download_script)
            script_path = f.name
        
        try:
            # Set up environment
            env = os.environ.copy()
            
            process = await asyncio.create_subprocess_exec(
                'python3', script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                result = json.loads(stdout.decode())
                
                if result.get('status') == 'success':
                    files = result.get('files', {})
                    
                    if files:
                        # Create job directory
                        job_dir = output_dir / job_id
                        job_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Save files
                        for filename, content in files.items():
                            file_path = job_dir / filename
                            with open(file_path, 'w') as f:
                                f.write(content)
                            logger.info(f"Saved: {file_path}")
                        
                        # Save metadata
                        metadata = {
                            'job_id': job_id,
                            'task_type': task_type,
                            'modal_call_id': modal_call_id,
                            'app_name': app_name,
                            'downloaded_files': list(files.keys()),
                            'result_keys': result.get('result_keys', [])
                        }
                        
                        metadata_path = job_dir / 'metadata.json'
                        with open(metadata_path, 'w') as f:
                            json.dump(metadata, f, indent=2)
                        
                        logger.info(f"Downloaded {len(files)} files for job {job_id}")
                        return True
                    else:
                        logger.warning(f"No files found for job {job_id}")
                        logger.info(f"Available result keys: {result.get('result_keys', [])}")
                else:
                    logger.error(f"Download failed for job {job_id}: {result}")
            else:
                logger.error(f"Download script failed for job {job_id}: {stderr.decode()}")
                
        except Exception as e:
            logger.error(f"Error downloading files for job {job_id}: {e}")
        finally:
            os.unlink(script_path)
        
        return False
    
    async def download_files(self, job_ids: List[str], output_dir: str) -> None:
        """Download files for multiple jobs"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Starting download for {len(job_ids)} jobs to {output_path}")
        
        # Get job information
        job_info = await self.get_job_info(job_ids)
        
        if not job_info:
            logger.error("No job information found")
            return
        
        # Download files for each job
        success_count = 0
        for job_id in job_ids:
            if job_id in job_info:
                if await self.download_job_files(job_id, job_info[job_id], output_path):
                    success_count += 1
            else:
                logger.warning(f"Job not found: {job_id}")
        
        logger.info(f"Successfully downloaded files for {success_count}/{len(job_ids)} jobs")

async def main():
    parser = argparse.ArgumentParser(description="Download files from Modal persistent volumes")
    parser.add_argument("--jobs", type=str, help="Comma-separated list of job IDs")
    parser.add_argument("--all-completed", action="store_true", help="Download all completed jobs")
    parser.add_argument("--output-dir", type=str, default="./modal_downloads", help="Output directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    downloader = ModalFileDownloader()
    
    if args.jobs:
        job_ids = [job.strip() for job in args.jobs.split(',')]
        await downloader.download_files(job_ids, args.output_dir)
    elif args.all_completed:
        logger.error("--all-completed not implemented yet. Please specify --jobs")
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())