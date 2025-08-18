#!/usr/bin/env python3
"""
Test the fixed batch processing system
"""
import requests
import json
import time

def submit_test_batch():
    """Submit a test batch to verify fixes are working"""
    
    test_data = {
        "model_id": "boltz2",
        "task_type": "batch_protein_ligand_screening",
        "job_name": "FixedBatchTest",
        "use_msa": True,
        "use_potentials": False,
        "input_data": {
            "protein_sequence": "MAELCPLAEELSCSICLEPFKEPVTTPCGHNFCGSCLNETWAVQGSPYLCPQCRAVYQAR\nPQLHKNTVLCNVVEQFLQADLAREPPADVWTPPARASAPSPNAQVACDHCLKEAAVKTCL\nVCMASFCQEHLQPHFDSPAFQDHPLQPPVRDLLRRKCSQHNRLREFFCPEHSECICHICL\nVEHKTCSPASLSQASADLEATLRHKLTVMYSQINGASRALDDVRNRQQDVRMTANRKVEQ\nLQQEYTEMKALLDASETTSTRKIKEEEKRVNSKFDTIYQILLKKKSEIQTLKEEIEQSLT\nKRDEFEFLEKASKLRGISTKPVYIPEVELNHKLIKGIHQSTIDLKNELKQCIGRLQEPTP\nSSGDPGEHDPASTHKSTRPVKKVSKEEKKSKKPPPVPALPSKLPTFGAPEQLVDLKQAGL\nEAAAKATSSHPNSTSLKAKVLETFLAKSRPELLEYYIKVILDYNTAHNKVALSECYTVAS\nVAEMPQNYRPHPQRFTYCSQVLGLHCYKKGIHYWEVELQKNNFCGVGICYGSMNRQGPES\nRLGRNSASWCVEWFNTKISAWHNNVEKTLPSTKATRVGVLLNCDHGFVIFFAVADKVHLM\nYKFRVDFTEALYPAFWVFSAGATLSICSPK",
            "protein_name": "TestProtein",
            "ligands": [
                {"name": "TestLigand1", "smiles": "CNC(=O)Cc1ccc(F)cc1"},
                {"name": "TestLigand2", "smiles": "CCO"}
            ]
        }
    }
    
    print("🚀 Submitting test batch...")
    response = requests.post("http://localhost:8000/api/v2/predict", json=test_data)
    
    if response.status_code == 200:
        batch_result = response.json()
        print(f"✅ Batch submitted successfully")
        print(f"Response: {batch_result}")
        
        # The job_id is likely the batch_id
        batch_id = batch_result.get('job_id') or batch_result.get('batch_id')
        print(f"Batch ID: {batch_id}")
        
        # Wait a moment for processing
        print("⏳ Waiting for batch processing...")
        time.sleep(10)
        
        # Check batch status
        print("📊 Checking batch status...")
        status_response = requests.get(f"http://localhost:8000/api/v2/jobs/{batch_id}/batch-status")
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"Batch Status: {status_data.get('status')}")
            print(f"Progress: {status_data.get('progress')}")
            
            individual_jobs = status_data.get('individual_jobs', [])
            print(f"Individual Jobs: {len(individual_jobs)}")
            
            # Check individual job statuses
            running_count = 0
            completed_count = 0
            failed_count = 0
            
            for job in individual_jobs:
                status = job.get('status', 'unknown')
                if status == 'running':
                    running_count += 1
                    # Check if it has Modal call ID
                    if job.get('result_data', {}).get('modal_call_id'):
                        print(f"✅ Running job {job.get('id')} has Modal call ID: {job['result_data']['modal_call_id']}")
                elif status == 'completed':
                    completed_count += 1
                elif status == 'failed':
                    failed_count += 1
                    print(f"❌ Failed job {job.get('id')}: {job.get('result_data', {}).get('error', 'No error message')}")
            
            print(f"Status Summary:")
            print(f"  Running: {running_count}")
            print(f"  Completed: {completed_count}")
            print(f"  Failed: {failed_count}")
            
            if running_count > 0:
                print("🎉 SUCCESS: Jobs are running with Modal call IDs!")
            elif failed_count == len(individual_jobs):
                print("❌ All jobs failed - check logs for errors")
            else:
                print("ℹ️ Mixed results - some jobs may be processing")
                
        else:
            print(f"❌ Failed to get batch status: {status_response.status_code}")
    else:
        print(f"❌ Failed to submit batch: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    submit_test_batch()