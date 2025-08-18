#!/bin/bash

# OMTX-Hub Backend Startup Script
# Activates virtual environment and starts the FastAPI server with post-processing enabled

echo "🚀 Starting OMTX-Hub Backend with Post-Processing..."

# Change to backend directory
cd "$(dirname "$0")"

# Activate virtual environment
echo "📦 Activating virtual environment..."
source .venv/bin/activate

# Check if post-processing dependencies are installed
echo "🔬 Checking post-processing dependencies..."
python -c "
try:
    import MDAnalysis
    import sklearn
    import rdkit
    import numba
    print('✅ All post-processing dependencies available')
    print(f'   MDAnalysis: {MDAnalysis.__version__}')
    print(f'   scikit-learn: {sklearn.__version__}')
    print(f'   RDKit: {rdkit.__version__}')
    print(f'   Numba: {numba.__version__}')
except ImportError as e:
    print(f'⚠️  Missing dependency: {e}')
    print('   System will fall back to mock data')
"

echo ""
echo "🌟 Starting FastAPI server..."
echo "📊 Dashboard will use real scientific analysis from Boltz-2 structures"
echo "🧬 Features enabled:"
echo "   • Real protein-ligand contact analysis"
echo "   • Binding mode clustering (Classical/Allosteric/Novel)"
echo "   • Chemical scaffold diversity analysis"
echo "   • Hotspot residue identification"
echo ""

# Start the FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

echo "🛑 Backend stopped"