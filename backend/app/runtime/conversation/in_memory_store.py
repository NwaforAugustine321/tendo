from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import lancedb
from lancedb.pydantic import LanceModel
from pydantic import Field
from app.runtime.chat.message import ChatMessage
from .context import ConversationContext
from .store import ConversationStore


class MessageRecord(LanceModel):
    """
    One row per message.
    """

    conversation_id: str

    role: str

    content: str

    created_at: datetime


class InMemConversationStore(ConversationStore):
    """
    Conversation store.

    """

    def __init__(
        self,
        *,
        namespace: str,
        db: lancedb.DBConnection | None = None,
        uri: str | Path = "./data/conversations",
        table_name: str = "messages",
    ) -> None:

        self._db = (
            db
            or lancedb.connect(
                str(
                    Path(uri) / namespace
                )
            )
        )

        if table_name in self._db.table_names():

            self._table = self._db.open_table(
                table_name,
            )

        else:

            self._table = self._db.create_table(
                table_name,
                schema=MessageRecord,
            )

    async def save(
        self,
        *,
        conversation: ConversationContext,
    ) -> None:
        """
        Save messages.
        """

        conversation_id = conversation.conversation_id or ""

        if not conversation.messages:
            return

        dicts = ChatMessage.to_dicts(conversation.messages)

        if not dicts:
            return

        now = datetime.now(UTC)

        rows = [
            MessageRecord(
                conversation_id=conversation_id,
                role=d["role"],
                content=d["content"],
                created_at=now,
            )
            for d in dicts
        ]

        self._table.add(rows)

    async def load(
        self,
        **kwargs: Any,
    ) -> ConversationContext:
        """
        Load all messages for a conversation.
        """

        conversation_id = kwargs.get(
            "conversation_id",
        )
        limit = kwargs.get(
            "limit",
            10,
        )

        if isinstance(limit, int):
            limit = 10

        if conversation_id is None:
            return ConversationContext()

        try:
            rows = (
                self._table.search()
                .where(
                    f"conversation_id = '{conversation_id}'"
                )
                .limit(limit)
                .to_list()
            )
        except Exception:
            rows = []

        dicts = [
            {"role": row["role"], "content": row["content"]}
            for row in rows
        ]

        messages = ChatMessage.from_dicts(dicts)

        return ConversationContext(
            conversation_id=conversation_id,
            messages=messages,
        )

    async def find_all(
        self,
        **kwargs: Any,
    ) -> list[ConversationContext]:

        limit = kwargs.get(
            "limit",
            10,
        )

        if isinstance(limit, int):
            limit = 10

        rows = self._table.search().limit(limit).to_list()

        # Group by conversation_id.
        groups: dict[str, list] = {}

        for row in rows:
            cid = row["conversation_id"]
            if cid not in groups:
                groups[cid] = []
            groups[cid].append(
                {"role": row["role"], "content": row["content"]}
            )

        return [
            ConversationContext(
                conversation_id=cid,
                messages=ChatMessage.from_dicts(dicts),
            )
            for cid, dicts in groups.items()
        ]

    async def delete(
        self,
        **kwargs: Any,
    ) -> None:

        conversation_id = kwargs.get(
            "conversation_id",
        )

        if conversation_id is None:
            return

        self._table.delete(
            f"conversation_id = '{conversation_id}'"
        )
