from __future__ import annotations

import logging

import httpx

from app.config.settings import settings
from app.runtime.rag.models import (
    RAGDocument,
)

from ..loader import (
    DocumentLoader,
)

logger = logging.getLogger(__name__)


class ImageLoader(
    DocumentLoader,
):
    """
    Loads an image by performing OCR and returning
    one RAG document.

    The image should be supplied as a data URL.
    """

    async def load(
        self,
        *,
        source: str | Path | Any,
        content_type: str | None = None,
    ) -> list[RAGDocument]:

        if not source:
            return []

        source = str(source)

        if not source.startswith("data:"):
            return []

        try:

            text = await self._image_ocr(
                source,
            )

        except Exception as error:

            logger.warning(
                "OCR extraction failed: %s",
                error,
            )

            return []

        if not text.strip():
            return []

        return [
            RAGDocument(
                id="",
                title="",
                source="image",
                content=text,
                metadata={"source_type": "image"},
            )
        ]

    async def _image_ocr(
        self,
        image_data_url: str,
    ) -> str:
        """
        Run NVIDIA OCR on an image data URL.
        """

        ocr_url = (
            "https://ai.api.nvidia.com/"
            "v1/cv/nvidia/nemotron-ocr-v2"
        )

        headers = {
            "Authorization": (
                f"Bearer {settings.nvidia_api_key}"
            ),
            "Accept": "application/json",
        }

        payload = {
            "input": [
                {
                    "type": "image_url",
                    "url": image_data_url,
                }
            ]
        }

        async with httpx.AsyncClient(
            timeout=60,
        ) as client:

            response = await client.post(
                ocr_url,
                headers=headers,
                json=payload,
            )

            response.raise_for_status()

            data = response.json()

        if (
            not isinstance(data, dict)
            or "data" not in data
        ):
            return ""

        texts: list[str] = []

        for page in data.get(
            "data",
            [],
        ):

            for detection in page.get(
                "text_detections",
                [],
            ):

                prediction = detection.get(
                    "text_prediction",
                    {},
                )

                text = prediction.get(
                    "text",
                    "",
                ).strip()

                if text:
                    texts.append(
                        text,
                    )

        return "\n".join(
            texts,
        )
