from __future__ import annotations

from app.runtime.rag.factory import (
    get_rag_store,
)

from .default_loader import (
    DefaultDocumentLoader,
)

from .default_splitter import (
    DefaultDocumentSplitter,
)

from .loaders.audio import AudioLoader
from .loaders.csv import CSVLoader
from .loaders.docx import DocxLoader
from .loaders.html import HTMLLoader
from .loaders.image import ImageLoader
from .loaders.json import JSONLoader
from .loaders.markdown import MarkdownLoader
from .loaders.pdf import PDFLoader
from .loaders.text import TextLoader
from .pipeline import (
    DocumentIngestionPipeline,
)


_pipeline: DocumentIngestionPipeline | None = None


def get_ingestion_pipeline(
) -> DocumentIngestionPipeline:

    global _pipeline

    if _pipeline is not None:
        return _pipeline

    loader = DefaultDocumentLoader()

    loader.register(
        ".txt",
        TextLoader(),
    )

    loader.register(
        ".md",
        MarkdownLoader(),
    )

    loader.register(
        ".pdf",
        PDFLoader(),
    )

    loader.register(
        ".png",
        ImageLoader(),
    )

    loader.register(
        ".jpg",
        ImageLoader(),
    )

    loader.register(
        ".jpeg",
        ImageLoader(),
    )

    loader.register(
        ".wav",
        AudioLoader(),
    )

    loader.register(
        ".mp3",
        AudioLoader(),
    )

    loader.register(
        ".html",
        HTMLLoader(),
    )

    loader.register(
        ".csv",
        CSVLoader(),
    )

    loader.register(
        ".json",
        JSONLoader(),
    )

    loader.register(
        ".docx",
        DocxLoader(),
    )

    _pipeline = (
        DocumentIngestionPipeline(
            loader=loader,
            splitter=DefaultDocumentSplitter(),
            store=get_rag_store(),
        )
    )

    return _pipeline
