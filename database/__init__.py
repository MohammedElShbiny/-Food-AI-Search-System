from .base import DatabaseInterface
from .sqlite_db import SQLiteDatabase

__all__ = ["DatabaseInterface", "SQLiteDatabase", "get_database"]

_db_instance = None


def get_database() -> DatabaseInterface:
    global _db_instance
    if _db_instance is None:
        _db_instance = SQLiteDatabase()
    return _db_instance
