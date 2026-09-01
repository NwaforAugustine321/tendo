
from __future__ import annotations

from typing import Any

from nvidia_rag import NvidiaRAG, NvidiaRAGIngestor
from nvidia_rag.utils.configuration import NvidiaRAGConfig

from .interface import DocumentSource, RAGPipeline, SourceType
from .vdb import VectorDB
from .config import create_config


class Pipeline(RAGPipeline):
    """
    RAG pipeline using NVIDIA RAG with a custom LanceDB VectorDB.

    NVIDIA RAG 2.5.x does not allow collection_name to be passed to
    NvidiaRAGIngestor when a custom vdb_op is supplied during initialization.

    Therefore, collection selection is handled by the custom VectorDB through
    its active collection_name.
    """

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
            config=self._config
        )

        self._rag = NvidiaRAG(
            config=self._config,
            vdb_op=self._vdb,
        )

        self._ingestor = NvidiaRAGIngestor(
            config=self._config,
            vdb_op=self._vdb,
        )

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    async def create_collection(
        self,
        name: str,
        collection_type: str | None = None,
    ) -> Any:
        """
        Create a LanceDB collection.

        Because a custom vdb_op is supplied to NvidiaRAGIngestor, we must
        manage the collection directly through VectorDB rather than passing
        collection_name to NvidiaRAGIngestor.create_collection().
        """

        if not name or not name.strip():
            raise ValueError(
                "collection name must not be empty"
            )

        collection_name = name.strip()

        # Set this as the active collection for NVIDIA RAG.
        self._vdb.set_collection(collection_name)

        # Create the actual LanceDB table if it does not already exist.
        return self._vdb.create_collection(
            collection_name=collection_name,
            collection_type=collection_type or "text",
        )

    async def delete_collection(
        self,
        name: str,
    ) -> Any:
        """
        Delete a LanceDB collection.
        """

        if not name or not name.strip():
            raise ValueError(
                "collection name must not be empty"
            )

        collection_name = name.strip()

        result = self._vdb.delete_collections(
            collection_names=[collection_name],
        )

        # If the deleted collection was the active collection, reset the
        # active collection to the default documents collection.
        if self._vdb.collection_name == collection_name:
            self._vdb.set_collection("documents")

        return result

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    async def ingest(
        self,
        collection: str,
        source: DocumentSource,
    ) -> Any:
        """
        Ingest a document into the requested collection.

        The collection is selected on the custom VectorDB before NVIDIA RAG
        starts ingestion. We intentionally do NOT pass collection_name to
        NvidiaRAGIngestor.upload_documents(), because NVIDIA RAG 2.5.x rejects
        that argument when a custom vdb_op was supplied.
        """

        if not collection or not collection.strip():
            raise ValueError(
                "collection must not be empty"
            )

        collection_name = collection.strip()
        file_path = str(source.value)

        # --------------------------------------------------------------
        # Select the collection on the custom VDB.
        #
        # NVIDIA RAG will resolve the collection through the injected
        # VectorDB instead of receiving collection_name as an argument.
        # --------------------------------------------------------------
        self._vdb.set_collection(collection_name)

        print(
            f">>>>> Active collection: {self._vdb.collection_name}"
        )

        # --------------------------------------------------------------
        # Check/create the LanceDB collection.
        # --------------------------------------------------------------
        exists = self._vdb.check_collection_exists(
            collection_name
        )

        if not exists:
            print(
                f">>>>> Creating collection: {collection_name}"
            )

            self._vdb.create_collection(
                collection_name=collection_name,
                collection_type="text",
            )
        else:
            print(
                f">>>>> Collection already exists: "
                f"{collection_name}"
            )

        # --------------------------------------------------------------
        # IMPORTANT:
        #
        # Do NOT pass collection_name here.
        #
        # NvidiaRAGIngestor 2.5.x raises:
        #
        # ValueError:
        # `collection_name` and `custom_metadata` arguments are not
        # supported when `vdb_op` is provided during initialization.
        #
        # The active collection is already set on self._vdb.
        # --------------------------------------------------------------
        print(
            f">>>>> Ingesting file: {file_path}"
        )

        return await self._ingestor.upload_documents(
            filepaths=[file_path],
            blocking=True,
        )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

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
