from __future__ import annotations

import pandas as pd


def transform_bcb_payload(rows: list[dict], series_code: int) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["date", "value", "series_code", "source"])

    df = df.rename(columns={"data": "date", "valor": "value"})
    df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y", errors="coerce")
    df["value"] = pd.to_numeric(df["value"].astype(str).str.replace(",", "."), errors="coerce")
    df["series_code"] = series_code
    df["source"] = df.get("source", "unknown")

    return df[["date", "value", "series_code", "source"]].sort_values("date").reset_index(drop=True)
