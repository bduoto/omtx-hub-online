#!/usr/bin/env python3
"""
Test batch screening by calling the handler directly
"""

import sys
import asyncio
import json
sys.path.append('.')

from tasks.task_handlers import task_handler_registry, TaskType

async def test_batch_handler():
    """Test batch handler directly"""
    
    print("🔍 TESTING BATCH HANDLER DIRECTLY")
    print("=" * 50)
    
    # Test data
    input_data = {
        "protein_name": "Carbonic Anhydrase II",
        "protein_sequence": "MKTAYIAKQRQISFVKSHFSRQ",
        "ligands": [
            {"name": "Ligand1", "smiles": "CC(=O)Oc1ccccc1C(=O)O"},
            {"name": "Ligand2", "smiles": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"}
        ],
        "use_msa": True,
        "use_potentials": False
    }
    
    print("📋 Input data:")
    print(json.dumps(input_data, indent=2))
    
    # Test schema validation first
    from schemas.task_schemas import task_schema_registry
    
    print("\n🔍 Testing schema validation...")
    validation_data = input_data.copy()
    validation_data['job_name'] = "TestBatch123"
    
    validation_result = task_schema_registry.validate_input(
        TaskType.BATCH_PROTEIN_LIGAND_SCREENING.value,
        validation_data
    )
    
    print(f"📊 Validation result: {validation_result}")
    
    if not validation_result["valid"]:
        print(f"❌ VALIDATION FAILED: {validation_result['errors']}")
        
        # Check what the schema expects
        schema = task_schema_registry.get_schema(TaskType.BATCH_PROTEIN_LIGAND_SCREENING.value)
        if schema:
            print("\n📋 Expected fields:")
            for field in schema.input_fields:
                print(f"  - {field.id} ({field.field_type.value}): {field.label}")
                if field.validation:
                    for rule in field.validation:
                        print(f"    └─ {rule.rule_type}: {rule.message}")
    else:
        print("✅ Validation passed!")
        
        # Now test the handler
        print("\n🔍 Testing handler...")
        try:
            result = await task_handler_registry.process_task(
                task_type=TaskType.BATCH_PROTEIN_LIGAND_SCREENING.value,
                input_data=input_data,
                job_name="TestBatch123",
                job_id="test-job-123",
                use_msa=True,
                use_potentials=False
            )
            
            print(f"✅ Handler result: {json.dumps(result, indent=2)}")
        except Exception as e:
            print(f"❌ Handler error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_batch_handler())