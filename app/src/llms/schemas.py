"""
Domain-specific Pydantic output schemas for both pipeline phases.

These are the structures that users customise to change what structurized data the LLM returns.
Phase 1 (TextExtractor) -- ExtractedTextSchema
Phase 2 (TextAnalyzer) -- AnalyzedTextSchema

Add or remove fields here, then update the matching system prompt and LLMConfig in
src/llms/config.py.

ExtractedTextSchema is not recommended to be changed, as it is a simple wrapper for a list of raw sentences. 
AnalyzedTextSchema is the one that should be modified to fit the searched information from a document.
"""

from pydantic import BaseModel


# Phase 1 -- PDF -> raw sentences
class ExtractedTextSchema(BaseModel):
    """Output schema for Phase 1 -- extraction."""
    raw_text: list[str]


# Phase 2 -- raw sentences -> structured information
class QuantifiableData(BaseModel):
    """A single quantifiable parameter extracted from a requirement."""
    parameter_value: float | None
    parameter_unit: str | None


class ParsedRequirement(BaseModel):
    """Single requirement parsed into a structured form."""
    requirement_summary: str
    parameters: list[QuantifiableData] = []


class AnalyzedTextSchema(BaseModel):
    """Output schema for Phase 2 -- formalization."""
    parsed_requirements: list[ParsedRequirement]
