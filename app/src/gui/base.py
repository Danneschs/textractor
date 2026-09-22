"""
BaseEvaluator -- abstract controller shared by all evaluation mode controllers.

Responsibilities:
render() -- phase-selector sidebar + context change detection
_load_records() -- dispatcher to the correct phase loader
_render_body() -- progress bar + dispatch to per-phase renderers
_save_*() -- shared DB write helpers (mode injected via EVAL_MODE)

Each subclass must define these class attributes:
EVAL_MODE -- EvalMode constant for this mode
PHASE_LABELS -- dict[EvalPhase, str] mapping phases to display strings
EMPTY_DOCS_MESSAGE -- warning shown when get_documents() returns []

Each subclass must implement these public hook methods:
get_documents() -- return the document list appropriate for this mode
load_phase1_records() -- load Phase-1 items from DB into self._state
load_phase2_records() -- load Phase-2 items from DB into self._state
render_phase1() -- render the Phase-1 evaluation UI for a single record
render_phase2() -- render the Phase-2 evaluation UI for a single record
render_phase1_actions() -- render Phase-1 action buttons (pinned to bottom)
render_phase2_actions() -- render Phase-2 action buttons (pinned to bottom)
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Generic, List, Optional, Sequence, TypeVar

import streamlit as st

from src.database.manager import DatabaseManager
from src.database.models import (
    AnalyzedTextEvalRecord,
    DocumentRecord,
    EvalMode,
    EvalResult,
    ExtractedTextEvalRecord,
)
from src.gui.card_mapper import map_card
from src.gui.models import BasePhase2Item, EvalPhase, Phase1Item
from src.gui.session_states import BaseSessionState
from src.gui.strings import UI

T_State = TypeVar("T_State", bound=BaseSessionState)


class BaseEvaluator(ABC, Generic[T_State]):
    """Abstract base controller shared by all evaluation mode implementations."""

    EVAL_MODE: ClassVar[EvalMode]
    PHASE_LABELS: ClassVar[dict[EvalPhase, str]] = {}
    EMPTY_DOCS_MESSAGE: ClassVar[str] = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Only check fully concrete (non-abstract) subclasses.
        if not getattr(cls, "__abstractmethods__", None):
            if not cls.PHASE_LABELS:
                raise TypeError(
                    f"{cls.__name__} must define a non-empty PHASE_LABELS")
            if not hasattr(cls, "EVAL_MODE"):
                raise TypeError(f"{cls.__name__} must define EVAL_MODE")
            if not cls.EMPTY_DOCS_MESSAGE:
                raise TypeError(
                    f"{cls.__name__} must define EMPTY_DOCS_MESSAGE")

    def __init__(self, db: DatabaseManager, state: T_State) -> None:
        self._db = db
        self._state = state

    @abstractmethod
    def get_documents(self) -> List[DocumentRecord]:
        """
        Return the list of documents available for selection in this mode.
        For example, benchmark returns only documents that have golden entries.
        """
        ...

    @abstractmethod
    def load_phase1_records(self, doc_id: int, user: str) -> None:
        """
        Load Phase-1 items from DB and write them into self._state.phase1_records.
        Must also set self._state.current_index = 0 and
        self._state.context = (doc_id, user, EvalPhase.PHASE1).
        May update additional mode-specific state slots (e.g. golden_texts).
        """
        ...

    @abstractmethod
    def load_phase2_records(self, doc_id: int, user: str) -> None:
        """
        Load Phase-2 items from DB and write them into self._state.phase2_records.
        Must also set self._state.current_index = 0 and
        self._state.context = (doc_id, user, EvalPhase.PHASE2).
        """
        ...

    @abstractmethod
    def render_phase1(self, item: Phase1Item) -> None:
        """
        Render the evaluation UI for a single Phase-1 record.
        Responsible for calling self._state.advance() and st.rerun() on user action.
        """
        ...

    @abstractmethod
    def render_phase2(self, item: BasePhase2Item) -> None:
        """
        Render the evaluation UI for a single Phase-2 record.
        Responsible for calling self._state.advance() and st.rerun() on user action.
        """
        ...

    @abstractmethod
    def render_phase1_actions(self, item: Phase1Item) -> None:
        """
        Render Phase-1 action buttons inside a st.bottom() container.
        Widget values needed by the buttons should be read from st.session_state
        using the same keys assigned to the widgets in render_phase1().
        """

    @abstractmethod
    def render_phase2_actions(self, item: BasePhase2Item) -> None:
        """
        Render Phase-2 action buttons inside a st.bottom() container.
        Widget values needed by the buttons should be read from st.session_state
        using the same keys assigned to the widgets in render_phase2().
        """

    def render(self, doc_id: int, user: str) -> None:
        """
        Render the phase-selector radio in the sidebar, detect context changes,
        trigger a data reload when needed, and dispatch to _render_body().
        """
        st.sidebar.radio(
            UI.Sidebar.PHASE_RADIO,
            options=list(EvalPhase),
            format_func=lambda x: self.PHASE_LABELS[x],
            key=self._state.KEY_PHASE,
            on_change=lambda: self._load_records(
                doc_id, user, self._state.eval_phase),
        )

        phase = self._state.eval_phase

        # Reload whenever doc, user, or phase changes.
        if (doc_id, user, phase) != self._state.context:
            self._load_records(doc_id, user, phase)

        self._render_body(doc_id, user, phase)

    def _load_records(self, doc_id: int, user: str, phase: EvalPhase) -> None:
        """
        Dispatch to the correct phase loader based on the current phase.
        Called by render() on context change and by the phase radio on_change.
        """
        if phase == EvalPhase.PHASE1:
            self.load_phase1_records(doc_id, user)
        else:
            self.load_phase2_records(doc_id, user)

    def _render_body(self, doc_id: int, user: str, phase: EvalPhase) -> None:
        """Render the sidebar progress bar and current record, or an empty-state message.

        context is None: records were never loaded for the current session.
        records == [] after a load: all evaluated or none remain for this selection.
        """
        idx = self._state.current_index
        if phase == EvalPhase.PHASE1:
            p1_records = self._state.phase1_records
            if not self._check_and_show_progress(doc_id, user, phase, idx, p1_records):
                return
            item_p1 = p1_records[idx]
            self.render_phase1(item_p1)
            with st._bottom:
                self.render_phase1_actions(item_p1)
        else:
            p2_records = self._state.phase2_records
            if not self._check_and_show_progress(doc_id, user, phase, idx, p2_records):
                return
            item_p2 = p2_records[idx]
            self.render_phase2(item_p2)
            with st._bottom:
                self.render_phase2_actions(item_p2)

    def _check_and_show_progress(
        self,
        doc_id: int,
        user: str,
        phase: EvalPhase,
        idx: int,
        records: "Sequence[Any]",
    ) -> bool:
        """
        Show the empty-state message and Refresh button when idx is out of range,
        or show the sidebar progress bar and return True when a record is ready.
        """
        total = len(records)
        if idx >= total:
            if self._state.context is None or total == 0:
                st.info(UI.Common.NO_RECORDS)
            else:
                st.success(UI.Common.ALL_DONE)
            if st.button(UI.Common.REFRESH):
                self._load_records(doc_id, user, phase)
                st.rerun()
            return False
        st.sidebar.markdown("---")
        st.sidebar.progress(
            (idx + 1) / total,
            text=UI.Common.PROGRESS.format(current=idx + 1, total=total),
        )
        return True

    def _save_extracted_eval(
        self,
        extracted_text_id: int,
        result: EvalResult,
        matched_golden_id: Optional[int] = None,
    ) -> None:
        """Store a Phase-1 evaluation verdict.

        EVAL_MODE and evaluator_name are injected automatically.
        matched_golden_id is only relevant in Benchmark mode (golden text pairing).
        """
        self._db.extracted_text_evals.insert(
            ExtractedTextEvalRecord(
                extracted_text_id=extracted_text_id,
                is_correct=result,
                evaluator_name=self._state.evaluator_name,
                matched_golden_id=matched_golden_id,
                mode=self.EVAL_MODE,
            )
        )

    def _save_analyzed_eval(
        self,
        analyzed_text_id: int,
        result: EvalResult,
        note: Optional[str] = None,
    ) -> None:
        """Store a Phase-2 evaluation verdict.

        EVAL_MODE and evaluator_name are injected automatically.
        note is an optional free-text comment from the evaluator.
        """
        self._db.analyzed_text_evals.insert(
            AnalyzedTextEvalRecord(
                analyzed_text_id=analyzed_text_id,
                is_correct=result,
                evaluator_name=self._state.evaluator_name,
                note=note,
                mode=self.EVAL_MODE,
            )
        )

    @staticmethod
    def _parse_cards(json_data: str) -> list[dict[str, Any]]:
        """Extract the list of requirement cards from a JSON string.

        Find the first list-typed value in the top-level dict -- works for any
        single-list-field Pydantic schema regardless of the field name.
        """
        try:
            parsed = json.loads(json_data)
            for v in parsed.values():
                if isinstance(v, list):
                    return v
        except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
            pass
        return []

    @staticmethod
    def _render_card_fields(card: dict[str, Any]) -> None:
        """Render the mapped field rows for one requirement card.

        Must be called inside an open st.container(border=True) block.
        The container and any status badge or action button are the caller's responsibility.
        """
        for label, value in map_card(card):
            st.write(f"**{label}:** {value}")
