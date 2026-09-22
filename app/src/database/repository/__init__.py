import contextlib
import sqlite3
from typing import Any, Callable, Iterator

from src.utils import Log


class BaseRepository:
    """Base class for all database repositories."""

    def __init__(self, connection_factory: Callable[[], sqlite3.Connection]):
        self._get_connection = connection_factory

    @contextlib.contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """Opens a connection and guarantees close on exit."""
        conn = self._get_connection()
        try:
            yield conn
        finally:
            conn.close()

    def _execute_write(self, query: str, params: tuple[Any, ...] = ()) -> int | None:
        """Execute a write query (INSERT/UPDATE/DELETE) and return lastrowid, or None on error."""
        try:
            with self._connection() as conn:
                with conn:
                    c = conn.cursor()
                    c.execute(query, params)
                    return c.lastrowid
        except sqlite3.Error as e:
            Log.error(
                f"Error writing to database. Query: {query} | Error: {e}")
            return None

    def _execute_read(self, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        """Execute a read query (SELECT) and return all rows, or [] on error."""
        try:
            with self._connection() as conn:
                c = conn.cursor()
                c.execute(query, params)
                return c.fetchall()
        except sqlite3.Error as e:
            Log.error(
                f"Error reading from database. Query: {query} | Error: {e}")
            return []
