from typing import Any, ContextManager, Optional, Protocol

from db.domain import ConnectionData


class Database(Protocol):
    def __init__(self, connection_data: ConnectionData) -> None:
        ...
        """
        Keyword arguments:
        self._connection_data -- mandatory data connection creation
        """

    def _get_connection(self) -> Any:
        ...

    def cursor(self) -> ContextManager:
        ...

    def init(self) -> None:
        ...
        """Create database if not exist"""

    def execute(self, q: str) -> None:
        ...

    def raw_execute(self, q: str) -> list[dict]:
        ...

    def fetch(self, table: str, column: str, value: Any) -> list[dict]:
        ...

    def fetchone(self, table: str, column: str, value: Any) -> Optional[dict]:
        ...

    def fetchall(self, table: str, columns: Optional[str] = None) -> list[dict]:
        ...

    def insert(self, table: str, data: dict[str, Any]) -> dict:
        ...

    def update(self, table: str, data: tuple[str, Any], condition: tuple[str, Any]) -> dict:
        ...

    def delete(self, table: str, column: str, value: str) -> dict:
        ...
