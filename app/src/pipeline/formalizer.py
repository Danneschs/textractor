import json
import time

from src.database.models import AnalyzedTextRecord
from src.pipeline.phase import Phase
from src.utils import Log, progress_with_bar


class FormalizationPhase(Phase):
    """
    Formalization phase of the pipeline.

    Reads every EXTRACTED_TEXT row that has not yet been analyzed by this
    model+prompt, sends the raw extracted text to the LLM backend (which returns
    a structured JSON string validated against AnalyzedTextSchema), and
    persists the result as an ANALYZED_TEXT row.

    Re-running this phase only processes extractions that are
    missing an ANALYZED_TEXT entry for the configured model+prompt.
    """

    def run(self) -> None:
        """Run the formalization phase."""
        model_name = self.backend.model_name

        prompt_id = self._register_prompt()
        if prompt_id is None:
            return
        model_id = self._register_model()
        if model_id is None:
            return

        pending = self.db.extracted_texts.get_pending_analysis(
            model_id, prompt_id)
        Log.info(
            message=f"Formalization: {len(pending)} extraction(s) pending for model '{model_name}'.",
            source=self,
        )

        if not pending:
            return

        for bar, extracted in progress_with_bar(pending, desc=f"Formalization [{model_name}]", total=len(pending)):
            bar.set_description(
                f"Formalization [{model_name}] id={extracted.id}")
            Log.info(
                message=f"Formalizing extracted_text id={extracted.id}...",
                source=self,
            )
            try:
                _start = time.perf_counter()
                result = self.backend.generate(
                    user_content=extracted.raw_text,
                    llm_config=self.llm_config,
                )
                duration_ms = int((time.perf_counter() - _start) * 1000)
                bar.set_postfix(done_in=f"{duration_ms}ms")
            except Exception as e:
                Log.error(
                    message=f"LLM error for extracted_text id={extracted.id}: {e}. Skipping...",
                    source=self,
                )
                continue

            extracted_id = extracted.id
            if extracted_id is None:
                Log.error(
                    message=f"ExtractedText record has no DB id. Skipping...", source=self)
                continue

            json_data = result.text
            try:
                parsed = json.loads(json_data)
                if "error" in parsed:
                    Log.error(
                        message=f"LLM returned error for extracted_text id={extracted_id}: {parsed['error']}. Skipping insert.",
                        source=self,
                    )
                    continue
            except (json.JSONDecodeError, TypeError, ValueError):
                pass  # not a JSON object -- store as-is; display will show no cards

            record = AnalyzedTextRecord(
                extracted_text_id=extracted_id,
                prompt_id=prompt_id,
                model_name=model_name,
                model_id=model_id,
                result=json_data,
                duration_ms=duration_ms,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            )
            self.db.analyzed_texts.insert(record)
