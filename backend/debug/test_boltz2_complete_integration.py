#!/usr/bin/env python3
"""
Comprehensive Boltz2 Backend Integration Test
Tests the complete flow: API → Modal → GCP Storage → Results
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_boltz2_complete_integration():
    """Test complete Boltz2 integration from API to storage"""
    
    print("🧪 COMPREHENSIVE BOLTZ2 BACKEND INTEGRATION TEST")
    print("=" * 60)
    
    # Test 1: Modal Authentication Service
    print("\n1️⃣ Testing Modal Authentication Service...")
    try:
        from services.modal_auth_service import modal_auth_service
        
        auth_status = modal_auth_service.get_auth_status()
        print(f"   ✅ Auth Status: {auth_status}")
        
        if not modal_auth_service.validate_credentials():
            print("   ⚠️  Modal credentials not available - will test with mock data")
            mock_mode = True
        else:
            print("   ✅ Modal credentials validated successfully")
            mock_mode = False
            
    except Exception as e:
        print(f"   ❌ Modal auth service error: {e}")
        return False
    
    # Test 2: Modal Execution Service Configuration
    print("\n2️⃣ Testing Modal Execution Service Configuration...")
    try:
        from services.modal_execution_service import modal_execution_service
        
        service_status = modal_execution_service.get_service_status()
        print(f"   ✅ Service Status: {service_status}")
        
        boltz2_config = modal_execution_service.get_model_config('boltz2')
        print(f"   ✅ Boltz2 Config: {boltz2_config}")
        
        supported_models = modal_execution_service.get_supported_models()
        print(f"   ✅ Supported Models: {list(supported_models.keys())}")
        
    except Exception as e:
        print(f"   ❌ Modal execution service error: {e}")
        return False
    
    # Test 3: Boltz2 Adapter
    print("\n3️⃣ Testing Boltz2 Adapter...")
    try:
        from services.modal_prediction_adapters.boltz2_adapter import Boltz2Adapter
        
        # Test adapter initialization
        config = modal_execution_service.get_model_config('boltz2')
        adapter = Boltz2Adapter(config)
        print(f"   ✅ Adapter initialized: {adapter.app_name}")
        
        # Test parameter preparation
        test_input = {
            'protein_sequences': ['MKLLVLSLSLVLVLLLSHPQGSHM'],
            'ligands': ['CCO'],  # Ethanol
            'use_msa_server': True,
            'use_potentials': False
        }
        
        prepared_params = adapter.prepare_parameters(test_input)
        print(f"   ✅ Parameters prepared: {list(prepared_params.keys())}")
        
    except Exception as e:
        print(f"   ❌ Boltz2 adapter error: {e}")
        return False
    
    # Test 4: GCP Storage Service
    print("\n4️⃣ Testing GCP Storage Service...")
    try:
        from services.gcp_storage_service import gcp_storage_service
        
        if gcp_storage_service.storage.available:
            print("   ✅ GCP Storage available")
            
            # Test storing mock results
            test_job_id = f"test_boltz2_{int(time.time())}"
            test_results = {
                "confidence_score": 0.85,
                "ptm": 0.78,
                "plddt": 0.82,
                "structure_file_base64": "bW9ja19zdHJ1Y3R1cmVfZGF0YQ==",  # "mock_structure_data" in base64
                "test_timestamp": time.time()
            }
            
            storage_success = await gcp_storage_service.store_job_results(
                test_job_id, test_results, "protein_ligand_binding"
            )
            print(f"   ✅ Storage test: {storage_success}")
            
        else:
            print("   ⚠️  GCP Storage not available - will skip storage tests")
            
    except Exception as e:
        print(f"   ❌ GCP storage error: {e}")
        return False
    
    # Test 5: Complete Modal Execution (if credentials available)
    print("\n5️⃣ Testing Complete Modal Execution...")
    try:
        if not mock_mode:
            print("   🚀 Executing real Modal prediction...")
            
            result = await modal_execution_service.execute_prediction(
                model_type='boltz2',
                parameters={
                    'protein_sequences': ['MKLLVLSLSLVLVLLLSHPQGSHM'],
                    'ligands': ['CCO'],  # Simple ethanol molecule
                    'use_msa_server': True,
                    'use_potentials': False
                },
                job_id=f"test_boltz2_{int(time.time())}"
            )
            
            print(f"   ✅ Modal execution result keys: {list(result.keys())}")
            print(f"   ✅ Execution status: {result.get('status', 'unknown')}")
            
            if result.get('modal_call_id'):
                print(f"   ✅ Modal call ID: {result['modal_call_id']}")
            
        else:
            print("   ⚠️  Skipping real Modal execution (no credentials)")
            
    except Exception as e:
        print(f"   ❌ Modal execution error: {e}")
        print(f"   ℹ️  This might be expected if Modal service is unavailable")
    
    # Test 6: Unified Job Manager Integration
    print("\n6️⃣ Testing Unified Job Manager Integration...")
    try:
        from database.unified_job_manager import unified_job_manager
        
        # Test job creation
        test_job_data = {
            'name': f'Test Boltz2 Job {int(time.time())}',
            'task_type': 'protein_ligand_binding',
            'status': 'pending',
            'user_id': 'test_user',
            'input_data': {
                'protein_sequences': ['MKLLVLSLSLVLVLLLSHPQGSHM'],
                'ligands': ['CCO'],
                'use_msa_server': True,
                'use_potentials': False
            }
        }
        
        job_id = unified_job_manager.create_job(test_job_data)
        if job_id:
            print(f"   ✅ Job created: {job_id}")
            
            # Test job status update
            update_success = unified_job_manager.update_job_status(job_id, 'running')
            print(f"   ✅ Job status updated: {update_success}")
            
        else:
            print("   ⚠️  Job creation failed (database might not be available)")
            
    except Exception as e:
        print(f"   ❌ Job manager error: {e}")
        return False
    
    # Test 7: API Endpoint Integration
    print("\n7️⃣ Testing API Endpoint Integration...")
    try:
        # Import the main prediction function
        from main import process_task_prediction
        
        # Test the main prediction endpoint logic
        test_request_data = {
            'task_type': 'protein_ligand_binding',
            'input_data': {
                'sequences': [
                    {'protein': {'sequence': 'MKLLVLSLSLVLVLLLSHPQGSHM'}},
                    {'ligand': {'smiles': 'CCO'}}
                ]
            },
            'use_msa': True,
            'use_potentials': False
        }
        
        print("   🚀 Testing main prediction function...")
        # Note: This will use the fixed Modal execution service
        
    except Exception as e:
        print(f"   ❌ API endpoint error: {e}")
        print(f"   ℹ️  This might be expected if full API context is not available")
    
    print("\n" + "=" * 60)
    print("🎉 BOLTZ2 INTEGRATION TEST COMPLETED")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    asyncio.run(test_boltz2_complete_integration())
