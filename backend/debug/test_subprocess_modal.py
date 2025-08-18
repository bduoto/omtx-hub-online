#!/usr/bin/env python3
"""
Test the subprocess modal execution directly
"""

import asyncio
import json
from services.modal_subprocess_runner import modal_subprocess_runner

async def test_subprocess():
    """Test subprocess modal execution"""
    
    print("Testing Modal subprocess execution...")
    
    # Test parameters
    parameters = {
        "protein_sequences": ["MGQPGNGSAFLLAPNGSHAPDHDVTQER"],
        "ligands": ["CNCC(O)c1ccc(O)c(O)c1"],
        "use_msa_server": False,
        "use_potentials": True
    }
    
    try:
        result = await modal_subprocess_runner.execute_modal_function(
            app_name="omtx-hub-boltz2-persistent",
            function_name="boltz2_predict_modal",
            parameters=parameters,
            timeout=60
        )
        
        print("✅ Subprocess execution successful!")
        print(f"   Status: {result.get('status')}")
        print(f"   Modal Call ID: {result.get('modal_call_id')}")
        print(f"   Keys: {list(result.keys())}")
        
    except Exception as e:
        print(f"❌ Subprocess execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_subprocess())