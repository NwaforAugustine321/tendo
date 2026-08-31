FROM nvcr.io/nvidia/nemo-microservices/nv-ingest:26.3.0

ENV ARROW_DEFAULT_MEMORY_POOL=system \
    OMP_NUM_THREADS=1 \
    CUDA_VISIBLE_DEVICES=-1 \
    MAX_INGEST_PROCESS_WORKERS=16 \
    INGEST_LOG_LEVEL=WARNING \
    INGEST_RAY_LOG_LEVEL=PRODUCTION \
    INGEST_DYNAMIC_MEMORY_THRESHOLD=0.80 \
    INGEST_DISABLE_DYNAMIC_SCALING=True \
    RAY_num_grpc_threads=1 \
    RAY_num_server_call_thread=1 \
    RAY_worker_num_grpc_internal_threads=1

ENV MESSAGE_CLIENT_TYPE=redis \
    REDIS_INGEST_TASK_QUEUE=ingest_task_queue

ENV APP_EMBEDDINGS_SERVERURL=https://integrate.api.nvidia.com/v1 \
    APP_EMBEDDINGS_MODELNAME=nvidia/llama-nemotron-embed-vl-1b-v2

ENV NEMOTRON_PARSE_HTTP_ENDPOINT=https://integrate.api.nvidia.com/v1/chat/completions \
    NEMOTRON_PARSE_INFER_PROTOCOL=http \
    NEMOTRON_PARSE_MODEL_NAME=nvidia/nemotron-parse

ENV OCR_HTTP_ENDPOINT=https://ai.api.nvidia.com/v1/cv/nvidia/nemotron-ocr-v1 \
    OCR_INFER_PROTOCOL=http \
    OCR_MODEL_NAME=pipeline

ENV YOLOX_HTTP_ENDPOINT=https://ai.api.nvidia.com/v1/cv/nvidia/nemotron-page-elements-v2 \
    YOLOX_INFER_PROTOCOL=http \
    YOLOX_GRAPHIC_ELEMENTS_HTTP_ENDPOINT=https://ai.api.nvidia.com/v1/cv/nvidia/nemotron-graphic-elements-v1 \
    YOLOX_GRAPHIC_ELEMENTS_INFER_PROTOCOL=http \
    YOLOX_TABLE_STRUCTURE_HTTP_ENDPOINT=https://ai.api.nvidia.com/v1/cv/nvidia/nemotron-table-structure-v1 \
    YOLOX_TABLE_STRUCTURE_INFER_PROTOCOL=http

ENV VLM_CAPTION_ENDPOINT=https://integrate.api.nvidia.com/v1/chat/completions \
    VLM_CAPTION_MODEL_NAME=nvidia/nemotron-nano-12b-v2-vl

ENV PDF_SPLIT_PAGE_COUNT=32 \
    NV_INGEST_MAX_UTIL=48 \
    COMPONENTS_TO_READY_CHECK=ALL

EXPOSE 7670
EXPOSE 7671
EXPOSE 8265