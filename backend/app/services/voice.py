
from __future__ import annotations

from typing import Any

from app.db.mongo_client import get_client
from app.db.tools.sessions import find_active_session


COLLECTION = "voice_sessions"


class VoiceService:

    async def resolve_session(
        self,
        *,
        business_id: str,
        user_id: str,
        session_id: str,
    ) -> str | None:

        if session_id:
            return session_id

        existing = await find_active_session(
            business_id,
            user_id,
        )

        if existing:
            return existing["id"]

        return None

    async def create_voice_session(
        self,
        *,
        session_id: str,
        user_id: str,
        business_id: str,
        room: str,
        livekit_url: str,
        livekit_token: str,
        token: str,
    ) -> dict[str, Any]:
        db = get_client()

        await db[COLLECTION].update_one(
            {
                "business_id": business_id,
                "user_id": user_id,
            },
            {
                "$set": {
                    "session_id": session_id,
                    "room": room,
                    "livekit_url": livekit_url,
                    "livekit_token": livekit_token,
                    "token": token,
                },
                "$setOnInsert": {
                    "user_id": user_id,
                    "business_id": business_id,
                },
            },
            upsert=True,
        )

        document = await db[COLLECTION].find_one(
            {
                "business_id": business_id,
                "user_id": user_id,
            },
        )

        if document is None:
            raise RuntimeError(
                "Voice session could not be created or retrieved.",
            )

        return document

    async def get_voice_session(
        self,
        *,
        business_id: str,
        user_id: str,
    ) -> dict[str, Any] | None:
        db = get_client()

        return await db[COLLECTION].find_one(
            {
                "business_id": business_id,
                "user_id": user_id,
            },
        )

    async def delete_voice_session(
        self,
        *,
        business_id: str,
        user_id: str,
    ) -> bool:
        db = get_client()

        result = await db[COLLECTION].delete_one(
            {
                "business_id": business_id,
                "user_id": user_id,
            },
        )

        return result.deleted_count > 0


voice_service = VoiceService()
