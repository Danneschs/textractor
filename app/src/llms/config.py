from enum import Enum
from typing import Optional
from dataclasses import dataclass
from pydantic import BaseModel

from src.llms.schemas import AnalyzedTextSchema
from src.llms.schemas import ExtractedTextSchema


class LLMList(Enum):
    """Available LLM models. Add new models here."""
    # Human
    HUMAN = "human"

    # OpenAI
    GPT_5_4_NANO = "gpt-5.4-nano"

    # Mistral
    MISTRAL_LARGE = "mistral-large-latest"

    # Llama
    LLAMA_3_2_LATEST = "llama3.2:latest"


@dataclass
class LLMConfig:
    """Configuration for a single pipeline phase.

    Set response_schema to a Pydantic BaseModel subclass to change the LLM output structure.
    Set system_content to change what the LLM is instructed to do.
    """
    system_content: str
    response_schema: Optional[type[BaseModel]] = None
    name: str = ""


EXTRACTION_SYSTEM_MESSAGE = """
You are an expert Requirements Engineer analyzing Software Requirement Specifications (SRS).
Your task is to carefully read the provided document and extract EVERY explicitly stated project requirement, constraint, or goal.

RULES:
1. COPY the raw text exactly as it appears in the document. Do not summarize or rephrase. IMPORTANT: If the source text contains double quotes ("), you must replace them with single quotes (') to ensure valid JSON output.
2. If some text section contains full context required for understanding the requirement the section is about, you should COPY ALL PARTS CONTAINING THE REQUIREMENT. For example, if there is a table, you should copy whole table as it is. Another example, when there is a long text and somewhere inside it there is a requirement without context, you should copy the sentence and ADDITIONALLY ADD CONTEXT to it (section title, sentence related to requirement, ...) -- there is still rule, that the context should be COPY -- so do not modify the sentences.
3. Extract ALL requirements. Missing a requirement is a critical failure.
4. You MUST return a valid JSON object with the following structure: {"raw_text": ["requirement 1", "requirement 2", ...]}
"""

ANALYSIS_SYSTEM_MESSAGE = """
You are an expert Technical Analyst. Your task is to process and analyze a raw software requirement and convert it into a structured, developer-friendly format.

You will receive a single raw requirement text. Review it carefully.
Your goal is to extract quantifiable parameters (if present) OR provide a clear, concise technical summary of the requirement. A single input text may contain multiple requirements -- split them if needed.

As example, from raw text "Display refresh rate should be 60 Hz, internet response should be 5 ms (minimum) and the system should be accessible only to authorized users.", you should extract requirements with following summaries and parameters:

{
  "parsed_requirements": [
    {
      "requirement_summary": "Display refresh rate",
      "parameters": [
        { "parameter_value": 60, "parameter_unit": "Hz" }
      ]
    },
    {
      "requirement_summary": "Internet response time",
      "parameters": [
        { "parameter_value": 5, "parameter_unit": "ms (minimum)" }
      ]
    },
    {
      "requirement_summary": "Access restricted to authorized users only",
      "parameters": []
    }
  ]
}

If the raw text clearly describes the requirement, copy is enough. But if the raw text is vague, ambiguous or contains a lot of unnecessary information, provide a concise and clear summary in "requirement_summary". The summary should be descriptive enough for software engineers to understand the requirement without referring back to the original text. Keep the language of the input -- if the input is in Czech, the output must be in Czech, and so on.

You MUST return a valid JSON object with the following structure:
{
  "parsed_requirements": [
    {
      "requirement_summary": "...", 
      "parameters": [
        {
          "parameter_value": ..., 
          "parameter_unit": "..."
        }
      ]
    }
  ]
}
"""

EXTRACTION_CONFIG = LLMConfig(
    system_content=EXTRACTION_SYSTEM_MESSAGE,
    response_schema=ExtractedTextSchema,
    name="Extraction phase",
)

ANALYSIS_CONFIG = LLMConfig(
    system_content=ANALYSIS_SYSTEM_MESSAGE,
    response_schema=AnalyzedTextSchema,
    name="Formalization phase",
)
