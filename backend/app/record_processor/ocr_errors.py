"""OCR processing exception hierarchy.

Defines custom exceptions for OCR-related failures in the record knowledge engine.
"""


class OCRProcessingError(Exception):
    """Base error for OCR processing failures."""

    pass


class OCRExtractionError(OCRProcessingError):
    """Raised when the NVIDIA API call fails after retries."""

    pass


class OCREmptyResultError(OCRProcessingError):
    """Raised when OCR returns no text from the image."""

    pass


class OCRInvalidImageError(OCRProcessingError):
    """Raised when the image content is invalid or corrupted."""

    pass
