from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from .event import LearningEvent
from .memory import (
    LearningKnowledge,
    LearningKnowledgeMemory,
)
from .models import LearningResult

logger = logging.getLogger(__name__)


class LearningService:

    def __init__(
        self,
        knowledge: LearningKnowledgeMemory
    ) -> None:

        self._event = LearningEvent()

        self._knowledge: LearningKnowledgeMemory = knowledge

    @property
    def event(
        self,
    ) -> LearningEvent:
        return self._event

    @property
    def knowledge(
        self,
    ) -> LearningKnowledge:
        return self._knowledge

    async def process(
        self,
        *,
        business_id: str,
        learn: Callable[
            [
                str,
                list[dict[str, Any]],
            ],
            Any,
        ],
        batch_size: int,
    ) -> LearningResult:

        business_id = self._validate_business_id(
            business_id,
        )

        if batch_size <= 0:
            raise ValueError(
                "batch_size must be greater than zero.",
            )

        final_result = LearningResult()

        # ======================================================
        # Process one document at a time.
        #
        # We NEVER move to another document until the current
        # document has been completely processed and committed.
        #
        # Source of truth: status column on business_events.
        # bla_cursors is kept as optimization only.
        # ======================================================

        document_count = 0

        while True:

            documents = (
                await self._event.get_next_pending_document(
                    business_id=business_id,
                )
            )

            if not documents:
                return final_result

            document = documents[0]

            document_key = document.get(
                "document_key",
            )

            if not isinstance(
                document_key,
                str,
            ) or not document_key.strip():

                raise ValueError(
                    "Business event document requires "
                    "a valid 'document_key'.",
                )

            document_key = document_key.strip()

            result, committed_cursor = await self._process_document(
                business_id=business_id,
                document_key=document_key,
                learn=learn,
                batch_size=batch_size,
            )

            # Mark all chunks of this document as processed
            await self._event.mark_document_processed(
                business_id=business_id,
                document_key=document_key,
            )

            document_count += 1

            # --------------------------------------------------
            # This document is fully learned, saved and
            # committed. Report it before moving on to the
            # next document's chunks.
            # --------------------------------------------------

            logger.info(
                "BLA document processing completed: "
                "business_id=%s "
                "document_key=%s "
                "documents_done=%s "
                "learned respond=%s",
                business_id,
                document_key,
                document_count,
                str(result.knowledge),
            )

            final_result = result

    # ==========================================================
    # Process one document
    # ==========================================================

    async def _process_document(
        self,
        *,
        business_id: str,
        document_key: str,
        learn: Callable[
            [
                str,
                list[dict[str, Any]],
            ],
            Any,
        ],
        batch_size: int,
    ) -> tuple[LearningResult, int]:

        # ------------------------------------------------------
        # Get all chunks for the document.
        #
        # The RPC guarantees ordering by chunk_index.
        # ------------------------------------------------------

        chunks = (
            await self._event.get_document_chunks(
                business_id=business_id,
                document_key=document_key,
            )
        )

        if not chunks:
            raise RuntimeError(
                "No chunks found for document "
                f"{document_key!r}.",
            )

        chunks.sort(
            key=lambda event: int(
                event["chunk_index"],
            ),
        )

        self._validate_document_chunks(
            document_key=document_key,
            chunks=chunks,
        )

        # Mark cursor as processing before starting work
        target_sequence_id = int(chunks[-1]["sequence_id"])
        await self._event.mark_processing(
            business_id=business_id,
            cursor=target_sequence_id,
        )

        # ------------------------------------------------------
        # Load the checkpoint.
        #
        # If the worker previously failed at chunk 4, the
        # checkpoint will contain chunk 3 and the accumulated
        # learned information up to chunk 3.
        #
        # Therefore we resume from chunk 4.
        # ------------------------------------------------------

        checkpoint = await self._event.get_checkpoint(
            business_id=business_id,
            document_key=document_key,
        )

        if checkpoint:

            last_chunk_index = int(
                checkpoint["last_chunk_index"],
            )

            last_sequence_id = int(
                checkpoint["last_sequence_id"],
            )

            accumulated_payload = (
                checkpoint.get(
                    "accumulated_payload",
                )
                or ""
            )

            if not isinstance(
                accumulated_payload,
                str,
            ):
                raise TypeError(
                    "Checkpoint accumulated_payload "
                    "must be a string.",
                )

            # --------------------------------------------------
            # chunk_index is 1-based, while `chunks` is a
            # 0-based list.
            #
            # chunk_index k  ->  chunks[k - 1]
            #
            # Resuming therefore starts at list position
            # `last_chunk_index` (which is chunk_index k + 1).
            # --------------------------------------------------

            start_index = last_chunk_index

            # --------------------------------------------------
            # Make sure checkpoint is actually inside this
            # document.
            # --------------------------------------------------

            if (
                last_chunk_index < 1
                or last_chunk_index > len(chunks)
            ):

                raise RuntimeError(
                    "Checkpoint chunk index is outside "
                    "the document. "
                    f"document_key={document_key!r}, "
                    f"last_chunk_index={last_chunk_index}, "
                    f"total_chunks={len(chunks)}.",
                )

            checkpoint_chunk = chunks[
                last_chunk_index - 1
            ]

            if int(
                checkpoint_chunk["sequence_id"],
            ) != last_sequence_id:

                raise RuntimeError(
                    "Checkpoint sequence_id does not match "
                    "the corresponding document chunk. "
                    f"document_key={document_key!r}.",
                )

        else:

            last_chunk_index = 0
            last_sequence_id = -1
            accumulated_payload = ""
            start_index = 0

        # ======================================================
        # Checkpoint already represents the complete document.
        #
        # This can happen if the worker crashed after saving
        # the final checkpoint but before committing the global
        # business cursor.
        # ======================================================

        if start_index >= len(chunks):

            final_sequence_id = int(
                chunks[-1]["sequence_id"],
            )

            result = await self._learn_final_checkpoint(
                business_id=business_id,
                document_key=document_key,
                accumulated_payload=accumulated_payload,
                learn=learn,
                total_chunks=len(chunks),
                last_chunk_index=len(chunks),
            )

            self._validate_result(
                result,
            )

            if result.knowledge:

                await self._knowledge.save_knowledge(
                    knowledge=result.knowledge,
                )

            await self._event.commit(
                business_id=business_id,
                cursor=final_sequence_id,
            )

            await self._event.delete_checkpoint(
                business_id=business_id,
                document_key=document_key,
            )

            return result, final_sequence_id

        # ======================================================
        # Process chunks sequentially.
        # ======================================================

        result = LearningResult()

        # ------------------------------------------------------
        # The checkpoint contains the learned state from the
        # previous successfully processed chunk.
        # ------------------------------------------------------

        previous_data = accumulated_payload

        # ------------------------------------------------------
        # batch_size controls how many chunks we fetch from the
        # already-known document at once.
        #
        # It does NOT allow us to process documents in parallel.
        # The chunks themselves remain strictly sequential.
        # ------------------------------------------------------

        for batch_start in range(
            start_index,
            len(chunks),
            batch_size,
        ):

            batch_end = min(
                batch_start + batch_size,
                len(chunks),
            )

            chunk_batch = chunks[
                batch_start:batch_end
            ]

            for chunk in chunk_batch:

                chunk_index = int(
                    chunk["chunk_index"],
                )

                sequence_id = int(
                    chunk["sequence_id"],
                )

                payload = chunk.get(
                    "payload",
                )

                if not isinstance(
                    payload,
                    str,
                ):
                    raise TypeError(
                        "Business event payload "
                        "must be a string.",
                    )

                # --------------------------------------------------
                # Build the input for this learning step.
                #
                # Previous learned information + current raw chunk.
                #
                # Example:
                #
                # chunk 0:
                #     raw chunk 0
                #
                # chunk 1:
                #     learned(chunk 0) + raw chunk 1
                #
                # chunk 2:
                #     learned(chunk 1) + raw chunk 2
                # --------------------------------------------------

                if previous_data:

                    information_payload = (
                        "[PREVIOUS PROCESSED INFORMATION]\n"
                        f"{previous_data}\n\n"
                        "[NEW DOCUMENT CHUNK]\n"
                        f"{payload}"
                    )

                else:

                    information_payload = payload

                result = await learn(
                    business_id=business_id,
                    information=[
                        {
                            "document_key": document_key,
                            "chunk_index": chunk_index,
                            "total_chunks": int(
                                chunk["total_chunks"],
                            ),
                            "payload": information_payload,
                        },
                    ],
                )

                self._validate_result(
                    result,
                )

                # --------------------------------------------------
                # Extract the state required by the next chunk.
                # --------------------------------------------------

                processed_data = (
                    self._extract_processed_data(
                        result=result,
                        fallback=information_payload,
                    )
                )

                # --------------------------------------------------
                # CRITICAL:
                #
                # Save checkpoint immediately after this chunk
                # succeeds and BEFORE processing the next chunk.
                #
                # If chunk 4 fails:
                #
                # checkpoint = chunk 3
                #
                # On restart:
                #
                # start_index = 4
                # previous_data = checkpoint data from chunk 3
                # --------------------------------------------------

                await self._event.save_checkpoint(
                    business_id=business_id,
                    document_key=document_key,
                    last_chunk_index=chunk_index,
                    last_sequence_id=sequence_id,
                    accumulated_payload=processed_data,
                    total_chunks=int(
                        chunk["total_chunks"],
                    ),
                )

                previous_data = processed_data

        # ======================================================
        # COMPLETE DOCUMENT
        # ======================================================

        if result.knowledge:

            await self._knowledge.save_knowledge(
                knowledge=result.knowledge,
            )

        final_sequence_id = int(
            chunks[-1]["sequence_id"],
        )

        # ------------------------------------------------------
        # Only now advance the global business cursor.
        # ------------------------------------------------------

        await self._event.commit(
            business_id=business_id,
            cursor=final_sequence_id,
        )

        # ------------------------------------------------------
        # Document is completely committed.
        # Checkpoint is no longer needed.
        # ------------------------------------------------------

        await self._event.delete_checkpoint(
            business_id=business_id,
            document_key=document_key,
        )

        return result, final_sequence_id

    # ==========================================================
    # Final checkpoint recovery
    # ==========================================================

    async def _learn_final_checkpoint(
        self,
        *,
        business_id: str,
        document_key: str,
        accumulated_payload: str,
        learn: Callable[
            [
                str,
                list[dict[str, Any]],
            ],
            Any,
        ],
        total_chunks: int,
        last_chunk_index: int,
    ) -> LearningResult:

        if not accumulated_payload.strip():

            return LearningResult()

        return await learn(
            business_id=business_id,
            information=[
                {
                    "document_key": document_key,
                    "chunk_index": last_chunk_index,
                    "total_chunks": total_chunks,
                    "payload": accumulated_payload,
                },
            ],
        )

    # ==========================================================
    # Extract checkpoint state
    # ==========================================================

    @staticmethod
    def _extract_processed_data(
        *,
        result: LearningResult,
        fallback: str,
    ) -> str:

        # ------------------------------------------------------
        # Use the knowledge output from the LLM as the
        # rolling summary for the next chunk.
        # This prevents the accumulated payload from growing
        # with repeated headers.
        # ------------------------------------------------------

        if result.knowledge:
            # knowledge is list[str], join them
            joined = "\n".join(result.knowledge).strip()
            if joined:
                return joined

        # ------------------------------------------------------
        # Preferred durable learning state.
        # ------------------------------------------------------

        if hasattr(
            result,
            "learned_context",
        ):

            learned_context = getattr(
                result,
                "learned_context",
            )

            if (
                isinstance(
                    learned_context,
                    str,
                )
                and learned_context.strip()
            ):

                return learned_context

        # ------------------------------------------------------
        # Alternative result content.
        # ------------------------------------------------------

        if hasattr(
            result,
            "content",
        ):

            content = getattr(
                result,
                "content",
            )

            if (
                isinstance(
                    content,
                    str,
                )
                and content.strip()
            ):

                return content

        # ------------------------------------------------------
        # Fallback — use the raw payload only (not the full
        # information_payload with headers).
        # ------------------------------------------------------

        return fallback

    # ==========================================================
    # Document validation
    # ==========================================================

    @staticmethod
    def _validate_document_chunks(
        *,
        document_key: str,
        chunks: list[dict[str, Any]],
    ) -> None:

        if not chunks:

            raise ValueError(
                "Document contains no chunks.",
            )

        total_chunks = int(
            chunks[0]["total_chunks"],
        )

        if total_chunks <= 0:

            raise ValueError(
                "Document total_chunks must be "
                "greater than zero.",
            )

        if len(chunks) != total_chunks:

            raise RuntimeError(
                "Document is incomplete. "
                f"document_key={document_key!r}, "
                f"expected={total_chunks}, "
                f"received={len(chunks)}.",
            )

        expected_indexes = set(
            range(
                1,
                total_chunks + 1,
            ),
        )

        actual_indexes = {
            int(
                chunk["chunk_index"],
            )
            for chunk in chunks
        }

        if actual_indexes != expected_indexes:

            raise RuntimeError(
                "Document chunks are incomplete "
                "or invalid. "
                f"document_key={document_key!r}, "
                f"expected_indexes={expected_indexes}, "
                f"actual_indexes={actual_indexes}.",
            )

        sequence_ids = [
            int(
                chunk["sequence_id"],
            )
            for chunk in chunks
        ]

        if sequence_ids != sorted(
            sequence_ids,
        ):

            raise RuntimeError(
                "Document chunks are not ordered by "
                "sequence_id. "
                f"document_key={document_key!r}.",
            )

    # ==========================================================
    # Validation
    # ==========================================================

    @staticmethod
    def _validate_business_id(
        business_id: str,
    ) -> str:

        if not isinstance(
            business_id,
            str,
        ):

            raise TypeError(
                "business_id must be a string.",
            )

        business_id = business_id.strip()

        if not business_id:

            raise ValueError(
                "business_id cannot be empty.",
            )

        return business_id

    @staticmethod
    def _validate_result(
        result: Any,
    ) -> None:

        if not isinstance(
            result,
            LearningResult,
        ):

            raise TypeError(
                "learn must return LearningResult.",
            )
