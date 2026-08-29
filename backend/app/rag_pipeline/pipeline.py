
from __future__ import annotations

from typing import Any

from pymilvus import MilvusClient

from nvidia_rag import NvidiaRAG, NvidiaRAGIngestor
from nvidia_rag.utils.configuration import NvidiaRAGConfig
from nvidia_rag.utils.vdb.milvus.milvus_vdb import MilvusVDB

from .interface import DocumentSource, RAGPipeline, SourceType


class Pipeline(RAGPipeline):

    def __init__(
        self,
        config: NvidiaRAGConfig,
        namespace: str,
    ):
        if not namespace:
            raise ValueError("namespace must not be empty")

        if config.vector_store.name != "milvus":
            raise ValueError(
                "Pipeline namespace isolation currently requires "
                "Milvus as the vector store"
            )

        self._namespace = namespace
        self._config = config

        # NVIDIA RAG stack
        self._rag = NvidiaRAG(config=config)

        # NVIDIA's native Milvus wrapper.
        #
        # We intentionally keep the collection name empty here because
        # the actual tenant collection is selected dynamically.
        self._vdb = MilvusVDB(
            collection_name="",
            milvus_uri=config.vector_store.url,
            username=getattr(config.vector_store, "username", ""),
            password=getattr(config.vector_store, "password", ""),
            embedding_model=self._rag.document_embedder,
            config=config,
        )

        # Native NVIDIA ingestion pipeline
        self._ingestor = NvidiaRAGIngestor(
            config=config,
            vdb_op=self._vdb,
        )

        self._rag.vdb_op = self._vdb

    def _get_milvus_client(self) -> MilvusClient:
        """Create a modern MilvusClient using the configured Zilliz/Milvus credentials."""

        vector_store = self._config.vector_store

        password = getattr(vector_store, "password", "")

        if hasattr(password, "get_secret_value"):
            password = password.get_secret_value()

        username = getattr(
            vector_store,
            "username",
            "",
        )

        token = f"{username}:{password}"

        return MilvusClient(
            uri=vector_store.url,
            token=token,
        )

    def _get_tenant_collection_name(
        self,
        collection: str,
    ) -> str:
        """
        Resolve the logical collection to the physical tenant collection.

        Example:
            namespace = business_001
            collection = documents

            -> business_001_documents
        """

        if not collection:
            raise ValueError("collection must not be empty")

        return f"{self._namespace}_{collection}"

    async def create_collection(
        self,
        name: str,
    ):
        tenant_collection = self._get_tenant_collection_name(name)

        dimension = getattr(
            self._config.embeddings,
            "dimensions",
            2048,
        )

        # Let NVIDIA create the exact schema and indexes it expects.
        return self._vdb.create_collection(
            collection_name=tenant_collection,
            dimension=dimension,
        )

    async def delete_collection(
        self,
        name: str,
    ):
        tenant_collection = self._get_tenant_collection_name(name)

        client = self._get_milvus_client()

        if client.has_collection(
            collection_name=tenant_collection,
        ):
            client.drop_collection(
                collection_name=tenant_collection,
            )

    async def ingest(
        self,
        collection: str,
        source: DocumentSource,
    ):
        if source.type is not SourceType.FILE:
            raise ValueError(
                f"Unsupported source type: {source.type}"
            )

        tenant_collection = self._get_tenant_collection_name(
            collection
        )

        client = self._get_milvus_client()

        # Create the collection if it does not already exist.
        if not client.has_collection(
            collection_name=tenant_collection,
        ):
            dimension = getattr(
                self._config.embeddings,
                "dimensions",
                2048,
            )

            self._vdb.create_collection(
                collection_name=tenant_collection,
                dimension=dimension,
            )

        # IMPORTANT:
        # NVIDIA's ingestor uses the collection_name stored
        # on the VDB instance.
        self._vdb.collection_name = tenant_collection

        return await self._ingestor.upload_documents(
            filepaths=[str(source.value)],
            blocking=True,
        )

    async def search(
        self,
        query: str,
        collections: list[str],
        top_k: int = 10,
    ):
        if not query:
            raise ValueError("query must not be empty")

        if not collections:
            raise ValueError(
                "at least one collection must be provided"
            )

        tenant_collections = [
            self._get_tenant_collection_name(collection)
            for collection in collections
        ]

        # NvidiaRAG.search() does not accept top_k directly in
        # the installed version, so configure retrieval instead.
        retriever_config = getattr(
            self._config,
            "retriever",
            None,
        )

        if retriever_config is not None:
            if hasattr(retriever_config, "top_k"):
                retriever_config.top_k = top_k

            elif hasattr(retriever_config, "top_n"):
                retriever_config.top_n = top_k

        return await self._rag.search(
            query=query,
            collection_names=tenant_collections,
        )
