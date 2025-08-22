"""
Authentication API endpoints for OMTX-Hub
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
import logging

from auth import JWTAuth, get_current_user, create_user_token, create_admin_token, create_test_tokens

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    """Login request model"""
    user_id: str = Field(..., description="User identifier")
    email: Optional[str] = Field(None, description="User email")
    password: Optional[str] = Field(None, description="Password (not implemented yet)")

class LoginResponse(BaseModel):
    """Login response model"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user_id: str = Field(..., description="User identifier")
    email: Optional[str] = Field(None, description="User email")
    expires_in: int = Field(default=86400, description="Token expiration in seconds")

class UserProfile(BaseModel):
    """User profile model"""
    user_id: str
    email: Optional[str] = None
    role: str
    is_anonymous: bool

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Simple login endpoint for development/testing
    
    In production, this would integrate with proper identity providers
    like Google OAuth, Auth0, or internal LDAP
    """
    try:
        # For development: simple user_id based authentication
        # In production: validate against identity provider
        
        if not request.user_id:
            raise HTTPException(status_code=400, detail="User ID is required")
        
        # Create JWT token
        access_token = create_user_token(request.user_id, request.email)
        
        logger.info(f"✅ User logged in: {request.user_id}")
        
        return LoginResponse(
            access_token=access_token,
            user_id=request.user_id,
            email=request.email,
            expires_in=86400  # 24 hours
        )
        
    except Exception as e:
        logger.error(f"❌ Login failed: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@router.post("/admin-login", response_model=LoginResponse)
async def admin_login(request: LoginRequest):
    """
    Admin login endpoint
    
    In production, this would have strict validation
    """
    try:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="User ID is required")
        
        # For development: simple admin token creation
        # In production: validate admin credentials properly
        
        access_token = create_admin_token(request.user_id, request.email)
        
        logger.info(f"✅ Admin logged in: {request.user_id}")
        
        return LoginResponse(
            access_token=access_token,
            user_id=request.user_id,
            email=request.email,
            expires_in=86400
        )
        
    except Exception as e:
        logger.error(f"❌ Admin login failed: {e}")
        raise HTTPException(status_code=500, detail="Admin login failed")

@router.get("/profile", response_model=UserProfile)
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Get current user profile"""
    
    return UserProfile(
        user_id=current_user["user_id"],
        email=current_user.get("email"),
        role=current_user.get("role", "user"),
        is_anonymous=current_user.get("is_anonymous", False)
    )

@router.get("/test-tokens")
async def get_test_tokens():
    """
    Get test tokens for development
    Only available in development mode
    """
    try:
        tokens = create_test_tokens()
        
        return {
            "message": "Test tokens for development use",
            "tokens": tokens,
            "usage": {
                "user_token": "Add to Authorization header: Bearer {user_token}",
                "admin_token": "Add to Authorization header: Bearer {admin_token}",
                "anonymous_fallback": "No Authorization header needed in development mode"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.post("/validate")
async def validate_token(current_user: dict = Depends(get_current_user)):
    """Validate current token and return user info"""
    
    return {
        "valid": True,
        "user": {
            "user_id": current_user["user_id"],
            "email": current_user.get("email"),
            "role": current_user.get("role", "user"),
            "is_anonymous": current_user.get("is_anonymous", False)
        }
    }