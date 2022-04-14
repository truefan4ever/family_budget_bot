import re

from db._postgres import Postgres
from db.constants import DB_ENGINES, DB_REGEX
from db.errors import DatabaseError
from db.models import ConnectionData
from db.protocols import Database


class DatabasesService:
    def __init__(self, connection_url: str) -> None:
        self._connection_url = connection_url
        self.connection_url_match: re.Match = self.__get_connection_url_match()

    def __get_connection_url_match(self) -> re.Match:
        try:
            result = re.search(DB_REGEX, self._connection_url)
            if result is None:
                raise DatabaseError(
                    f'Database connection string "{self._connection_url}" does not match with expected regex.'
                )
            return result
        except AttributeError:
            raise DatabaseError(
                f'Database connection string "{self._connection_url}" does not match with expected regex.'
            )
        except ValueError:
            raise DatabaseError(f'Port is invalid integer. Database connection string "{self._connection_url}".')

    def get_database(self) -> Database:
        engine = self.connection_url_match.group("db_engine")
        if engine == DB_ENGINES.POSTGRES.value:
            return Postgres(self.connection_data)

        raise DatabaseError("Can not find database engine.")

    @property
    def connection_data(self) -> ConnectionData:
        try:
            return ConnectionData(
                host=self.connection_url_match.group("db_hostname"),
                port=int(self.connection_url_match.group("db_port")),
                username=self.connection_url_match.group("db_username"),
                password=self.connection_url_match.group("db_password"),
                dbname=self.connection_url_match.group("db_name"),
            )
        except IndexError:
            raise DatabaseError("Something wrong with regex")
