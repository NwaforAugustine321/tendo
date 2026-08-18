from __future__ import annotations

from app.runtime.agents.run_context import (
    RunContext,
)

import re


class UserTaskPromptBuilder:
    """
    Builds the prompt section describing the
    current user request.
    """

    HEADER = (
        "\nUSER_TASK_TO_PROCESS:\n"
        "{task}\n\n"

    )

    def __init__(self):
        self._dangerous_patterns = [
            r'ignore\s+(all\s+)?previous\s+instructions?',
            r'you\s+are\s+now\s+(in\s+)?developer\s+mode',
            r'system\s+override',
            r'reveal\s+prompt',
        ]

        self._fuzzy_patterns = [
            'ignore', 'bypass', 'override', 'reveal', 'delete', 'system'
        ]

        self._high_risk_keywords = [
            "password", "api_key", "admin", "system prompt", "bypass", "override"
        ]

        self._injection_patterns = ["ignore instructions",
                                    "developer mode", "reveal prompt"]

    def build(
        self,
        message: str,
    ) -> str:

        if not message:
            return ""

        sanitized = self.sanitize_input(message)
        sanitized = self.detect_injection(sanitized)
        sanitized = self.requires_approval(sanitized)

        return self.HEADER.replace("{task}", sanitized)

    def detect_injection(self, text: str) -> str:
        # Standard pattern matching
        if any(re.search(pattern, text, re.IGNORECASE)
                for pattern in self._dangerous_patterns):
            return f"[INJECTION_DETECTED] {text}"

        # Fuzzy matching for misspelled words (typoglycemia defense)
        words = re.findall(r'\b\w+\b', text.lower())
        for word in words:
            for pattern in self._fuzzy_patterns:
                if self._is_similar_word(word, pattern):
                    return f"[INJECTION_DETECTED] {text}"
        return text

    def sanitize_input(self, text: str) -> str:
        # Normalize common obfuscations
        text = re.sub(r'\s+', ' ', text)  # Collapse whitespace
        text = re.sub(r'(.)\1{3,}', r'\1', text)  # Remove char repetition

        for pattern in self._dangerous_patterns:
            text = re.sub(pattern, '[FILTERED]', text, flags=re.IGNORECASE)
        return text

    def requires_approval(self, text: str) -> str:
        risk_score = sum(1 for keyword in self._high_risk_keywords
                         if keyword in text.lower())

        risk_score += sum(2 for pattern in self._injection_patterns
                          if pattern in text.lower())

        if risk_score >= 3:
            return f"[REQUIRES_APPROVAL] {text}"
        return text

    def _is_similar_word(self, word: str, target: str, threshold: int = 2) -> bool:
        if abs(len(word) - len(target)) > threshold:
            return False
        # Simple Levenshtein distance
        if len(word) < len(target):
            word, target = target, word
        prev = list(range(len(target) + 1))
        for i, c1 in enumerate(word, 1):
            curr = [i]
            for j, c2 in enumerate(target, 1):
                curr.append(min(
                    prev[j] + 1,
                    curr[j - 1] + 1,
                    prev[j - 1] + (0 if c1 == c2 else 1),
                ))
            prev = curr
        return prev[-1] <= threshold
