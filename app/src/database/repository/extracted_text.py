from typing import List, Optional

from src.database.models import ExtractedTextRecord, EvalMode
from src.database.repository import BaseRepository
from src.utils import Log

_JOIN = """
    JOIN EXTRACTION_RUN er ON er.id = et.extraction_run_id
    JOIN MODEL m ON m.id = er.model_id
"""
_SELECT = (
    "SELECT et.id, et.extraction_run_id, et.raw_text, "
    "er.document_id, er.prompt_id, er.model_id, m.name AS model_name "
    "FROM EXTRACTED_TEXT et" + _JOIN
)


class ExtractedTextRepository(BaseRepository):

    def insert(self, record: ExtractedTextRecord) -> Optional[int]:
        """Insert an extracted text record. Return its ID, or None on error."""
        row_id = self._execute_write(
            "INSERT INTO EXTRACTED_TEXT (extraction_run_id, raw_text) VALUES (?, ?)",
            (record.extraction_run_id, record.raw_text),
        )
        if row_id is None:
            Log.error(
                message="ExtractedTextRepository.insert failed.", source=self)
        return row_id

    def get_by_document(self, document_id: int) -> List[ExtractedTextRecord]:
        """Return all extracted texts for a given document."""
        rows = self._execute_read(
            f"{_SELECT} WHERE er.document_id = ?",
            (document_id,),
        )
        return [ExtractedTextRecord(**dict(row)) for row in rows]

    def get_pending_analysis(self, model_id: int, prompt_id: int) -> List[ExtractedTextRecord]:
        """Return all extracted texts not yet analyzed by the given model+prompt, newest first."""
        rows = self._execute_read(
            f"""
            {_SELECT}
            WHERE NOT EXISTS (
                SELECT 1 FROM ANALYZED_TEXT at
                WHERE at.extracted_text_id = et.id
                  AND at.model_id = ?
                  AND at.prompt_id = ?
            )
            ORDER BY et.id DESC
            """,
            (model_id, prompt_id),
        )
        return [ExtractedTextRecord(**dict(row)) for row in rows]

    def get_by_id(self, extracted_text_id: int) -> Optional[ExtractedTextRecord]:
        """Return an extracted text record by its id, or None."""
        rows = self._execute_read(
            f"{_SELECT} WHERE et.id = ? LIMIT 1",
            (extracted_text_id,),
        )
        return ExtractedTextRecord(**dict(rows[0])) if rows else None

    def has_golden(self, document_id: int) -> bool:
        """Return True if the document has at least one golden (human) extracted text."""
        rows = self._execute_read(
            f"""
            SELECT 1 FROM EXTRACTED_TEXT et{_JOIN}
            WHERE er.document_id = ? AND m.name = 'human' LIMIT 1
            """,
            (document_id,),
        )
        return len(rows) > 0

    def has_non_golden(self, document_id: int) -> bool:
        """Return True if the document has at least one non-golden (LLM) extracted text."""
        rows = self._execute_read(
            f"""
            SELECT 1 FROM EXTRACTED_TEXT et{_JOIN}
            WHERE er.document_id = ? AND m.name != 'human' LIMIT 1
            """,
            (document_id,),
        )
        return len(rows) > 0

    def get_golden_by_document(self, document_id: int) -> List[ExtractedTextRecord]:
        """Return all golden (human-annotated) extracted texts for a given document."""
        rows = self._execute_read(
            f"""
            {_SELECT}
            WHERE er.document_id = ?
              AND m.name = 'human'
            """,
            (document_id,),
        )
        return [ExtractedTextRecord(**dict(row)) for row in rows]

    def get_unevaluated_non_golden(
        self,
        document_id: int,
        evaluator_name: str,
        mode: EvalMode,
        only_with_golden: bool = False,
    ) -> List[ExtractedTextRecord]:
        """Return non-golden (LLM generated) extracted texts for a document not yet evaluated by the given user.

        When only_with_golden=True, restrict to documents that have at least one human-annotated
        extracted text (for Benchmark Phase 1).
        """
        golden_filter = ""
        if only_with_golden:
            golden_filter = """
              AND EXISTS (
                  SELECT 1 FROM EXTRACTED_TEXT et2
                  JOIN EXTRACTION_RUN er2 ON er2.id = et2.extraction_run_id
                  JOIN MODEL m2 ON m2.id = er2.model_id
                  WHERE er2.document_id = er.document_id AND m2.name = 'human'
              )"""
        rows = self._execute_read(
            f"""
            {_SELECT}
            WHERE er.document_id = ?
              AND m.name != 'human'
              AND NOT EXISTS (
                  SELECT 1 FROM EXTRACTED_TEXT_EVAL ete
                  WHERE ete.extracted_text_id = et.id
                    AND ete.evaluator_name = ?
                    AND ete.mode = ?
              ){golden_filter}
            """,
            (document_id, evaluator_name, mode),
        )
        return [ExtractedTextRecord(**dict(row)) for row in rows]
