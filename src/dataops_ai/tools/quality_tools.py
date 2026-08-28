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
                    details=f"A coluna {_column_label(column)} não existe, então não dá para avaliar nulos nela.",
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
            details=f"Não dá para verificar duplicados. Colunas ausentes: {_join_columns(missing_columns)}.",
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
    for column in expected_schema:
        if column not in df.columns:
            issues.append(
                QualityIssue(
                    check_name="check_schema",
                    status="fail",
                    column=column,
                    rows_affected=len(df),
                    details=f"A coluna esperada {_column_label(column)} não existe na base.",
                )
            )
    return issues


def check_types(df: pd.DataFrame, expected_schema: dict[str, str]) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    for column, expected_type in expected_schema.items():
        if column not in df.columns:
            continue
        actual_type = _semantic_dtype(df[column])
        issues.append(
            QualityIssue(
                check_name="check_types",
                status="pass" if actual_type == expected_type else "fail",
                column=column,
                details=f"Esperado: {_type_label(expected_type)}. Encontrado: {_type_label(actual_type)}.",
            )
        )
    return issues


def compare_schema(df: pd.DataFrame, expected_schema: dict[str, str] | None = None) -> list[QualityIssue]:
    schema = expected_schema or EXPECTED_SCHEMA
    return [*check_schema(df, schema), *check_types(df, schema)]


def check_anomalies(df: pd.DataFrame, value_column: str = "value") -> QualityIssue:
    if value_column not in df.columns:
        return QualityIssue(
            check_name="check_anomalies",
            status="fail",
            column=value_column,
            rows_affected=len(df),
            details=f"Não dá para verificar anomalias. Coluna ausente: {_column_label(value_column)}.",
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
        details=f"{invalid_count} valor(es) numérico(s) inválido(s) e {negative_count} valor(es) negativo(s).",
    )


def check_drift_zscore(
    df: pd.DataFrame,
    value_column: str = "value",
    threshold: float = 3.5,
) -> QualityIssue:
    if value_column not in df.columns:
        return QualityIssue(
            check_name="check_drift_zscore",
            status="pass",
            column=value_column,
            details="Coluna ausente; verificação de drift ignorada.",
        )

    numeric_values = pd.to_numeric(df[value_column], errors="coerce").dropna()
    if len(numeric_values) < 3:
        return QualityIssue(
            check_name="check_drift_zscore",
            status="pass",
            column=value_column,
            details="Amostra insuficiente para cálculo estatístico de drift.",
        )

    std = float(numeric_values.std())
    if std == 0.0 or pd.isna(std):
        return QualityIssue(
            check_name="check_drift_zscore",
            status="pass",
            column=value_column,
            details="Série estável sem desvio padrão apurável.",
        )

    mean = float(numeric_values.mean())
    zscores = (numeric_values - mean).abs() / std
    outliers = zscores[zscores > threshold]
    outlier_count = len(outliers)

    if outlier_count > 0:
        max_z = float(outliers.max())
        return QualityIssue(
            check_name="check_drift_zscore",
            status="fail",
            column=value_column,
            rows_affected=outlier_count,
            details=(
                f"{outlier_count} registro(s) com anomalia estatística severa "
                f"(Z-score > {threshold}σ). Maior desvio observado: {max_z:.2f}σ."
            ),
        )

    return QualityIssue(
        check_name="check_drift_zscore",
        status="pass",
        column=value_column,
        details=f"Valores dentro da distribuição normal esperada (Z-score <= {threshold}σ).",
    )


def check_pii_exposure(df: pd.DataFrame) -> QualityIssue:
    import re

    cpf_pattern = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
    email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

    found_pii: list[str] = []
    text_cols = [col for col in df.columns if df[col].dtype == "object"]
    for col in text_cols:
        series_str = df[col].astype(str)
        has_cpf = series_str.str.contains(cpf_pattern).any()
        has_email = series_str.str.contains(email_pattern).any()
        if has_cpf or has_email:
            found_pii.append(col)

    if found_pii:
        return QualityIssue(
            check_name="check_pii_exposure",
            status="fail",
            column=", ".join(found_pii),
            rows_affected=len(df),
            details=f"Possível vazamento de PII (CPF/email) detectado na(s) coluna(s): {', '.join(found_pii)}.",
        )

    return QualityIssue(
        check_name="check_pii_exposure",
        status="pass",
        details="Nenhuma exposição de dados sensíveis (PII/LGPD) detectada.",
    )


def run_quality_checks(
    df: pd.DataFrame,
    dataset_name: str = "bcb_timeseries",
    contract: object | None = None,
) -> QualityReport:
    issues: list[QualityIssue] = []
    expected_schema = getattr(contract, "expected_schema", EXPECTED_SCHEMA)
    required_cols = getattr(contract, "required_columns", ["date", "value", "series_code"])
    unique_cols = getattr(contract, "unique_columns", ["date", "series_code"]) or ["date", "series_code"]

    issues.extend(compare_schema(df, expected_schema))
    issues.extend(check_nulls(df, required_cols))
    issues.append(check_duplicates(df, unique_cols))
    issues.append(check_anomalies(df, "value"))
    issues.append(check_drift_zscore(df, "value"))
    issues.append(check_pii_exposure(df))

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
        "series_code": "código da série",
        "source": "origem",
    }
    return labels.get(column, column)


def _join_columns(columns: list[str]) -> str:
    return ", ".join(_column_label(column) for column in columns)


def _type_label(dtype: str) -> str:
    labels = {
        "datetime": "data",
        "numeric": "número",
        "text": "texto",
    }
    return labels.get(dtype, dtype)

