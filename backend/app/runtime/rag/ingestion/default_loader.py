from __future__ import annotations

from pathlib import Path
from typing import Any

from app.runtime.rag.models import RAGDocument

from .loader import DocumentLoader


class DefaultDocumentLoader(
    DocumentLoader,
):
    """
    Routes document loading to the appropriate
    loader based on the input source.
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
        Register the default document loaders.
        """

        from .loaders.audio import (
            AudioLoader,
        )
        from .loaders.csv import (
            CSVLoader,
        )
        from .loaders.docx import (
            DocxLoader,
        )
        from .loaders.html import (
            HTMLLoader,
        )
        from .loaders.image import (
            ImageLoader,
        )
        from .loaders.json import (
            JSONLoader,
        )
        from .loaders.markdown import (
            MarkdownLoader,
        )
        from .loaders.pdf import (
            PDFLoader,
        )
        from .loaders.text import (
            TextLoader,
        )

        #
        # Text
        #
        self.register(
            ".txt",
            TextLoader(),
        )

        self.register(
            ".md",
            MarkdownLoader(),
        )

        #
        # PDF
        #
        self.register(
            ".pdf",
            PDFLoader(),
        )

        #
        # Images
        #
        image_loader = ImageLoader()

        self.register(
            ".png",
            image_loader,
        )

        self.register(
            ".jpg",
            image_loader,
        )

        self.register(
            ".jpeg",
            image_loader,
        )

        self.register(
            ".webp",
            image_loader,
        )

        #
        # Audio
        #
        audio_loader = AudioLoader()

        self.register(
            ".wav",
            audio_loader,
        )

        self.register(
            ".mp3",
            audio_loader,
        )

        self.register(
            ".m4a",
            audio_loader,
        )

        self.register(
            ".flac",
            audio_loader,
        )

        #
        # Other formats
        #
        self.register(
            ".html",
            HTMLLoader(),
        )

        self.register(
            ".csv",
            CSVLoader(),
        )

        self.register(
            ".json",
            JSONLoader(),
        )

        self.register(
            ".docx",
            DocxLoader(),
        )

    async def load(
        self,
        *,
        source: str | Path | Any,
    ) -> list[RAGDocument]:

        if not isinstance(
            source,
            (str, Path),
        ):
            raise ValueError(
                f"Unsupported source type "
                f"'{type(source).__name__}'."
            )

        path = Path(source)

        extension = (
            path.suffix.lower()
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
            source=path,
        )
