import logging
from typing import Any

from app.config.settings import settings

logger = logging.getLogger(__name__)

_reranker = None


def get_reranker():
   
    global _reranker
    if _reranker is not None:
        return _reranker

    try:
        from langchain_nvidia_ai_endpoints import NVIDIARerank
        _reranker = NVIDIARerank(
            model=settings.nvidia_rerank_model,
            api_key=settings.nvidia_api_key,
        )
        logger.info(f"NVIDIA Reranker initialized: {settings.nvidia_rerank_model}")
        return _reranker
    except Exception as e:
        logger.warning(f"Failed to initialize NVIDIA reranker: {e}")
        return None


def rerank_results(query: str, documents: list[str], top_k: int = 30) -> list[str]:
    """Rerank a list of document strings by relevance to the query.

    Args:
        query: The search query.
        documents: List of document text strings to rerank.
        top_k: Number of top results to return after reranking.

    Returns:
        List of reranked document strings (most relevant first), trimmed to top_k.
    """
    if not documents:
        return []

    reranker = get_reranker()
    if reranker is None:
        # Fallback: return original order, trimmed to top_k
        return documents[:top_k]

    try:
        from langchain_core.documents import Document

        # Truncate documents to fit reranker's 8192 token limit (~6000 chars safe)
        MAX_RERANK_CHARS = 6000
        docs = [Document(page_content=text[:MAX_RERANK_CHARS]) for text in documents]
        reranked = reranker.compress_documents(query=query, documents=docs)
        # Map back to original full documents
        truncated_to_full = {text[:MAX_RERANK_CHARS]: text for text in documents}
        return [truncated_to_full.get(doc.page_content, doc.page_content) for doc in reranked[:top_k]]
    except Exception as e:
        logger.warning(f"Reranking failed, using original order: {e}")
        return documents[:top_k]
