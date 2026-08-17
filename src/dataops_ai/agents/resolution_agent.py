from __future__ import annotations

from dataops_ai.models import AgentDiagnosis, InvestigationReport, QualityReport, ResolutionPlan


class ResolutionAgent:
    def build_plan(
        self,
        quality_report: QualityReport,
        diagnosis: AgentDiagnosis,
        investigation: InvestigationReport,
    ) -> ResolutionPlan:
        failed_names = {issue.check_name for issue in quality_report.failed_checks}
        missing_schema = _has_missing_column_issue(quality_report)
        type_issue = _has_type_issue(quality_report)
        api_issue = "fallback" in investigation.hypothesis.lower() or "coleta" in investigation.hypothesis.lower()

        return ResolutionPlan(
            agent_name="ResolutionAgent",
            summary=self._summary(failed_names, api_issue, missing_schema, type_issue),
            impact=self._impact(quality_report, diagnosis, api_issue),
            correction_steps=self._correction_steps(failed_names, api_issue, missing_schema, type_issue),
            prevention_steps=self._prevention_steps(failed_names, api_issue, missing_schema, type_issue),
            requires_manual_review=self._requires_manual_review(diagnosis, failed_names, api_issue, missing_schema),
        )

    def _summary(
        self,
        failed_names: set[str],
        api_issue: bool,
        missing_schema: bool,
        type_issue: bool,
    ) -> str:
        if api_issue and not failed_names:
            return "A correcao principal e operacional: validar a origem e reprocessar a coleta."
        if missing_schema:
            return "A correcao principal e ajustar o contrato de colunas antes de seguir com a carga."
        if type_issue:
            return "A correcao principal e corrigir a conversao de tipos antes da carga final."
        if "check_duplicates" in failed_names:
            return "A correcao principal e remover duplicados e tornar a carga idempotente."
        if "check_nulls" in failed_names or "check_anomalies" in failed_names:
            return "A correcao principal e tratar valores ausentes ou invalidos antes da carga final."
        return "Nao ha correcao imediata para aplicar nesta execucao."

    def _impact(self, quality_report: QualityReport, diagnosis: AgentDiagnosis, api_issue: bool) -> str:
        if api_issue and not quality_report.failed_checks:
            return (
                "Os dados carregados passaram nas validacoes, mas a coleta usou fallback. "
                "Isso reduz confianca operacional e pede reprocessamento quando a origem estabilizar."
            )

        if diagnosis.severity in {"high", "critical"}:
            return "A base nao deve seguir para consumo sem revisao, porque o incidente pode afetar analises posteriores."

        if quality_report.failed_checks:
            return "O impacto parece limitado, mas a base precisa de ajuste antes de ser considerada confiavel."

        return "Nao foi identificado impacto relevante nesta execucao."

    def _correction_steps(
        self,
        failed_names: set[str],
        api_issue: bool,
        missing_schema: bool,
        type_issue: bool,
    ) -> list[str]:
        steps: list[str] = []

        if api_issue:
            steps.extend(
                [
                    "Validar disponibilidade da API do Banco Central.",
                    "Reexecutar a extracao sem fallback.",
                    "Comparar o novo arquivo bruto com o arquivo gerado durante o fallback.",
                ]
            )

        if missing_schema:
            steps.extend(
                [
                    "Conferir as colunas recebidas no arquivo bruto.",
                    "Ajustar o mapeamento da transformacao para restaurar a coluna esperada.",
                    "Reprocessar a base e rodar as validacoes novamente.",
                ]
            )

        if type_issue:
            steps.extend(
                [
                    "Inspecionar os valores que nao foram convertidos para numero.",
                    "Aplicar conversao numerica com tratamento para erro.",
                    "Separar registros invalidos antes de gravar a tabela final.",
                ]
            )

        if ("check_nulls" in failed_names or "check_anomalies" in failed_names) and not type_issue:
            steps.extend(
                [
                    "Isolar as linhas com valor vazio ou invalido.",
                    "Verificar se o erro veio da origem ou da conversao no transform.",
                    "Definir regra: bloquear carga, descartar linha ou preencher valor conforme criterio do dado.",
                ]
            )

        if "check_duplicates" in failed_names:
            steps.extend(
                [
                    "Remover duplicados usando data e codigo da serie como chave.",
                    "Adicionar regra de deduplicacao antes de gravar no banco.",
                ]
            )

        return steps or ["Manter monitoramento da pipeline."]

    def _prevention_steps(
        self,
        failed_names: set[str],
        api_issue: bool,
        missing_schema: bool,
        type_issue: bool,
    ) -> list[str]:
        steps = ["Registrar o incidente no historico da pipeline."]

        if api_issue:
            steps.append("Adicionar alerta quando a pipeline usar fallback.")
        if missing_schema:
            steps.append("Criar validacao de contrato antes da etapa de carga.")
        if type_issue:
            steps.append("Validar tipos das colunas obrigatorias antes de gravar no banco.")
        if "check_nulls" in failed_names or "check_anomalies" in failed_names:
            steps.append("Criar regra de quarentena para linhas com valor invalido.")
        if "check_duplicates" in failed_names:
            steps.append("Criar chave unica ou controle de idempotencia na tabela final.")

        return steps

    def _requires_manual_review(
        self,
        diagnosis: AgentDiagnosis,
        failed_names: set[str],
        api_issue: bool,
        missing_schema: bool,
    ) -> bool:
        if failed_names == {"check_duplicates"}:
            return False

        return api_issue or diagnosis.severity in {"high", "critical"} or missing_schema


def _has_missing_column_issue(quality_report: QualityReport) -> bool:
    return any(
        issue.check_name == "check_schema" and "nao existe" in issue.details
        for issue in quality_report.failed_checks
    )


def _has_type_issue(quality_report: QualityReport) -> bool:
    return any(
        issue.check_name == "check_schema" and "Esperado:" in issue.details
        for issue in quality_report.failed_checks
    )
