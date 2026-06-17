from .base import DatabaseInterface
from .sqlite_db import SQLiteDatabase

__all__ = ["DatabaseInterface", "SQLiteDatabase", "get_database"]


def get_database() -> DatabaseInterface:
    return SQLiteDatabase()
