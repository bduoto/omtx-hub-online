#!/usr/bin/env python3
"""
Test Modal call to see if call IDs are being generated
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the backend directory to the Python path
sys.path.insert(0, '/Users/bryanduoto/Desktop/omtx-hub/backend')

async def test_modal_call():
    """Test modal call ID generation"""
    print("🧪 Testing Modal call ID generation...\n")
    
    try:
        # Import the function
        from test_minimal_backend import run_modal_prediction_subprocess
        
        # Test with minimal data
        print("1️⃣ Calling run_modal_prediction_subprocess...")
        result = await run_modal_prediction_subprocess(
            protein_sequences=["MKLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLQRRSRH"],  # Short test sequence
            ligands=["CCO"],  # Ethanol as test ligand
            use_msa_server=False,  # Disable MSA for faster testing
            use_potentials=False
        )
        
        print(f"2️⃣ Result received:")
        print(f"   Type: {type(result)}")
        print(f"   Keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
        
        if isinstance(result, dict):
            modal_call_id = result.get('modal_call_id')
            status = result.get('status')
            message = result.get('message')
            
            print(f"   Modal Call ID: {modal_call_id}")
            print(f"   Status: {status}")
            print(f"   Message: {message}")
            
            if modal_call_id:
                print("✅ Modal call ID generated successfully!")
                return True
            else:
                print("❌ No Modal call ID in result")
                return False
        else:
            print("❌ Result is not a dictionary")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Modal call: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    asyncio.run(test_modal_call())