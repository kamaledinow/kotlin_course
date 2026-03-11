from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class Data:
    """Episode container used for generation and deterministic eval."""

    question: str
    answer: str
    difficulty: int = 1
    initial_state: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "difficulty": self.difficulty,
            "initial_state": self.initial_state,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "Data":
        return cls(
            question=payload["question"],
            answer=payload["answer"],
            difficulty=payload.get("difficulty", 1),
            initial_state=payload.get("initial_state", {}),
            metadata=payload.get("metadata", {}),
        )
