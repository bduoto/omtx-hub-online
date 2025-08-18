#!/usr/bin/env python3
"""
Test the new GCP storage-first reconstruction function
"""

import os
import sys
import asyncio

# Add the parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_gcp_reconstruction():
    """Test the GCP storage-first reconstruction"""
    
    batch_id = "2b4036e5-d3c8-4620-9d84-47f99c7f01ca"  # trim25 batch
    
    print(f"🧪 Testing GCP storage-first reconstruction for batch {batch_id}")
    
    try:
        from api.unified_batch_api import reconstruct_enhanced_results_from_database
        
        # Test reconstruction
        result = await reconstruct_enhanced_results_from_database(
            batch_id=batch_id,
            page=1,
            page_size=50,
            progressive=True,
            include_running=True
        )
        
        print(f"✅ Reconstruction successful!")
        print(f"   Method: {result.get('method')}")
        print(f"   Total jobs: {result.get('total')}")
        print(f"   Results page: {len(result.get('individual_results', []))}")
        print(f"   Summary: {result.get('summary', {})}")
        
        # Check some individual results
        individual_results = result.get('individual_results', [])
        if individual_results:
            print(f"\n📊 Sample results:")
            for i, job in enumerate(individual_results[:5]):
                print(f"   {i+1}. {job.get('ligand_name')} - Affinity: {job.get('affinity')} - Status: {job.get('status')} - Source: {job.get('data_source')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Reconstruction failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(test_gcp_reconstruction())