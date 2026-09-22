"""
GUI display dataclasses (read-only views assembled from DB rows)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EvalPhase(str, Enum):
    """Which pipeline phase is being evaluated."""
    PHASE1 = "phase1"
    PHASE2 = "phase2"


@dataclass
class Phase1Item:
    """One row shown to the evaluator during Phase 1 (extraction evaluation)."""
    id: int
    model_name: str
    raw_text: str
    file_path: str = ""


@dataclass
class BasePhase2Item:
    """Common base for all Phase-2 evaluation items."""


@dataclass
class Phase2Item(BasePhase2Item):
    """One row shown to the evaluator during Phase 2 (analysis evaluation)."""
    id: int
    model_name: str
    parent_raw_text: str
    result: str


@dataclass
class ModelGoldenUsage:
    """
    Tracks which golden text IDs have already been matched per model for the
    current document/evaluator. Stored as a single object in session state.

    Prevents the same golden text from appearing in the selectbox twice for
    the same model -- while keeping it visible for other models.
    """
    _assignments: dict[str, set[int]] = field(default_factory=dict)

    def is_used(self, model_name: str, golden_id: int) -> bool:
        """Return True if golden_id has already been matched for model_name."""
        return golden_id in self._assignments.get(model_name, set())

    def mark(self, model_name: str, golden_id: int) -> None:
        """Record that golden_id was matched to an extracted text from model_name."""
        self._assignments.setdefault(model_name, set()).add(golden_id)

    def used_for(self, model_name: str) -> set[int]:
        """Return the set of golden IDs already used for model_name."""
        return self._assignments.get(model_name, set())

    @classmethod
    def from_db(cls, raw: dict[str, set[int]]) -> "ModelGoldenUsage":
        """Build from the dict returned by ExtractedTextEvalRepository.get_matched_golden_ids_by_model."""
        obj = cls()
        obj._assignments = {k: set(v) for k, v in raw.items()}
        return obj


@dataclass
class BenchPhase2Item(BasePhase2Item):
    """
    One Phase-2 record: one model's analysis cards compared to the human cards
    for a single golden extracted text.
    """
    extracted_text_id: int  # parent golden extracted text ID
    raw_text: str  # golden sentence shown at the top as context
    model_name: str  # model being evaluated
    model_analysis_id: int  # ANALYZED_TEXT.id -- used when saving the verdict
    model_cards: list[dict[str, Any]]  # one dict per item extracted by model
    # one dict per item in human ground truth (may be [])
    human_cards: list[dict[str, Any]]
