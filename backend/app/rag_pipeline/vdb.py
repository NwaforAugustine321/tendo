from __future__ import annotations
from typing import Any
from pymilvus import DataType, MilvusClient, connections
from nvidia_rag.utils.vdb.milvus.milvus_vdb import MilvusVDB
from nv_ingest_client.util.milvus import (
    create_nvingest_schema,
    create_nvingest_index_params,
)


class NamespaceMilvusVDB(MilvusVDB):
    NAMESPACE_FIELD = "namespace"

    def __init__(
        self,
        *,
        namespace: str,
        collection_name: str,
        milvus_uri: str,
        embedding_model: Any,
        config: Any = None,
        username: str = "",
        password: str = "",
        **kwargs: Any,
    ):
        if not namespace:
            raise ValueError("namespace must not be empty")

        self.namespace = namespace

        # 1. Safely parse token out of config
        token = getattr(config.vector_store, "token", "")
        if not token and getattr(config.vector_store, "password", None):
            pwd = config.vector_store.password
            pwd_str = pwd.get_secret_value() if hasattr(pwd, "get_secret_value") else pwd
            user = getattr(config.vector_store, "username",
                           "db_user") or "db_user"
            token = f"{user}:{pwd_str}"

        # 2. Force PyMilvus global aliases so NVIDIA's super() calls bypass localhost
        try:
            connections.connect(alias="default", uri=milvus_uri, token=token)
            connections.connect(alias=milvus_uri, uri=milvus_uri, token=token)
        except Exception:
            pass

        # 3. Call super WITHOUT passing vdb_endpoint as a direct keyword
        super().__init__(
            collection_name=collection_name,
            milvus_uri=milvus_uri,
            embedding_model=embedding_model,
            config=config,
            username=username,
            password=password,
            **kwargs,
        )

    def _get_milvus_client(self) -> MilvusClient:
        vstore = self.config.vector_store
        token = getattr(vstore, "token", "")
        if not token and getattr(vstore, "password", None):
            pwd = vstore.password
            pwd_str = pwd.get_secret_value() if hasattr(pwd, "get_secret_value") else pwd
            user = getattr(vstore, "username", "db_user") or "db_user"
            token = f"{user}:{pwd_str}"

        # Use the endpoint saved by the base class initialization
        endpoint = getattr(self, "vdb_endpoint", vstore.url)
        return MilvusClient(uri=endpoint, token=token)

    def create_collection(
        self,
        collection_name: str,
        dimension: int = 2048,
        collection_type: str = "text",
    ) -> None:
        client = self._get_milvus_client()

        if client.has_collection(collection_name):
            self.collection_name = collection_name
            return

        search_type = getattr(self.config.vector_store, "search_type", "dense")
        sparse = (search_type.value == "hybrid") if hasattr(
            search_type, "value") else (search_type == "hybrid")

        schema = create_nvingest_schema(
            dense_dim=dimension,
            sparse=sparse,
            local_index=False,
        )

        schema.add_field(
            field_name=self.NAMESPACE_FIELD,
            datatype=DataType.VARCHAR,
            max_length=256,
            is_partition_key=True,
        )

        index_params = create_nvingest_index_params(
            sparse=sparse,
            gpu_index=getattr(self.config.vector_store,
                              "enable_gpu_index", False),
            gpu_search=getattr(self.config.vector_store,
                               "enable_gpu_search", False),
            local_index=False,
        )

        client.create_collection(
            collection_name=collection_name,
            schema=schema,
            index_params=index_params,
        )
        self.collection_name = collection_name

    def write_to_index(self, records: list, **kwargs: Any) -> None:
        rows = []
        for record in records:
            if not isinstance(record, dict):
                continue
            row = dict(record)
            row[self.NAMESPACE_FIELD] = self.namespace
            rows.append(row)

        if not rows:
            return None

        kwargs["collection_name"] = self.collection_name
        return super().write_to_index(rows, **kwargs)

    def retrieval(self, queries: list, **kwargs: Any) -> list:
        namespace_filter = f'{self.NAMESPACE_FIELD} == "{self.namespace}"'
        existing_filter = kwargs.get("filter_expr", "")

        if existing_filter:
            kwargs["filter_expr"] = f"({existing_filter}) AND ({namespace_filter})"
        else:
            kwargs["filter_expr"] = namespace_filter

        return super().retrieval(queries, **kwargs)
