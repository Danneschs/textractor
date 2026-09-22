"""
Session state accessors for the evaluator GUI.

BaseSessionState provides @property access to fixed st.session_state keys.
Since only one mode runs per process, there is no risk of key collisions and
no namespace prefixes are needed.

The _KEY_* class constants name the string keys used in st.session_state
(not the values themselves). E.g. _KEY_INDEX = "index" stores an int index.

Empty-state logic relies on two conditions:
state.context is None -- records were never loaded for the current session
len(state.phaseN_records) == 0 -- loaded but exhausted (all evaluated or none exist)
"""

from __future__ import annotations

from typing import Optional, Sequence

import streamlit as st

from src.database.models import ExtractedTextRecord
from src.gui.models import (
    BasePhase2Item,
    EvalPhase,
    ModelGoldenUsage,
    Phase1Item,
)


class BaseSessionState:
    """
    Typed @property accessor layer over st.session_state.

    All persistent GUI state goes through this class. Direct access to
    st.session_state[key] is intentionally confined to this module.

    The context tuple (doc_id, user, phase) acts as the cache key: any change
    to it triggers a data reload in BaseEvaluator.render().
    """

    # Widget key for the phase radio button.
    KEY_PHASE = "eval_phase"

    # Private keys for programmatic state (not tied to any widget).
    _KEY_INDEX = "index"
    _KEY_P1_RECORDS = "phase1_records"
    _KEY_P2_RECORDS = "phase2_records"
    _KEY_CONTEXT = "context"

    def init(self) -> None:
        """Seed st.session_state with defaults on the first Streamlit run.

        Safe to call on every rerun -- only missing keys are written.
        Subclasses should call super().init() then seed their own keys.
        """
        defaults: dict = {
            self._KEY_INDEX: 0,
            self._KEY_P1_RECORDS: [],
            self._KEY_P2_RECORDS: [],
            self._KEY_CONTEXT: None,
            self.KEY_PHASE: EvalPhase.PHASE1,
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    @property
    def phase1_records(self) -> Sequence[Phase1Item]:
        """Current list of Phase-1 items to evaluate."""
        return st.session_state.get(self._KEY_P1_RECORDS, [])

    @phase1_records.setter
    def phase1_records(self, value: Sequence[Phase1Item]) -> None:
        st.session_state[self._KEY_P1_RECORDS] = value

    @property
    def phase2_records(self) -> Sequence[BasePhase2Item]:
        """Current list of Phase-2 items to evaluate."""
        return st.session_state.get(self._KEY_P2_RECORDS, [])

    @phase2_records.setter
    def phase2_records(self, value: Sequence[BasePhase2Item]) -> None:
        st.session_state[self._KEY_P2_RECORDS] = value

    @property
    def context(self) -> tuple[int, str, EvalPhase] | None:
        """The (doc_id, user, phase) tuple active when records were last loaded.

        None means records have never been loaded for the current session.
        """
        return st.session_state.get(self._KEY_CONTEXT)

    @context.setter
    def context(self, value: tuple[int, str, EvalPhase]) -> None:
        st.session_state[self._KEY_CONTEXT] = value

    @property
    def current_index(self) -> int:
        """Zero-based index of the record currently shown to the evaluator."""
        return st.session_state.get(self._KEY_INDEX, 0)

    @current_index.setter
    def current_index(self, value: int) -> None:
        st.session_state[self._KEY_INDEX] = value

    def advance(self) -> None:
        """Move forward by one record."""
        st.session_state[self._KEY_INDEX] = self.current_index + 1

    @property
    def evaluator_name(self) -> str:
        """The name entered in the sidebar text input. Empty string if not set."""
        return st.session_state.get("evaluator_name", "")

    @property
    def selected_doc_id(self) -> Optional[int]:
        """The document ID chosen in the sidebar selectbox. None if not selected."""
        return st.session_state.get("selected_doc_id")

    @property
    def eval_phase(self) -> EvalPhase:
        """The phase chosen via the sidebar radio button."""
        return st.session_state.get(self.KEY_PHASE, EvalPhase.PHASE1)


class BenchmarkSessionState(BaseSessionState):
    """
    Session state for Benchmark mode.

    Adds a golden_texts slot: the list of ExtractedTextRecord entries for the
    current document that serve as the matching pool in Phase 1.
    Cleared when Phase 2 is active (not needed there).
    """

    _KEY_GOLDEN = "golden_texts"
    _KEY_USED_GOLDEN = "used_golden_ids"  # ModelGoldenUsage

    def init(self) -> None:
        """Seed golden_texts and used_golden_ids in addition to base defaults."""
        super().init()
        if self._KEY_GOLDEN not in st.session_state:
            st.session_state[self._KEY_GOLDEN] = []
        if self._KEY_USED_GOLDEN not in st.session_state:
            st.session_state[self._KEY_USED_GOLDEN] = ModelGoldenUsage()

    @property
    def golden_texts(self) -> list[ExtractedTextRecord]:
        """Golden (model_name == 'human') extracted texts for the current document.

        Used by BenchmarkEvaluator to populate the Phase-1 match selectbox.
        """
        return st.session_state.get(self._KEY_GOLDEN, [])

    @golden_texts.setter
    def golden_texts(self, value: list[ExtractedTextRecord]) -> None:
        st.session_state[self._KEY_GOLDEN] = value

    @property
    def golden_usage(self) -> ModelGoldenUsage:
        """Tracks which golden IDs have already been matched per model for the current document.

        Populated from DB on load, updated on confirm.
        """
        return st.session_state.get(self._KEY_USED_GOLDEN, ModelGoldenUsage())

    @golden_usage.setter
    def golden_usage(self, value: ModelGoldenUsage) -> None:
        st.session_state[self._KEY_USED_GOLDEN] = value


class ProductionSessionState(BaseSessionState):
    """
    Session state for Production mode.

    Currently adds no extra slots beyond BaseSessionState.
    Kept as a concrete subclass so that:
      - ProductionEvaluator can type-hint its state parameter precisely.
      - Future production only state.
    """
    ...
