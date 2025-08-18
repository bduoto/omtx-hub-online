"""
Modal Prediction Adapters
Model-specific adapters for different Modal prediction services
"""

from .boltz2_adapter import Boltz2Adapter
from .rfantibody_adapter import RFAntibodyAdapter
from .chai1_adapter import Chai1Adapter

__all__ = ['Boltz2Adapter', 'RFAntibodyAdapter', 'Chai1Adapter']