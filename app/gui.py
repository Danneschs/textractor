"""
Streamlit evaluator GUI for the two-phase extraction pipeline.

EvaluatorApp owns the sidebar chrome (title, mode badge, user input, document selectbox) and delegates all phase-level rendering to the appropriate controller.

The document selectbox is populated via controller.get_documents().
Adding a new mode requires only a new BaseEvaluator subclass and one branch in _build_controller().

Active mode is determined once at process start from the EVALUATOR_MODE environment variable (accepted values: "production" | "benchmark").
Default is "benchmark" when the variable is absent or unrecognised.
"""

from __future__ import annotations

import os
from typing import Optional

import streamlit as st
from dotenv import load_dotenv

from src.database.manager import DatabaseManager
from src.database.models import EvalMode
from src.gui.base import BaseEvaluator
from src.gui.benchmark import BenchmarkEvaluator
from src.gui.production import ProductionEvaluator
from src.gui.session_states import BenchmarkSessionState, ProductionSessionState
from src.gui.strings import UI
from src.utils import get_db_path

load_dotenv()

# Sidebar widget keys -- owned by EvaluatorApp because it renders these widgets.
_KEY_USER = "evaluator_name"
_KEY_DOC = "selected_doc_id"

_MODE_DISPLAY = {
    EvalMode.PRODUCTION: UI.Sidebar.MODE_PRODUCTION,
    EvalMode.BENCHMARK: UI.Sidebar.MODE_BENCHMARK,
}


def resolve_mode() -> EvalMode:
    """Read MODE from the environment.

    Fall back to BENCHMARK when the variable is absent or holds an invalid value.
    """
    load_dotenv()
    raw = os.getenv("MODE", "benchmark").lower()
    try:
        return EvalMode(raw)
    except ValueError:
        return EvalMode.BENCHMARK


# Resolved once at import time -- stable for the lifetime of the process.
_ACTIVE_MODE: EvalMode = resolve_mode()


@st.cache_resource
def get_database() -> DatabaseManager:
    """Instantiate and cache the DatabaseManager for the lifetime of the Streamlit process.

    st.cache_resource ensures a single instance is shared across reruns.
    """
    return DatabaseManager(get_db_path())


def _build_controller(mode: EvalMode, db: DatabaseManager) -> BaseEvaluator:
    """
    Factory: construct the appropriate evaluator controller for the given mode.

    To add a new mode: create a BaseEvaluator subclass, add an EvalMode value,
    and add one branch here. EvaluatorApp itself needs no changes.
    """
    if mode == EvalMode.PRODUCTION:
        return ProductionEvaluator(db, ProductionSessionState())
    else:
        return BenchmarkEvaluator(db, BenchmarkSessionState())


class EvaluatorApp:
    """
    Outer shell of the evaluator application.

    Owns layout setup and the shared sidebar sections. Delegates all
    phase-level rendering to self._controller. Contains zero mode-specific
    branches -- all per-mode variation is absorbed by the controller interface.
    """

    APP_TITLE = UI.Sidebar.APP_TITLE

    def __init__(self) -> None:
        """Resolve mode, connect to DB, build the appropriate controller. Once per process."""
        self._db: DatabaseManager = get_database()
        self._mode: EvalMode = _ACTIVE_MODE
        self._controller: BaseEvaluator = _build_controller(
            self._mode, self._db)

    def run(self) -> None:
        """Configure page, initialise session state, render sidebar, render main area."""
        st.set_page_config(page_title=self.APP_TITLE, layout="wide")
        self._controller._state.init()
        self._render_sidebar()
        self._render_main()

    def _render_sidebar(self) -> None:
        """Render the shared sidebar sections: title, mode badge, user input, and document selectbox.

        The document selectbox is populated via controller.get_documents().
        Contains no mode-specific branches.
        """
        st.sidebar.title(self.APP_TITLE)
        st.sidebar.subheader(_MODE_DISPLAY[self._mode])

        st.sidebar.text_input(UI.Sidebar.ENTER_NAME, key=_KEY_USER)

        all_docs = self._controller.get_documents()
        if not all_docs:
            st.sidebar.warning(self._controller.EMPTY_DOCS_MESSAGE)
            return

        st.sidebar.selectbox(
            UI.Sidebar.SELECT_DOCUMENT,
            options=[d.id for d in all_docs],
            format_func=lambda x: next(
                (d.filename for d in all_docs if d.id == x), str(x)),
            key=_KEY_DOC,
        )

    def _render_main(self) -> None:
        """Guard against missing user name and document, then delegate to the controller."""
        user: str = st.session_state.get(_KEY_USER, "")
        if not user:
            st.warning(UI.Sidebar.NO_NAME_WARNING)
            return

        doc_id: Optional[int] = st.session_state.get(_KEY_DOC)
        if doc_id is None:
            st.info(UI.Sidebar.NO_DOC_INFO)
            return

        self._controller.render(doc_id, user)


if __name__ == "__main__":
    app = EvaluatorApp()
    app.run()
