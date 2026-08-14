from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from dataops_ai.models import QualityIssue, QualityReport


EXPECTED_SCHEMA = {
    "date": "datetime",
    "value": "numeric",
    "series_code": "numeric",
    "source": "text",
}


def check_nulls(df: pd.DataFrame, required_columns: list[str]) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    for column in required_columns:
        if column not in df.columns:
            issues.append(
                QualityIssue(
                    check_name="check_nulls",
                    status="fail",
                    column=column,
                    rows_affected=len(df),
                    details=f"Column {column} is missing, so nulls cannot be evaluated.",
                )
            )
            continue

        null_count = int(df[column].isna().sum())
        issues.append(
            QualityIssue(
                check_name="check_nulls",
                status="fail" if null_count else "pass",
                column=column,
                rows_affected=null_count,
                details=f"{null_count} null values found in {column}.",
            )
        )
    return issues


def check_duplicates(df: pd.DataFrame, subset: list[str]) -> QualityIssue:
    missing_columns = [column for column in subset if column not in df.columns]
    if missing_columns:
        return QualityIssue(
            check_name="check_duplicates",
            status="fail",
            rows_affected=len(df),
            details=f"Cannot check duplicates. Missing columns: {', '.join(missing_columns)}.",
        )

    duplicate_count = int(df.duplicated(subset=subset).sum())
    return QualityIssue(
        check_name="check_duplicates",
        status="fail" if duplicate_count else "pass",
        rows_affected=duplicate_count,
        details=f"{duplicate_count} duplicate rows found using {', '.join(subset)}.",
    )


def check_schema(df: pd.DataFrame, expected_schema: dict[str, str]) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    for column, expected_type in expected_schema.items():
        if column not in df.columns:
            issues.append(
                QualityIssue(
                    check_name="check_schema",
                    status="fail",
                    column=column,
                    rows_affected=len(df),
                    details=f"Expected column {column} is missing.",
                )
            )
            continue

        actual_type = _semantic_dtype(df[column])
        issues.append(
            QualityIssue(
                check_name="check_schema",
                status="pass" if actual_type == expected_type else "fail",
                column=column,
                details=f"Expected {expected_type}, got {actual_type}.",
            )
        )
    return issues


def check_anomalies(df: pd.DataFrame, value_column: str = "value") -> QualityIssue:
    if value_column not in df.columns:
        return QualityIssue(
            check_name="check_anomalies",
            status="fail",
            column=value_column,
            rows_affected=len(df),
            details=f"Cannot check anomalies. Missing column {value_column}.",
        )

    numeric_values = pd.to_numeric(df[value_column], errors="coerce")
    invalid_count = int(numeric_values.isna().sum())
    negative_count = int((numeric_values < 0).sum())
    affected = invalid_count + negative_count

    return QualityIssue(
        check_name="check_anomalies",
        status="fail" if affected else "pass",
        column=value_column,
        rows_affected=affected,
        details=f"{invalid_count} invalid numeric values and {negative_count} negative values found.",
    )


def run_quality_checks(df: pd.DataFrame, dataset_name: str = "bcb_timeseries") -> QualityReport:
    issues: list[QualityIssue] = []
    issues.extend(check_schema(df, EXPECTED_SCHEMA))
    issues.extend(check_nulls(df, ["date", "value", "series_code"]))
    issues.append(check_duplicates(df, ["date", "series_code"]))
    issues.append(check_anomalies(df, "value"))

    return QualityReport(
        dataset_name=dataset_name,
        checked_at=datetime.now(UTC),
        total_rows=len(df),
        issues=issues,
    )


def _semantic_dtype(series: pd.Series) -> str:
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    return "text"

