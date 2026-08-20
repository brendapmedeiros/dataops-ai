from __future__ import annotations

from pathlib import Path

from dataops_ai.models import AgentDiagnosis, InvestigationReport, QualityReport
from dataops_ai.tools.database_tools import DatabaseClient
from dataops_ai.tools.log_tools import read_pipeline_logs


class InvestigationAgent:
    def __init__(self, database_url: str, logs_dir: Path) -> None:
        self.database = DatabaseClient(database_url)
        self.logs_dir = logs_dir

    def investigate(
        self,
        quality_report: QualityReport,
        diagnosis: AgentDiagnosis,
        scenario: str,
        run_id: str,
        table_name: str = "bcb_timeseries",
    ) -> InvestigationReport:
        failed_checks = quality_report.failed_checks
        logs = read_pipeline_logs(self.logs_dir, limit=5)
        api_fallback_logs = [
            log
            for log in logs
            if log.get("event") == "api_fallback_used"
            and log.get("payload", {}).get("scenario") == scenario
            and log.get("payload", {}).get("run_id") == run_id
        ][-1:]
        rows_in_database = self.database.count_rows(table_name)
        sample = self.database.query_database(f"select * from {table_name} limit 5")

        evidence = [
            f"A base {table_name} tem {rows_in_database} linha(s) carregada(s) no banco.",
            f"A validação encontrou {len(failed_checks)} falha(s) em {quality_report.total_rows} linha(s).",
            f"Run id da execução: {run_id}.",
            f"Foram encontrados {len(logs)} registro(s) recente(s) de execução nos logs.",
        ]

        if not sample.empty:
            evidence.append(f"A amostra do banco tem as colunas: {', '.join(sample.columns)}.")

        for log in api_fallback_logs:
            payload = log.get("payload", {})
            source = _source_label(payload.get("source", "origem desconhecida"))
            reason = payload.get("reason", "motivo não informado")
            evidence.append(f"Log de coleta: API não respondeu como esperado; fallback usado ({source}, {reason}).")

        for issue in failed_checks:
            column = f" na coluna {issue.column}" if issue.column else ""
            evidence.append(f"Falha de {issue.check_name}{column}: {issue.details}")

        return InvestigationReport(
            agent_name="InvestigationAgent",
            summary=self._build_summary(
                failed_checks_count=len(failed_checks),
                rows_in_database=rows_in_database,
                api_fallback_used=bool(api_fallback_logs),
            ),
            evidence=evidence,
            hypothesis=self._build_hypothesis(quality_report, diagnosis, sample, bool(api_fallback_logs)),
            next_steps=self._build_next_steps(quality_report, diagnosis, bool(api_fallback_logs)),
        )

    def _build_summary(self, failed_checks_count: int, rows_in_database: int, api_fallback_used: bool) -> str:
        if api_fallback_used and failed_checks_count == 0:
            return (
                "A qualidade dos dados passou, mas a investigação encontrou falha operacional "
                "na coleta e uso de fallback."
            )

        if failed_checks_count == 0:
            return "A investigação não encontrou incidente para aprofundar."

        return (
            f"A investigação confirmou {failed_checks_count} falha(s) de qualidade "
            f"com {rows_in_database} linha(s) já carregada(s) no banco."
        )

    def _build_hypothesis(
        self,
        quality_report: QualityReport,
        diagnosis: AgentDiagnosis,
        sample,
        api_fallback_used: bool,
    ) -> str:
        failed_names = {issue.check_name for issue in quality_report.failed_checks}

        if api_fallback_used:
            return (
                "O incidente parece ter origem na coleta. Os logs mostram falha de acesso à API "
                "e uso de fallback antes da transformação."
            )

        if not failed_names:
            return "A execução parece consistente. Não há evidência de falha nas validações atuais."

        if _has_missing_column_issue(quality_report):
            return (
                "O problema provavelmente aconteceu na transformação, porque a estrutura final "
                "não bate com o contrato esperado pela validação."
            )

        if _has_type_issue(quality_report):
            return (
                "O problema está ligado ao tipo do dado carregado. A coluna existe, mas chegou "
                "com formato diferente do esperado e precisa de conversão antes da carga final."
            )

        if "check_duplicates" in failed_names:
            return (
                "O problema parece estar ligado à repetição de dados na carga ou na extração. "
                "A chave de controle da série deve ser revisada para evitar duplicidade."
            )

        if "check_nulls" in failed_names or "check_anomalies" in failed_names:
            if "value" in sample.columns:
                null_count = int(sample["value"].isna().sum())
                if null_count:
                    return (
                        "A amostra do banco já mostra valor nulo, então o problema chegou até a carga. "
                        "O próximo passo é comparar arquivo bruto e CSV transformado."
                    )

            return (
                "O problema está relacionado ao valor da série. A causa mais provável é dado ausente "
                "na origem ou falha de conversão durante a transformação."
            )

        return diagnosis.summary

    def _build_next_steps(
        self,
        quality_report: QualityReport,
        diagnosis: AgentDiagnosis,
        api_fallback_used: bool,
    ) -> list[str]:
        failed_names = {issue.check_name for issue in quality_report.failed_checks}
        steps = ["Conferir o arquivo bruto salvo em data/raw."]

        if api_fallback_used:
            steps.extend(
                [
                    "Verificar se a API do Banco Central estava disponível no momento da coleta.",
                    "Reprocessar a extração quando a origem estiver estável.",
                    "Manter o fallback registrado nos logs para auditoria da execução.",
                ]
            )

        if _has_missing_column_issue(quality_report):
            steps.append("Comparar as colunas do CSV processado com o contrato esperado.")
        if _has_type_issue(quality_report):
            steps.append("Inspecionar os valores que não foram convertidos para número.")
            steps.append("Revisar a conversão de tipos na transformação antes da carga.")
        if "check_nulls" in failed_names or "check_anomalies" in failed_names:
            steps.append("Filtrar as linhas com valor vazio ou inválido no CSV processado.")
        if "check_duplicates" in failed_names:
            steps.append("Verificar se a mesma data e série foram carregadas mais de uma vez.")

        if diagnosis.needs_investigation_agent:
            steps.append("Registrar o incidente para acompanhar a causa na próxima versão.")

        return steps


def _source_label(source: str) -> str:
    labels = {
        "simulated_api_timeout_fallback": "fallback local",
        "local_fallback": "fallback local",
        "bcb_api": "API do Banco Central",
    }
    return labels.get(source, source)


def _has_missing_column_issue(quality_report: QualityReport) -> bool:
    return any(
        issue.check_name == "check_schema" and "não existe" in issue.details
        for issue in quality_report.failed_checks
    )


def _has_type_issue(quality_report: QualityReport) -> bool:
    return any(
        issue.check_name == "check_types"
        for issue in quality_report.failed_checks
    )
