

from __future__ import annotations
import logging
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
from app.execution.models import ReflectionOutput
from app.memory.memory import Memory

logger = logging.getLogger(__name__)

SKILL_SCOPE = "/skills"
SIMILARITY_THRESHOLD = 0.85


class SkillOutcome(str, Enum):
    UPDATE = "update"
    MERGE = "merge"
    IGNORE = "ignore"
    CREATE = "create"


class SkillDecision(BaseModel):
    candidate: dict = Field(default_factory=dict)
    outcome: SkillOutcome
    rationale: str


class SkillManager:

    def __init__(self, business_id: str) -> None:
        self._business_id = business_id
        self._memory = Memory(scopes=[f"/business/{business_id}{SKILL_SCOPE}"], business_id=business_id)

    async def process_candidates(self, reflection: ReflectionOutput) -> list[SkillDecision]:
        decisions: list[SkillDecision] = []
        for candidate in reflection.candidate_skills:
            decision = await self._evaluate_candidate(candidate)
            decisions.append(decision)
        return decisions

    async def _evaluate_candidate(self, candidate: dict) -> SkillDecision:
        skill_id = candidate.get("skill_id", "")
        content = candidate.get("content", "")
        category = candidate.get("category", "")

        if not skill_id or not content:
            return SkillDecision(
                candidate=candidate,
                outcome=SkillOutcome.IGNORE,
                rationale="Missing skill_id or content",
            )

        similar = await self._memory.recall(content, limit=3)

        if not similar:
            return await self._create_skill(candidate)

        best_match = similar[0]
        best_content = best_match.content

        if self._is_duplicate(content, best_content):
            return SkillDecision(
                candidate=candidate,
                outcome=SkillOutcome.IGNORE,
                rationale=f"Duplicate of existing skill: {best_match.id}",
            )

        if self._is_similar_but_different(content, best_content):
            return await self._update_skill(candidate, best_match)

        return await self._create_skill(candidate)

    async def _create_skill(self, candidate: dict) -> SkillDecision:
        content = candidate.get("content", "")
        category = candidate.get("category", "")
        skill_id = candidate.get("skill_id", "")

        try:
            await self._memory.remember(
                content=content,
                metadata={"skill_id": skill_id, "category": category},
            )
            return SkillDecision(
                candidate=candidate,
                outcome=SkillOutcome.CREATE,
                rationale=f"New skill '{skill_id}' created",
            )
        except Exception as e:
            logger.warning("Failed to create skill '%s': %s", skill_id, e)
            return SkillDecision(
                candidate=candidate,
                outcome=SkillOutcome.IGNORE,
                rationale=f"Write failed: {e}",
            )

    async def _update_skill(self, candidate: dict, existing: Any) -> SkillDecision:
        content = candidate.get("content", "")
        category = candidate.get("category", "")
        skill_id = candidate.get("skill_id", "")

        try:
            self._memory._storage.delete_by_id(existing.id)
            await self._memory.remember(
                content=content,
                metadata={"skill_id": skill_id, "category": category},
            )
            return SkillDecision(
                candidate=candidate,
                outcome=SkillOutcome.UPDATE,
                rationale=f"Updated existing skill (replaced {existing.id})",
            )
        except Exception as e:
            logger.warning("Failed to update skill '%s': %s", skill_id, e)
            return SkillDecision(
                candidate=candidate,
                outcome=SkillOutcome.IGNORE,
                rationale=f"Write failed: {e}",
            )

    @staticmethod
    def _is_duplicate(new_content: str, existing_content: str) -> bool:
        new_norm = new_content.strip().lower()
        existing_norm = existing_content.strip().lower()
        return new_norm == existing_norm

    @staticmethod
    def _is_similar_but_different(new_content: str, existing_content: str) -> bool:
        new_norm = new_content.strip().lower()
        existing_norm = existing_content.strip().lower()
        if new_norm == existing_norm:
            return False
        shorter = min(len(new_norm), len(existing_norm))
        longer = max(len(new_norm), len(existing_norm))
        if longer == 0:
            return False
        return shorter / longer > 0.5

    async def get_skills(self, query: str, limit: int = 10) -> list[Any]:
        """Retrieve relevant skills for a given query."""
        return await self._memory.recall(query, limit=limit)
