"""
Main entry point for Textractor. Provides a command-line interface to run the extraction and formalization pipeline, as well as an option to launch the Streamlit-based GUI for interactive evaluation.
"""

import subprocess
import sys

from dotenv import load_dotenv

from src.utils import Log, get_db_path
from src.documents.loaders import LocalLoader
from src.database.manager import DatabaseManager
from src.documents.ingestors import DocumentIngestor, GoldenDatasetIngestor
from src.pipeline.extractor import ExtractionPhase
from src.pipeline.formalizer import FormalizationPhase
from src.llms.backends import LLMBackend, BACKEND_REGISTRY
from src.llms.config import LLMList, EXTRACTION_CONFIG, ANALYSIS_CONFIG
from src.documents.models import FileType

DATA_PATH = "data/raw_pdfs"
GOLDEN_PATH = "data/golden_seed"

_SELECTABLE_MODELS = list(BACKEND_REGISTRY)


def _create_backend(model: LLMList) -> LLMBackend:
    """Instantiate an LLM backend based on the provided model enum."""
    return BACKEND_REGISTRY[model](model)


def _select_model(prompt: str) -> LLMList:
    """Prompt the user to select an LLM model from the available options."""
    print(f"\n{prompt}")
    for i, m in enumerate(_SELECTABLE_MODELS, 1):
        print(f"  {i}. {m.value}")
    while True:
        raw = input(input_char).strip()
        if raw.isdigit() and 1 <= int(raw) <= len(_SELECTABLE_MODELS):
            return _SELECTABLE_MODELS[int(raw) - 1]
        print("Invalid choice, try again.")


def _launch_gui() -> None:
    """Launch the Streamlit GUI for interactive evaluation."""
    print("Starting Textractor Studio... (press Ctrl+C to stop)")
    subprocess.run(["streamlit", "run", "gui.py"])


def main(extractor_model: LLMList | None, analyzer_model: LLMList | None) -> None:
    """Run the Textractor pipeline with the specified models for each phase."""
    load_dotenv()
    Log.setup_logging()

    db = DatabaseManager(get_db_path())
    loader = LocalLoader(root_dir=DATA_PATH, file_type=FileType.PDF)

    ingestor = DocumentIngestor(
        db, loader, image_output_dir="data/extracted_images")
    ingestor.ingest_all()

    golden_ingestor = GoldenDatasetIngestor(db, GOLDEN_PATH)
    golden_ingestor.ingest_all()

    Log.info(message="Starting pipeline...")
    if extractor_model is not None:
        ExtractionPhase(db, _create_backend(
            extractor_model), EXTRACTION_CONFIG).run()
    if analyzer_model is not None:
        FormalizationPhase(db, _create_backend(
            analyzer_model), ANALYSIS_CONFIG).run()
    Log.info(message="Pipeline complete.")


if __name__ == "__main__":
    input_char = "> "
    thick_line = "===================================="
    thin_line = "------------------------------------"
    while True:
        try:
            print(thick_line)
            print("             TEXTRACTOR             ")
            print(thick_line)

            print("1. Run Textractor")
            print("2. Start Textractor Studio")
            print("3. Exit")
            choice = input(input_char).strip()

            if choice == "1":
                print(thin_line)
                print("Select phases to run:")
                print("  1. Both")
                print("  2. Extraction only")
                print("  3. Formalization only")
                phase = input(input_char).strip()
                if phase not in ("1", "2", "3"):
                    print("Invalid choice, try again.")
                    continue
                print(thin_line)
                ext_model = _select_model(
                    "Select extraction model (phase 1):") if phase in ("1", "2") else None
                if phase == "1":
                    print(thin_line)
                ana_model = _select_model(
                    "Select formalization model (phase 2):") if phase in ("1", "3") else None
                print(thin_line)
                if ext_model:
                    print(f"Extraction    : {ext_model.value}")
                if ana_model:
                    print(f"Formalization : {ana_model.value}")
                main(ext_model, ana_model)
            elif choice == "2":
                _launch_gui()
            elif choice == "3":
                sys.exit(0)
            else:
                print("Invalid choice, try again.")
        except Exception as e:
            Log.error(f"An error occurred: {e}")
            print("An error occurred: ", e)
