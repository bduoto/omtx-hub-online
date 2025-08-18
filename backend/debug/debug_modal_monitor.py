#!/usr/bin/env python3
"""
Debug script to manually test Modal monitor processing
"""
import asyncio
import os
import json

# Set Modal auth
os.environ['MODAL_TOKEN_ID'] = 'ak-4gwOEVs4hEAwy27Lf7b1Tz'
os.environ['MODAL_TOKEN_SECRET'] = 'as-cauu6z3bil26giQmKgXdyQ'

from services.modal_monitor import modal_monitor

async def debug_modal_processing():
    """Test Modal monitor processing manually"""
    
    print("🔍 Debugging Modal monitor processing...")
    
    # Get a job with Modal call ID that should be completed
    modal_call_id = "fc-01K1JVQAQ134Y4W01CEVK6B2FF"  # From our earlier check
    
    print(f"🔍 Testing Modal call: {modal_call_id}")
    
    try:
        # Test getting Modal result directly
        modal_result = await modal_monitor.get_modal_result(modal_call_id)
        print(f"✅ Modal result: {modal_result['status']}")
        
        if modal_result['status'] == 'completed':
            print("🎉 Modal job completed successfully!")
            result_data = modal_result['result']
            print(f"   Affinity: {result_data.get('affinity', 'N/A')}")
            print(f"   Confidence: {result_data.get('confidence', 'N/A')}")
            print(f"   Has structure: {bool(result_data.get('structure_file_base64'))}")
            
            # Test GCP storage
            from services.gcp_storage_service import gcp_storage_service
            job_id = "pdbIISgRLAAU3eAgGld7"  # The job that has this Modal call ID
            
            print(f"🗂️ Testing GCP storage for job: {job_id}")
            success = await gcp_storage_service.store_job_results(
                job_id, result_data, 'protein_ligand_binding'
            )
            print(f"GCP storage result: {'✅ Success' if success else '❌ Failed'}")
            
        elif modal_result['status'] == 'running':
            print("⏳ Modal job still running...")
        else:
            print(f"❌ Modal job failed: {modal_result.get('error')}")
            
    except Exception as e:
        print(f"❌ Error testing Modal: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_modal_processing())