from src.documents.loaders import LocalLoader
import json
import logging
from abc import ABC, abstractmethod
from pdfplumber import open as pdf_open
import pypdfium2 as pdfium  # type: ignore
from pypdfium2.raw import FPDF_PAGEOBJ_IMAGE  # type: ignore
from pathlib import Path
from typing import Optional
import io

from src.database.manager import DatabaseManager
from src.documents.loaders import Loader
from src.documents.writers import ImageWriter
from src.database.models import DocumentRecord, ExtractedTextRecord, AnalyzedTextRecord, PromptRecord, ModelRecord, ExtractionRunRecord
from src.documents.models import FileType
from src.documents.schemas import GoldenDatasetSchema
from src.llms.schemas import AnalyzedTextSchema
from src.llms.config import LLMList

from src.utils import Log, progress


class BaseIngestor(ABC):
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def _should_skip(self, filename: str) -> bool:
        """Return True (and log) if the file should be skipped due to 'skip_' prefix."""
        if filename.startswith("skip_"):
            Log.debug(
                message=f"File '{filename}' has 'skip_' prefix. Skipping ingestion...",
                source=self,
            )
            return True
        return False

    @abstractmethod
    def ingest_all(self) -> None: ...


class DocumentIngestor(BaseIngestor):
    """
    Load documents via the supplied Loader, parse each PDF, and store DocumentRecords to the database.

    Extracts raw_full_text (all page text concatenated) and image_folder_path (path to the
    per-document folder of embedded image XObjects, or None when the PDF has no images).
    Already-ingested filenames are skipped silently.
    """

    def __init__(
        self,
        db: DatabaseManager,
        loader: Loader,
        image_output_dir: str | Path | None = None
    ):
        super().__init__(db)
        self.loader = loader
        self.image_output_dir = Path(
            image_output_dir) if image_output_dir else None
        self._image_writer = ImageWriter(
            base_output_dir=self.image_output_dir) if self.image_output_dir else None

    def _extract_images(self, pdf_bytes: bytes, filename: str) -> Optional[str]:
        """Extract every embedded image XObject from a PDF and save it to disk.

        Return the path of the per-document image folder, or None if nothing was saved
        (no writer configured, or no images in the PDF).
        """
        if not self._image_writer or not self.image_output_dir:
            return None

        stem = Path(filename).stem
        doc_image_dir = self.image_output_dir / stem
        doc_image_dir.mkdir(parents=True, exist_ok=True)

        saved_any = False
        pdf = pdfium.PdfDocument(pdf_bytes)
        try:
            for page_num, page in enumerate(pdf, start=1):
                try:
                    img_idx = 0
                    for obj in page.get_objects(filter=[FPDF_PAGEOBJ_IMAGE]):
                        img_idx += 1
                        prefix = doc_image_dir / f"page{page_num}_{img_idx}"
                        if self._image_writer.write(obj, prefix):
                            saved_any = True
                except Exception as e:
                    Log.warning(
                        message=f"Failed to enumerate images on page {page_num} of '{filename}': {e}",
                        source=self,
                    )
                finally:
                    page.close()
        finally:
            pdf.close()

        return doc_image_dir.as_posix() if saved_any else None

    def ingest_all(self) -> None:
        """Ingest every document from the loader into the database."""
        for loaded_doc in progress(self.loader, desc="Ingesting documents", total=len(self.loader)):
            filename = loaded_doc.filename
            file_path = loaded_doc.file_path

            if self._should_skip(Path(filename).name):
                continue

            try:
                # Check, if the document is already ingested (by filename) -- skip if so
                existing_doc = self.db.documents.get_by_filename(filename)
                if existing_doc:
                    Log.debug(
                        message=f"Document '{filename}' already exists in DB (id={existing_doc.id}). Skipping ingestion...",
                        source=self,
                    )
                    continue

                with pdf_open(io.BytesIO(loaded_doc.data)) as pdf:
                    # Text extraction
                    pages_text = [
                        page.extract_text() or "" for page in pdf.pages]
                    raw_full_text = "\n".join(t for t in pages_text if t)

                # Image extraction (every embedded image XObject)
                image_folder_path = self._extract_images(
                    loaded_doc.data, filename)

            except Exception as e:
                Log.error(
                    message=f"Failed to parse '{filename}': {e}. Skipping...",
                    source=self,
                )
                continue

            if not raw_full_text:
                Log.warning(
                    message=f"No text found in '{filename}'. Skipping...",
                    source=self,
                )
                continue

            record = DocumentRecord(
                filename=filename,
                file_path=file_path,
                raw_full_text=raw_full_text,
                image_folder_path=image_folder_path,
            )
            doc_id = self.db.documents.insert(record)
            if doc_id:
                Log.info(
                    message=f"Ingested '{filename}' (id={doc_id}).",
                    source=self,
                )
            else:
                Log.error(
                    message=f"Insert failed for '{filename}'.",
                    source=self,
                )


