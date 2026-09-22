from typing import Optional

from src.database.models import AnalyzedTextEvalRecord, EvalMode
from src.database.repository import BaseRepository
from src.utils import Log


class AnalyzedTextEvalRepository(BaseRepository):

    def insert(self, eval_record: AnalyzedTextEvalRecord) -> Optional[int]:
        """Insert an evaluation for an analyzed text. Return its ID, or None on error."""
        row_id = self._execute_write(
            """
            INSERT INTO ANALYZED_TEXT_EVAL (analyzed_text_id, is_correct, evaluator_name, note, mode)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                eval_record.analyzed_text_id,
                eval_record.is_correct,
                eval_record.evaluator_name,
                eval_record.note,
                eval_record.mode,
            ),
        )
        if row_id is None:
            Log.error(
                message="AnalyzedTextEvalRepository.insert failed.", source=self)
        return row_id

    def already_evaluated(self, analyzed_text_id: int, evaluator_name: str, mode: EvalMode) -> bool:
        """Return True if this user already submitted an evaluation for the record in the given mode."""
        rows = self._execute_read(
            """
            SELECT 1 FROM ANALYZED_TEXT_EVAL
            WHERE analyzed_text_id = ? AND evaluator_name = ? AND mode = ?
            LIMIT 1
            """,
            (analyzed_text_id, evaluator_name, mode),
        )
        return len(rows) > 0
