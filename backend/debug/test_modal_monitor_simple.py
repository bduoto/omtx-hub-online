#!/usr/bin/env python3
"""
Simple test of modal monitor execution
"""

import os
import modal

# Set Modal credentials
os.environ['MODAL_TOKEN_ID'] = 'ak-4gwOEVs4hEAwy27Lf7b1Tz'
os.environ['MODAL_TOKEN_SECRET'] = 'as-cauu6z3bil26giQmKgXdyQ'

def test_modal_call_retrieval():
    """Test retrieving a Modal call result"""
    
    print("Testing Modal call result retrieval...")
    
    # Let's test if we can call the Modal function and get results
    try:
        # Get a recently created job with a Modal call ID
        # You'll need to replace this with an actual call ID from your logs
        
        print("\n1. Testing Modal app access...")
        app = modal.App.lookup("omtx-hub-boltz2-persistent", create_if_missing=False)
        print(f"✅ Found Modal app: {app}")
        
        # Try to list recent function calls to see if any completed
        print("\n2. Checking for recent Modal calls...")
        
        # If you have a recent call ID from the logs, you can test it like this:
        # call_id = "fc-xyz123"  # Replace with actual call ID from logs
        # call = modal.FunctionCall.from_id(call_id)
        # try:
        #     result = call.get(timeout=5)
        #     print(f"✅ Call completed! Result keys: {list(result.keys())}")
        # except Exception as e:
        #     if "still running" in str(e).lower():
        #         print("✅ Call still running (as expected)")
        #     else:
        #         print(f"❌ Call error: {e}")
        
        print("✅ Modal access working")
        
    except Exception as e:
        print(f"❌ Modal access error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_modal_call_retrieval()