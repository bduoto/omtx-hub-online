#!/usr/bin/env python3
"""
Test Modal subprocess generation and execution
"""

import asyncio
import sys
import os
sys.path.append('.')

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from test_minimal_backend import run_modal_prediction_subprocess

async def test_modal_subprocess():
    """Test Modal subprocess execution"""
    
    print("🧪 Testing Modal subprocess execution...")
    
    # Test with simple protein-ligand prediction
    test_protein_sequences = ["MTEST"]
    test_ligands = ["CCO"]  # Ethanol
    
    try:
        print("\n📞 Calling run_modal_prediction_subprocess...")
        result = await run_modal_prediction_subprocess(
            protein_sequences=test_protein_sequences,
            ligands=test_ligands,
            use_msa_server=True,
            use_potentials=False
        )
        
        print(f"✅ Subprocess completed successfully!")
        print(f"Result keys: {list(result.keys()) if result else 'None'}")
        
        if result:
            print(f"Status: {result.get('status', 'unknown')}")
            print(f"Modal call ID: {result.get('modal_call_id', 'none')}")
            print(f"Message: {result.get('message', 'none')}")
            
            if result.get('modal_call_id'):
                print(f"\n🎯 Modal call ID generated successfully: {result['modal_call_id']}")
                return True
            else:
                print(f"\n❌ No Modal call ID in result")
                return False
        else:
            print(f"\n❌ No result returned")
            return False
            
    except Exception as e:
        print(f"\n❌ Subprocess failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_modal_subprocess())
    if success:
        print("\n🎉 Modal subprocess is working correctly!")
    else:
        print("\n💥 Modal subprocess needs fixing!")