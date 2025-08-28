#!/bin/bash

# Test protein-ligand prediction via API
curl -X POST "https://omtx-hub-backend-338254269321.us-central1.run.app/api/v1/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "boltz2",
    "protein_sequence": "MVLSEGEWQLVLHVWAKVEADVAGHGQDILIRLFKSHPETLEKFDRFKHLKTEAEMKASEDLKKHGVTVLTALGAILKKKGHHEAELKPLAQSHATKHKIPIKYLEFISEAIIHVLHSRHPGNFGADAQGAMNKALELFRKDIAAKYKELGYQG",
    "ligand_smiles": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O",
    "job_name": "Test Ibuprofen Binding",
    "user_id": "omtx_deployment_user",
    "parameters": {}
  }' | jq '.'

