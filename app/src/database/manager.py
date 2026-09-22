import sqlite3
from pathlib import Path

from src.database.repository.document import DocumentRepository
from src.database.repository.prompt import PromptRepository
from src.database.repository.model import ModelRepository
from src.database.repository.extraction_run import ExtractionRunRepository
from src.database.repository.extracted_text import ExtractedTextRepository
from src.database.repository.analyzed_text import AnalyzedTextRepository
from src.database.repository.extracted_text_eval import ExtractedTextEvalRepository
from src.database.repository.analyzed_text_eval import AnalyzedTextEvalRepository


class DatabaseManager:
    """Manager for working with SQLite database for extraction and formalization."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        self.documents = DocumentRepository(self._get_connection)
        self.prompts = PromptRepository(self._get_connection)
        self.models = ModelRepository(self._get_connection)
        self.extraction_runs = ExtractionRunRepository(self._get_connection)
        self.extracted_texts = ExtractedTextRepository(self._get_connection)
        self.analyzed_texts = AnalyzedTextRepository(self._get_connection)
        self.extracted_text_evals = ExtractedTextEvalRepository(
            self._get_connection)
        self.analyzed_text_evals = AnalyzedTextEvalRepository(
            self._get_connection)

    def _get_connection(self) -> sqlite3.Connection:
        """Opens and configures a new DB connection."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Create all tables if they do not exist."""
        conn = self._get_connection()
        with conn:
            c = conn.cursor()

            c.execute("""
                CREATE TABLE IF NOT EXISTS DOCUMENT (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL UNIQUE,
                    file_path TEXT NOT NULL UNIQUE,
                    image_folder_path TEXT UNIQUE,
                    upload_date TEXT NOT NULL,
                    raw_full_text TEXT NOT NULL
                )
            """)

            c.execute("""
                CREATE TABLE IF NOT EXISTS PROMPT (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    value TEXT NOT NULL
                )
            """)

            c.execute("""
                CREATE TABLE IF NOT EXISTS MODEL (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                )
            """)

            c.execute("""
                CREATE TABLE IF NOT EXISTS EXTRACTION_RUN (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    prompt_id INTEGER NOT NULL,
                    model_id INTEGER NOT NULL,
                    extracted_at TEXT NOT NULL,
                    duration_ms INTEGER,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    FOREIGN KEY(document_id) REFERENCES DOCUMENT(id) ON DELETE CASCADE,
                    FOREIGN KEY(prompt_id) REFERENCES PROMPT(id),
                    FOREIGN KEY(model_id) REFERENCES MODEL(id)
                )
            """)

            c.execute("""
                CREATE TABLE IF NOT EXISTS EXTRACTED_TEXT (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    extraction_run_id INTEGER NOT NULL,
                    raw_text TEXT NOT NULL,
                    FOREIGN KEY(extraction_run_id) REFERENCES EXTRACTION_RUN(id) ON DELETE CASCADE
                )
            """)

            c.execute("""
                CREATE TABLE IF NOT EXISTS ANALYZED_TEXT (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    extracted_text_id INTEGER NOT NULL,
                    prompt_id INTEGER NOT NULL,
                    model_id INTEGER NOT NULL,
                    analyzed_at TEXT NOT NULL,
                    result TEXT NOT NULL,
                    duration_ms INTEGER,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    FOREIGN KEY(extracted_text_id) REFERENCES EXTRACTED_TEXT(id) ON DELETE CASCADE,
                    FOREIGN KEY(prompt_id) REFERENCES PROMPT(id),
                    FOREIGN KEY(model_id) REFERENCES MODEL(id)
                )
            """)

            c.execute("""
                CREATE TABLE IF NOT EXISTS EXTRACTED_TEXT_EVAL (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    extracted_text_id INTEGER NOT NULL,
                    is_correct INTEGER NOT NULL,
                    evaluator_name TEXT NOT NULL,
                    matched_golden_id INTEGER,
                    note TEXT,
                    mode TEXT NOT NULL DEFAULT 'benchmark',
                    FOREIGN KEY(extracted_text_id) REFERENCES EXTRACTED_TEXT(id) ON DELETE CASCADE,
                    FOREIGN KEY(matched_golden_id) REFERENCES EXTRACTED_TEXT(id) ON DELETE SET NULL
                )
            """)

            c.execute("""
                CREATE TABLE IF NOT EXISTS ANALYZED_TEXT_EVAL (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analyzed_text_id INTEGER NOT NULL,
                    is_correct INTEGER NOT NULL,
                    evaluator_name TEXT NOT NULL,
                    note TEXT,
                    mode TEXT NOT NULL DEFAULT 'benchmark',
                    FOREIGN KEY(analyzed_text_id) REFERENCES ANALYZED_TEXT(id) ON DELETE CASCADE
                )
            """)

            c.execute("CREATE INDEX IF NOT EXISTS idx_extraction_run_doc_model_prompt "
                      "ON EXTRACTION_RUN(document_id, model_id, prompt_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_extracted_text_run "
                      "ON EXTRACTED_TEXT(extraction_run_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_analyzed_text_extracted_model_prompt "
                      "ON ANALYZED_TEXT(extracted_text_id, model_id, prompt_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_extracted_eval_extracted_evaluator_mode "
                      "ON EXTRACTED_TEXT_EVAL(extracted_text_id, evaluator_name, mode)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_extracted_eval_golden_evaluator_mode "
                      "ON EXTRACTED_TEXT_EVAL(matched_golden_id, evaluator_name, mode) "
                      "WHERE matched_golden_id IS NOT NULL")
            c.execute("CREATE INDEX IF NOT EXISTS idx_analyzed_eval_analyzed_evaluator_mode "
                      "ON ANALYZED_TEXT_EVAL(analyzed_text_id, evaluator_name, mode)")
        conn.close()
