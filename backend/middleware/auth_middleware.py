"""
Authentication Middleware - Multi-tenant authentication with external service integration
Distinguished Engineer Implementation - Production-ready with multiple auth methods
"""

import os
import jwt
import logging
import aiohttp
from typing import Dict, Optional
from datetime import datetime, timedelta

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.cloud import firestore

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

class AuthMiddleware:
    """Enterprise authentication middleware with multiple auth methods"""
    
    def __init__(self):
        self.db = firestore.Client()
        
        # Configuration from environment
        self.jwt_secret = os.getenv("JWT_SECRET")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.external_auth_url = os.getenv("AUTH_SERVICE_URL")
        self.api_key_enabled = os.getenv("API_KEY_AUTH_ENABLED", "true").lower() == "true"
        
        # Cache for API keys (in production, use Redis)
        self.api_key_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        logger.info("🔐 AuthMiddleware initialized with multi-method authentication")
    
    async def verify_jwt_token(self, token: str) -> Dict[str, str]:
        """Verify JWT token from external auth service"""
        
        try:
            # Method 1: Local JWT verification (if secret provided)
            if self.jwt_secret:
                payload = jwt.decode(
                    token,
                    self.jwt_secret,
                    algorithms=[self.jwt_algorithm]
                )
                
                # Extract standard JWT claims
                user_id = payload.get("sub")  # Standard JWT subject claim
                email = payload.get("email")
                tier = payload.get("tier", "free")
                
                if not user_id:
                    raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
                
                return {
                    "user_id": user_id,
                    "email": email,
                    "tier": tier,
                    "auth_method": "jwt_local"
                }
            
            # Method 2: External auth service verification
            elif self.external_auth_url:
                return await self._verify_external_token(token)
            
            else:
                raise HTTPException(status_code=500, detail="No authentication method configured")
                
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"❌ JWT verification failed: {str(e)}")
            raise HTTPException(status_code=401, detail="Authentication failed")
    
    async def _verify_external_token(self, token: str) -> Dict[str, str]:
        """Verify token with external authentication service"""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.external_auth_url}/verify",
                    json={"token": token},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        return {
                            "user_id": data["user_id"],
                            "email": data.get("email"),
                            "tier": data.get("tier", "free"),
                            "auth_method": "external_service"
                        }
                    elif response.status == 401:
                        raise HTTPException(status_code=401, detail="Invalid token")
                    else:
                        raise HTTPException(status_code=503, detail="Authentication service unavailable")
                        
        except aiohttp.ClientError as e:
            logger.error(f"❌ External auth service error: {str(e)}")
            raise HTTPException(status_code=503, detail="Authentication service unavailable")
    
    async def verify_api_key(self, api_key: str) -> Dict[str, str]:
        """Verify API key with caching"""
        
        if not self.api_key_enabled:
            raise HTTPException(status_code=401, detail="API key authentication disabled")
        
        # Check cache first
        cache_key = f"api_key:{api_key}"
        if cache_key in self.api_key_cache:
            cached_data, cached_time = self.api_key_cache[cache_key]
            if datetime.utcnow() - cached_time < timedelta(seconds=self.cache_ttl):
                return cached_data
        
        try:
            # Look up API key in Firestore
            api_keys_ref = self.db.collection('api_keys')
            query = api_keys_ref.where('key_hash', '==', self._hash_api_key(api_key)).limit(1)
            
            results = list(query.stream())
            
            if not results:
                raise HTTPException(status_code=401, detail="Invalid API key")
            
            key_data = results[0].to_dict()
            
            # Check if key is active
            if not key_data.get('active', False):
                raise HTTPException(status_code=401, detail="API key inactive")
            
            # Check expiration
            if key_data.get('expires_at') and key_data['expires_at'] < datetime.utcnow():
                raise HTTPException(status_code=401, detail="API key expired")
            
            # Update last used
            results[0].reference.update({
                'last_used': firestore.SERVER_TIMESTAMP,
                'usage_count': firestore.Increment(1)
            })
            
            user_data = {
                "user_id": key_data['user_id'],
                "email": key_data.get('email'),
                "tier": key_data.get('tier', 'free'),
                "auth_method": "api_key",
                "api_key_name": key_data.get('name', 'unnamed')
            }
            
            # Cache the result
            self.api_key_cache[cache_key] = (user_data, datetime.utcnow())
            
            return user_data
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ API key verification failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Authentication error")
    
    async def verify_session_cookie(self, session_id: str) -> Dict[str, str]:
        """Verify session cookie from main application"""
        
        try:
            # Look up session in Firestore
            session_ref = self.db.collection('sessions').document(session_id)
            session_doc = session_ref.get()
            
            if not session_doc.exists:
                raise HTTPException(status_code=401, detail="Invalid session")
            
            session_data = session_doc.to_dict()
            
            # Check if session is expired
            if session_data.get('expires_at') and session_data['expires_at'] < datetime.utcnow():
                raise HTTPException(status_code=401, detail="Session expired")
            
            # Update last accessed
            session_ref.update({
                'last_accessed': firestore.SERVER_TIMESTAMP
            })
            
            return {
                "user_id": session_data['user_id'],
                "email": session_data.get('email'),
                "tier": session_data.get('tier', 'free'),
                "auth_method": "session_cookie"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Session verification failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Authentication error")
    
    async def get_current_user(self, request: Request) -> Dict[str, str]:
        """Extract and validate user from request - supports multiple auth methods"""
        
        # Method 1: JWT Bearer token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            user_data = await self.verify_jwt_token(token)
            
            # Ensure user exists in our system
            await self._ensure_user_exists(user_data)
            return user_data
        
        # Method 2: API Key
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            user_data = await self.verify_api_key(api_key)
            await self._ensure_user_exists(user_data)
            return user_data
        
        # Method 3: Session cookie (from main app)
        session_id = request.cookies.get("session_id", "")
        if session_id:
            user_data = await self.verify_session_cookie(session_id)
            await self._ensure_user_exists(user_data)
            return user_data
        
        # Method 4: Development mode (if enabled)
        if os.getenv("DEVELOPMENT_MODE", "false").lower() == "true":
            dev_user_id = request.headers.get("X-Dev-User-ID")
            if dev_user_id:
                logger.warning(f"🚧 Development mode: Using user {dev_user_id}")
                return {
                    "user_id": dev_user_id,
                    "email": f"{dev_user_id}@dev.local",
                    "tier": "pro",
                    "auth_method": "development"
                }
        
        raise HTTPException(status_code=401, detail="No valid authentication provided")
    
    async def _ensure_user_exists(self, user_data: Dict[str, str]):
        """Ensure user document exists in Firestore"""
        
        user_id = user_data["user_id"]
        user_ref = self.db.collection('users').document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            # Create user document
            user_document = {
                'user_id': user_id,
                'email': user_data.get('email'),
                'tier': user_data.get('tier', 'free'),
                'created_at': firestore.SERVER_TIMESTAMP,
                'last_active': firestore.SERVER_TIMESTAMP,
                'settings': {
                    'notifications_enabled': True,
                    'webhook_url': None,
                    'webhook_secret': None
                },
                'auth_methods': [user_data.get('auth_method', 'unknown')]
            }
            
            user_ref.set(user_document)
            logger.info(f"✅ Created user document for {user_id}")
        else:
            # Update last active
            user_ref.update({
                'last_active': firestore.SERVER_TIMESTAMP
            })
    
    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for secure storage lookup"""
        import hashlib
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    async def create_api_key(self, user_id: str, name: str, expires_days: Optional[int] = None) -> str:
        """Create new API key for user"""
        
        import secrets
        
        # Generate secure API key
        api_key = f"omtx_{secrets.token_urlsafe(32)}"
        key_hash = self._hash_api_key(api_key)
        
        # Calculate expiration
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        # Store in Firestore
        api_key_doc = {
            'key_hash': key_hash,
            'user_id': user_id,
            'name': name,
            'active': True,
            'created_at': firestore.SERVER_TIMESTAMP,
            'expires_at': expires_at,
            'last_used': None,
            'usage_count': 0
        }
        
        self.db.collection('api_keys').add(api_key_doc)
        
        logger.info(f"✅ Created API key '{name}' for user {user_id}")
        
        return api_key

# Global auth instance
auth = AuthMiddleware()

# FastAPI dependency
async def get_current_user(request: Request) -> Dict[str, str]:
    """FastAPI dependency for user authentication"""
    return await auth.get_current_user(request)

# Optional dependency (doesn't raise error if no auth)
async def get_current_user_optional(request: Request) -> Optional[Dict[str, str]]:
    """Optional FastAPI dependency for user authentication"""
    try:
        return await auth.get_current_user(request)
    except HTTPException:
        return None
