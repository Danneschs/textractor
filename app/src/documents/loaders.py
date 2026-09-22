from pathlib import Path
from typing_extensions import override
from abc import ABC, abstractmethod
from typing import Iterator

from src.documents.models import FileType, LoadedDocument


class Loader(ABC):
    @abstractmethod
    def prepare(self) -> None:
        """Ensure data is available."""

    @abstractmethod
    def __iter__(self) -> Iterator[LoadedDocument]:
        """Yield dataset items one by one as LoadedDocument objects."""

    @abstractmethod
    def __len__(self) -> int:
        """Return the number of items in the dataset."""


class LocalLoader(Loader):
    def __init__(self, root_dir: str | Path, file_type: FileType = FileType.PDF):
        """Initialize the local file loader.

        root_dir -- root directory to search for files recursively
        file_type -- type of files to load (default FileType.PDF)
        """
        self.root_dir = Path(root_dir)
        self.file_type = file_type
        self._files: list[Path] | None = None

    def prepare(self) -> None:
        if self._files is not None:
            return

        if not self.root_dir.exists():
            raise FileNotFoundError(self.root_dir)

        self._files = list(self.root_dir.rglob(self.file_type.pattern))

    def __iter__(self) -> Iterator[LoadedDocument]:
        self.prepare()
        assert self._files is not None
        for path in self._files:
            with open(path, "rb") as f:
                # Always return bytes - extractors will decode if needed
                # path is relative when root_dir is relative (which is the convention)
                yield LoadedDocument(data=f.read(), filename=path.name, file_path=path.as_posix())

    def __len__(self) -> int:
        self.prepare()
        assert self._files is not None
        return len(self._files)
