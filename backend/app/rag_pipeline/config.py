from nvidia_rag.utils.configuration import NvidiaRAGConfig
from app.config.settings import settings
import os
ingest_domain = "http://3.226.250.54"


os.environ["NVIDIA_API_KEY"] = settings.nvidia_api_key

os.environ["NGC_API_KEY"] = os.environ["NVIDIA_API_KEY"]


def create_config() -> NvidiaRAGConfig:

    return NvidiaRAGConfig.from_dict(
        {

            "nv_ingest": {
                "message_client_hostname": f"{ingest_domain}",
                "message_client_port": 7670,
                "extract_infographics": True,
                "redis_host": f"{ingest_domain}",
                "redis_port": 6379,
                "backend": "nrl",
                "nrl_run_mode": "batch"

            },
            "embeddings": {
                "model_name": "nvidia/llama-nemotron-embed-vl-1b-v2",
                "model_engine": "nvidia-ai-endpoints",
                "server_url": "https://integrate.api.nvidia.com/v1",


            },
            "ranking": {
                "enable_reranker": True,
                "model_name": "nvidia/llama-nemotron-rerank-vl-1b-v2",
                # "model_engine": "nvidia-ai-endpoints",
                # "server_url": "https://integrate.api.nvidia.com/v1",
            },

        }
    )
