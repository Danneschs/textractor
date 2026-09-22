from typing import List, Optional

from src.database.models import ModelRecord
from src.database.repository import BaseRepository
from src.utils import Log


class ModelRepository(BaseRepository):

    def get_or_insert(self, record: ModelRecord) -> Optional[int]:
        """Return the model ID by name, or insert a new row and return its ID."""
        try:
            with self._connection() as conn:
                with conn:
                    c = conn.cursor()
                    c.execute("SELECT id FROM MODEL WHERE name = ?", (record.name,))
                    row = c.fetchone()
                    if row:
                        return row["id"]
                    c.execute("INSERT INTO MODEL (name) VALUES (?)", (record.name,))
                    return c.lastrowid
        except Exception as e:
            Log.error(message=f"ModelRepository.get_or_insert failed: {e}", source=self)
            return None

    def get_all(self) -> List[ModelRecord]:
        """Return all models."""
        rows = self._execute_read("SELECT * FROM MODEL")
        return [ModelRecord(**dict(row)) for row in rows]
