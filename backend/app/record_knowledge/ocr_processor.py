"""OCR text extraction using NVIDIA nemotron-ocr-v2.

This module provides the OCRProcessor class for extracting text from images
via the NVIDIA nemotron-ocr-v2 REST API with retry logic and error handling.
"""

import asyncio
import base64
import logging

import httpx

from app.record_knowledge.ocr_errors import (
    OCREmptyResultError,
    OCRExtractionError,
    OCRInvalidImageError,
)

logger = logging.getLogger(__name__)

# Supported image MIME types mapped from file extensions
_EXTENSION_TO_MIME = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "bmp": "image/bmp",
    "tiff": "image/tiff",
    "tif": "image/tiff",
    "webp": "image/webp",
}

# Default MIME type when format cannot be determined
_DEFAULT_MIME = "image/png"


class OCRProcessor:
    """Handles OCR text extraction via NVIDIA nemotron-ocr-v2."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout: int,
        max_retries: int,
    ):
        """Initialize the OCR processor.

        Args:
            api_key: NVIDIA API key for authentication.
            base_url: Base URL for the nemotron-ocr-v2 API.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retry attempts for transient failures.
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    def _normalize_image_input(self, image_content: str) -> str:
        """Convert URL or raw base64 to data URL format.

        Accepts:
        - A URL pointing to an image (http/https)
        - A data URL already in the correct format
        - Raw base64-encoded image data

        Returns:
            A string in the format: data:image/<format>;base64,<data>
            OR a direct URL (http/https) that the API can fetch.

        Raises:
            OCRInvalidImageError: If the input is empty or cannot be normalized.
        """
        if not image_content or not image_content.strip():
            raise OCRInvalidImageError("Image content is empty")

        image_content = image_content.strip()

        # Already a data URL
        if image_content.startswith("data:image/"):
            return image_content

        # HTTP/HTTPS URL - pass through directly, API will fetch the image
        if image_content.startswith(("http://", "https://")):
            return image_content

        # Raw base64 - validate and wrap with detected MIME type
        mime = self._detect_mime_from_base64(image_content)
        return f"data:{mime};base64,{image_content}"

    def _detect_mime_from_base64(self, b64_data: str) -> str:
        """Detect MIME type from base64-encoded image data.

        Args:
            b64_data: Base64-encoded image bytes.

        Returns:
            The detected MIME type, or default if detection fails.
        """
        try:
            # Decode just the first few bytes to detect magic numbers
            header = base64.b64decode(b64_data[:32] + "==")
            if header[:8] == b"\x89PNG\r\n\x1a\n":
                return "image/png"
            if header[:2] == b"\xff\xd8":
                return "image/jpeg"
            if header[:6] in (b"GIF87a", b"GIF89a"):
                return "image/gif"
            if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
                return "image/webp"
            if header[:2] in (b"BM",):
                return "image/bmp"
        except Exception:
            pass
        return _DEFAULT_MIME

    async def _call_api(self, image_data_url: str) -> dict:
        """Make the HTTP request to nemotron-ocr-v2 /v1/infer endpoint.

        Args:
            image_data_url: Image in data URL format.

        Returns:
            The JSON response from the API.

        Raises:
            OCRInvalidImageError: For HTTP 422 (invalid request).
            OCRExtractionError: For other HTTP errors or timeouts.
        """
        url = f"{self.base_url}/v1/infer"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": [
                {
                    "type": "image_url",
                    "url": image_data_url,
                }
            ],
            "model": "nvidia/nemotron-ocr-v2",
            "merge_levels": ["paragraph"],
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
            except httpx.TimeoutException as e:
                raise OCRExtractionError(
                    f"OCR API request timed out: {e}"
                ) from e
            except httpx.RequestError as e:
                raise OCRExtractionError(
                    f"OCR API request failed: {e}"
                ) from e

        if response.status_code == 422:
            raise OCRInvalidImageError(
                f"Invalid image data (HTTP 422): {response.text}"
            )

        if response.status_code == 429:
            raise OCRExtractionError(
                f"OCR API rate limited (HTTP 429): {response.text}"
            )

        if response.status_code >= 500:
            raise OCRExtractionError(
                f"OCR API server error (HTTP {response.status_code}): {response.text}"
            )

        if response.status_code != 200:
            raise OCRExtractionError(
                f"OCR API error (HTTP {response.status_code}): {response.text}"
            )

        return response.json()

    def _parse_response(self, response: dict) -> str:
        """Extract text from API response, joining all text_detections.

        Args:
            response: The parsed JSON response from the API.

        Returns:
            Concatenated text from all detections, separated by newlines.

        Raises:
            OCREmptyResultError: If no text detections are found.
        """
        texts = []
        data = response.get("data", [])
        for item in data:
            detections = item.get("text_detections", [])
            for detection in detections:
                text_prediction = detection.get("text_prediction", {})
                text = text_prediction.get("text", "")
                if text:
                    texts.append(text)

        if not texts:
            raise OCREmptyResultError("No text extracted from image")

        return "\n\n".join(texts)

    async def _call_with_retry(self, image_data_url: str) -> dict:
        """Call API with exponential backoff retry.

        Non-retryable errors (HTTP 422 / OCRInvalidImageError) are raised immediately.
        Retryable errors (429, 5xx, timeouts) are retried up to max_retries times.

        Args:
            image_data_url: Image in data URL format.

        Returns:
            The JSON response from the API.

        Raises:
            OCRInvalidImageError: Immediately on invalid image (no retry).
            OCRExtractionError: After all retries are exhausted.
        """
        last_error: OCRExtractionError | None = None

        for attempt in range(self.max_retries + 1):
            try:
                return await self._call_api(image_data_url)
            except OCRInvalidImageError:
                raise  # Non-retryable
            except OCRExtractionError as e:
                last_error = e
                if attempt < self.max_retries:
                    wait = 2**attempt  # 1s, 2s, 4s...
                    logger.warning(
                        f"OCR API call failed (attempt {attempt + 1}/{self.max_retries + 1}), "
                        f"retrying in {wait}s: {e}"
                    )
                    await asyncio.sleep(wait)

        raise last_error  # type: ignore[misc]

    async def extract_text(self, image_content: str) -> str:
        """Extract text from an image.

        This is the public entry point for OCR processing. It normalizes the
        input, calls the API with retry logic, and parses the response.

        Args:
            image_content: Either a URL to an image or base64-encoded image data.

        Returns:
            Extracted text concatenated from all detections.

        Raises:
            OCRExtractionError: When extraction fails after retries.
            OCREmptyResultError: When no text is detected in the image.
            OCRInvalidImageError: When the image content is invalid or corrupted.
        """
        image_data_url = self._normalize_image_input(image_content)
        response = await self._call_with_retry(image_data_url)
        return self._parse_response(response)
