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

    def ensure_record_columns(self, record: dict, table_name: str) -> None:
        _validate_table_name(table_name)
        if not self.table_exists(table_name):
            return

        existing_columns = set(self.column_names(table_name))
        missing_columns = [column for column in record if column not in existing_columns]
        if not missing_columns:
            return

        if self.database_url.startswith("sqlite:///"):
            db_path = Path(self.database_url.removeprefix("sqlite:///"))
            with sqlite3.connect(db_path) as connection:
                for column in missing_columns:
                    connection.execute(f"alter table {table_name} add column {column} text")
            return

        from sqlalchemy import create_engine, text

        engine = create_engine(self.database_url)
        try:
            with engine.begin() as connection:
                for column in missing_columns:
                    connection.execute(text(f"alter table {table_name} add column {column} text"))
        except Exception as exc:
            raise RuntimeError(_database_error_message(self.database_url)) from exc

    def column_names(self, table_name: str) -> list[str]:
        _validate_table_name(table_name)
        if self.database_url.startswith("sqlite:///"):
            db_path = Path(self.database_url.removeprefix("sqlite:///"))
            with sqlite3.connect(db_path) as connection:
                rows = connection.execute(f"pragma table_info({table_name})").fetchall()
            return [row[1] for row in rows]

        from sqlalchemy import create_engine, inspect

        engine = create_engine(self.database_url)
        try:
            return [column["name"] for column in inspect(engine).get_columns(table_name)]
        except Exception as exc:
            raise RuntimeError(_database_error_message(self.database_url)) from exc

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

    def table_exists(self, table_name: str) -> bool:
        _validate_table_name(table_name)
        if self.database_url.startswith("sqlite:///"):
            db_path = Path(self.database_url.removeprefix("sqlite:///"))
            with sqlite3.connect(db_path) as connection:
                cursor = connection.execute(
                    "select 1 from sqlite_master where type = 'table' and name = ?",
                    (table_name,),
                )
                return cursor.fetchone() is not None

        from sqlalchemy import create_engine, inspect

        engine = create_engine(self.database_url)
        try:
            return inspect(engine).has_table(table_name)
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
                "SQLAlchemy é obrigatório para usar PostgreSQL. Instale o requirements.txt ou use sqlite:///dataops_ai.db."
            ) from exc

        engine = create_engine(self.database_url)
        try:
            df.to_sql(table_name, engine, if_exists=if_exists, index=False)
        except Exception as exc:
            raise RuntimeError(_database_error_message(self.database_url)) from exc


def _validate_table_name(table_name: str) -> None:
    if not _TABLE_NAME.match(table_name):
        raise ValueError(f"Nome de tabela inválido: {table_name}")


def _database_error_message(database_url: str) -> str:
    if database_url.startswith("postgresql"):
        return (
            "Não foi possível conectar ao PostgreSQL. "
            "Verifique se o banco está rodando e se DATABASE_URL está correto. "
            "Com Docker, use: docker compose up -d postgres."
        )

    return "Não foi possível executar a operação no banco configurado."
