from src.database.manager import DatabaseManager
from src.pipeline.extractor import ExtractionPhase
from src.pipeline.formalizer import FormalizationPhase


class Pipeline:
    """Orchestrate the pipeline.

    Extraction phase: raw document text -> LLM -> EXTRACTED_TEXT rows
    Formalization phase: extracted sentences -> LLM -> ANALYZED_TEXT rows
    Re-running only processes records missing from the DB.
    """

    def __init__(self, db: DatabaseManager, extractor: ExtractionPhase, analyzer_list: list[FormalizationPhase]):
        self.db = db
        self.extractor = extractor
        self.analyzer_list = analyzer_list

    def run_extraction(self) -> None:
        self.extractor.run()

    def run_formalization(self) -> None:
        for analyzer in self.analyzer_list:
            analyzer.run()

    def run(self) -> None:
        self.run_extraction()
        self.run_formalization()