class GoldenDatasetIngestor(BaseIngestor):
    """Handles ingestion of golden datasets to the database."""

    def __init__(self, db: DatabaseManager, golden_dir: str | Path):
        super().__init__(db)
        self.golden_dir = Path(golden_dir)

    def _store_golden_prompt(self) -> Optional[int]:
        """Ensure the "golden_human_expert" prompt exists in the database. Return its ID or None on error."""
        prompt_name = "golden_human_expert"
        prompt_value = "_"

        # Inserting the prompt if it doesn't exist, and retrieving its ID
        prompt_id = self.db.prompts.get_or_insert(PromptRecord(
            name=prompt_name,
            value=prompt_value
        ))

        return prompt_id

    def _insert_golden_document(self, document_id: int, document_filename: str, document: GoldenDatasetSchema[AnalyzedTextSchema]):
        """Store the golden dataset in the database. Skip if golden data already exists for this document."""

        # Idempotency guard: skip if golden extracted texts already exist for this document
        if self.db.extracted_texts.has_golden(document_id):
            Log.debug(
                f"Golden data for document '{document_filename}' already exists. Skipping.")
            return False

        prompt_id = self._store_golden_prompt()
        if not prompt_id:
            Log.error(
                "Failed to ensure existence of golden prompt in the database.")
            return False

        human_model_id = self.db.models.get_or_insert(
            ModelRecord(name=LLMList.HUMAN.value))
        if not human_model_id:
            Log.error("Failed to register human model in the database.")
            return False

        run_id = self.db.extraction_runs.insert(ExtractionRunRecord(
            document_id=document_id,
            prompt_id=prompt_id,
            model_id=human_model_id,
            model_name=LLMList.HUMAN.value,
            duration_ms=None,
        ))
        if not run_id:
            Log.error("Failed to create golden extraction run in the database.")
            return False

        for req in document.golden_parameters:
            # Phase 1 insertion (extracted text)
            extracted_id = self.db.extracted_texts.insert(ExtractedTextRecord(
                document_id=document_id,
                prompt_id=prompt_id,
                model_name=LLMList.HUMAN.value,
                model_id=human_model_id,
                raw_text=req.raw_text,
                extraction_run_id=run_id,
            ))

            # Phase 2 insertion (analyzed text)
            if extracted_id and req.analyzed_data:
                analyzed_json_string = req.analyzed_data.model_dump_json()

                self.db.analyzed_texts.insert(AnalyzedTextRecord(
                    extracted_text_id=extracted_id,
                    prompt_id=prompt_id,
                    model_name=LLMList.HUMAN.value,
                    model_id=human_model_id,
                    result=analyzed_json_string,
                ))

        Log.info(
            f"Golden data for document {document_filename} were successfully stored to DB.")

    def ingest_single_file(self, json_path: Path):
        """Load, validate, and ingest a single golden dataset JSON file into the database."""

        if self._should_skip(json_path.name):
            return

        # Loading
        with open(json_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        # Validation + parsing to Pydantic model
        try:
            golden_doc = GoldenDatasetSchema[AnalyzedTextSchema].model_validate(
                raw_data)
        except Exception as e:
            Log.error(
                f"Error validating file {json_path.name} -- invalid JSON structure: {e}")
            return

        # Find the corresponding document in the DB by filename (the document must already exist for linking)
        doc = self.db.documents.get_by_filename(golden_doc.document_filename)
        if not doc:
            Log.error(
                f"Document '{golden_doc.document_filename}' is not in the DB. Please run DocumentIngestor first.")
            return

        # Writing to DB
        if not doc.id:
            Log.error(
                f"Document '{golden_doc.document_filename}' has no ID in DB. Cannot link golden data.")
            return

        self._insert_golden_document(
            doc.id, golden_doc.document_filename, golden_doc)

    def ingest_all(self):
        """Ingest all golden dataset JSON files found in the configured directory."""
        if not self.golden_dir.exists():
            Log.error(
                f"Directory {self.golden_dir} does not exist. Cannot ingest golden datasets.")
            return

        json_files = list(self.golden_dir.glob(FileType.JSON.value[0]))
        for json_path in progress(json_files, desc="Ingesting golden data", total=len(json_files)):
            self.ingest_single_file(json_path)
