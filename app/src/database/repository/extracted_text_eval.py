from typing import Optional

from src.database.models import ExtractedTextEvalRecord, EvalMode
from src.database.repository import BaseRepository
from src.utils import Log


class ExtractedTextEvalRepository(BaseRepository):

    def _is_golden_already_matched(
        self,
        matched_golden_id: int,
        evaluator_name: str,
        mode: EvalMode,
        extracted_text_id: int,
    ) -> bool:
        """Return True if this evaluator already matched the given golden for the same model and mode."""
        rows = self._execute_read(
            """
            SELECT 1 FROM EXTRACTED_TEXT_EVAL ete
            JOIN EXTRACTED_TEXT et ON et.id = ete.extracted_text_id
            JOIN EXTRACTION_RUN er ON er.id = et.extraction_run_id
            WHERE ete.matched_golden_id = ?
              AND ete.evaluator_name = ?
              AND ete.mode = ?
              AND er.model_id = (
                  SELECT er2.model_id FROM EXTRACTED_TEXT et2
                  JOIN EXTRACTION_RUN er2 ON er2.id = et2.extraction_run_id
                  WHERE et2.id = ?
              )
            LIMIT 1
            """,
            (matched_golden_id, evaluator_name, mode, extracted_text_id),
        )
        return len(rows) > 0

    def insert(self, eval_record: ExtractedTextEvalRecord) -> Optional[int]:
        """Insert a Phase-1 evaluation record. Return its ID, or None on error or duplicate golden match."""
        if eval_record.matched_golden_id is not None:
            if self._is_golden_already_matched(
                eval_record.matched_golden_id,
                eval_record.evaluator_name,
                eval_record.mode,
                eval_record.extracted_text_id,
            ):
                Log.error(
                    message=f"Golden {eval_record.matched_golden_id} already matched "
                            f"by {eval_record.evaluator_name} in mode {eval_record.mode}.",
                    source=self,
                )
                return None
        return self._execute_write(
            """
            INSERT INTO EXTRACTED_TEXT_EVAL
            (extracted_text_id, is_correct, evaluator_name, matched_golden_id, note, mode)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                eval_record.extracted_text_id,
                eval_record.is_correct,
                eval_record.evaluator_name,
                eval_record.matched_golden_id,
                eval_record.note,
                eval_record.mode,
            ),
        )

    def get_matched_golden_ids_by_model(
        self,
        document_id: int,
        evaluator_name: str,
        mode: EvalMode,
    ) -> dict[str, set[int]]:
        """Return a mapping of {model_name -> set of golden IDs} that this evaluator has already matched
        (CORRECT) for the given document and mode.
        """
        rows = self._execute_read(
            """
            SELECT m.name AS model_name, ete.matched_golden_id AS golden_id
            FROM EXTRACTED_TEXT_EVAL ete
            JOIN EXTRACTED_TEXT et ON ete.extracted_text_id = et.id
            JOIN EXTRACTION_RUN er ON er.id = et.extraction_run_id
            JOIN MODEL m ON m.id = er.model_id
            WHERE er.document_id = ?
              AND ete.evaluator_name = ?
              AND ete.mode = ?
              AND ete.is_correct = 1
              AND ete.matched_golden_id IS NOT NULL
            """,
            (document_id, evaluator_name, mode),
        )
        result: dict[str, set[int]] = {}
        for row in rows:
            model = row["model_name"]
            golden_id = row["golden_id"]
            result.setdefault(model, set()).add(golden_id)
        return result

    def already_evaluated(self, extracted_text_id: int, evaluator_name: str, mode: EvalMode) -> bool:
        """Return True if this user already submitted an evaluation for the record in the given mode."""
        rows = self._execute_read(
            """
            SELECT 1 FROM EXTRACTED_TEXT_EVAL
            WHERE extracted_text_id = ? AND evaluator_name = ? AND mode = ?
            LIMIT 1
            """,
            (extracted_text_id, evaluator_name, mode),
        )
        return len(rows) > 0
