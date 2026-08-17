from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pandas as pd


_TABLE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class DatabaseClient:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def ping(self) -> bool:
        if self.database_url.startswith("sqlite:///"):
            db_path = Path(self.database_url.removeprefix("sqlite:///"))
            with sqlite3.connect(db_path) as connection:
                connection.execute("select 1")
            return True

        from sqlalchemy import create_engine, text

        engine = create_engine(self.database_url)
        try:
            with engine.connect() as connection:
                connection.execute(text("select 1"))
            return True
        except Exception as exc:
            raise RuntimeError(_database_error_message(self.database_url)) from exc

    def write_dataframe(self, df: pd.DataFrame, table_name: str) -> None:
        self._save_dataframe(df, table_name, if_exists="replace")

    def append_dataframe(self, df: pd.DataFrame, table_name: str) -> None:
        self._save_dataframe(df, table_name, if_exists="append")

    def append_record(self, record: dict, table_name: str) -> None:
        self.append_dataframe(pd.DataFrame([record]), table_name)

    def _save_dataframe(self, df: pd.DataFrame, table_name: str, if_exists: str) -> None:
        _validate_table_name(table_name)
        if self.database_url.startswith("sqlite:///"):
            db_path = Path(self.database_url.removeprefix("sqlite:///"))
            with sqlite3.connect(db_path) as connection:
                df.to_sql(table_name, connection, if_exists=if_exists, index=False)
            return

        self._write_with_sqlalchemy(df, table_name, if_exists)

    def count_rows(self, table_name: str) -> int:
        _validate_table_name(table_name)
        if self.database_url.startswith("sqlite:///"):
            db_path = Path(self.database_url.removeprefix("sqlite:///"))
            with sqlite3.connect(db_path) as connection:
                cursor = connection.execute(f"select count(*) from {table_name}")
                return int(cursor.fetchone()[0])

        from sqlalchemy import create_engine, text

        engine = create_engine(self.database_url)
        try:
            with engine.connect() as connection:
                return int(connection.execute(text(f"select count(*) from {table_name}")).scalar_one())
        except Exception as exc:
            raise RuntimeError(_database_error_message(self.database_url)) from exc

    def query_database(self, sql: str) -> pd.DataFrame:
        if self.database_url.startswith("sqlite:///"):
            db_path = Path(self.database_url.removeprefix("sqlite:///"))
            with sqlite3.connect(db_path) as connection:
                return pd.read_sql_query(sql, connection)

        from sqlalchemy import create_engine

        engine = create_engine(self.database_url)
        try:
            return pd.read_sql_query(sql, engine)
        except Exception as exc:
            raise RuntimeError(_database_error_message(self.database_url)) from exc

    def _write_with_sqlalchemy(self, df: pd.DataFrame, table_name: str, if_exists: str) -> None:
        try:
            from sqlalchemy import create_engine
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "SQLAlchemy is required for PostgreSQL. Install requirements.txt or use sqlite:///dataops_ai.db."
            ) from exc

        engine = create_engine(self.database_url)
        try:
            df.to_sql(table_name, engine, if_exists=if_exists, index=False)
        except Exception as exc:
            raise RuntimeError(_database_error_message(self.database_url)) from exc


def _validate_table_name(table_name: str) -> None:
    if not _TABLE_NAME.match(table_name):
        raise ValueError(f"Invalid table name: {table_name}")


def _database_error_message(database_url: str) -> str:
    if database_url.startswith("postgresql"):
        return (
            "Nao foi possivel conectar ao PostgreSQL. "
            "Verifique se o banco esta rodando e se DATABASE_URL esta correto. "
            "Com Docker, use: docker compose up -d postgres."
        )

    return "Nao foi possivel executar a operacao no banco configurado."
