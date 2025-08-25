#!/bin/bash
# Integration test script

echo "🧪 TESTING OMTX-HUB INTEGRATION"
echo "================================"
echo ""

# Test backend health
echo "1️⃣ Testing Backend Health..."
curl -s http://localhost:8000/health | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'   ✅ Backend: {d[\"status\"]}')" || echo "   ❌ Backend not responding"
echo ""

# Test jobs endpoint
echo "2️⃣ Testing Jobs Endpoint..."
curl -s "http://localhost:8000/api/v1/jobs?user_id=current_user&limit=200" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'   ✅ Jobs API: {len(d.get(\"jobs\", []))} jobs returned')" || echo "   ❌ Jobs endpoint error"
echo ""

# Test batch prediction
echo "3️⃣ Testing Batch Prediction..."
BATCH_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/predict/batch \
  -H "Content-Type: application/json" \
  -d '{
    "model": "boltz2",
    "batch_name": "integration_test",
    "protein_sequence": "MKWVTFISLLFSSAYS",
    "ligands": [
      {"smiles": "CCO", "name": "ethanol"},
      {"smiles": "CC(=O)O", "name": "acetic_acid"}
    ]
  }')

echo "$BATCH_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'   ✅ Batch API: {d[\"batch_id\"]} created with {d[\"total_jobs\"]} jobs')" || echo "   ❌ Batch endpoint error"
echo ""

# Test single prediction
echo "4️⃣ Testing Single Prediction..."
PRED_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "model": "boltz2",
    "protein_sequence": "MKWVTFISLLFSSAYS",
    "ligand_smiles": "CCO",
    "job_name": "test_prediction"
  }')

echo "$PRED_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'   ✅ Predict API: {d[\"job_id\"]} - {d[\"status\"]}')" || echo "   ❌ Predict endpoint error"
echo ""

# Test GPU worker health
echo "5️⃣ Testing GPU Worker..."
curl -s https://boltz2-production-v2-zhye5az7za-uc.a.run.app/health | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'   ✅ GPU Worker: {d[\"status\"]} (GPU: {d[\"gpu_available\"]})')" || echo "   ❌ GPU worker not responding"
echo ""

echo "================================"
echo "✅ INTEGRATION TEST COMPLETE"
echo "================================"
echo ""
echo "Frontend URL: http://localhost:5173"
echo "Backend URL: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Try these in your browser:"
echo "1. Open http://localhost:5173"
echo "2. Submit a protein-ligand prediction"
echo "3. Check 'My Results' page"