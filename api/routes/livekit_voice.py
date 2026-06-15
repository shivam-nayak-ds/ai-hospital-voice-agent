"""
livekit_voice.py
----------------
FastAPI routes for LiveKit browser-based voice integration.
Generates room tokens so the browser UI can connect to LiveKit Cloud.
"""

import os
import time
import uuid
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.utils.logger import custom_logger as logger

router = APIRouter(prefix="/api/livekit", tags=["LiveKit Voice"])


# ─── LiveKit JWT Token Generation ─────────────────────────────────────────────

def _generate_token(room_name: str, participant_identity: str) -> str:
    """
    Generates a LiveKit access token for a participant to join a room.
    Uses the livekit-api SDK to sign JWTs with LIVEKIT_API_KEY + LIVEKIT_API_SECRET.
    """
    from livekit import api as lk_api

    api_key = os.getenv("LIVEKIT_API_KEY", "")
    api_secret = os.getenv("LIVEKIT_API_SECRET", "")

    if not api_key or not api_secret:
        raise HTTPException(status_code=500, detail="LiveKit API credentials not configured")

    token = (
        lk_api.AccessToken(api_key, api_secret)
        .with_identity(participant_identity)
        .with_name(participant_identity)
        .with_grants(
            lk_api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )
        .to_jwt()
    )
    return token


# ─── Schemas ──────────────────────────────────────────────────────────────────

class TokenRequest(BaseModel):
    room: str = "hospital-demo"
    user: str = ""


class TokenResponse(BaseModel):
    token: str
    room: str
    url: str
    user: str


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/token", response_model=TokenResponse, summary="Get LiveKit room token")
async def get_livekit_token(
    room: str = Query(default="hospital-demo", description="Room name to join"),
    user: str = Query(default="", description="User identity (auto-generated if empty)"),
):
    """
    GET /api/livekit/token?room=hospital-demo&user=patient_1

    Returns a LiveKit JWT token + room URL for the browser client to connect.
    """
    if not user:
        user = f"patient_{uuid.uuid4().hex[:8]}"

    livekit_url = os.getenv("LIVEKIT_URL", "")
    if not livekit_url:
        raise HTTPException(status_code=500, detail="LIVEKIT_URL not configured in .env")

    try:
        token = _generate_token(room_name=room, participant_identity=user)
        logger.info(f"LiveKit token generated: room={room}, user={user}")

        return TokenResponse(
            token=token,
            room=room,
            url=livekit_url,
            user=user,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate LiveKit token: {e}")
        raise HTTPException(status_code=500, detail=f"Token generation failed: {str(e)}")


@router.post("/token", response_model=TokenResponse, summary="Get LiveKit room token (POST)")
async def post_livekit_token(req: TokenRequest):
    """
    POST /api/livekit/token
    Body: {"room": "hospital-demo", "user": "patient_1"}
    """
    user = req.user or f"patient_{uuid.uuid4().hex[:8]}"
    livekit_url = os.getenv("LIVEKIT_URL", "")

    if not livekit_url:
        raise HTTPException(status_code=500, detail="LIVEKIT_URL not configured in .env")

    try:
        token = _generate_token(room_name=req.room, participant_identity=user)
        logger.info(f"LiveKit token generated (POST): room={req.room}, user={user}")

        return TokenResponse(
            token=token,
            room=req.room,
            url=livekit_url,
            user=user,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate LiveKit token: {e}")
        raise HTTPException(status_code=500, detail=f"Token generation failed: {str(e)}")
