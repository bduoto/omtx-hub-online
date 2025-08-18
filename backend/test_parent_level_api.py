#!/usr/bin/env python3
"""
Test parent-level batch results API directly
"""

import os
import sys
import asyncio
import json

# Add the backend directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_parent_level_api():
    """Test the parent-level batch results API directly"""
    
    batch_id = "2b4036e5-d3c8-4620-9d84-47f99c7f01ca"
    
    print(f"🔍 Testing parent-level API for batch {batch_id}")
    
    try:
        from api.unified_batch_api import get_enhanced_batch_results
        
        result = await get_enhanced_batch_results(
            batch_id=batch_id,
            include_raw_modal=True,
            format="json",
            page=1,
            page_size=5,
            summary_only=False,
            progressive=True,
            include_running=True
        )
        
        print(f"\n✅ API RESULT:")
        print(f"   Data source: {result.get('data_source')}")
        print(f"   Total results: {result.get('pagination', {}).get('total_results')}")
        print(f"   Individual results count: {len(result.get('individual_results', []))}")
        print(f"   Batch statistics: {result.get('batch_statistics', {})}")
        
        # Check first result
        individual_results = result.get('individual_results', [])
        if individual_results:
            first_result = individual_results[0]
            print(f"   First result job_id: {first_result.get('job_id')}")
            print(f"   First result ligand_name: {first_result.get('ligand_name')}")
            print(f"   First result affinity: {first_result.get('affinity')}")
            print(f"   First result confidence: {first_result.get('confidence')}")
        
        return True
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_parent_level_api())