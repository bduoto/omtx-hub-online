#!/usr/bin/env python3
"""
Compare direct reconstruction function output vs API output
"""

import os
import sys
import asyncio
import requests
import json

# Add the parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def compare_outputs():
    """Compare reconstruction function vs API output"""
    
    batch_id = "2b4036e5-d3c8-4620-9d84-47f99c7f01ca"
    
    print(f"🔍 Comparing reconstruction function vs API output for batch {batch_id}")
    
    # 1. Call reconstruction function directly
    try:
        from api.unified_batch_api import reconstruct_enhanced_results_from_database
        
        direct_result = await reconstruct_enhanced_results_from_database(
            batch_id=batch_id,
            page=1,
            page_size=5,
            progressive=True,
            include_running=True
        )
        
        print(f"\n📋 DIRECT RECONSTRUCTION RESULT:")
        print(f"   Method: {direct_result.get('method')}")
        print(f"   Total: {direct_result.get('total')}")
        print(f"   Individual results count: {len(direct_result.get('individual_results', []))}")
        
        # Check first result
        individual_results = direct_result.get('individual_results', [])
        if individual_results:
            first_result = individual_results[0]
            print(f"   First result affinity: {first_result.get('affinity')}")
            print(f"   First result confidence: {first_result.get('confidence')}")
            print(f"   First result data_source: {first_result.get('data_source')}")
        
    except Exception as e:
        print(f"❌ Direct reconstruction failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 2. Call API endpoint
    try:
        api_response = requests.get(f"http://localhost:8000/api/v3/batches/{batch_id}/enhanced-results?page=1&page_size=5")
        
        if api_response.status_code == 200:
            api_data = api_response.json()
            
            print(f"\n🌐 API ENDPOINT RESULT:")
            api_individual = api_data.get('individual_results', [])
            print(f"   Individual results count: {len(api_individual)}")
            
            if api_individual:
                first_api_result = api_individual[0]
                print(f"   First result affinity: {first_api_result.get('affinity')}")
                print(f"   First result confidence: {first_api_result.get('confidence')}")
                print(f"   First result data_source: {first_api_result.get('data_source')}")
                
            # Check for method field
            print(f"   API method: {api_data.get('method', 'NOT FOUND')}")
            
        else:
            print(f"❌ API call failed: {api_response.status_code}")
            print(f"   Response: {api_response.text}")
            
    except Exception as e:
        print(f"❌ API call failed: {e}")
    
    print(f"\n🔍 COMPARISON:")
    if individual_results and api_individual:
        direct_affinity = individual_results[0].get('affinity', 0)
        api_affinity = api_individual[0].get('affinity', 0)
        
        print(f"   Direct reconstruction affinity: {direct_affinity}")
        print(f"   API endpoint affinity: {api_affinity}")
        print(f"   Values match: {direct_affinity == api_affinity}")

if __name__ == "__main__":
    asyncio.run(compare_outputs())