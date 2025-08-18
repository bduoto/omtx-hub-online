#!/usr/bin/env python3
"""
Test MSA parameter passing to Modal
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the backend directory to the Python path
sys.path.insert(0, '/Users/bryanduoto/Desktop/omtx-hub/backend')

async def test_msa_parameter():
    """Test MSA parameter passing"""
    print("🧪 Testing MSA parameter passing...\n")
    
    try:
        from test_minimal_backend import run_modal_prediction_subprocess
        
        # Test 1: Explicit use_msa_server=True
        print("1️⃣ Testing with use_msa_server=True...")
        result1 = await run_modal_prediction_subprocess(
            protein_sequences=["MKFLVNVALVFMVVYISYIYA"],
            ligands=["CCO"],
            use_msa_server=True,  # Explicit True
            use_potentials=False
        )
        print(f"   Result: {result1}")
        
        # Test 2: Explicit use_msa_server=False (should fail on Modal)
        print("\n2️⃣ Testing with use_msa_server=False...")
        result2 = await run_modal_prediction_subprocess(
            protein_sequences=["MKFLVNVALVFMVVYISYIYA"],
            ligands=["CCO"],
            use_msa_server=False,  # Explicit False
            use_potentials=False
        )
        print(f"   Result: {result2}")
        
        # Test 3: Default parameter (should be True)
        print("\n3️⃣ Testing with default parameter...")
        result3 = await run_modal_prediction_subprocess(
            protein_sequences=["MKFLVNVALVFMVVYISYIYA"],
            ligands=["CCO"]
            # use_msa_server not specified, should default to True
        )
        print(f"   Result: {result3}")
        
        # Check Modal call IDs
        print(f"\n📊 Modal Call IDs:")
        print(f"   Test 1 (True): {result1.get('modal_call_id', 'NONE')}")
        print(f"   Test 2 (False): {result2.get('modal_call_id', 'NONE')}")
        print(f"   Test 3 (Default): {result3.get('modal_call_id', 'NONE')}")
        
        # All should have Modal call IDs since they're async spawns
        # The difference will be in the Modal execution (True should work, False should fail)
        
        print(f"\n💡 Analysis:")
        print("All tests should generate Modal call IDs (async spawn).")
        print("The difference is in Modal execution:")
        print("- use_msa_server=True: Should succeed")
        print("- use_msa_server=False: Should fail with MSA error")
        print("- Default: Should succeed (defaults to True)")
        
    except Exception as e:
        print(f"❌ Error testing MSA parameter: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_msa_parameter())