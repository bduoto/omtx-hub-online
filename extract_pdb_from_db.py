#!/usr/bin/env python3
"""
Extract .pdb files from database job results
"""

import os
import json
import asyncio
from pathlib import Path
import base64
import argparse

# Add backend to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database.unified_job_manager import unified_job_manager

async def extract_pdb_files(job_ids=None, output_dir="./extracted_pdbs", limit=10):
    """Extract PDB files from job results in database"""
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get jobs
    if job_ids:
        jobs = []
        for job_id in job_ids:
            job = await unified_job_manager.get_job(job_id)
            if job:
                jobs.append(job)
    else:
        # Get recent completed jobs
        all_jobs = await unified_job_manager.get_all_jobs(limit=limit)
        jobs = [job for job in all_jobs if job.get('status') == 'completed']
    
    print(f"📊 Found {len(jobs)} jobs to process")
    
    extracted_count = 0
    for job in jobs:
        job_id = job.get('job_id', 'unknown')
        result = job.get('result', {})
        
        if not isinstance(result, dict):
            continue
        
        # Create job directory
        job_dir = output_path / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        
        files_found = False
        
        # 1. Check structure_file_content
        if result.get('structure_file_content'):
            file_path = job_dir / 'structure.pdb'
            with open(file_path, 'w') as f:
                f.write(result['structure_file_content'])
            print(f"✅ Extracted: {file_path}")
            files_found = True
        
        # 2. Check structure_file_base64
        if result.get('structure_file_base64'):
            try:
                decoded = base64.b64decode(result['structure_file_base64'])
                file_path = job_dir / 'structure_base64.pdb'
                with open(file_path, 'wb') as f:
                    f.write(decoded)
                print(f"✅ Extracted: {file_path}")
                files_found = True
            except Exception as e:
                print(f"⚠️  Failed to decode base64 for {job_id}: {e}")
        
        # 3. Check structure_files dictionary
        if result.get('structure_files') and isinstance(result['structure_files'], dict):
            for filename, content in result['structure_files'].items():
                file_path = job_dir / filename
                with open(file_path, 'w') as f:
                    f.write(content)
                print(f"✅ Extracted: {file_path}")
                files_found = True
        
        # 4. Check all_structures array
        if result.get('all_structures') and isinstance(result['all_structures'], list):
            for i, struct in enumerate(result['all_structures']):
                if isinstance(struct, dict) and struct.get('content'):
                    filename = struct.get('filename', f'structure_{i}.pdb')
                    file_path = job_dir / filename
                    with open(file_path, 'w') as f:
                        f.write(struct['content'])
                    print(f"✅ Extracted: {file_path}")
                    files_found = True
        
        if files_found:
            # Save metadata
            metadata = {
                'job_id': job_id,
                'task_type': job.get('task_type', ''),
                'status': job.get('status', ''),
                'created_at': str(job.get('created_at', '')),
                'job_name': job.get('job_name', ''),
                'affinity': result.get('affinity', ''),
                'confidence': result.get('confidence', '')
            }
            
            with open(job_dir / 'metadata.json', 'w') as f:
                json.dump(metadata, f, indent=2)
            
            extracted_count += 1
        else:
            # Remove empty directory
            job_dir.rmdir()
    
    print(f"\n🎉 Extracted PDB files from {extracted_count}/{len(jobs)} jobs")
    print(f"📁 Files saved to: {output_path.absolute()}")

async def show_job_structure_info():
    """Show information about structure storage in jobs"""
    
    print("📊 Analyzing structure storage in recent jobs...")
    
    jobs = await unified_job_manager.get_all_jobs(limit=20)
    
    structure_stats = {
        'total_jobs': len(jobs),
        'completed_jobs': 0,
        'jobs_with_structures': 0,
        'storage_methods': {
            'structure_file_content': 0,
            'structure_file_base64': 0,
            'structure_files': 0,
            'all_structures': 0
        }
    }
    
    for job in jobs:
        if job.get('status') == 'completed':
            structure_stats['completed_jobs'] += 1
            
            result = job.get('result', {})
            if isinstance(result, dict):
                has_structure = False
                
                if result.get('structure_file_content'):
                    structure_stats['storage_methods']['structure_file_content'] += 1
                    has_structure = True
                
                if result.get('structure_file_base64'):
                    structure_stats['storage_methods']['structure_file_base64'] += 1
                    has_structure = True
                
                if result.get('structure_files'):
                    structure_stats['storage_methods']['structure_files'] += 1
                    has_structure = True
                
                if result.get('all_structures'):
                    structure_stats['storage_methods']['all_structures'] += 1
                    has_structure = True
                
                if has_structure:
                    structure_stats['jobs_with_structures'] += 1
    
    print(json.dumps(structure_stats, indent=2))
    
    print("\n💡 Summary:")
    print(f"- {structure_stats['jobs_with_structures']}/{structure_stats['completed_jobs']} completed jobs have structure files")
    print(f"- Most common storage: {max(structure_stats['storage_methods'], key=structure_stats['storage_methods'].get)}")

async def main():
    parser = argparse.ArgumentParser(description="Extract PDB files from database")
    parser.add_argument("job_ids", nargs="*", help="Specific job IDs to extract")
    parser.add_argument("--output-dir", default="./extracted_pdbs", help="Output directory")
    parser.add_argument("--limit", type=int, default=10, help="Limit for recent jobs")
    parser.add_argument("--info", action="store_true", help="Show structure storage info")
    
    args = parser.parse_args()
    
    if args.info:
        await show_job_structure_info()
    else:
        await extract_pdb_files(
            job_ids=args.job_ids if args.job_ids else None,
            output_dir=args.output_dir,
            limit=args.limit
        )

if __name__ == "__main__":
    asyncio.run(main())