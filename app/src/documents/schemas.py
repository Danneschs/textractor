from pydantic import BaseModel, Field
from typing import List, TypeVar, Generic

# Generic type for golden dataset JSON schema
T = TypeVar('T')


class GoldenParameter(BaseModel, Generic[T]):
    """One golden dataset entry pairing a Phase-1 raw text with its expected Phase-2 analysis."""
    raw_text: str = Field(...,
                          description="Extracted text from the document (Phase 1).")

    analyzed_data: T = Field(...,
                             description="Analyzed text from the document (Phase 2). This is the 'golden' expected output for the LLM to match.")


class GoldenDatasetSchema(BaseModel, Generic[T]):
    """Golden dataset for one document: filename and list of golden parameters."""
    document_filename: str
    golden_parameters: List[GoldenParameter[T]]
