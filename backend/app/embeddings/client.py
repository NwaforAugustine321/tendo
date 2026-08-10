from app.embeddings.nvidia import get_client as get_nvidia


def get_embedding_client():
    return get_nvidia()
