#!/usr/bin/env python3
"""
Test the new file naming service
"""

import sys
sys.path.append('.')

from services.file_naming import file_naming

def test_file_naming():
    """Test different file naming scenarios"""
    
    print("🧪 Testing File Naming Service...")
    
    # Test 1: Single job
    print("\n1. Single Job:")
    single_job_data = {
        'id': 'abc123-def456',
        'name': 'Job dwDO5y68',
        'input_data': {
            'job_name': 'dwDO5y68',
            'task_type': 'protein_ligand_binding',
            'protein_sequence': 'MAELCPLAEELSCSICLEPFKEPVTTPCGHNFCGSCLNETWAVQGSPYLCPQCRAVYQAR',
            'ligand_smiles': 'CCO'
        }
    }
    
    names = file_naming.generate_job_file_names(single_job_data)
    print(f"   Generated names: {names}")
    
    # Test 2: Batch job - first ligand
    print("\n2. Batch Job - First Ligand:")
    batch_job_data = {
        'id': 'batch123-001',
        'name': 'dwDO5y68 - ligand_1',
        'input_data': {
            'job_name': 'dwDO5y68',
            'task_type': 'protein_ligand_binding',
            'protein_sequence': 'MAELCPLAEELSCSICLEPFKEPVTTPCGHNFCGSCLNETWAVQGSPYLCPQCRAVYQAR',
            'ligand_smiles': 'CNC(=O)c1cc(NC[C@@H]2C[C@H]2c2ccnn2C)cc(-c2cc(Cl)cc(Cl)c2)c1',
            'ligand_name': '1',
            'parent_batch_id': 'batch123',
            'batch_index': 0
        }
    }
    
    names = file_naming.generate_job_file_names(batch_job_data)
    print(f"   Generated names: {names}")
    
    # Test 3: Batch job with protein name - second ligand
    print("\n3. Batch Job with Protein Name - Second Ligand:")
    batch_job_with_protein = {
        'id': 'batch123-002',
        'name': 'dwDO5y68 - compound_A',
        'input_data': {
            'job_name': 'dwDO5y68',
            'protein_name': 'TRIM25',  # Explicit protein name
            'task_type': 'protein_ligand_binding',
            'protein_sequence': 'MAELCPLAEELSCSICLEPFKEPVTTPCGHNFCGSCLNETWAVQGSPYLCPQCRAVYQAR',
            'ligand_smiles': 'CC(C)C(=O)N1CCN(C(=O)C2=CC=CC=C2)CC1',
            'ligand_name': 'compound_A',
            'parent_batch_id': 'batch123',
            'batch_index': 1
        }
    }
    
    names = file_naming.generate_job_file_names(batch_job_with_protein)
    print(f"   Generated names: {names}")
    
    # Test 4: Batch job with special characters
    print("\n4. Batch Job with Special Characters:")
    special_chars_job = {
        'id': 'batch123-003',
        'name': 'Test/Job@2024 - ligand#3',
        'input_data': {
            'job_name': 'Test/Job@2024',
            'protein_name': 'TRIM-25/variant',
            'task_type': 'protein_ligand_binding',
            'ligand_name': 'ligand#3',
            'parent_batch_id': 'batch123',
            'batch_index': 2
        }
    }
    
    names = file_naming.generate_job_file_names(special_chars_job)
    print(f"   Generated names: {names}")
    
    # Test 5: Test storage paths
    print("\n5. Storage Paths:")
    job_id = "test-job-123"
    for file_type, file_name in names.items():
        storage_path = file_naming.get_storage_path(job_id, file_name)
        print(f"   {file_type}: {storage_path}")

if __name__ == "__main__":
    test_file_naming()