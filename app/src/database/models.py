from dataclasses import dataclass
from typing import Optional

from enum import Enum


@dataclass
class DocumentRecord:
    """Record for an uploaded document."""
    filename: str
    file_path: str
    raw_full_text: str
    image_folder_path: Optional[str] = None
    upload_date: str = ""  # Set automatically on insert
    id: Optional[int] = None


@dataclass
class PromptRecord:
    """Record for a prompt used in extraction or analysis."""
    name: str
    value: str
    id: Optional[int] = None


@dataclass
class ModelRecord:
    """Record for a model (LLM or human annotator)."""
    name: str
    id: Optional[int] = None


@dataclass
class ExtractionRunRecord:
    """One ingestion event in Phase 1: one document * prompt * model (LLM or human)."""
    document_id: int
    prompt_id: int
    model_name: str   # populated on read via JOIN with MODEL
    model_id: int     # FK to MODEL, used on INSERT
    extracted_at: str = ""
    duration_ms: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    id: Optional[int] = None


@dataclass
class ExtractedTextRecord:
    """Phase 1: Extracted text from document."""
    document_id: int
    prompt_id: int
    model_name: str  # populated on read via JOIN with MODEL; not stored in EXTRACTED_TEXT
    model_id: int    # not stored in EXTRACTED_TEXT; carried for context
    raw_text: str
    extraction_run_id: int  # FK to EXTRACTION_RUN
    id: Optional[int] = None


class EvalMode(str, Enum):
    """Which evaluation pipeline produced this record."""
    PRODUCTION = "production"
    BENCHMARK = "benchmark"


class EvalResult(int, Enum):
    """Binary correctness verdict for an evaluation record."""
    CORRECT = 1
    INCORRECT = 0


@dataclass
class AnalyzedTextRecord:
    """Phase 2: Formalized analysis of an extracted text."""
    extracted_text_id: int
    prompt_id: int
    model_name: str   # populated on read via JOIN with MODEL
    model_id: int     # FK to MODEL, used on INSERT
    result: str
    analyzed_at: str = ""
    duration_ms: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    id: Optional[int] = None


@dataclass
class ExtractedTextEvalRecord:
    """Evaluation record for a Phase 1 extracted text."""
    extracted_text_id: int
    is_correct: int
    evaluator_name: str
    matched_golden_id: Optional[int] = None
    note: Optional[str] = None
    mode: EvalMode = EvalMode.BENCHMARK
    id: Optional[int] = None


@dataclass
class AnalyzedTextEvalRecord:
    """Evaluation record for a Phase 2 analyzed text."""
    analyzed_text_id: int
    is_correct: int
    evaluator_name: str
    note: Optional[str] = None
    mode: EvalMode = EvalMode.BENCHMARK
    id: Optional[int] = None
