"""Embedding provider module — vendor-switching layer for text embeddings."""

from app.embeddings.client import get_embedding_client

__all__ = ["get_embedding_client"]
