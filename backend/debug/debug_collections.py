#!/usr/bin/env python3
"""
Debug Firestore Collections to understand data structure
"""

import os
from dotenv import load_dotenv
load_dotenv()

try:
    from database.gcp_job_manager import gcp_job_manager
    from config.gcp_database import gcp_database
    
    print("🔍 Debugging Firestore Collections")
    print("=" * 50)
    
    if not gcp_database.available:
        print("❌ GCP Database not available")
        exit(1)
    
    # List all collections
    print("\n📁 Available Collections:")
    collections = gcp_database.db.collections()
    collection_names = []
    for col in collections:
        collection_names.append(col.id)
        print(f"   📂 {col.id}")
    
    # Check each collection
    for collection_name in collection_names:
        print(f"\n🔍 Collection: {collection_name}")
        
        try:
            # Get first few documents
            docs = gcp_database.db.collection(collection_name).limit(3).stream()
            doc_count = 0
            
            for doc in docs:
                doc_count += 1
                data = doc.to_dict()
                print(f"   📄 Doc {doc_count} (ID: {doc.id}):")
                
                # Show key fields
                key_fields = ['id', 'name', 'type', 'task_type', 'status', 'user_id', 'created_at', 'job_id', 'job_name']
                for field in key_fields:
                    if field in data:
                        value = data[field]
                        if isinstance(value, str) and len(value) > 50:
                            value = value[:50] + "..."
                        print(f"     {field}: {value}")
                
                print(f"     Total fields: {len(data.keys())}")
                print(f"     All keys: {list(data.keys())}")
                print()
                
                if doc_count >= 2:  # Show max 2 docs per collection
                    break
            
            if doc_count == 0:
                print("   📭 Collection is empty")
                
        except Exception as e:
            print(f"   ❌ Error reading collection {collection_name}: {e}")
    
    # Test specific queries
    print(f"\n🔍 Testing Specific Queries:")
    
    # Query 1: Recent jobs from jobs collection
    try:
        recent_jobs = gcp_job_manager.get_recent_jobs(limit=3)
        print(f"   📊 get_recent_jobs(): {len(recent_jobs)} jobs")
        for i, job in enumerate(recent_jobs[:2]):
            print(f"     Job {i+1}: {job.get('name', 'No name')} ({job.get('status', 'No status')})")
    except Exception as e:
        print(f"   ❌ get_recent_jobs() failed: {e}")
    
    # Query 2: User job results from my_results collection  
    try:
        user_results = gcp_job_manager.get_user_job_results(limit=3)
        print(f"   📊 get_user_job_results(): {len(user_results)} results")
        for i, result in enumerate(user_results[:2]):
            print(f"     Result {i+1}: {result.get('job_name', 'No name')} ({result.get('status', 'No status')})")
    except Exception as e:
        print(f"   ❌ get_user_job_results() failed: {e}")
    
    # Query 3: User jobs with new method
    try:
        user_jobs = gcp_job_manager.get_user_jobs("current_user", limit=3)
        print(f"   📊 get_user_jobs(): {len(user_jobs)} jobs")
        for i, job in enumerate(user_jobs[:2]):
            print(f"     User Job {i+1}: {job.get('name', 'No name')} ({job.get('status', 'No status')})")
    except Exception as e:
        print(f"   ❌ get_user_jobs() failed: {e}")
    
    print(f"\n💡 RECOMMENDATIONS:")
    if 'jobs' in collection_names and 'my_results' in collection_names:
        print("   📊 Both 'jobs' and 'my_results' collections exist")
        print("   🔄 Enhanced endpoints should query BOTH collections or unify data")
        print("   🎯 Legacy endpoints use 'my_results', enhanced use 'jobs'")
    elif 'my_results' in collection_names:
        print("   📊 Only 'my_results' collection found")
        print("   🔄 Enhanced endpoints should query 'my_results' collection")
    elif 'jobs' in collection_names:
        print("   📊 Only 'jobs' collection found") 
        print("   🔄 Legacy endpoints should query 'jobs' collection")
    
except Exception as e:
    print(f"❌ Failed to debug collections: {e}")
    import traceback
    traceback.print_exc()