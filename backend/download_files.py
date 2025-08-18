#!/usr/bin/env python3
"""
Download Modal files - run from backend directory
Usage: python download_files.py job1,job2,job3 [output_dir]
"""

import os
import sys
import json
import asyncio
import tempfile
from pathlib import Path
from database.unified_job_manager import unified_job_manager

async def download_job_files(job_ids, output_dir="./downloads"):
    """Download files for specified job IDs"""
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"📥 Starting download for {len(job_ids)} jobs...")
    
    # Get job info from database
    jobs_info = {}
    for job_id in job_ids:
        job = await unified_job_manager.get_job(job_id)
        if job:
            jobs_info[job_id] = job
            print(f"✅ Found job: {job_id} ({job.get('task_type', 'unknown')})")
        else:
            print(f"❌ Job not found: {job_id}")
    
    if not jobs_info:
        print("No valid jobs found!")
        return
    
    # Setup Modal auth
    modal_config_path = os.path.expanduser("~/.modal.toml")
    modal_token_id = None
    modal_token_secret = None
    
    if os.path.exists(modal_config_path):
        try:
            import toml
            with open(modal_config_path, 'r') as f:
                config = toml.load(f)
                for profile_name, profile_data in config.items():
                    if profile_data.get('active', False):
                        modal_token_id = profile_data.get('token_id')
                        modal_token_secret = profile_data.get('token_secret')
                        break
        except Exception as e:
            print(f"Warning: Could not read Modal config: {e}")
    
    # Download files for each job
    success_count = 0
    for job_id, job_info in jobs_info.items():
        modal_call_id = job_info.get('modal_call_id')
        task_type = job_info.get('task_type', '')
        
        if not modal_call_id:
            print(f"⚠️  No Modal call ID for job {job_id}")
            continue
        
        # Determine app name
        if 'boltz' in task_type.lower() or 'protein' in task_type.lower():
            app_name = 'omtx-hub-boltz2-persistent'
        elif 'chai' in task_type.lower():
            app_name = 'omtx-hub-chai1'
        elif 'antibody' in task_type.lower() or 'nanobody' in task_type.lower():
            app_name = 'rfantibody-real-phase2'
        else:
            print(f"⚠️  Unknown task type for job {job_id}: {task_type}")
            continue
        
        print(f"📡 Downloading {job_id} from {app_name}...")
        
        # Create download script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            download_script = f"""
import modal
import json
import sys
import os

try:
    # Set Modal credentials
    if "{modal_token_id}" and "{modal_token_secret}":
        os.environ['MODAL_TOKEN_ID'] = "{modal_token_id}"
        os.environ['MODAL_TOKEN_SECRET'] = "{modal_token_secret}"
    
    # Get call result
    call = modal.FunctionCall.from_id("{modal_call_id}")
    
    if not call.finished:
        print(json.dumps({{"error": "Call not finished", "status": "running"}}))
        sys.exit(0)
    
    result = call.get()
    
    # Extract files
    files = {{}}
    
    if isinstance(result, dict):
        # Structure file content
        if 'structure_file_content' in result and result['structure_file_content']:
            files['structure.pdb'] = result['structure_file_content']
        
        # Base64 files
        if 'structure_file_base64' in result and result['structure_file_base64']:
            import base64
            try:
                decoded = base64.b64decode(result['structure_file_base64'])
                files['structure_base64.pdb'] = decoded.decode('utf-8')
            except:
                pass
        
        # Multiple structure files
        if 'structure_files' in result and isinstance(result['structure_files'], dict):
            files.update(result['structure_files'])
        
        # All structures array
        if 'all_structures' in result and isinstance(result['all_structures'], list):
            for i, struct in enumerate(result['all_structures']):
                if isinstance(struct, dict) and 'content' in struct:
                    filename = struct.get('filename', f'structure_{{i}}.pdb')
                    files[filename] = struct['content']
    
    print(json.dumps({{
        "status": "success",
        "files": files,
        "job_id": "{job_id}",
        "modal_call_id": "{modal_call_id}"
    }}))
    
except Exception as e:
    print(json.dumps({{"error": str(e)}}), file=sys.stderr)
    sys.exit(1)
"""
            f.write(download_script)
            script_path = f.name
        
        try:
            # Run download script
            env = os.environ.copy()
            if modal_token_id and modal_token_secret:
                env['MODAL_TOKEN_ID'] = modal_token_id
                env['MODAL_TOKEN_SECRET'] = modal_token_secret
            
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
                        job_dir = output_path / job_id
                        job_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Save files
                        for filename, content in files.items():
                            file_path = job_dir / filename
                            with open(file_path, 'w') as f:
                                f.write(content)
                            print(f"  💾 {file_path}")
                        
                        # Save metadata
                        metadata = {
                            'job_id': job_id,
                            'task_type': task_type,
                            'modal_call_id': modal_call_id,
                            'app_name': app_name,
                            'files': list(files.keys())
                        }
                        
                        with open(job_dir / 'metadata.json', 'w') as f:
                            json.dump(metadata, f, indent=2)
                        
                        success_count += 1
                        print(f"✅ Downloaded {len(files)} files for {job_id}")
                    else:
                        print(f"⚠️  No files found for {job_id}")
                else:
                    print(f"❌ Download failed for {job_id}: {result}")
            else:
                print(f"❌ Script failed for {job_id}: {stderr.decode()}")
                
        except Exception as e:
            print(f"❌ Error downloading {job_id}: {e}")
        finally:
            os.unlink(script_path)
    
    print(f"\n🎉 Successfully downloaded files for {success_count}/{len(jobs_info)} jobs")
    print(f"📁 Files saved to: {output_path.absolute()}")

async def main():
    if len(sys.argv) < 2:
        print("Usage: python download_files.py job1,job2,job3 [output_dir]")
        sys.exit(1)
    
    job_ids = [job.strip() for job in sys.argv[1].split(',')]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./downloads"
    
    await download_job_files(job_ids, output_dir)

if __name__ == "__main__":
    asyncio.run(main())