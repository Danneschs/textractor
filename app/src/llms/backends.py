import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from openai import OpenAI, APITimeoutError
from mistralai.client.models import TextChunk
from mistralai.client import Mistral

from src.llms.config import LLMConfig, LLMList
from src.utils import Log

import ollama
from ollama import ChatResponse

TIMEOUT_SECONDS = 12000


@dataclass
class GenerateResult:
    """Return value of LLMBackend.generate(): extracted text plus token usage."""
    text: str
    input_tokens: Optional[int]
    output_tokens: Optional[int]


class LLMBackend(ABC):
    """
    Base class for all LLM backends.

    For adding a new backend, subclass this and implement the generate() method. Then add the new backend to BACKEND_REGISTRY at the bottom of this file.
    """

    def __init__(self, model: LLMList) -> None:
        self.model = model

    @property
    def model_name(self) -> str:
        """String model identifier used for DB tracking and API calls."""
        return self.model.value

    @abstractmethod
    def generate(self, user_content: str, llm_config: LLMConfig) -> GenerateResult:
        """Send user_content and system prompt (from llm_config) to the LLM.

        Return a GenerateResult with the response text and token usage.
        """
        ...


class OpenAIBackend(LLMBackend):
    """Backend for OpenAI models. When new OpenAI model in LLMList is added, add it to the _ALLOWED set here."""
    _ALLOWED = {LLMList.GPT_5_4_NANO}

    def __init__(self, model: LLMList):
        if model not in self._ALLOWED:
            raise ValueError(
                f"OpenAIBackend does not support {model!r}. Allowed: {self._ALLOWED}")
        super().__init__(model)
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
        self.client: OpenAI = OpenAI(api_key=key)

    def generate(self, user_content: str, llm_config: LLMConfig) -> GenerateResult:
        raw_content: str | None = None
        try:
            # Structured output via Pydantic schema  ->  .parse() returns a typed object
            if llm_config.response_schema is not None:
                response = self.client.responses.parse(
                    model=self.model_name,
                    temperature=0.0,
                    instructions=llm_config.system_content,
                    input=user_content,
                    text_format=llm_config.response_schema,
                    timeout=TIMEOUT_SECONDS,
                )
                raw_content = response.output_text
                parsed = response.output_parsed
                if parsed is None:
                    raise ValueError(
                        "Model returned empty structured response (None).")
                return GenerateResult(
                    text=parsed.model_dump_json(),
                    input_tokens=response.usage.input_tokens if response.usage else None,
                    output_tokens=response.usage.output_tokens if response.usage else None,
                )

            # Plain text / unstructured fallback
            plain_response = self.client.responses.create(
                model=self.model_name,
                temperature=0.0,
                instructions=llm_config.system_content,
                input=user_content,
                timeout=TIMEOUT_SECONDS,
            )
            content = plain_response.output_text
            if not content:
                raise ValueError("Model returned empty response (None).")
            return GenerateResult(
                text=content,
                input_tokens=plain_response.usage.input_tokens if plain_response.usage else None,
                output_tokens=plain_response.usage.output_tokens if plain_response.usage else None,
            )

        except APITimeoutError as e:
            Log.log_failed_response(
                message=f"[TIMEOUT] {self.model_name}: {e}", source=self)
            return GenerateResult(text='{"error": "timeout"}', input_tokens=None, output_tokens=None)
        except Exception as e:
            if raw_content is not None:
                Log.log_failed_response(message=raw_content, source=self)
            Log.error(message=f"OpenAI API error: {e}", source=self)
            return GenerateResult(text=f'{{"error": "OpenAI API Error: {str(e)}"}}', input_tokens=None, output_tokens=None)


