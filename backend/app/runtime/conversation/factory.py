from __future__ import annotations

from .provider import ConversationProvider
from .store import ConversationStore


def create_conversation_provider(
    *,
    store: ConversationStore,
) -> ConversationProvider:
    """
    Create a ConversationProvider.
    """

    return ConversationProvider(
        store=store,
    )
