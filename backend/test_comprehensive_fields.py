#!/usr/bin/env python3
"""
Test comprehensive field extraction in parent-level batch results
"""

import os
import sys
import asyncio
import json

# Add the backend directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_comprehensive_fields():
    """Test comprehensive field extraction in parent-level batch results"""
    
    batch_id = "2b4036e5-d3c8-4620-9d84-47f99c7f01ca"
    
    print(f"🔍 Testing comprehensive fields for batch {batch_id}")
    
    try:
        from api.unified_batch_api import get_enhanced_batch_results
        
        result = await get_enhanced_batch_results(
            batch_id=batch_id,
            include_raw_modal=True,
            format="json",
            page=1,
            page_size=100,  # Get more results to find completed ones
            summary_only=False,
            progressive=True,
            include_running=True
        )
        
        individual_results = result.get('individual_results', [])
        print(f"\n✅ API RESULT: Found {len(individual_results)} individual results")
        
        # Find first job with results
        completed_job = None
        for job in individual_results:
            if job.get('affinity') and job.get('affinity') != 0:
                completed_job = job
                break
        
        if completed_job:
            print(f"\n📊 COMPREHENSIVE FIELDS FOR COMPLETED JOB {completed_job['job_id'][:8]}:")
            print(f"   Status: {completed_job.get('status')}")
            print(f"   Ligand Name: {completed_job.get('ligand_name')}")
            print(f"   Ligand SMILES: {completed_job.get('ligand_smiles')}")
            print(f"   Affinity: {completed_job.get('affinity')}")
            print(f"   Confidence: {completed_job.get('confidence')}")
            print(f"   Affinity Prob: {completed_job.get('affinity_prob')}")
            print(f"   Ens. Affinity: {completed_job.get('ens_affinity')}")
            print(f"   Ens. Prob: {completed_job.get('ens_prob')}")
            print(f"   Ens. Aff 2: {completed_job.get('ens_aff_2')}")
            print(f"   Ens. Prob 2: {completed_job.get('ens_prob_2')}")
            print(f"   Ens. Aff 1: {completed_job.get('ens_aff_1')}")
            print(f"   Ens. Prob 1: {completed_job.get('ens_prob_1')}")
            print(f"   iPTM: {completed_job.get('iptm_score')}")
            print(f"   Ligand iPTM: {completed_job.get('ligand_iptm')}")
            print(f"   Complex ipLDDT: {completed_job.get('complex_iplddt')}")
            print(f"   Complex iPDE: {completed_job.get('complex_ipde')}")
            print(f"   Complex pLDDT: {completed_job.get('complex_plddt')}")
            print(f"   PTM: {completed_job.get('ptm_score')}")
            print(f"   pLDDT (legacy): {completed_job.get('plddt_score')}")
            print(f"   Has Structure: {completed_job.get('has_structure')}")
            
            # Check which fields have non-null values
            comprehensive_fields = [
                'affinity_prob', 'ens_affinity', 'ens_prob', 'ens_aff_2', 'ens_prob_2', 
                'ens_aff_1', 'ens_prob_1', 'iptm_score', 'ligand_iptm', 'complex_iplddt', 
                'complex_ipde', 'complex_plddt', 'ptm_score', 'plddt_score'
            ]
            
            populated_fields = []
            null_fields = []
            
            for field in comprehensive_fields:
                value = completed_job.get(field)
                if value is not None and value != 0:
                    populated_fields.append(field)
                else:
                    null_fields.append(field)
            
            print(f"\n📈 FIELD ANALYSIS:")
            print(f"   ✅ Populated fields ({len(populated_fields)}): {', '.join(populated_fields)}")
            print(f"   ❌ Null/zero fields ({len(null_fields)}): {', '.join(null_fields)}")
            
        else:
            print(f"❌ No completed jobs found with actual result data")
            
            # Show status distribution 
            status_counts = {}
            for job in individual_results:
                status = job.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            print(f"📊 Status distribution: {status_counts}")
        
        return True
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_comprehensive_fields())