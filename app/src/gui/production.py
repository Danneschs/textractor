"""
ProductionEvaluator -- controller for the Production mode.

Phase 1: The evaluator confirms or rejects whether an LLM-extracted text is a
         valid extraction from the source PDF (side-by-side: text + PDF viewer).
Phase 2: The evaluator confirms or rejects whether the LLM JSON analysis correctly
         represents the source sentence extracted in Phase 1.

The two phases ARE logically linked: Phase 2 only surfaces analyses whose
parent extracted text was marked CORRECT by this evaluator in Phase 1.
"""

from __future__ import annotations

import html
import json
from typing import List

import streamlit as st
from streamlit_pdf_viewer import pdf_viewer  # type: ignore
from typing_extensions import override

from src.database.manager import DatabaseManager
from src.database.models import DocumentRecord, EvalMode, EvalResult
from src.gui.base import BaseEvaluator
from src.gui.models import BasePhase2Item, EvalPhase, Phase1Item, Phase2Item
from src.gui.session_states import ProductionSessionState
from src.gui.strings import UI


class ProductionEvaluator(BaseEvaluator[ProductionSessionState]):
    """Evaluation controller for Production mode."""

    EVAL_MODE = EvalMode.PRODUCTION
    EMPTY_DOCS_MESSAGE = UI.Production.NO_DOCUMENTS
    PHASE_LABELS = {
        EvalPhase.PHASE1: UI.Common.PHASE1_LABEL,
        EvalPhase.PHASE2: UI.Common.PHASE2_LABEL,
    }

    def __init__(self, db: DatabaseManager, state: ProductionSessionState) -> None:
        super().__init__(db, state)

    @override
    def get_documents(self) -> List[DocumentRecord]:
        """Return all documents in the database (no golden-data filter needed)."""
        return self._db.documents.get_all()

    @override
    def load_phase1_records(self, doc_id: int, user: str) -> None:
        """Load non-golden extracted texts for doc_id not yet evaluated by this user in PRODUCTION mode."""
        records = self._build_phase1_items(doc_id, user)
        self._state.phase1_records = records
        self._state.current_index = 0
        self._state.context = (doc_id, user, EvalPhase.PHASE1)

    @override
    def load_phase2_records(self, doc_id: int, user: str) -> None:
        """Load analyses whose parent extracted text was marked correct by this user in PRODUCTION mode.

        Filters out analyses with error-JSON results and already evaluated ones.
        """
        records = self._build_phase2_items(doc_id, user)
        self._state.phase2_records = records
        self._state.current_index = 0
        self._state.context = (doc_id, user, EvalPhase.PHASE2)

    def _build_phase1_items(self, doc_id: int, user: str) -> List[Phase1Item]:
        """Query unevaluated non-golden extracted texts, attaching file_path for the PDF viewer."""
        doc = self._db.documents.get_by_id(doc_id)
        file_path = doc.file_path.replace("\\", "/") if doc else ""
        result: List[Phase1Item] = []
        for r in self._db.extracted_texts.get_unevaluated_non_golden(
                doc_id, user, EvalMode.PRODUCTION):
            if r.id is None:
                continue
            result.append(Phase1Item(
                id=r.id, model_name=r.model_name, raw_text=r.raw_text,
                file_path=file_path))
        return result

    def _build_phase2_items(self, doc_id: int, user: str) -> List[Phase2Item]:
        """Query analyses linked to correct Phase-1 evaluations by this user.

        Caches parent extracted-text lookups to avoid N+1 queries.
        Skips analyses whose JSON contains an error key.
        """
        analyzed = self._db.analyzed_texts.get_unevaluated_for_correct_extracted(
            doc_id, user)
        parent_cache: dict[int, str] = {}
        items: List[Phase2Item] = []
        for at in analyzed:
            if at.id is None:
                continue
            try:
                parsed = json.loads(at.result)
                if "error" in parsed:
                    continue
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
            if at.extracted_text_id not in parent_cache:
                parent = self._db.extracted_texts.get_by_id(
                    at.extracted_text_id)
                parent_cache[at.extracted_text_id] = (
                    parent.raw_text if parent else "(Text not found)"
                )
            items.append(Phase2Item(
                id=at.id,
                model_name=at.model_name,
                parent_raw_text=parent_cache[at.extracted_text_id],
                result=at.result,
            ))
        return items

    @override
    def render_phase1(self, item: Phase1Item) -> None:
        """
        Two-column layout: left shows the extracted text, right shows the PDF viewer.
        """
        st.subheader(UI.Production.P1_SUBHEADER.format(model=item.model_name))

        with st.expander(UI.Common.HOW_TO_TITLE, expanded=False):
            st.markdown(UI.Production.P1_HOW_TO_BODY)
        with st.expander(UI.Common.GOAL_TITLE, expanded=False):
            st.markdown(UI.Production.P1_GOAL_BODY)

        col_left, col_right = st.columns([2, 3])

        with col_left:
            st.markdown(UI.Production.P1_FOUND_TEXT)
            with st.container(border=True):
                st.markdown(item.raw_text)

        with col_right:
            st.markdown(UI.Production.P1_SOURCE_FILE)
            if item.file_path:
                try:
                    pdf_viewer(item.file_path, height=1150, render_text=True)
                except FileNotFoundError:
                    st.warning(UI.Production.P1_NO_PDF)
            else:
                st.warning(UI.Production.P1_NO_PDF)

    @override
    def render_phase1_actions(self, item: Phase1Item) -> None:
        """Show Confirm / Reject buttons side by side."""
        col1, col2 = st.columns(2)
        with col1:
            if st.button(UI.Production.P1_VALID, use_container_width=True, type="primary"):
                self._save_extracted_eval(item.id, EvalResult.CORRECT)
                self._state.advance()
                st.rerun()
        with col2:
            if st.button(UI.Production.P1_INVALID, use_container_width=True):
                self._save_extracted_eval(item.id, EvalResult.INCORRECT)
                self._state.advance()
                st.rerun()

    @override
    def render_phase2(self, item: BasePhase2Item) -> None:
        """Show the source sentence as context, then all requirement cards for review.

        Cards can be toggled as reviewed (frontend only, no DB write).
        Verdict buttons are shown below all cards via render_phase2_actions().
        """
        assert isinstance(item, Phase2Item)
        prod = item
        marks_key = f"prod_marks_{prod.id}"
        st.session_state.setdefault(marks_key, set())

        st.subheader(UI.Production.P2_SUBHEADER)

        with st.expander(UI.Common.HOW_TO_TITLE, expanded=False):
            st.markdown(UI.Production.P2_HOW_TO_BODY)
        with st.expander(UI.Common.GOAL_TITLE, expanded=False):
            st.markdown(UI.Production.P2_GOAL_BODY)

        st.markdown(UI.Common.P2_ANALYZED_SENTENCE)
        st.info(prod.parent_raw_text)

        st.markdown(
            f"{UI.Production.P2_MODEL_HEADING_PREFIX}"
            f"<code style='color:{UI.Colors.BLUE_HEX};padding:2px 6px;border-radius:3px'>"
            f"{html.escape(prod.model_name)}</code>",
            unsafe_allow_html=True,
        )

        cards = self._parse_cards(prod.result)
        if cards:
            cols = st.columns(2)
            for i, card in enumerate(cards):
                marked: set = st.session_state[marks_key]
                is_marked = i in marked
                with cols[i % 2].container(border=True):
                    self._render_card_fields(card)
                    if is_marked:
                        st.success(UI.Production.P2_UNMARK)
                        if st.button(UI.Production.P2_UNMARK, key=f"unmark_{prod.id}_{i}",
                                     use_container_width=True):
                            st.session_state[marks_key].discard(i)
                            st.rerun()
                    else:
                        if st.button(UI.Production.P2_MARK, key=f"mark_{prod.id}_{i}",
                                     use_container_width=True):
                            st.session_state[marks_key].add(i)
                            st.rerun()
        else:
            st.warning(UI.Common.NO_CARDS)

        st.markdown("---")
        st.text_area(
            UI.Common.NOTE_LABEL,
            key=f"note_{prod.id}",
            placeholder=UI.Common.NOTE_PLACEHOLDER,
        )

    @override
    def render_phase2_actions(self, item: BasePhase2Item) -> None:
        """Show Correct / Incorrect buttons side by side, with a text area for optional notes."""
        assert isinstance(item, Phase2Item)
        prod = item
        note = st.session_state.get(f"note_{prod.id}", "") or None
        col1, col2 = st.columns(2)
        with col1:
            if st.button(UI.Common.CORRECT, use_container_width=True, type="primary"):
                self._save_analyzed_eval(
                    prod.id, EvalResult.CORRECT, note=note)
                self._state.advance()
                st.rerun()
        with col2:
            if st.button(UI.Common.WRONG, use_container_width=True):
                self._save_analyzed_eval(
                    prod.id, EvalResult.INCORRECT, note=note)
                self._state.advance()
                st.rerun()
