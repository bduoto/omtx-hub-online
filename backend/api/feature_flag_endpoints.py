"""
Feature Flag API Endpoints
Provides feature flag status to frontend
"""

import logging
from fastapi import APIRouter, Query
from typing import Dict, Any

from config.feature_flags import feature_flags, get_client_flags

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/features", tags=["feature_flags"])

@router.get("/flags")
async def get_feature_flags(
    user_id: str = Query("current_user", description="User ID for rollout checks")
) -> Dict[str, Any]:
    """
    Get feature flags for the current user
    Returns only client-safe flags
    """
    
    flags = get_client_flags(user_id)
    
    return {
        "user_id": user_id,
        "flags": flags,
        "api_version": "v3" if flags.get('use_v3_api') else "v2"
    }

@router.get("/all-flags")
async def get_all_feature_flags() -> Dict[str, Any]:
    """
    Get all feature flags (admin endpoint)
    In production, this should be protected
    """
    
    return {
        "flags": feature_flags.get_all_flags(),
        "environment": "development"  # Should come from config
    }