class MistralBackend(LLMBackend):
    """Backend for Mistral models. When new Mistral model in LLMList is added, add it to the _ALLOWED set here."""
    _ALLOWED = {LLMList.MISTRAL_LARGE}

    def __init__(self, model: LLMList):
        if model not in self._ALLOWED:
            raise ValueError(
                f"MistralBackend does not support {model!r}. Allowed: {self._ALLOWED}")
        super().__init__(model)
        key = os.getenv("MISTRAL_API_KEY")
        if not key:
            raise ValueError(
                "MISTRAL_API_KEY environment variable is not set.")
        self.client: Mistral = Mistral(api_key=key)

    def generate(self, user_content: str, llm_config: LLMConfig) -> GenerateResult:
        raw_content: str | None = None
        try:
            kwargs = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": llm_config.system_content},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0,
            }

            if llm_config.response_schema is not None:
                kwargs["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": llm_config.response_schema.__name__,
                        "schema": llm_config.response_schema.model_json_schema(),
                        "strict": True,
                    },
                }

            response = self.client.chat.complete(
                **kwargs, timeout_ms=TIMEOUT_SECONDS * 1000)  # type: ignore
            content = response.choices[0].message.content
            if isinstance(content, list):
                raw_content = "".join(
                    chunk.text for chunk in content if isinstance(chunk, TextChunk)
                )
            else:
                raw_content = content  # type: ignore

            if not raw_content:
                raise ValueError("Model returned empty response.")

            input_tokens = response.usage.prompt_tokens if response.usage else None
            output_tokens = response.usage.completion_tokens if response.usage else None

            if llm_config.response_schema is not None:
                validated = llm_config.response_schema.model_validate_json(
                    raw_content)
                return GenerateResult(text=validated.model_dump_json(), input_tokens=input_tokens, output_tokens=output_tokens)

            return GenerateResult(text=raw_content, input_tokens=input_tokens, output_tokens=output_tokens)
        except Exception as e:
            if raw_content is not None:
                Log.log_failed_response(message=raw_content, source=self)
            if "timeout" in str(e).lower():
                Log.log_failed_response(
                    message=f"[TIMEOUT] {self.model_name}: {e}", source=self)
                return GenerateResult(text='{"error": "timeout"}', input_tokens=None, output_tokens=None)
            Log.error(message=f"Mistral API error: {e}", source=self)
            return GenerateResult(text=f'{{"error": "Mistral API Error: {str(e)}"}}', input_tokens=None, output_tokens=None)


class LlamaBackend(LLMBackend):
    """Ollama backend -- no API key required, model runs locally. When new Llama model in LLMList is added, add it to the _ALLOWED set here."""
    _ALLOWED = {LLMList.LLAMA_3_2_LATEST}

    def __init__(self, model: LLMList):
        if model not in self._ALLOWED:
            raise ValueError(
                f"LlamaBackend does not support {model!r}. Allowed: {self._ALLOWED}")
        super().__init__(model)
        self.client = ollama.Client(timeout=TIMEOUT_SECONDS)

    def generate(self, user_content: str, llm_config: LLMConfig) -> GenerateResult:
        raw_content: str | None = None
        try:
            kwargs: dict = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": llm_config.system_content},
                    {"role": "user",   "content": user_content},
                ],
                "options": {"temperature": 0.0},
            }

            if llm_config.response_schema is not None:
                kwargs["format"] = llm_config.response_schema.model_json_schema()

            response: ChatResponse = self.client.chat(**kwargs)
            raw_content = response.message.content

            if not raw_content:
                raise ValueError("Model returned empty response.")

            input_tokens = response.prompt_eval_count
            output_tokens = response.eval_count

            if llm_config.response_schema is not None:
                validated = llm_config.response_schema.model_validate_json(
                    raw_content)
                return GenerateResult(text=validated.model_dump_json(), input_tokens=input_tokens, output_tokens=output_tokens)

            return GenerateResult(text=raw_content, input_tokens=input_tokens, output_tokens=output_tokens)

        except Exception as e:
            if raw_content is not None:
                Log.log_failed_response(message=raw_content, source=self)
            if "timeout" in str(e).lower():
                Log.log_failed_response(
                    message=f"[TIMEOUT] {self.model_name}: {e}", source=self)
                return GenerateResult(text='{"error": "timeout"}', input_tokens=None, output_tokens=None)
            Log.error(message=f"Ollama API error: {e}", source=self)
            return GenerateResult(text=f'{{"error": "Ollama API Error: {str(e)}"}}', input_tokens=None, output_tokens=None)


# Maps every LLMList value to its backend class.
# To add a new model, add it to LLMList in config.py and to the backend's _ALLOWED set.
BACKEND_REGISTRY: dict[LLMList, type[LLMBackend]] = {
    model: cls
    for cls in (OpenAIBackend, MistralBackend, LlamaBackend)
    for model in cls._ALLOWED
}
