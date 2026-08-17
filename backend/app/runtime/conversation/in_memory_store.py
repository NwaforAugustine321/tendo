from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import lancedb
from lancedb.pydantic import LanceModel
from pydantic import Field
from app.db.tools.messages import save_messages
from app.runtime.chat.message import ChatMessage

from .context import ConversationContext
from .store import ConversationStore

logger = logging.getLogger(__name__)


class ConversationRecord(LanceModel):
    """
    One row per conversation.
    """

    conversation_id: str

    summary: str | None = None

    metadata: str = Field(
        default="{}",
    )

    created_at: datetime

    updated_at: datetime


class MessageRecord(LanceModel):
    """
    One row per message.
    """

    message_id: str

    conversation_id: str

    role: str

    content: str

    created_at: datetime


class InMemConversationStore(
    ConversationStore,
):
    """
    LanceDB implementation of ConversationStore.
    """

    def __init__(
        self,
        *,
        namespace: str,
        db: lancedb.DBConnection | None = None,
        uri: str | Path = "./data/conversations",
    ) -> None:

        self._namespace = namespace

        self._db = (
            db
            or lancedb.connect(
                str(
                    Path(uri) / namespace
                )
            )
        )

        self._conversation_table = (
            self._get_or_create_table(
                "conversations",
                ConversationRecord,
            )
        )

        self._message_table = (
            self._get_or_create_table(
                "messages",
                MessageRecord,
            )
        )

    def _get_or_create_table(
        self,
        name: str,
        schema: type[LanceModel],
    ):

        if name in self._db.table_names():
            return self._db.open_table(
                name,
            )

        return self._db.create_table(
            name,
            schema=schema,
        )

    async def save_conversation(
        self,
        *,
        conversation: ConversationContext,
    ) -> None:

        conversation_id = conversation.conversation_id

        if conversation_id is None:
            raise ValueError(
                "conversation_id is required."
            )

        now = datetime.now(
            UTC,
        )

        rows = (
            self._conversation_table.search()
            .where(
                f"conversation_id = '{conversation_id}'"
            )
            .limit(1)
            .to_list()
        )

        if rows:

            self._conversation_table.update(
                where=(
                    f"conversation_id = "
                    f"'{conversation_id}'"
                ),
                values={
                    "summary": conversation.summary,
                    "metadata": json.dumps(
                        conversation.metadata,
                    ),
                    "updated_at": now,
                },
            )

            return

        self._conversation_table.add(
            [
                ConversationRecord(
                    conversation_id=conversation_id,
                    summary=conversation.summary,
                    metadata=json.dumps(
                        conversation.metadata,
                    ),
                    created_at=now,
                    updated_at=now,
                )
            ]
        )

    async def load_conversation(
        self,
        *,
        conversation_id: str,
    ) -> ConversationContext | None:

        rows = (
            self._conversation_table.search()
            .where(
                f"conversation_id = '{conversation_id}'"
            )
            .limit(1)
            .to_list()
        )

        if not rows:
            return None

        row = rows[0]

        return ConversationContext(
            conversation_id=row[
                "conversation_id"
            ],
            summary=row.get(
                "summary",
            ),
            metadata=json.loads(
                row.get(
                    "metadata",
                    "{}",
                )
            ),
        )

    async def find_all(
        self,
    ) -> list[ConversationContext]:

        rows = (
            self._conversation_table.search()
            .to_list()
        )

        return [
            ConversationContext(
                conversation_id=row[
                    "conversation_id"
                ],
                summary=row.get(
                    "summary",
                ),
                metadata=json.loads(
                    row.get(
                        "metadata",
                        "{}",
                    )
                ),
            )
            for row in rows
        ]

    async def delete_conversation(
        self,
        *,
        conversation_id: str,
    ) -> None:

        self._conversation_table.delete(
            (
                f"conversation_id = "
                f"'{conversation_id}'"
            )
        )

        await self.delete_messages(
            conversation_id=conversation_id,
        )

    async def append_messages(
        self,
        *,
        conversation_id: str,
        messages: list[ChatMessage],
    ) -> None:

        if not messages:
            return

        now = datetime.now(
            UTC,
        )

        rows = [
            MessageRecord(
                message_id=message.message_id,
                conversation_id=conversation_id,
                role=message.role,
                content=str(
                    message.content,
                ),
                created_at=now,
            )
            for message in messages
        ]

        self._message_table.add(
            rows,
        )

        asyncio.create_task(
            self._persist_to_long_term_mem(
                conversation_id=conversation_id,
                messages=messages,
            )
        )

    async def _persist_to_long_term_mem(
        self,
        *,
        conversation_id: str,
        messages: list[ChatMessage],
    ) -> None:
        """Persist messages to long term memory without blocking the main flow."""

        try:

            msg_dicts = [
                {
                    "role": message.role,
                    "content": str(message.content),
                }
                for message in messages
                if message.role in ("user", "assistant", "system")
                and message.content
            ]

            if not msg_dicts:
                return

            await save_messages(
                business_id=self._namespace,
                session_id=conversation_id,
                messages=msg_dicts,
            )

        except Exception as exc:
            logger.warning(
                "Long term message persist failed: %s",
                exc,
            )

    async def load_messages(
        self,
        *,
        conversation_id: str,
        summary: str | None = None,
        limit: int | None = None,
    ) -> list[ChatMessage]:

        query = (
            self._message_table.search()
            .where(
                f"conversation_id = '{conversation_id}'"
            )
        )

        if limit is not None:
            query = query.limit(
                limit,
            )

        rows = query.to_list()

        rows.sort(
            key=lambda row: row[
                "created_at"
            ],
        )

        messages: list[
            ChatMessage
        ] = []

        if summary:

            messages.append(
                ChatMessage.summary(
                    summary,
                )
            )

        messages.extend(
            ChatMessage(
                message_id=row[
                    "message_id"
                ],
                role=row[
                    "role"
                ],
                content=row[
                    "content"
                ],
            )
            for row in rows
        )

        return messages

    async def delete_messages(
        self,
        *,
        conversation_id: str,
        message_ids: list[str] | None = None,
    ) -> None:

        #
        # Delete the entire conversation.
        #
        if message_ids is None:

            self._message_table.delete(
                (
                    f"conversation_id = "
                    f"'{conversation_id}'"
                )
            )

            return

        if not message_ids:
            return

        #
        # Delete summarized messages only.
        #
        for message_id in message_ids:

            self._message_table.delete(
                (
                    f"conversation_id = "
                    f"'{conversation_id}' "
                    f"AND message_id = "
                    f"'{message_id}'"
                )
            )
