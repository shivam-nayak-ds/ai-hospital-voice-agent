"""
auth.py
-------
JWT token creation and verification for ASHA Hospital Agent.
Handles access tokens (short-lived) and refresh tokens (long-lived).
"""

import time
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.utils.logger import custom_logger as logger
from config.settings import settings

# ─── JWT Configuration ─────────────────────────────────────────────────────────
JWT_SECRET = settings.JWT_SECRET
JWT_ALGORITHM = "HS256"

# Token lifetimes
ACCESS_TOKEN_EXPIRE_MINUTES = 15    # Short-lived for security
REFRESH_TOKEN_EXPIRE_DAYS = 7       # Long-lived for convenience

# Role-based access
ROLES = ["patient", "doctor", "admin"]

# ─── Token Creation ───────────────────────────────────────────────────────────

def create_access_token(user_id: str, role: str = "patient") -> str:
    """
    Creates a short-lived JWT access token.
    Used for authenticating API requests.
    """
    now = time.time()
    payload = {
        "sub": user_id,           # Subject (user ID)
        "role": role,             # User role (patient/doctor/admin)
        "iat": int(now),          # Issued at
        "exp": int(now + ACCESS_TOKEN_EXPIRE_MINUTES * 60),  # Expiration
        "type": "access"          # Token type
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    logger.info(f"Access token created for user {user_id} (role: {role})")
    return token


def create_refresh_token(user_id: str) -> str:
    """
    Creates a long-lived JWT refresh token.
    Used to obtain new access tokens without re-login.
    """
    now = time.time()
    payload = {
        "sub": user_id,
        "iat": int(now),
        "exp": int(now + REFRESH_TOKEN_EXPIRE_DAYS * 86400),
        "type": "refresh"
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    logger.info(f"Refresh token created for user {user_id}")
    return token


def verify_token(token: str) -> Optional[dict]:
    """
    Verifies a JWT token's signature and expiration.
    Returns the payload dict if valid, None if invalid/expired.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None


# ─── FastAPI Dependency ───────────────────────────────────────────────────────
# Use this as a dependency to protect routes: Depends(get_current_user)

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> dict:
    """
    FastAPI dependency that extracts and validates the JWT from Authorization header.
    Raises 401 if token is missing, invalid, or expired.
    
    Usage in routes:
        @router.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            # user = {"sub": "user_id", "role": "patient", ...}
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type — access token required"
        )
    
    return payload


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """
    FastAPI dependency that requires admin role.
    Usage: async def admin_route(user: dict = Depends(require_admin)):
    """
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


async def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> Optional[dict]:
    """
    FastAPI dependency for optional authentication.
    Returns user dict if token is valid, None if no token provided.
    Useful for routes that work with or without auth.
    """
    if not credentials:
        return None
    
    payload = verify_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        return None
    
    return payload
