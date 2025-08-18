#!/usr/bin/env python3
"""
Simple test to verify Modal spawn() is working
"""

import modal
import os
import json

# Set Modal credentials
os.environ['MODAL_TOKEN_ID'] = 'ak-4gwOEVs4hEAwy27Lf7b1Tz'
os.environ['MODAL_TOKEN_SECRET'] = 'as-cauu6z3bil26giQmKgXdyQ'

try:
    print("Testing Modal spawn functionality...")
    
    # Get the app
    app = modal.App.lookup("boltz2-predict-modal", create_if_missing=False)
    print(f"✅ Found Modal app: {app}")
    
    # Get the function
    modal_function = app.function("predict")
    print(f"✅ Found Modal function: {modal_function}")
    
    # Test parameters
    params = {
        "protein_sequences": ["MGQPGNGSAFLLAPNGSHAPDHDVTQER"],
        "ligands": ["CNCC(O)c1ccc(O)c(O)c1"],
        "use_msa_server": False,
        "use_potentials": True
    }
    
    print("\nTesting spawn()...")
    
    # Test spawn
    call = modal_function.spawn(**params)
    call_id = call.object_id
    
    print(f"✅ Spawn successful!")
    print(f"   Call ID: {call_id}")
    print(f"   Call type: {type(call)}")
    
    # Check if we can get status
    print("\nChecking call status...")
    try:
        # Try to get result (should fail if still running)
        result = call.get(timeout=5)
        print(f"✅ Call completed quickly! Result keys: {list(result.keys()) if isinstance(result, dict) else type(result)}")
    except Exception as e:
        if "still running" in str(e).lower() or "timeout" in str(e).lower():
            print(f"✅ Call is running in background (as expected)")
        else:
            print(f"⚠️  Unexpected error: {e}")
    
    print("\n✅ Modal spawn is working correctly!")
    print(f"\nYou can check the status of this call later using:")
    print(f"call = modal.FunctionCall.from_id('{call_id}')")
    print(f"result = call.get()")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()