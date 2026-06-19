"""
auth.py (routes)
----------------
Authentication endpoints for ASHA Hospital Agent.
Handles OTP-based login and JWT token refresh.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Optional
from src.core.auth import (
    create_access_token,
    create_refresh_token,
    verify_token,
    get_current_user
)
from src.utils.logger import custom_logger as logger

router = APIRouter(prefix="/api/auth", tags=["Auth"])


# ─── Request/Response Schemas ─────────────────────────────────────────────────

class LoginRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=10, description="10-digit phone number")
    otp: str = Field(..., min_length=4, max_length=4, description="4-digit OTP code")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes in seconds
    user_id: str
    role: str = "patient"


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenOnlyResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 900


# ─── OTP Store (In production: use Redis with TTL) ────────────────────────────
# For demo purposes, OTP is always "1234" for any phone number
# In production: integrate Twilio Verify API or MSG91
_MOCK_OTP = "1234"


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse, summary="Login with phone + OTP")
async def login(payload: LoginRequest):
    """
    POST /api/auth/login
    -------------------
    Authenticates user with phone number and OTP code.
    Returns JWT access token (15 min) and refresh token (7 days).
    
    **Demo mode:** OTP is always "1234" for any phone number.
    **Production:** Integrate Twilio Verify or MSG91 for real SMS delivery.
    """
    log = logger.bind(phone=payload.phone)
    log.info(f"Login attempt for phone: {payload.phone}")
    
    # Verify OTP (mock — in production, call Twilio Verify API)
    if payload.otp != _MOCK_OTP:
        log.warning(f"Invalid OTP attempt for phone: {payload.phone}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid OTP code. Please check your messages."
        )
    
    # Generate user ID from phone (in production: look up in DB)
    user_id = f"patient_{payload.phone}"
    role = "patient"
    
    # Check if this is an admin phone (demo purposes)
    if payload.phone == "9999999999":
        user_id = "admin_001"
        role = "admin"
        log.info("Admin login detected")
    
    # Create tokens
    access_token = create_access_token(user_id=user_id, role=role)
    refresh_token = create_refresh_token(user_id=user_id)
    
    log.success(f"Login successful for {user_id} (role: {role})")
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=900,
        user_id=user_id,
        role=role
    )


@router.post("/refresh", response_model=TokenOnlyResponse, summary="Refresh access token")
async def refresh_token(payload: RefreshRequest):
    """
    POST /api/auth/refresh
    ---------------------
    Exchanges a valid refresh token for a new access token.
    Used when the access token expires (every 15 minutes).
    """
    token_data = verify_token(payload.refresh_token)
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    if token_data.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type — refresh token required"
        )
    
    user_id = token_data.get("sub")
    new_access_token = create_access_token(user_id=user_id, role="patient")
    
    logger.info(f"Access token refreshed for user: {user_id}")
    
    return TokenOnlyResponse(
        access_token=new_access_token,
        expires_in=900
    )


@router.get("/me", summary="Get current user info")
async def get_me(user: dict = Depends(get_current_user)):
    """
    GET /api/auth/me
    ---------------
    Returns the current authenticated user's information.
    Requires valid access token in Authorization header.
    """
    return {
        "user_id": user.get("sub"),
        "role": user.get("role"),
        "token_expires_at": user.get("exp")
    }
