from abc import ABC, abstractmethod
from typing import Optional

from src.database.manager import DatabaseManager
from src.llms.backends import LLMBackend
from src.llms.config import LLMConfig
from src.database.models import ModelRecord, PromptRecord
from src.utils import Log


class Phase(ABC):
    """Abstract base class for all pipeline phases."""

    def __init__(self, db: DatabaseManager, backend: LLMBackend, llm_config: LLMConfig):
        self.db = db
        self.backend = backend
        self.llm_config = llm_config

    def _register_prompt(self) -> Optional[int]:
        """Register the configured prompt in the DB and return its ID, or None on error."""
        prompt_id = self.db.prompts.get_or_insert(
            PromptRecord(
                name=self.llm_config.name,
                value=self.llm_config.system_content,
            )
        )
        if prompt_id is None:
            Log.error(message="Could not register prompt in DB.", source=self)
        return prompt_id

    def _register_model(self) -> Optional[int]:
        """Register the backend model in the DB and return its ID, or None on error."""
        model_id = self.db.models.get_or_insert(
            ModelRecord(name=self.backend.model_name))
        if model_id is None:
            Log.error(message="Could not register model in DB.", source=self)
        return model_id

    @abstractmethod
    def run(self) -> None: ...
    """Run the phase. Must be implemented by subclasses."""
