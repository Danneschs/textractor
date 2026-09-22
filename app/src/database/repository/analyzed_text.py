from datetime import datetime
from typing import List, Optional

from src.database.models import AnalyzedTextRecord, ExtractedTextRecord, EvalMode
from src.database.repository import BaseRepository
from src.utils import Log


class AnalyzedTextRepository(BaseRepository):

    def insert(self, record: AnalyzedTextRecord) -> Optional[int]:
        """Insert an AnalyzedTextRecord. Return its ID, or None on error."""
        record.analyzed_at = datetime.now().isoformat(timespec="seconds")
        row_id = self._execute_write(
            """
            INSERT INTO ANALYZED_TEXT
            (extracted_text_id, prompt_id, model_id, analyzed_at, result, duration_ms, input_tokens, output_tokens)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (record.extracted_text_id, record.prompt_id, record.model_id,
             record.analyzed_at, record.result, record.duration_ms,
             record.input_tokens, record.output_tokens),
        )
        if row_id is None:
            Log.error(
                message="AnalyzedTextRepository.insert failed.", source=self)
        return row_id

    def get_by_extracted_text(self, extracted_text_id: int) -> List[AnalyzedTextRecord]:
        """Return all analyzed texts for a given extracted text."""
        rows = self._execute_read(
            """
            SELECT at.*, m.name AS model_name
            FROM ANALYZED_TEXT at
            JOIN MODEL m ON m.id = at.model_id
            WHERE at.extracted_text_id = ?
            """,
            (extracted_text_id,),
        )
        return [AnalyzedTextRecord(**dict(row)) for row in rows]

    def has_any_for_document(self, document_id: int, golden: bool) -> bool:
        """Return True if the document has at least one analyzed text for golden or non-golden extracted texts."""
        model_filter = "= 'human'" if golden else "!= 'human'"
        rows = self._execute_read(
            f"""
            SELECT 1 FROM ANALYZED_TEXT at
            JOIN EXTRACTED_TEXT et ON et.id = at.extracted_text_id
            JOIN EXTRACTION_RUN er ON er.id = et.extraction_run_id
            JOIN MODEL m ON m.id = er.model_id
            WHERE er.document_id = ? AND m.name {model_filter}
            LIMIT 1
            """,
            (document_id,),
        )
        return len(rows) > 0

    def get_unevaluated_for_correct_extracted(
        self, document_id: int, evaluator_name: str
    ) -> List[AnalyzedTextRecord]:
        """Return analyzed texts whose parent extracted text was marked correct by the given user
        in production mode, and that the user has not yet evaluated in production mode.
        """
        rows = self._execute_read(
            """
            SELECT at.*, m.name AS model_name
            FROM ANALYZED_TEXT at
            JOIN MODEL m ON m.id = at.model_id
            JOIN EXTRACTED_TEXT et ON et.id = at.extracted_text_id
            JOIN EXTRACTION_RUN er ON er.id = et.extraction_run_id
            JOIN MODEL em ON em.id = er.model_id
            WHERE er.document_id = ?
              AND em.name != 'human'
              AND EXISTS (
                  SELECT 1 FROM EXTRACTED_TEXT_EVAL ete
                  WHERE ete.extracted_text_id = et.id
                    AND ete.evaluator_name = ?
                    AND ete.is_correct = 1
                    AND ete.mode = 'production'
              )
              AND NOT EXISTS (
                  SELECT 1 FROM ANALYZED_TEXT_EVAL ate
                  WHERE ate.analyzed_text_id = at.id
                    AND ate.evaluator_name = ?
                    AND ate.mode = 'production'
              )
            """,
            (document_id, evaluator_name, evaluator_name),
        )
        return [AnalyzedTextRecord(**dict(row)) for row in rows]

    def get_unevaluated_golden_groups(self, document_id: int, evaluator_name: str) -> List[ExtractedTextRecord]:
        """Return golden (human annotated) extracted text rows for the document that have at least one
        golden analyzed text not yet evaluated by the given user in benchmark mode.
        """
        rows = self._execute_read(
            """
            SELECT DISTINCT et.id, et.raw_text, et.extraction_run_id,
                   er.document_id, er.prompt_id, er.model_id, em.name AS model_name
            FROM EXTRACTED_TEXT et
            JOIN EXTRACTION_RUN er ON er.id = et.extraction_run_id
            JOIN MODEL em ON em.id = er.model_id
            JOIN ANALYZED_TEXT at ON at.extracted_text_id = et.id
            JOIN MODEL am ON am.id = at.model_id
            WHERE er.document_id = ?
              AND em.name = 'human'
              AND am.name != 'human'
              AND at.id NOT IN (
                  SELECT analyzed_text_id
                  FROM ANALYZED_TEXT_EVAL
                  WHERE evaluator_name = ?
                    AND mode = 'benchmark'
              )
            """,
            (document_id, evaluator_name),
        )
        return [ExtractedTextRecord(**dict(row)) for row in rows]
