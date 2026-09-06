from __future__ import annotations

import json
from typing import Any

from .model import (
    InvalidVoiceSessionMetadata,
    VoiceSessionData,
)


class VoiceSessionMetadataParser:
    """
    Parse and validate LiveKit voice-session metadata.

    The complete metadata payload is preserved so the voice session
    and graph can access all context supplied when the agent starts.
    """

    def parse(
        self,
        metadata: str | None,
    ) -> VoiceSessionData:
        """
        Parse metadata into VoiceSessionData.

        The complete JSON object is preserved as attributes.
        """

        if not metadata:
            raise InvalidVoiceSessionMetadata(
                "Voice session metadata is missing.",
            )

        try:
            payload = json.loads(
                metadata,
            )

        except (
            json.JSONDecodeError,
            TypeError,
        ) as exc:
            raise InvalidVoiceSessionMetadata(
                "Voice session metadata contains invalid JSON.",
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise InvalidVoiceSessionMetadata(
                "Voice session metadata must be a JSON object.",
            )

        return VoiceSessionData(**payload)
