from __future__ import annotations

import pandas as pd


SCENARIOS = {
    "none",
    "scenario_01_null_values",
    "scenario_02_schema_drift",
    "scenario_03_api_timeout",
    "scenario_04_duplicate_records",
    "scenario_05_invalid_type",
}


def apply_scenario(df: pd.DataFrame, scenario: str) -> pd.DataFrame:
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario}")

    staged = df.copy()
    if scenario == "none" or staged.empty:
        return staged

    if scenario == "scenario_01_null_values":
        staged.loc[staged.index[0], "value"] = None
    elif scenario == "scenario_02_schema_drift":
        staged = staged.rename(columns={"value": "valor_taxa"})
    elif scenario == "scenario_03_api_timeout":
        staged["source"] = "simulated_api_timeout_fallback"
    elif scenario == "scenario_04_duplicate_records":
        staged = pd.concat([staged, staged.iloc[[0]]], ignore_index=True)
    elif scenario == "scenario_05_invalid_type":
        staged["value"] = staged["value"].astype("object")
        staged.loc[staged.index[0], "value"] = "invalid_value"

    return staged
