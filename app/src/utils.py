import logging
import os
from datetime import datetime
from typing import Iterable, Iterator, Tuple, TypeVar

from tqdm import tqdm  # type: ignore

_T = TypeVar("_T")


class Log:
    """Utility class for logging with consistent formatting and optional file logging."""
    @staticmethod
    def error(message: str, source=None):
        Log._log(logging.ERROR, message, source)

    @staticmethod
    def warning(message: str, source=None):
        Log._log(logging.WARNING, message, source)

    @staticmethod
    def info(message: str, source=None):
        Log._log(logging.INFO, message, source)

    @staticmethod
    def debug(message: str, source=None):
        Log._log(logging.DEBUG, message, source)

    @staticmethod
    def log_failed_response(message: str, source=None):
        os.makedirs("logs", exist_ok=True)
        with open(os.path.join("logs", "failed_responses.log"), "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n\n")

    @staticmethod
    def _log(level, message, source):
        if source is None:
            name = "root"
        elif isinstance(source, type):
            name = source.__name__
        else:
            name = source.__class__.__name__

        logging.getLogger(name).log(level, message)

    @staticmethod
    def setup_logging(log_to_file: bool = True):
        """Configure logging at the start of the application."""
        fmt = "[%(asctime)s:%(msecs)03d][%(levelname)s][%(name)s] %(message)s"
        datefmt = "%H:%M:%S"
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        handlers: list[logging.Handler] = [console_handler]

        if log_to_file:
            os.makedirs("logs", exist_ok=True)
            log_filename = datetime.now().strftime("%d_%m_%Y_%H_%M_%S") + ".log"
            file_handler = logging.FileHandler(
                os.path.join("logs", log_filename), encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            handlers.append(file_handler)

        logging.basicConfig(level=logging.DEBUG, format=fmt,
                            datefmt=datefmt, handlers=handlers)


def _suppress_console_handlers():
    """Return a context manager that suppresses console logging from the root logger.

    File handlers remain active; log messages still reach the file handler.
    """
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        root_logger = logging.getLogger()
        stream_handlers = [
            h for h in root_logger.handlers
            if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        ]
        for h in stream_handlers:
            root_logger.removeHandler(h)
        try:
            yield
        finally:
            for h in stream_handlers:
                root_logger.addHandler(h)

    return _ctx()


def progress(iterable: Iterable[_T], desc: str, total: int | None = None) -> Iterator[_T]:
    """Wrap an iterable with a tqdm progress bar, suppressing console logs while active.

    Log messages still reach the file handler during this period.
    """
    with _suppress_console_handlers():
        yield from tqdm(iterable, desc=desc, total=total, unit="item")


def progress_with_bar(
    iterable: Iterable[_T], desc: str, total: int | None = None
) -> Iterator[Tuple[tqdm, _T]]:
    """Like progress(), but yield (bar, item) tuples to allow updating the bar mid-operation."""
    with _suppress_console_handlers():
        bar = tqdm(iterable, desc=desc, total=total, unit="doc")
        for item in bar:
            yield bar, item


def get_db_path() -> str:
    """Return the database file path from the DATABASE_PATH env variable."""
    return os.environ.get("DATABASE_PATH", "data/database.db")
