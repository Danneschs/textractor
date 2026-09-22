from dataclasses import dataclass
from typing import Any
from enum import Enum


@dataclass
class LoadedDocument:
    """Represents a document loaded from disk or a dataset."""
    data: bytes
    filename: str
    # Relative path to the source file on disk
    file_path: str = ""


class FileType(Enum):
    """Supported file types with their glob patterns and extensions."""
    PDF = ("*.pdf", ".pdf")
    JSON = ("*.json", ".json")

    def __init__(self, pattern: str, extension: str):
        self.pattern = pattern
        self.extension = extension
