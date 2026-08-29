from __future__ import annotations

from typing import Any, Sequence

from app.runtime.agents.agent import Agent
from app.runtime.llm_vendors.langchain import LangChainLLM
from app.runtime.utils.tag_parser import (
    extract_json,
    extract_tag,
)

from .agent_router import (
    EntityAgentRouter,
    entity_agent_router,
)
from .config.config import EntityConfig
from .service import (
    EntityService,
    entity_service,
)
from .types import EntityInput, EntityResolution


class EntityAgent:

    def __init__(
        self,
        *,
        config: EntityConfig | None = None,
        router: EntityAgentRouter = entity_agent_router,
        entity_service: EntityService = entity_service,
        llm: LangChainLLM,
    ) -> None:
        self.config = config
        self.router = router
        self.entity_service = entity_service
        self.llm = llm

    # ========================================================================
    # RUN / ORCHESTRATION
    # ========================================================================

    async def run(
        self,
        *,
        business_id: str,
        object_type: str,
        source: str | None = None,
        chunks: Sequence[Any] | None = None,
    ) -> list[EntityResolution]:

        route = await self.router.route(
            business_id=business_id,
            object_type=object_type,
        )

        if route is None:
            raise ValueError(
                f"No enabled entity agent configured for "
                f"{object_type}"
            )

        self.config = route.config

        document_chunks = self._normalize_chunks(
            source=source,
            chunks=chunks,
        )

        if not document_chunks:
            raise ValueError(
                f"No content provided for entity extraction: "
                f"{object_type}"
            )

        specialist = Agent(
            name=route.agent_name,
            llm=self.llm,
            instructions=self.build_extraction_prompt(),
            enable_runtime_mem=False,
            enable_runtime_rag=False,
            enable_self_reflection=False,
        )

        # IMPORTANT:
        # One session is used for the entire document.
        #
        # This allows the specialist to see previous chunks and maintain
        # document-level context while processing the current chunk.
        session = specialist.create_session()

        extracted_entities: list[dict[str, Any]] = []

        total_chunks = len(document_chunks)

        for index, chunk in enumerate(document_chunks):

            response = await session.run(
                self.build_chunk_prompt(
                    chunk=chunk,
                    chunk_index=index,
                    total_chunks=total_chunks,
                ),
            )

            entities = self.parse_response(
                response.text,
            )

            print('entities, extracted >>>>', entities)

            extracted_entities.extend(
                entities,
            )

        if not extracted_entities:
            return []

        # --------------------------------------------------------------------
        # FINAL CONSOLIDATION
        #
        # The specialist has already seen the complete document through the
        # same session. We now ask it to merge duplicate/partial entities.
        # --------------------------------------------------------------------

        consolidated_response = await session.run(
            self.build_consolidation_prompt(
                entities=extracted_entities,
            ),
        )

        consolidated_entities = self.parse_response(
            consolidated_response.text,
        )

        resolutions: list[EntityResolution] = []

        for data in consolidated_entities:

            entity = self.build_output(
                data,
            )

            resolution = await self.entity_service.resolve(
                business_id=business_id,
                entity=entity,
            )

            resolutions.append(
                resolution,
            )

        return resolutions

    # ========================================================================
    # CHUNK NORMALIZATION
    # ========================================================================

    @staticmethod
    def _normalize_chunks(
        *,
        source: str | None,
        chunks: Sequence[Any] | None,
    ) -> list[str]:

        if chunks is not None:

            result: list[str] = []

            for chunk in chunks:

                if isinstance(chunk, str):
                    content = chunk

                else:
                    content = getattr(
                        chunk,
                        "content",
                        None,
                    )

                if not isinstance(content, str):
                    continue

                content = content.strip()

                if content:
                    result.append(
                        content,
                    )

            return result

        if source is not None:

            source = source.strip()

            if source:
                return [source]

        return []

    # ========================================================================
    # EXTRACTION PROMPT
    # ========================================================================

    def build_extraction_prompt(self) -> str:

        if self.config is None:
            raise ValueError(
                "Entity configuration is required "
                "before building extraction prompt"
            )

        fields: list[str] = []

        for field in self.config.fields:

            aliases = (
                f" Aliases: {', '.join(field.aliases)}."
                if field.aliases
                else ""
            )

            required = (
                " Required."
                if field.required
                else " Optional."
            )

            description = (
                field.description
                or field.type
            )

            fields.append(
                f"- {field.name}: "
                f"{description}."
                f"{required}"
                f"{aliases}"
            )

        field_definitions = "\n".join(
            fields
        )

        instructions = ""

        if self.config.agent is not None:
            instructions = (
                self.config.agent.instructions.strip()
            )

        return f"""
You are the specialist responsible for extracting
{self.config.object_type} entities from a document.

Entity type:
{self.config.object_type}

Fields:
{field_definitions}

{instructions}

The document may be provided in multiple chunks.

All chunks belong to the SAME document.

Maintain context across chunks.

Rules:

- Extract only information explicitly supported by
  the document.
- Do not invent or infer unsupported information.
- A single chunk may contain zero, one, or many
  entities.
- The same entity may appear across multiple chunks.
- Do not assume that two mentions are different
  entities merely because they occur in different
  chunks.
- Preserve context from previous chunks.
- Use the configured field names exactly.
- Normalize values when appropriate.
- Missing values may temporarily be null while
  processing individual chunks.
- Final validation happens after consolidation.
- Return extraction results only inside an
  <entities> tag.
- The content inside <entities> must be a valid
  JSON array.
- Do not return markdown.
- Do not return explanations.
- Do not return any other tags.

Chunk response format:

<entities>
[
    {{
        "field_name": "value"
    }}
]
</entities>
""".strip()

    # ========================================================================
    # CHUNK PROMPT
    # ========================================================================

    def build_chunk_prompt(
        self,
        *,
        chunk: str,
        chunk_index: int,
        total_chunks: int,
    ) -> str:

        return f"""
Process chunk {chunk_index + 1} of {total_chunks}
from the SAME document.

Previous chunks are part of this same document and
their context must be preserved.

Current chunk:

{chunk}

Extract every {self.config.object_type}
entity that is supported by this chunk.

Important:

- There may be multiple entities.
- An entity may have been introduced in a previous
  chunk.
- If this chunk adds information to an entity already
  seen, associate the information with that entity.
- Do not invent missing information.
- Do not treat repeated mentions as automatically
  being different entities.

Return only:

<entities>
[
    {{
        "field_name": "value"
    }}
]
</entities>
""".strip()

    # ========================================================================
    # CONSOLIDATION
    # ========================================================================

    def build_consolidation_prompt(
        self,
        *,
        entities: list[dict[str, Any]],
    ) -> str:

        if self.config is None:
            raise ValueError(
                "Entity configuration is required "
                "before consolidation"
            )

        return f"""
The complete document has now been processed.

You extracted candidate {self.config.object_type}
entities from multiple chunks.

Consolidate the candidates into the final set of
entities.

Candidates:

{entities}

Rules:

- Merge candidates that clearly refer to the same
  real-world entity.
- Do not merge different entities.
- Combine information from different chunks when
  they refer to the same entity.
- Prefer the most complete supported value when
  multiple chunks provide the same field.
- Do not invent values.
- Remove duplicate entities.
- Use only these configured fields:

{chr(10).join(
            f"- {field.name}: {field.description or field.type}"
            for field in self.config.fields
        )}

- Required fields must be present in the final
  result.
- Return only the final entities.
- Return exactly one <entities> tag.
- The content inside <entities> must be a valid
  JSON array.
- Do not return markdown.
- Do not return explanations.
- Do not return any other tags.

Required response:

<entities>
[
    {{
        "field_name": "value"
    }}
]
</entities>
""".strip()

    # ========================================================================
    # RESPONSE PARSING
    # ========================================================================

    @staticmethod
    def parse_response(
        text: str,
    ) -> list[dict[str, Any]]:

        raw = extract_tag(
            text,
            "entities",
        )

        # Backwards compatibility with a specialist that
        # returns a single <entity>.
        if not raw:
            raw = extract_tag(
                text,
                "entity",
            )

        if not raw:
            return
            # raise ValueError(
            #     "Entity agent response does not contain "
            #     "<entities> tag"
            # )

        parsed = extract_json(
            raw,
        )

        if isinstance(parsed, dict):
            return [parsed]

        if not isinstance(parsed, list):
            raise ValueError(
                "Entity agent response must contain "
                "a JSON array"
            )

        result: list[dict[str, Any]] = []

        for item in parsed:

            if not isinstance(item, dict):
                raise ValueError(
                    "Each item inside <entities> "
                    "must be a JSON object"
                )

            result.append(
                item,
            )

        return result

    # ========================================================================
    # OUTPUT
    # ========================================================================

    def build_output(
        self,
        data: dict[str, Any],
    ) -> EntityInput:

        if self.config is None:
            raise ValueError(
                "Entity configuration is required "
                "before building output"
            )

        self.validate_output(
            data,
        )

        filtered_data = self.filter_data(
            data,
        )

        return EntityInput(
            object_type=self.config.object_type,
            data=filtered_data,
        )

    def filter_data(
        self,
        data: dict[str, Any],
    ) -> dict[str, Any]:

        if self.config is None:
            raise ValueError(
                "Entity configuration is required "
                "before filtering output"
            )

        field_names = set(
            self.config.field_names()
        )

        return {
            field_name: value
            for field_name, value in data.items()
            if field_name in field_names
        }

    # ========================================================================
    # VALIDATION
    # ========================================================================

    def validate_output(
        self,
        data: dict[str, Any],
    ) -> None:

        if self.config is None:
            raise ValueError(
                "Entity configuration is required "
                "before validating output"
            )

        unknown_fields = (
            set(data)
            - set(self.config.field_names())
        )

        if unknown_fields:
            raise ValueError(
                "Unknown entity fields for "
                f"{self.config.object_type}: "
                f"{', '.join(sorted(unknown_fields))}"
            )

        missing_fields = [
            field.name
            for field in self.config.required_fields()
            if field.name not in data
            or data[field.name] is None
        ]

        if missing_fields:
            raise ValueError(
                "Missing required entity fields for "
                f"{self.config.object_type}: "
                f"{', '.join(missing_fields)}"
            )
