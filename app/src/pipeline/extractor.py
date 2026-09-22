import time

from src.llms.schemas import ExtractedTextSchema
from src.database.models import ExtractionRunRecord
from src.pipeline.phase import Phase
from src.utils import Log, progress_with_bar


class ExtractionPhase(Phase):
    """
    Extraction phase of the pipeline.

    Reads every DOCUMENT row that has not yet been processed by this model+prompt, 
    sends the raw full text to the LLM backend (which returns a structured JSON string validated against ExtractedTextSchema), and persists the result as an EXTRACTED_TEXT row.

    Re-running this phase only processes documents that are missing an EXTRACTED_TEXT entry for the configured model+prompt.
    """

    def run(self) -> None:
        """Run the extraction phase."""
        model_name = self.backend.model_name

        prompt_id = self._register_prompt()
        if prompt_id is None:
            return
        model_id = self._register_model()
        if model_id is None:
            return

        pending = self.db.documents.get_pending_extraction(model_id, prompt_id)
        Log.info(
            message=f"Extraction: {len(pending)} document(s) pending for model '{model_name}'.",
            source=self,
        )

        if not pending:
            return

        for bar, doc in progress_with_bar(pending, desc=f"Extraction [{model_name}]", total=len(pending)):
            bar.set_description(f"Extraction [{model_name}] {doc.filename}")
            Log.info(
                message=f"Extracting '{doc.filename}' (doc_id={doc.id})...",
                source=self,
            )
            try:
                _start = time.perf_counter()
                result = self.backend.generate(
                    user_content=doc.raw_full_text,
                    llm_config=self.llm_config,
                )
                duration_ms = int((time.perf_counter() - _start) * 1000)
                bar.set_postfix(done_in=f"{duration_ms}ms")
            except Exception as e:
                Log.error(
                    message=f"LLM error for '{doc.filename}': {e}. Skipping...",
                    source=self,
                )
                continue

            if doc.id is None:
                Log.error(
                    message=f"Document '{doc.filename}' has no DB id. Skipping...", source=self)
                continue

            try:
                parsed = ExtractedTextSchema.model_validate_json(result.text)
            except Exception as e:
                Log.error(
                    message=f"Failed to parse LLM response for '{doc.filename}': {e}. Skipping...",
                    source=self,
                )
                continue

            run_record = ExtractionRunRecord(
                document_id=doc.id,
                prompt_id=prompt_id,
                model_name=model_name,
                model_id=model_id,
                duration_ms=duration_ms,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            )
            run_id = self.db.extraction_runs.insert_with_texts(
                run_record, parsed.raw_text)
            if run_id is None:
                Log.error(
                    message=f"Could not insert ExtractionRun+texts for '{doc.filename}'. Skipping...",
                    source=self,
                )
                continue
