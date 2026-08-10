import logging
from typing import Any
import pyarrow as pa
from lancedb.rerankers import Reranker
from app.config.settings import settings

logger = logging.getLogger(__name__)

MAX_RERANK_CHARS = 6000
SCORE_COL = "_relevance_score"


class EReranker(Reranker):

    def __init__(self, return_score="relevance"):
        super().__init__(return_score)
        self._client = None

    def _get_client(self):
        if self._client is None:
            from langchain_nvidia_ai_endpoints import NVIDIARerank
            self._client = NVIDIARerank(
                model=settings.nvidia_rerank_model,
                api_key=settings.nvidia_api_key,
            )
        return self._client

    def _score_documents(self, query: str, texts: list[str]) -> list[float]:
        from langchain_core.documents import Document

        client = self._get_client()
        docs = [Document(page_content=t[:MAX_RERANK_CHARS]) for t in texts]
        try:
            results = client.compress_documents(query=query, documents=docs)
            score_map = {}
            for doc in results:
                score_map[doc.page_content] = doc.metadata.get(
                    "relevance_score", 0.0)
            return [score_map.get(t[:MAX_RERANK_CHARS], 0.0) for t in texts]
        except Exception as e:
            logger.warning(f"Reranking failed: {e}")
            return [1.0 / (i + 1) for i in range(len(texts))]

    def rerank_hybrid(self, query: str, vector_results: pa.Table, fts_results: pa.Table) -> pa.Table:
        combined = self.merge_results(vector_results, fts_results)
        texts = combined.column("content").to_pylist()
        scores = self._score_documents(query, texts)
        combined = combined.append_column(
            SCORE_COL, pa.array(scores, type=pa.float64())
        )
        indices = sorted(range(len(scores)),
                         key=lambda i: scores[i], reverse=True)
        return combined.take(indices)

    def rerank_vector(self, query: str, vector_results: pa.Table) -> pa.Table:
        texts = vector_results.column("content").to_pylist()
        scores = self._score_documents(query, texts)
        vector_results = vector_results.append_column(
            SCORE_COL, pa.array(scores, type=pa.float64())
        )
        indices = sorted(range(len(scores)),
                         key=lambda i: scores[i], reverse=True)
        return vector_results.take(indices)

    def rerank_fts(self, query: str, fts_results: pa.Table) -> pa.Table:
        texts = fts_results.column("content").to_pylist()
        scores = self._score_documents(query, texts)
        fts_results = fts_results.append_column(
            SCORE_COL, pa.array(scores, type=pa.float64())
        )
        indices = sorted(range(len(scores)),
                         key=lambda i: scores[i], reverse=True)
        return fts_results.take(indices)


reranker_instance = EReranker()
