from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class SourceType(StrEnum):
    FILE = "file"
    URL = "url"
    BASE64 = "base64"


@dataclass(frozen=True)
class DocumentSource:
    type: SourceType
    value: str


class RAGPipeline(ABC):

    @abstractmethod
    async def create_collection(self, name: str, collection_type: str | None = None) -> Any:
        ...

    @abstractmethod
    async def delete_collection(self, name: str) -> Any:
        ...

    @abstractmethod
    async def ingest(
        self,
        collection: str,
        source: DocumentSource,
    ) -> Any:
        ...

    @abstractmethod
    async def search(
        self,
        query: str,
        collections: list[str],
        top_k: int = 10,
    ) -> Any:
        ...
