from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pandas as pd


_TABLE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class DatabaseClient:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def write_dataframe(self, df: pd.DataFrame, table_name: str) -> None:
        _validate_table_name(table_name)
        if self.database_url.startswith("sqlite:///"):
            db_path = Path(self.database_url.removeprefix("sqlite:///"))
            with sqlite3.connect(db_path) as connection:
                df.to_sql(table_name, connection, if_exists="replace", index=False)
            return

        self._write_with_sqlalchemy(df, table_name)

    def count_rows(self, table_name: str) -> int:
        _validate_table_name(table_name)
        if self.database_url.startswith("sqlite:///"):
            db_path = Path(self.database_url.removeprefix("sqlite:///"))
            with sqlite3.connect(db_path) as connection:
                cursor = connection.execute(f"select count(*) from {table_name}")
                return int(cursor.fetchone()[0])

        from sqlalchemy import create_engine, text

        engine = create_engine(self.database_url)
        with engine.connect() as connection:
            return int(connection.execute(text(f"select count(*) from {table_name}")).scalar_one())

    def query_database(self, sql: str) -> pd.DataFrame:
        if self.database_url.startswith("sqlite:///"):
            db_path = Path(self.database_url.removeprefix("sqlite:///"))
            with sqlite3.connect(db_path) as connection:
                return pd.read_sql_query(sql, connection)

        from sqlalchemy import create_engine

        engine = create_engine(self.database_url)
        return pd.read_sql_query(sql, engine)

    def _write_with_sqlalchemy(self, df: pd.DataFrame, table_name: str) -> None:
        try:
            from sqlalchemy import create_engine
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "SQLAlchemy is required for PostgreSQL. Install requirements.txt or use sqlite:///dataops_ai.db."
            ) from exc

        engine = create_engine(self.database_url)
        df.to_sql(table_name, engine, if_exists="replace", index=False)


def _validate_table_name(table_name: str) -> None:
    if not _TABLE_NAME.match(table_name):
        raise ValueError(f"Invalid table name: {table_name}")
