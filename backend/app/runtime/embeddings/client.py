from .nvidia import ENvidiaEmbedding

_client = None


def get_embedding_client():
    global _client
    if _client is None:
        _client = ENvidiaEmbedding()
    return _client
