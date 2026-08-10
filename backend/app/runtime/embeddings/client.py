
from .nvidia import ENvidiaEmbedding

global _client

_client = ENvidiaEmbedding()


def get_embedding_client():
    return _client
