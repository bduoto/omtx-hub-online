#!/bin/bash
# Entrypoint script for Boltz-2 GPU Worker
# Supports both HTTP service and job execution modes

set -e

echo "🚀 Starting Boltz-2 GPU Worker"
echo "=============================="
echo "Mode detection:"

# Check if we're running as a Cloud Run Job (has job parameters)
if [ -n "$JOB_ID" ] && [ -n "$PROTEIN_SEQUENCE" ] && [ -n "$LIGAND_SMILES" ]; then
    echo "📋 Cloud Run Job mode detected"
    echo "   Job ID: $JOB_ID"
    echo "   Protein length: ${#PROTEIN_SEQUENCE}"
    echo "   Ligand: ${LIGAND_NAME:-unknown} ($LIGAND_SMILES)"
    echo ""
    echo "🔬 Running prediction job..."
    exec python3 job_main.py
    
else
    echo "🌐 HTTP Service mode detected"
    echo "   Port: ${PORT:-8080}"
    echo ""
    echo "🏃 Starting Flask service with Gunicorn..."
    exec gunicorn \
        --bind "0.0.0.0:${PORT:-8080}" \
        --workers 1 \
        --threads 4 \
        --timeout 300 \
        --worker-class sync \
        --access-logfile - \
        --error-logfile - \
        simple_main:app
fi