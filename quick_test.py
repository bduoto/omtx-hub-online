import requests
import time
import json

# Submit a test job
response = requests.post(
    "https://omtx-hub-backend-338254269321.us-central1.run.app/api/v1/predict",
    json={
        "model": "boltz2",
        "protein_sequence": "MVLSEGEWQLVLHVWAKVEADVAGHGQDILIRLFKSHPETLEKFDRFKHLKTEAEMKASEDLKKHGVTVLTALGAILKKKGHHEAELKPLAQSHATKHKIPIKYLEFISEAIIHVLHSRHPGNFGADAQGAMNKALELFRKDIAAKYKELGYQG",
        "ligand_smiles": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O",
        "job_name": "Quick Test",
        "user_id": "omtx_deployment_user"
    }
)

result = response.json()
print(f"Job submitted: {result['job_id']}")
print(f"Initial status: {result['status']}")

# Wait and check status
time.sleep(30)

status_response = requests.get(
    f"https://omtx-hub-backend-338254269321.us-central1.run.app/api/v1/jobs/{result['job_id']}"
)
status = status_response.json()
print(f"\nJob status after 30 seconds:")
print(json.dumps(status, indent=2))
