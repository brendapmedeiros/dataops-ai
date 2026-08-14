from __future__ import annotations

import pandas as pd

from dataops_ai.tools.database_tools import DatabaseClient


def load_timeseries(df: pd.DataFrame, database_url: str, table_name: str = "bcb_timeseries") -> int:
    db = DatabaseClient(database_url)
    db.write_dataframe(df, table_name)
    return db.count_rows(table_name)
