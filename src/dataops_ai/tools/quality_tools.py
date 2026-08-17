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
                    details=f"A coluna {_column_label(column)} nao existe, entao nao da para avaliar nulos nela.",
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
                details=f"{null_count} valor(es) nulo(s) encontrado(s) em {_column_label(column)}.",
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
            details=f"Nao da para verificar duplicados. Colunas ausentes: {_join_columns(missing_columns)}.",
        )

    duplicate_count = int(df.duplicated(subset=subset).sum())
    return QualityIssue(
        check_name="check_duplicates",
        status="fail" if duplicate_count else "pass",
        rows_affected=duplicate_count,
        details=f"{duplicate_count} linha(s) duplicada(s) usando {_join_columns(subset)}.",
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
                    details=f"A coluna esperada {_column_label(column)} nao existe na base.",
                )
            )
            continue

        actual_type = _semantic_dtype(df[column])
        issues.append(
            QualityIssue(
                check_name="check_schema",
                status="pass" if actual_type == expected_type else "fail",
                column=column,
                details=f"Esperado: {_type_label(expected_type)}. Encontrado: {_type_label(actual_type)}.",
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
            details=f"Nao da para verificar anomalias. Coluna ausente: {_column_label(value_column)}.",
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
        details=f"{invalid_count} valor(es) numerico(s) invalido(s) e {negative_count} valor(es) negativo(s).",
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


def _column_label(column: str) -> str:
    labels = {
        "date": "data",
        "value": "valor",
        "series_code": "codigo da serie",
        "source": "origem",
    }
    return labels.get(column, column)


def _join_columns(columns: list[str]) -> str:
    return ", ".join(_column_label(column) for column in columns)


def _type_label(dtype: str) -> str:
    labels = {
        "datetime": "data",
        "numeric": "numero",
        "text": "texto",
    }
    return labels.get(dtype, dtype)

