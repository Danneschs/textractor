"""
UI constants for the evaluator GUI -- strings, colours, and other presentational values.

All user-visible text and visual constants are defined here so that:
  - values have a single source of truth,
  - the rendering code stays free of hard-coded literals,
  - future localisation only requires changes in this file.

Usage::

    from src.gui.strings import UI

    st.subheader(UI.Benchmark.P1_SUBHEADER)
    st.button(UI.Common.CORRECT)

Strings that contain a placeholder use a plain Python format-string convention;
call  .format(...)  at the call site, for example: st.subheader(UI.Production.P1_SUBHEADER.format(model=item.model_name))
"""


class UI:
    """Top-level class; use the nested classes directly."""

    class Colors:
        """Hex codes for colours used in the UI."""
        BLUE_HEX = "#4da6ff"  # for info boxes and model name badges

    class Sidebar:
        """Constants for the sidebar."""
        APP_TITLE = "Textractor Studio"
        MODE_PRODUCTION = "Production mode"
        MODE_BENCHMARK = "Benchmark mode"
        ENTER_NAME = "Enter your name:"
        SELECT_DOCUMENT = "Select document:"
        PHASE_RADIO = "Evaluation phase:"
        NO_NAME_WARNING = (
            "Enter your name in the sidebar to start evaluating."
        )
        NO_DOC_INFO = (
            "Select a document in the sidebar to start evaluating."
        )

    class Common:
        """Constants shared by both evaluation modes and phases."""
        NO_RECORDS = "There are no records to evaluate for this document."
        ALL_DONE = (
            "All done! There are no more records to evaluate for this phase."
        )
        REFRESH = "Refresh data"
        # Progress bar text -- placeholder: {current}, {total}
        PROGRESS = "Progress: {current} / {total}"
        NO_CARDS = "The model returned no cards."
        NOTE_LABEL = "Note (optional):"
        NOTE_PLACEHOLDER = "Optional note for this evaluation..."
        CORRECT = "Correct"
        WRONG = "Incorrect"

        # Phase labels (identical in both modes)
        PHASE1_LABEL = "Phase 1 (Extraction)"
        PHASE2_LABEL = "Phase 2 (Formalization)"

        # Advice panel titles (shared by all modes and phases)
        HOW_TO_TITLE = "How to proceed?"
        GOAL_TITLE = "What is the goal?"

        # Shared Phase-2 label
        P2_ANALYZED_SENTENCE = "**Sentence formalized by the model:**"

    class Production:
        """Constants specific to the Production evaluation mode."""
        NO_DOCUMENTS = "No documents found in the database."

        # Phase 1
        # Placeholder: {model}
        P1_SUBHEADER = "Mode: Production | Phase 1 | Model: {model}"
        P1_FOUND_TEXT = "**Extracted text:**"
        P1_SOURCE_FILE = "**Source file:**"
        P1_NO_PDF = "PDF file is not available."
        P1_VALID = "Correct"
        P1_INVALID = "Incorrect"
        P1_HOW_TO_BODY = (
            "Look at the extracted text on the left and find it in the source PDF on the right.\n\n"
            "- If the text appears in the document, click **Correct**.\n"
            "- If it does not appear or was modified by the model, click **Incorrect**."
        )
        P1_GOAL_BODY = (
            "The goal is to verify that each extracted text by the LLM is actually present in the source "
            "document. Correctly extracted requirements are shown in Phase 2 "
            "evaluation, if their formalization by some LLM exists. If the extraction is incorrect, the formalization is not evaluated, as it would be meaningless."
        )

        # Phase 2
        P2_SUBHEADER = "Formalization evaluation"
        P2_MODEL_HEADING_PREFIX = "#### :blue[Evaluated model ]"
        P2_MARK = "Review"
        P2_UNMARK = "Reviewed"
        P2_HOW_TO_BODY = (
            "Review the sentence from Phase 1 (shown above) and the structured formalization below.\n\n"
            "- Check whether the requirement summary is accurate.\n"
            "- Check whether quantifiable parameters (values and units) were extracted correctly.\n"
            "- Click **Correct** or **Incorrect** to submit your verdict. "
            "An optional note about the formalization can be added."
        )
        P2_GOAL_BODY = (
            "The goal is to evaluate whether the LLM correctly formalized a requirement that was "
            "already confirmed as correctly extracted. This covers both the summary and any "
            "quantifiable data (values and units)."
        )

    class Benchmark:
        """Constants specific to the Benchmark evaluation mode."""
        NO_DOCUMENTS = "No documents with a golden standard found in the database."

        # Phase 1
        P1_SUBHEADER = "Semantic match search"
        P1_HOW_TO_BODY = (
            "Compare the text found by the model **(left)** with the requirements from the golden "
            "standard **(right)**.\n\n"
            "- Select the requirement that the text semantically matches and click "
            "**Confirm match**.\n"
            "- If the text does not match any requirement (the model made it up), "
            "click **Not in golden standard**.\n\n"
            "If the model split one requirement into multiple parts, mark all parts as "
            "**Not in golden standard** -- a split requirement has lost its context and is incorrect.\n\n"
            "Requirements from the golden standard that have already been matched are marked."
        )
        P1_GOAL_BODY = (
            "The goal of this evaluation phase is to determine how well language models can find data in a large text.\n"
            "- If the found text matches a text in the golden standard, the language **model successfully found the requirement**.\n"
            "- If the text cannot be matched (no semantically identical text exists in the golden standard), "
            "**the language model hallucinated the text**.\n"
        )
        P1_FOUND_TEXT_HEADING = ":blue[Found text |]"
        P1_GOLDEN_HEADING = ":green[Golden standard]"
        P1_SEARCH_LABEL = "Search in golden standard:"
        P1_SEARCH_PLACEHOLDER = "Start typing…"
        P1_GOLDEN_RADIO_LABEL = "Available golden standard requirements:"
        P1_NO_GOLDEN = (
            "No golden standard requirements are available for this document."
        )
        P1_NO_SEARCH_RESULTS = "No requirements match the search."
        P1_ALREADY_PAIRED_SUFFIX = " (already matched)"
        P1_CONFIRM = "Confirm match"
        P1_NOT_IN_GOLDEN = "Not in golden standard"

        # Phase 2
        P2_SUBHEADER = "Formalization evaluation and output comparison"
        P2_HOW_TO_BODY = (
            "Pair the model cards (right) with the correct reference cards (left).\n\n"
            "- Click **Select** on any card (reference or model).\n"
            "- Click **Pair** on the matching card on the other side.\n"
            "- If a model card has no reference counterpart, click **Incorrect**.\n\n"
            "To submit your verdict click **Correct** or **Incorrect** at the bottom. "
            "An optional note can be added. The card pairings are not saved."
        )
        P2_GOAL_BODY = (
            "The goal is to determine how well language models formalize a short text.\n"
            "- Agreement with the human reference means the model succeeded.\n"
            "- Different values, missing or extra cards mean the model failed."
        )
        P2_GOLDEN_HEADING = "##### :green[Golden standard reference]"
        P2_MODEL_HEADING_PREFIX = "##### :blue[Model ]"
        P2_NO_GOLDEN_CARDS = "Reference JSON is missing!"
        P2_SELECT = "Select"
        P2_PAIR = "Pair"
        P2_UNPAIR = "Unpair"
        P2_UNMARK = "Unmark"
        P2_DESELECT = "Deselect"
        P2_HALLUCINATION = "Hallucination"
        P2_MARK = "Mark"
        P2_SELECTED_BADGE = "Selected"
        P2_MARKED_BADGE = "Marked"
        # Placeholder: {n}
        P2_PAIR_BADGE = "Pair {n}"
