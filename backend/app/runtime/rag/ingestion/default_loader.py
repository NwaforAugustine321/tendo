from __future__ import annotations

from pathlib import Path
from typing import Any

from app.runtime.rag.models import RAGDocument

from .loader import DocumentLoader


CONTENT_TYPE_EXTENSIONS: dict[str, list[str]] = {
    "text": [".txt"],
    "markdown": [".md"],
    "pdf": [".pdf"],
    "image": [".png", ".jpg", ".jpeg", ".webp"],
    "audio": [".mp3", ".wav", ".m4a", ".flac", ".mpeg", ".ogg", ".aac", ".wma"],
}


class DefaultDocumentLoader(
    DocumentLoader,
):
    """
    Routes document loading to the appropriate
    loader based on content_type or file extension.
    """

    def __init__(
        self,
    ) -> None:

        self._loaders: dict[
            str,
            DocumentLoader,
        ] = {}

        self.register_defaults()

    @property
    def loaders(
        self,
    ) -> dict[str, DocumentLoader]:

        return self._loaders

    def register(
        self,
        extension: str,
        loader: DocumentLoader,
    ) -> None:
        """
        Register a loader for a file extension.
        """

        self._loaders[
            extension.lower()
        ] = loader

    def register_defaults(
        self,
    ) -> None:
        """
        Register the default document loaders

        """

        from .loaders.audio import AudioLoader
        from .loaders.image import ImageLoader
        from .loaders.markdown import MarkdownLoader
        from .loaders.pdf import PDFLoader
        from .loaders.text import TextLoader

        loader_map = {
            "text": TextLoader(),
            "markdown": MarkdownLoader(),
            "pdf": PDFLoader(),
            "image": ImageLoader(),
            "audio": AudioLoader(),
        }

        for content_type, extensions in CONTENT_TYPE_EXTENSIONS.items():
            loader = loader_map[content_type]
            for ext in extensions:
                self.register(ext, loader)

    async def load(
        self,
        *,
        source: str | Path | Any,
        content_type: str | None = None,
    ) -> list[RAGDocument]:

        if not isinstance(
            source,
            (str, Path),
        ):
            raise ValueError(
                f"Unsupported source type "
                f"'{type(source).__name__}'."
            )

        all_extensions = {
            ext
            for extensions in CONTENT_TYPE_EXTENSIONS.values()
            for ext in extensions
        }

        # If content_type is a group key (e.g. "image", "audio", "text"),
        # resolve to the first extension in that group.
        if content_type in CONTENT_TYPE_EXTENSIONS:
            extension = CONTENT_TYPE_EXTENSIONS[content_type][0]
        else:
            extension = f".{content_type}"

        if extension not in all_extensions:
            raise ValueError(
                f"Unsupported content type "
                f"'{content_type}'."
            )

        loader = self._loaders.get(
            extension,
        )

        if loader is None:
            raise ValueError(
                f"No document loader registered "
                f"for '{extension}'."
            )

        return await loader.load(
            source=source,
        )
