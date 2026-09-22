from typing import List, Optional

from src.database.models import PromptRecord
from src.database.repository import BaseRepository
from src.utils import Log


class PromptRepository(BaseRepository):

    def get_or_insert(self, prompt: PromptRecord) -> Optional[int]:
        """Return the ID of a prompt matching the given content, or insert a new row and return its ID.

        Identity is based on content -- changing the text always produces a new row.
        """
        try:
            with self._connection() as conn:
                with conn:
                    c = conn.cursor()
                    c.execute("SELECT id FROM PROMPT WHERE value = ?",
                              (prompt.value,))
                    row = c.fetchone()
                    if row:
                        return row["id"]
                    # Ensure name is unique -- append counter if already taken
                    c.execute(
                        "SELECT COUNT(*) FROM PROMPT WHERE name = ?", (prompt.name,))
                    count = c.fetchone()[0]
                    unique_name = prompt.name if count == 0 else f"{prompt.name} ({count})"
                    c.execute(
                        "INSERT INTO PROMPT (name, value) VALUES (?, ?)",
                        (unique_name, prompt.value),
                    )
                    return c.lastrowid
        except Exception as e:
            Log.error(
                message=f"PromptRepository.get_or_insert failed: {e}",
                source=self,
            )
            return None

    def get_all(self) -> List[PromptRecord]:
        """Return all prompts."""
        rows = self._execute_read("SELECT * FROM PROMPT")
        return [PromptRecord(**dict(row)) for row in rows]
