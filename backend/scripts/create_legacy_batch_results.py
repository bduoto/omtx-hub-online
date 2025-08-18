#!/usr/bin/env python3
"""
Legacy Batch Results Creator

Scans individual job files for historical batches and creates parent-level 
batch_results.json files for fast API lookups.

Usage:
    python3 scripts/create_legacy_batch_results.py [batch_id]
    python3 scripts/create_legacy_batch_results.py --all  # Process all historical batches
"""

import os
import sys
import asyncio
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas.batch_results_schema import create_batch_results_from_jobs, ParentBatchResults
from services.batch_file_scanner import batch_file_scanner
from services.gcp_storage_service import gcp_storage_service
from config.gcp_database import gcp_database
from models.enhanced_job_model import JobType

async def get_all_historical_batch_ids() -> List[str]:
    """Get all historical batch IDs from database"""
    
    print(f"🔍 Scanning database for historical batch jobs...")
    
    try:
        batch_parent_query = (
            gcp_database.db.collection('jobs')
            .where('job_type', '==', JobType.BATCH_PARENT.value)
            .select(['id'])  # Only need IDs
        )
        
        batch_ids = []
        for doc in batch_parent_query.stream():
            batch_ids.append(doc.id)
        
        print(f"✅ Found {len(batch_ids)} historical batch jobs")
        return batch_ids
        
    except Exception as e:
        print(f"❌ Error scanning database: {e}")
        return []

async def create_batch_results_for_batch(batch_id: str) -> bool:
    """Create parent-level batch results for a specific batch"""
    
    print(f"\n🚀 Processing batch {batch_id}")
    
    try:
        # Check if batch_results.json already exists
        existing_path = f"batches/{batch_id}/batch_results.json"
        existing_content = gcp_storage_service.storage.download_file(existing_path)
        
        if existing_content:
            print(f"⚠️  batch_results.json already exists for {batch_id}, REGENERATING with comprehensive fields...")
            # Continue to regenerate instead of skipping
        
        # Get child jobs from database
        child_jobs_query = (
            gcp_database.db.collection('jobs')
            .where('batch_parent_id', '==', batch_id)
            .limit(2000)
        )
        
        child_jobs_docs = list(child_jobs_query.stream())
        if not child_jobs_docs:
            print(f"❌ No child jobs found for batch {batch_id}")
            return False
        
        job_ids = [doc.id for doc in child_jobs_docs]
        print(f"📊 Found {len(job_ids)} child jobs in database")
        
        # Create input data map for scanner
        input_data_map = {}
        for i, doc in enumerate(child_jobs_docs):
            job_data = doc.to_dict()
            job_id = doc.id
            input_data = job_data.get('input_data', {})
            
            input_data_map[job_id] = {
                'ligand_name': str(i + 1),  # Sequential naming: "1", "2", "3"
                'ligand_smiles': input_data.get('ligand_smiles', ''),
                'batch_index': i + 1
            }
        
        # Use BatchFileScanner to get actual results
        print(f"🔍 Scanning GCP storage for actual result files...")
        all_jobs = await batch_file_scanner.reconstruct_batch_results_simple(
            batch_id=batch_id,
            job_ids=job_ids,
            input_data_map=input_data_map
        )
        
        completed_count = len([j for j in all_jobs if j['has_results']])
        print(f"📁 Found {completed_count} jobs with actual result files")
        
        # Get batch creation time from first child job
        created_at = None
        if child_jobs_docs:
            first_job = child_jobs_docs[0].to_dict()
            if 'created_at' in first_job:
                created_at = first_job['created_at']
        
        # Create parent batch results
        parent_results = create_batch_results_from_jobs(
            batch_id=batch_id,
            job_results=all_jobs,
            created_at=created_at
        )
        
        # Save to GCP storage
        results_json = parent_results.model_dump_json(indent=2)
        upload_path = f"batches/{batch_id}/batch_results.json"
        
        success = gcp_storage_service.storage.upload_file(
            upload_path,
            results_json.encode('utf-8'),
            content_type='application/json'
        )
        
        if success:
            print(f"✅ Created batch_results.json for {batch_id}")
            print(f"   📊 Summary: {completed_count}/{len(all_jobs)} jobs completed")
            print(f"   📁 Stored at: {upload_path}")
            return True
        else:
            print(f"❌ Failed to upload batch_results.json for {batch_id}")
            return False
            
    except Exception as e:
        print(f"❌ Error processing batch {batch_id}: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main function"""
    
    parser = argparse.ArgumentParser(description='Create parent-level batch results for historical batches')
    parser.add_argument('batch_id', nargs='?', help='Specific batch ID to process')
    parser.add_argument('--all', action='store_true', help='Process all historical batches')
    parser.add_argument('--limit', type=int, default=10, help='Limit number of batches to process (default: 10)')
    
    args = parser.parse_args()
    
    if args.batch_id:
        # Process specific batch
        print(f"🎯 Processing specific batch: {args.batch_id}")
        success = await create_batch_results_for_batch(args.batch_id)
        if success:
            print(f"\n✅ Successfully processed batch {args.batch_id}")
        else:
            print(f"\n❌ Failed to process batch {args.batch_id}")
            sys.exit(1)
            
    elif args.all:
        # Process all historical batches
        print(f"🚀 Processing all historical batches (limit: {args.limit})")
        
        batch_ids = await get_all_historical_batch_ids()
        if not batch_ids:
            print("❌ No historical batches found")
            sys.exit(1)
        
        # Limit processing
        batch_ids = batch_ids[:args.limit]
        
        print(f"📋 Will process {len(batch_ids)} batches")
        
        successful = 0
        failed = 0
        
        for i, batch_id in enumerate(batch_ids, 1):
            print(f"\n📦 [{i}/{len(batch_ids)}] Processing batch {batch_id}")
            
            success = await create_batch_results_for_batch(batch_id)
            if success:
                successful += 1
            else:
                failed += 1
        
        print(f"\n📊 SUMMARY:")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📈 Success rate: {successful / len(batch_ids) * 100:.1f}%")
        
    else:
        print("❌ Please specify a batch ID or use --all flag")
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())