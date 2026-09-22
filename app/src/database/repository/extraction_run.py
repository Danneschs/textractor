import sqlite3
from datetime import datetime
from typing import Optional

from src.database.models import ExtractionRunRecord
from src.database.repository import BaseRepository
from src.utils import Log


class ExtractionRunRepository(BaseRepository):

    def insert(self, record: ExtractionRunRecord) -> Optional[int]:
        """Insert one ExtractionRunRecord. Return its ID, or None on error."""
        record.extracted_at = datetime.now().isoformat(timespec="seconds")
        row_id = self._execute_write(
            """
            INSERT INTO EXTRACTION_RUN
            (document_id, prompt_id, model_id, extracted_at, duration_ms, input_tokens, output_tokens)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (record.document_id, record.prompt_id, record.model_id,
             record.extracted_at, record.duration_ms,
             record.input_tokens, record.output_tokens),
        )
        if row_id is None:
            Log.error(
                message="ExtractionRunRepository.insert failed.", source=self)
        return row_id

    def insert_with_texts(
        self,
        run: ExtractionRunRecord,
        raw_texts: list[str],
    ) -> Optional[int]:
        """Atomically insert one ExtractionRun and all its ExtractedText rows.

        Return the run ID on success, or None on any error (full rollback).
        """
        run.extracted_at = datetime.now().isoformat(timespec="seconds")
        try:
            with self._connection() as conn:
                with conn:
                    c = conn.cursor()
                    c.execute(
                        "INSERT INTO EXTRACTION_RUN "
                        "(document_id, prompt_id, model_id, extracted_at, duration_ms, input_tokens, output_tokens) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (run.document_id, run.prompt_id, run.model_id,
                         run.extracted_at, run.duration_ms,
                         run.input_tokens, run.output_tokens),
                    )
                    run_id = c.lastrowid
                    for raw_text in raw_texts:
                        c.execute(
                            "INSERT INTO EXTRACTED_TEXT (extraction_run_id, raw_text) "
                            "VALUES (?, ?)",
                            (run_id, raw_text),
                        )
            return run_id
        except sqlite3.Error as e:
            Log.error(message=f"insert_with_texts failed: {e}", source=self)
            return None
