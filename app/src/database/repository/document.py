from datetime import datetime
from typing import List, Optional

from src.database.models import DocumentRecord
from src.database.repository import BaseRepository
from src.utils import Log


class DocumentRepository(BaseRepository):

    def insert(self, doc: DocumentRecord) -> Optional[int]:
        """Insert a new document, or skip if filename already exists.

        Return the document ID (new or existing), or None on error.
        """
        doc.upload_date = datetime.now().isoformat(timespec="seconds")
        try:
            with self._connection() as conn:
                with conn:
                    c = conn.cursor()
                    c.execute(
                        """INSERT OR IGNORE INTO DOCUMENT
                           (filename, file_path, image_folder_path, upload_date, raw_full_text)
                           VALUES (?, ?, ?, ?, ?)""",
                        (doc.filename, doc.file_path,
                         doc.image_folder_path, doc.upload_date, doc.raw_full_text),
                    )
                    c.execute(
                        "SELECT id FROM DOCUMENT WHERE filename = ?", (doc.filename,))
                    row = c.fetchone()
                    return row["id"] if row else None
        except Exception as e:
            Log.error(
                message=f"DocumentRepository.insert failed for '{doc.filename}': {e}",
                source=self,
            )
            return None

    def get_all(self) -> List[DocumentRecord]:
        """Return all documents ordered by upload date descending."""
        rows = self._execute_read(
            "SELECT * FROM DOCUMENT ORDER BY upload_date DESC")
        return [DocumentRecord(**dict(row)) for row in rows]

    def get_all_with_golden(self) -> List[DocumentRecord]:
        """Return only documents that have at least one golden extracted text."""
        rows = self._execute_read(
            """
            SELECT d.* FROM DOCUMENT d
            WHERE EXISTS (
                SELECT 1 FROM EXTRACTION_RUN er
                JOIN MODEL m ON m.id = er.model_id
                WHERE er.document_id = d.id AND m.name = 'human'
            )
            ORDER BY d.upload_date DESC
            """
        )
        return [DocumentRecord(**dict(row)) for row in rows]

    def get_pending_extraction(self, model_id: int, prompt_id: int) -> List[DocumentRecord]:
        """Return documents not yet processed by the given model+prompt in Phase 1."""
        rows = self._execute_read(
            """
            SELECT d.*
            FROM DOCUMENT d
            WHERE NOT EXISTS (
                SELECT 1 FROM EXTRACTION_RUN er
                WHERE er.document_id = d.id
                  AND er.model_id = ?
                  AND er.prompt_id = ?
            )
            """,
            (model_id, prompt_id),
        )
        return [DocumentRecord(**dict(row)) for row in rows]

    def get_by_id(self, doc_id: int) -> Optional[DocumentRecord]:
        """Return a document by primary key, or None if not found."""
        row = self._execute_read(
            "SELECT * FROM DOCUMENT WHERE id = ? LIMIT 1", (doc_id,))
        return DocumentRecord(**dict(row[0])) if row else None

    def get_by_filename(self, filename: str) -> Optional[DocumentRecord]:
        """Return a document by filename, or None if not found."""
        row = self._execute_read(
            "SELECT * FROM DOCUMENT WHERE filename = ?", (filename,))
        return DocumentRecord(**dict(row[0])) if row else None
