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
        table_name: str = "bcb_timeseries",
    ) -> InvestigationReport:
        failed_checks = quality_report.failed_checks
        logs = read_pipeline_logs(self.logs_dir, limit=5)
        rows_in_database = self.database.count_rows(table_name)
        sample = self.database.query_database(f"select * from {table_name} limit 5")

        evidence = [
            f"A base {table_name} tem {rows_in_database} linha(s) carregada(s) no banco.",
            f"A validacao encontrou {len(failed_checks)} falha(s) em {quality_report.total_rows} linha(s).",
            f"Foram encontrados {len(logs)} registro(s) recente(s) de execucao nos logs.",
        ]

        if not sample.empty:
            evidence.append(f"A amostra do banco tem as colunas: {', '.join(sample.columns)}.")

        for issue in failed_checks:
            column = f" na coluna {issue.column}" if issue.column else ""
            evidence.append(f"Falha de {issue.check_name}{column}: {issue.details}")

        return InvestigationReport(
            agent_name="InvestigationAgent",
            summary=self._build_summary(failed_checks_count=len(failed_checks), rows_in_database=rows_in_database),
            evidence=evidence,
            hypothesis=self._build_hypothesis(quality_report, diagnosis, sample),
            next_steps=self._build_next_steps(quality_report, diagnosis),
        )

    def _build_summary(self, failed_checks_count: int, rows_in_database: int) -> str:
        if failed_checks_count == 0:
            return "A investigacao nao encontrou incidente para aprofundar."

        return (
            f"A investigacao confirmou {failed_checks_count} falha(s) de qualidade "
            f"com {rows_in_database} linha(s) ja carregada(s) no banco."
        )

    def _build_hypothesis(self, quality_report: QualityReport, diagnosis: AgentDiagnosis, sample) -> str:
        failed_names = {issue.check_name for issue in quality_report.failed_checks}

        if not failed_names:
            return "A execucao parece consistente. Nao ha evidencia de falha nos checks atuais."

        if "check_schema" in failed_names:
            return (
                "O problema provavelmente aconteceu na transformacao, porque a estrutura final "
                "nao bate com o contrato esperado pela validacao."
            )

        if "check_duplicates" in failed_names:
            return (
                "O problema parece estar ligado a repeticao de dados na carga ou na extracao. "
                "A chave de controle da serie deve ser revisada para evitar duplicidade."
            )

        if "check_nulls" in failed_names or "check_anomalies" in failed_names:
            if "value" in sample.columns:
                null_count = int(sample["value"].isna().sum())
                if null_count:
                    return (
                        "A amostra do banco ja mostra valor nulo, entao o problema chegou ate a carga. "
                        "O proximo passo e comparar arquivo bruto e CSV transformado."
                    )

            return (
                "O problema esta relacionado ao valor da serie. A causa mais provavel e dado ausente "
                "na origem ou falha de conversao durante a transformacao."
            )

        return diagnosis.summary

    def _build_next_steps(self, quality_report: QualityReport, diagnosis: AgentDiagnosis) -> list[str]:
        failed_names = {issue.check_name for issue in quality_report.failed_checks}
        steps = ["Conferir o arquivo bruto salvo em data/raw."]

        if "check_schema" in failed_names:
            steps.append("Comparar as colunas do CSV processado com o contrato esperado.")
        if "check_nulls" in failed_names or "check_anomalies" in failed_names:
            steps.append("Filtrar as linhas com valor vazio ou invalido no CSV processado.")
        if "check_duplicates" in failed_names:
            steps.append("Verificar se a mesma data e serie foram carregadas mais de uma vez.")

        if diagnosis.needs_investigation_agent:
            steps.append("Registrar o incidente para acompanhar a causa na proxima versao.")

        return steps
