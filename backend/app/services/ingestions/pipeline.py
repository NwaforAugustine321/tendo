
from __future__ import annotations

from typing import Any

from nvidia_rag import NvidiaRAG, NvidiaRAGIngestor

from .config import create_config
from .interface import DocumentSource, RAGPipeline
from .vdb import VectorDB


class Pipeline(RAGPipeline):

    def __init__(
        self,
        namespace: str,
    ):
        if not namespace:
            raise ValueError("namespace must not be empty")

        self._namespace = namespace
        self._config = create_config()

        self._vdb = VectorDB(
            namespace=namespace,
            table_name="documents",
            config=self._config,
        )

        self._rag = NvidiaRAG(
            config=self._config,
            vdb_op=self._vdb,
        )

        self._ingestor = NvidiaRAGIngestor(
            config=self._config,
            vdb_op=self._vdb,
        )

    async def create_collection(
        self,
        name: str,
        collection_type: str | None = None,
    ) -> Any:
        if not name or not name.strip():
            raise ValueError(
                "collection name must not be empty"
            )

        collection_name = name.strip()

        self._vdb.set_collection(collection_name)

        return self._vdb.create_collection(
            collection_name=collection_name,
            collection_type=collection_type or "text",
        )

    async def delete_collection(
        self,
        name: str,
    ) -> Any:
        if not name or not name.strip():
            raise ValueError(
                "collection name must not be empty"
            )

        collection_name = name.strip()

        result = self._vdb.delete_collections(
            collection_names=[collection_name],
        )

        if self._vdb.collection_name == collection_name:
            self._vdb.set_collection("documents")

        return result

    async def ingest(
        self,
        collection: str,
        source: DocumentSource,
    ) -> Any:
        if not collection or not collection.strip():
            raise ValueError(
                "collection must not be empty"
            )

        collection_name = collection.strip()
        file_path = str(source.value)

        self._vdb.set_collection(collection_name)

        exists = self._vdb.check_collection_exists(
            collection_name
        )

        if not exists:
            self._vdb.create_collection(
                collection_name=collection_name,
                collection_type="text",
            )

        return await self._ingestor.upload_documents(
            filepaths=[file_path],
            blocking=True,
        )

    async def search(
        self,
        query: str,
        collections: list[str],
        top_k: int = 10,
    ) -> Any:
        if not query or not query.strip():
            raise ValueError("query must not be empty")

        if not collections:
            raise ValueError(
                "at least one collection must be provided"
            )

        collection_names = list(
            dict.fromkeys(
                name.strip()
                for name in collections
                if name and name.strip()
            )
        )

        if not collection_names:
            raise ValueError(
                "at least one valid collection must be provided"
            )

        return await self._rag.search(
            query=query,
            reranker_top_k=top_k,
            vdb_top_k=100,
            collection_names=collection_names,
        )
