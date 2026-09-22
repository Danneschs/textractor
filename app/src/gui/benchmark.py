"""
BenchmarkEvaluator -- controller for the Benchmark (golden-standard comparison) mode.

Phase 1: The evaluator matches each LLM-extracted text to the correct golden
         dataset entry, or marks it as a hallucination.
Phase 2: The evaluator compares each LLM JSON analysis against the human-written
         golden JSON, one golden sentence at a time.

The two phases are NOT logically linked: Phase 2 uses all golden sentences
regardless of Phase 1 outcomes.
"""

from __future__ import annotations

import html
import json
from typing import List, Optional

import streamlit as st
from typing_extensions import override

from src.database.manager import DatabaseManager
from src.database.models import DocumentRecord, EvalMode, EvalResult, ExtractedTextRecord
from src.gui.base import BaseEvaluator
from src.gui.models import BasePhase2Item, BenchPhase2Item, EvalPhase, ModelGoldenUsage, Phase1Item
from src.gui.session_states import BenchmarkSessionState
from src.gui.strings import UI


class BenchmarkEvaluator(BaseEvaluator[BenchmarkSessionState]):
    """Evaluation controller for Benchmark mode."""

    EVAL_MODE = EvalMode.BENCHMARK
    EMPTY_DOCS_MESSAGE = UI.Benchmark.NO_DOCUMENTS
    PHASE_LABELS = {
        EvalPhase.PHASE1: UI.Common.PHASE1_LABEL,
        EvalPhase.PHASE2: UI.Common.PHASE2_LABEL,
    }

    def __init__(self, db: DatabaseManager, state: BenchmarkSessionState) -> None:
        super().__init__(db, state)

    @override
    def get_documents(self) -> List[DocumentRecord]:
        """Return only documents that have at least one golden extracted text entry."""
        return self._db.documents.get_all_with_golden()

    @override
    def load_phase1_records(self, doc_id: int, user: str) -> None:
        """Load unevaluated non-golden extracted texts that have a golden counterpart.

        Also populate golden_texts (matching pool) and golden_usage (already-matched
        golden IDs per model, seeded from DB so cross-session state is respected).
        """
        records = self._build_phase1_items(doc_id, user)
        self._state.golden_texts = self._fetch_golden_texts(doc_id)
        raw_usage = self._db.extracted_text_evals.get_matched_golden_ids_by_model(
            doc_id, user, EvalMode.BENCHMARK)
        self._state.golden_usage = ModelGoldenUsage.from_db(raw_usage)
        self._state.phase1_records = records
        self._state.current_index = 0
        self._state.context = (doc_id, user, EvalPhase.PHASE1)

    @override
    def load_phase2_records(self, doc_id: int, user: str) -> None:
        """Load golden extracted texts grouped with their unevaluated LLM analyses.

        Clears golden_texts (not needed in Phase 2).
        """
        records = self._build_phase2_items(doc_id, user)
        self._state.golden_texts = []  # not used in Phase 2
        self._state.phase2_records = records
        self._state.current_index = 0
        self._state.context = (doc_id, user, EvalPhase.PHASE2)

    def _build_phase1_items(self, doc_id: int, user: str) -> List[Phase1Item]:
        """Query unevaluated non-golden extracted texts that have a golden counterpart to match against."""
        doc = self._db.documents.get_by_id(doc_id)
        file_path = doc.file_path if doc else ""
        result: List[Phase1Item] = []
        for r in self._db.extracted_texts.get_unevaluated_non_golden(
                doc_id, user, EvalMode.BENCHMARK, only_with_golden=True):
            if r.id is None:
                continue
            result.append(Phase1Item(
                id=r.id, model_name=r.model_name, raw_text=r.raw_text,
                file_path=file_path))
        return result

    def _fetch_golden_texts(self, doc_id: int) -> List[ExtractedTextRecord]:
        """Return all golden extracted text entries for doc_id (matching pool for Phase-1 selectbox)."""
        return [r for r in self._db.extracted_texts.get_golden_by_document(doc_id)
                if r.id is not None]

    def _build_phase2_items(self, doc_id: int, user: str) -> List[BenchPhase2Item]:
        """Build one BenchPhase2Item per non-human, non-error analysis for each unevaluated golden extracted text.

        Human cards are shared across all items for the same golden sentence.
        """
        golden_ets = self._db.analyzed_texts.get_unevaluated_golden_groups(
            doc_id, user)
        result: List[BenchPhase2Item] = []

        for et in golden_ets:
            if et.id is None:
                continue
            analyses = self._db.analyzed_texts.get_by_extracted_text(et.id)
            human_entry = next(
                (a for a in analyses if a.model_name == "human"), None)
            human_cards = self._parse_cards(
                human_entry.result) if human_entry else []

            for a in analyses:
                if a.id is None or a.model_name == "human":
                    continue
                if self._db.analyzed_text_evals.already_evaluated(a.id, user, EvalMode.BENCHMARK):
                    continue
                try:
                    parsed = json.loads(a.result)
                    if "error" in parsed:
                        continue
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass
                result.append(BenchPhase2Item(
                    extracted_text_id=et.id,
                    raw_text=et.raw_text,
                    model_name=a.model_name,
                    model_analysis_id=a.id,
                    model_cards=self._parse_cards(a.result),
                    human_cards=human_cards,
                ))

        return result

    @override
    def render_phase1(self, item: Phase1Item) -> None:
        """
        Two-column layout: model text (left) | golden standard search (right).
        Action buttons are pinned to the bottom via st.bottom().
        On confirm: saves CORRECT + matched_golden_id and marks golden as used.
        On reject:  saves INCORRECT (hallucination, no golden link).
        """
        st.subheader(UI.Benchmark.P1_SUBHEADER)

        with st.expander(UI.Common.HOW_TO_TITLE, expanded=False):
            st.markdown(UI.Benchmark.P1_HOW_TO_BODY)

        with st.expander(UI.Common.GOAL_TITLE, expanded=False):
            st.markdown(UI.Benchmark.P1_GOAL_BODY)

        usage = self._state.golden_usage
        used_ids = usage.used_for(item.model_name)
        golden_options = {g.id: g.raw_text for g in self._state.golden_texts}

        col_model, col_golden = st.columns(2)

        with col_model:
            # used for an inline <code> tag (no <style> block).
            st.markdown(
                f"#### {UI.Benchmark.P1_FOUND_TEXT_HEADING} "
                f"<code style='color:{UI.Colors.BLUE_HEX};"
                f"padding:2px 6px;border-radius:3px'>"
                f"{html.escape(item.model_name)}</code>",
                unsafe_allow_html=True,
            )
            st.info(item.raw_text)

        with col_golden:
            st.markdown(f"#### {UI.Benchmark.P1_GOLDEN_HEADING}")
            if not golden_options:
                st.warning(UI.Benchmark.P1_NO_GOLDEN)
            else:
                search = st.text_input(
                    UI.Benchmark.P1_SEARCH_LABEL,
                    placeholder=UI.Benchmark.P1_SEARCH_PLACEHOLDER,
                    key=f"golden_search_{item.id}",
                )
                term = search.strip().lower()
                all_golden = self._state.golden_texts
                available = [
                    g for g in all_golden
                    if g.id not in used_ids and (not term or term in g.raw_text.lower())
                ]
                already_matched = [
                    g for g in all_golden
                    if g.id in used_ids and (not term or term in g.raw_text.lower())
                ]

                with st.container(height=400):
                    if not available and not already_matched and term:
                        st.info(UI.Benchmark.P1_NO_SEARCH_RESULTS)
                    if available:
                        st.radio(
                            UI.Benchmark.P1_GOLDEN_RADIO_LABEL,
                            options=[g.id for g in available],
                            format_func=lambda gid: golden_options[gid],
                            label_visibility="collapsed",
                            key=f"golden_radio_{item.id}",
                        )
                    for g in already_matched:
                        st.markdown(
                            f"<div style='opacity:0.45;padding:4px 0'>"
                            f"<small>{html.escape(UI.Benchmark.P1_ALREADY_PAIRED_SUFFIX)}</small><br>"
                            f"{html.escape(g.raw_text)}</div>",
                            unsafe_allow_html=True,
                        )

    @override
    def render_phase1_actions(self, item: Phase1Item) -> None:
        """Render the action buttons for a Phase-1 evaluation item."""
        # selected_golden_id is stored in session state by the radio widget.
        selected_golden_id = st.session_state.get(f"golden_radio_{item.id}")
        col_confirm, col_reject = st.columns(2)
        with col_confirm:
            if st.button(
                UI.Benchmark.P1_CONFIRM,
                use_container_width=True,
                disabled=selected_golden_id is None,
                type="primary",
            ):
                assert selected_golden_id is not None
                self._save_extracted_eval(
                    item.id, EvalResult.CORRECT, matched_golden_id=selected_golden_id)
                self._state.golden_usage.mark(
                    item.model_name, selected_golden_id)
                self._state.advance()
                st.rerun()
        with col_reject:
            if st.button(
                UI.Benchmark.P1_NOT_IN_GOLDEN,
                use_container_width=True,
            ):
                self._save_extracted_eval(item.id, EvalResult.INCORRECT)
                self._state.advance()
                st.rerun()

    @override
    def render_phase2(self, item: BasePhase2Item) -> None:
        """Render two-column click-to-match layout with symmetric card selection.

        Either side can be selected first; clicking the opposite side pairs them.
        Model cards additionally support hallucination (no human counterpart).
        Clicking a selected card again deselects it.
        State is frontend-only -- not persisted to DB.
        """
        assert isinstance(item, BenchPhase2Item)
        bench = item
        aid = bench.model_analysis_id
        sel_key = f"p2_sel_{aid}"    # {"side": "h"|"m", "idx": int} | None
        pairs_key = f"p2_pairs_{aid}"  # {model_idx: human_idx | None}
        st.session_state.setdefault(sel_key, None)
        st.session_state.setdefault(pairs_key, {})

        st.subheader(UI.Benchmark.P2_SUBHEADER)

        with st.expander(UI.Common.HOW_TO_TITLE, expanded=False):
            st.markdown(UI.Benchmark.P2_HOW_TO_BODY)

        with st.expander(UI.Common.GOAL_TITLE, expanded=False):
            st.markdown(UI.Benchmark.P2_GOAL_BODY)

        st.markdown(UI.Common.P2_ANALYZED_SENTENCE)
        st.info(bench.raw_text)

        col_model, col_human = st.columns(2)
        sel: Optional[dict] = st.session_state[sel_key]
        pairings: dict = st.session_state[pairs_key]

        # Determine which model card is "currently selected" (if any)
        sel_model_idx = sel["idx"] if sel and sel["side"] == "m" else None
        sel_human_idx = sel["idx"] if sel and sel["side"] == "h" else None

        # Helper: pair number (1-based insertion order) for a model card index
        def pair_num(model_i: int) -> int:
            return list(pairings.keys()).index(model_i) + 1

        # ---- Model cards (left) ----
        with col_model:
            st.markdown(
                f"{UI.Benchmark.P2_MODEL_HEADING_PREFIX}"
                f"<code style='color:{UI.Colors.BLUE_HEX};padding:2px 6px;border-radius:3px'>"
                f"{html.escape(bench.model_name)}</code>",
                unsafe_allow_html=True,
            )
            if bench.model_cards:
                for i, card in enumerate(bench.model_cards):
                    is_m_selected = (sel_model_idx == i)
                    is_paired = i in pairings
                    # int or None (hallucination)
                    paired_human = pairings.get(i)

                    with st.container(border=True):
                        self._render_card_fields(card)
                        # Status badge -- always rendered to keep card height stable
                        if is_m_selected:
                            st.info(UI.Benchmark.P2_SELECTED_BADGE)
                        elif is_paired:
                            if isinstance(paired_human, int):
                                st.success(
                                    UI.Benchmark.P2_PAIR_BADGE.format(n=pair_num(i)))
                            elif paired_human == "marked":
                                st.success(UI.Benchmark.P2_MARKED_BADGE)
                            else:
                                st.error(UI.Benchmark.P2_HALLUCINATION)
                        else:
                            # zero-width space -- reserves badge height
                            st.info("\u200b")
                        # Action button (always last, inside container)
                        if is_paired:
                            unpair_label = UI.Benchmark.P2_UNMARK if paired_human == "marked" else UI.Benchmark.P2_UNPAIR
                            if st.button(unpair_label,
                                         key=f"unpair_m{i}_{aid}",
                                         use_container_width=True):
                                st.session_state[pairs_key].pop(i, None)
                                st.rerun()
                        elif is_m_selected:
                            if st.button(UI.Benchmark.P2_DESELECT,
                                         key=f"desel_m{i}_{aid}",
                                         use_container_width=True):
                                st.session_state[sel_key] = None
                                st.rerun()
                        elif sel_human_idx is not None:
                            # A human card is waiting -- offer to pair
                            if st.button(UI.Benchmark.P2_PAIR,
                                         key=f"pair_m{i}_{aid}",
                                         use_container_width=True):
                                st.session_state[pairs_key][i] = sel_human_idx
                                st.session_state[sel_key] = None
                                st.rerun()
                        else:
                            # Nothing selected -- offer Select | Mark | Hallucination
                            bc1, bc2, bc3 = st.columns(3)
                            with bc1:
                                if st.button(UI.Benchmark.P2_SELECT,
                                             key=f"sel_m{i}_{aid}",
                                             use_container_width=True):
                                    st.session_state[sel_key] = {
                                        "side": "m", "idx": i}
                                    st.rerun()
                            with bc2:
                                if st.button(UI.Benchmark.P2_MARK,
                                             key=f"mark_m{i}_{aid}",
                                             use_container_width=True):
                                    st.session_state[pairs_key][i] = "marked"
                                    st.session_state[sel_key] = None
                                    st.rerun()
                            with bc3:
                                if st.button(UI.Benchmark.P2_HALLUCINATION,
                                             key=f"hal_m{i}_{aid}",
                                             use_container_width=True):
                                    st.session_state[pairs_key][i] = None
                                    st.session_state[sel_key] = None
                                    st.rerun()
            else:
                st.warning(UI.Common.NO_CARDS)

        # ---- Human cards (right) ----
        with col_human:
            st.markdown(UI.Benchmark.P2_GOLDEN_HEADING)
            if bench.human_cards:
                for j, card in enumerate(bench.human_cards):
                    paired_model = next(
                        (mi for mi, hi in pairings.items() if hi == j), None)
                    is_h_selected = (sel_human_idx == j)

                    with st.container(border=True):
                        self._render_card_fields(card)
                        # Status badge -- always rendered to keep card height stable
                        if paired_model is not None:
                            st.success(UI.Benchmark.P2_PAIR_BADGE.format(
                                n=pair_num(paired_model)))
                        elif is_h_selected:
                            st.info(UI.Benchmark.P2_SELECTED_BADGE)
                        else:
                            # zero-width space -- reserves badge height
                            st.info("\u200b")
                        # Action button (always last, inside container)
                        if paired_model is not None:
                            if st.button(UI.Benchmark.P2_UNPAIR,
                                         key=f"unpair_h{j}_{aid}",
                                         use_container_width=True):
                                st.session_state[pairs_key].pop(
                                    paired_model, None)
                                st.rerun()
                        elif is_h_selected:
                            if st.button(UI.Benchmark.P2_DESELECT,
                                         key=f"desel_h{j}_{aid}",
                                         use_container_width=True):
                                st.session_state[sel_key] = None
                                st.rerun()
                        elif sel_model_idx is not None and sel_model_idx not in pairings:
                            # A model card is waiting -- offer to pair
                            if st.button(UI.Benchmark.P2_PAIR,
                                         key=f"pair_h{j}_{aid}",
                                         use_container_width=True):
                                st.session_state[pairs_key][sel_model_idx] = j
                                st.session_state[sel_key] = None
                                st.rerun()
                        else:
                            # Nothing selected on model side -- allow selecting this H card
                            if st.button(UI.Benchmark.P2_SELECT,
                                         key=f"sel_h{j}_{aid}",
                                         use_container_width=True):
                                st.session_state[sel_key] = {
                                    "side": "h", "idx": j}
                                st.rerun()
            else:
                st.warning(UI.Benchmark.P2_NO_GOLDEN_CARDS)

        st.markdown("---")
        st.text_area(
            UI.Common.NOTE_LABEL,
            key=f"note_{aid}",
            placeholder=UI.Common.NOTE_PLACEHOLDER,
        )

    @override
    def render_phase2_actions(self, item: BasePhase2Item) -> None:
        """Render the action buttons for a Phase-2 evaluation item."""
        assert isinstance(item, BenchPhase2Item)
        bench = item
        aid = bench.model_analysis_id
        note = st.session_state.get(f"note_{aid}", "") or None
        col_correct, col_wrong = st.columns(2)
        with col_correct:
            if st.button(UI.Common.CORRECT, use_container_width=True, type="primary"):
                self._save_analyzed_eval(aid, EvalResult.CORRECT, note=note)
                self._state.advance()
                st.rerun()
        with col_wrong:
            if st.button(UI.Common.WRONG, use_container_width=True):
                self._save_analyzed_eval(aid, EvalResult.INCORRECT, note=note)
                self._state.advance()
                st.rerun()
