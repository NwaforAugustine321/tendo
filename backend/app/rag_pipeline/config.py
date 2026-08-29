from nvidia_rag.utils.configuration import NvidiaRAGConfig


def create_config() -> NvidiaRAGConfig:
    return NvidiaRAGConfig.from_dict(
        {
            "vector_store": {
                "name": "milvus",
                "url": "https://in03-87999fc6931bf94.serverless.aws-eu-central-1.cloud.zilliz.com",
                "search_type": "dense",
                "username": "db_87999fc6931bf94",
                "password": "rgw4T!nqXp!4Bix",
                "enable_gpu_index": False,
                "enable_gpu_search": False,
            },
            "nv_ingest": {
                "backend": "nrl",
                "nrl_run_mode": "batch",
            },
            "embeddings": {
                "model_name": "nvidia/llama-nemotron-embed-vl-1b-v2",
                "model_engine": "nvidia-ai-endpoints",
                "dimensions": 2048,
                "server_url": "https://integrate.api.nvidia.com/v1",
            },
            "ranking": {
                "server_url": "",
            },
            "llm": {
                "server_url": "",
            },
        }
    )
