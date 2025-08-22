"""
JWT Authentication for OMTX-Hub
Simple token-based authentication with user isolation
"""

import os
import jwt
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'omtx-hub-default-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

# Security scheme
security = HTTPBearer(auto_error=False)

class JWTAuth:
    """JWT Authentication handler"""
    
    @staticmethod
    def create_access_token(user_id: str, email: Optional[str] = None, role: str = "user") -> str:
        """Create JWT access token"""
        
        try:
            payload = {
                "user_id": user_id,
                "email": email,
                "role": role,
                "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
                "iat": datetime.utcnow(),
                "iss": "omtx-hub"
            }
            
            token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
            logger.info(f"✅ Created JWT token for user: {user_id}")
            return token
            
        except Exception as e:
            logger.error(f"❌ Failed to create JWT token: {e}")
            raise HTTPException(status_code=500, detail="Failed to create authentication token")
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            
            # Check if token is expired (jwt.decode already does this, but explicit check)
            exp = payload.get('exp')
            if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
                raise HTTPException(status_code=401, detail="Token has expired")
            
            logger.info(f"✅ Verified JWT token for user: {payload.get('user_id')}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("⚠️ JWT token has expired")
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"⚠️ Invalid JWT token: {e}")
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        except Exception as e:
            logger.error(f"❌ Failed to verify JWT token: {e}")
            raise HTTPException(status_code=401, detail="Authentication failed")

# Authentication dependency functions
async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Dict[str, Any]:
    """Get current authenticated user from JWT token"""
    
    if not credentials:
        # For development/testing, allow anonymous access with default user_id
        if os.getenv('ENVIRONMENT') == 'development':
            logger.warning("⚠️ No authentication provided, using anonymous user (development mode)")
            return {
                "user_id": "anonymous",
                "email": None,
                "role": "user",
                "is_anonymous": True
            }
        else:
            raise HTTPException(
                status_code=401,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"}
            )
    
    # Verify the token
    payload = JWTAuth.verify_token(credentials.credentials)
    return {
        "user_id": payload.get("user_id"),
        "email": payload.get("email"),
        "role": payload.get("role", "user"),
        "is_anonymous": False
    }

async def get_current_user_id(user: Dict[str, Any] = Depends(get_current_user)) -> str:
    """Extract user_id from authenticated user"""
    return user["user_id"]

async def require_admin_role(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Require admin role for endpoint access"""
    
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    return user

# Utility functions
def create_user_token(user_id: str, email: Optional[str] = None) -> str:
    """Create authentication token for user"""
    return JWTAuth.create_access_token(user_id, email)

def create_admin_token(user_id: str, email: Optional[str] = None) -> str:
    """Create admin authentication token"""
    return JWTAuth.create_access_token(user_id, email, role="admin")

# Development helper
def create_test_tokens() -> Dict[str, str]:
    """Create test tokens for development/testing"""
    
    if os.getenv('ENVIRONMENT') != 'development':
        raise Exception("Test tokens only available in development mode")
    
    return {
        "user_token": create_user_token("test_user", "test@omtx.ai"),
        "admin_token": create_admin_token("admin_user", "admin@omtx.ai"),
        "anonymous_fallback": "anonymous"
    }