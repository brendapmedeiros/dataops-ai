from __future__ import annotations

import json

from dataops_ai.llm.provider import GeminiClient
from dataops_ai.models import AgentDiagnosis, QualityReport


class DataQualityAgent:
    def __init__(self, gemini_api_key: str | None, gemini_model: str) -> None:
        self.gemini_api_key = gemini_api_key
        self.gemini_model = gemini_model
        self.engine_used = "regras_locais"

    def diagnose(self, report: QualityReport, context: dict) -> AgentDiagnosis:
        if not report.failed_checks:
            self.engine_used = "regras_locais"
            return self._rule_based_diagnosis(report)

        if not self.gemini_api_key:
            self.engine_used = "regras_locais"
            return self._rule_based_diagnosis(report)

        try:
            response = GeminiClient(self.gemini_api_key, self.gemini_model).generate_json(
                self._build_prompt(report, context)
            )
            self.engine_used = "gemini"
            return AgentDiagnosis(**response)
        except Exception:
            self.engine_used = "regras_locais"
            return self._rule_based_diagnosis(report)

    def _build_prompt(self, report: QualityReport, context: dict) -> str:
        return (
            "Voce e o DataQualityAgent de um projeto de DataOps. "
            "Responda apenas JSON valido com estes campos: "
            "agent_name, severity, summary, probable_causes, recommended_actions, "
            "needs_investigation_agent. "
            "A severity deve ser low, medium, high ou critical. "
            "Escreva summary, probable_causes e recommended_actions em portugues do Brasil, "
            "sem acentos, com tom direto e natural, sem cara de texto generico de IA. "
            "Nao cite nomes internos em ingles como value, dataset ou scenario_01_null_values; "
            "prefira termos como valor, base e cenario testado.\n\n"
            f"QUALITY_REPORT={report.model_dump_json()}\n"
            f"CONTEXT={json.dumps(context, ensure_ascii=True)}"
        )

    def _rule_based_diagnosis(self, report: QualityReport) -> AgentDiagnosis:
        failed = report.failed_checks
        failed_names = {issue.check_name for issue in failed}

        if not failed:
            return AgentDiagnosis(
                agent_name="DataQualityAgent",
                severity="low",
                summary="Nenhum incidente de qualidade foi encontrado.",
                probable_causes=["A saida da pipeline bate com as regras de qualidade esperadas."],
                recommended_actions=["Continuar monitorando as proximas execucoes da pipeline."],
                needs_investigation_agent=False,
            )

        severity = "medium"
        if "check_schema" in failed_names:
            severity = "high"
        if any(issue.rows_affected >= max(1, report.total_rows // 2) for issue in failed):
            severity = "critical"

        causes = []
        if "check_schema" in failed_names:
            causes.append("Mudanca de schema entre a saida da transformacao e o contrato esperado.")
        if "check_nulls" in failed_names:
            causes.append("Valores ausentes vindos da API ou introduzidos na transformacao.")
        if "check_duplicates" in failed_names:
            causes.append("Extracao ou carga repetida, possivelmente sem regra de idempotencia.")
        if "check_anomalies" in failed_names:
            causes.append("Falha ao converter valor numerico ou valor inesperado vindo da origem.")

        return AgentDiagnosis(
            agent_name="DataQualityAgent",
            severity=severity,
            summary=f"Foram encontradas {len(failed)} falha(s) de qualidade na base {report.dataset_name}.",
            probable_causes=causes or ["Uma regra de qualidade falhou e precisa ser revisada."],
            recommended_actions=[
                "Olhar o arquivo bruto, o CSV transformado e os logs da pipeline.",
                "Revisar os detalhes das validacoes antes de usar essa base em etapas seguintes.",
                "Na V2, acionar o agente de investigacao quando a causa nao estiver clara.",
            ],
            needs_investigation_agent=severity in {"high", "critical"},
        )
