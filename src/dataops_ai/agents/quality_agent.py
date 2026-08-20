from __future__ import annotations

import json

from dataops_ai.llm.provider import GeminiClient
from dataops_ai.models import AgentDiagnosis, LLMMetadata, QualityReport


PROMPT_VERSION = "quality-diagnosis-v1"


class DataQualityAgent:
    def __init__(
        self,
        gemini_api_key: str | None,
        gemini_model: str,
        store_interactions: bool = True,
        gemini_client: GeminiClient | None = None,
    ) -> None:
        self.gemini_api_key = gemini_api_key
        self.gemini_model = gemini_model
        self.store_interactions = store_interactions
        self.gemini_client = gemini_client
        self.engine_used = "regras_locais"
        self.llm_metadata = LLMMetadata(prompt_version=PROMPT_VERSION)

    def diagnose(self, report: QualityReport, context: dict) -> AgentDiagnosis:
        if not report.failed_checks:
            self.engine_used = "regras_locais"
            self.llm_metadata = _local_metadata("sem falha de qualidade")
            return self._rule_based_diagnosis(report)

        if not self.gemini_api_key:
            self.engine_used = "regras_locais"
            self.llm_metadata = _local_metadata("GEMINI_API_KEY não configurada")
            return self._rule_based_diagnosis(report)

        try:
            client = self.gemini_client or GeminiClient(
                self.gemini_api_key,
                self.gemini_model,
                store_interaction=self.store_interactions,
                prompt_version=PROMPT_VERSION,
            )
            response = client.generate_json(
                self._build_prompt(report, context),
                AgentDiagnosis.model_json_schema(),
                tools=_gemini_tools(),
                tool_handlers=_tool_handlers(report, context),
            )
            self.engine_used = "gemini"
            self.llm_metadata = response.metadata
            return AgentDiagnosis(**response.data)
        except Exception as exc:
            self.engine_used = "regras_locais"
            self.llm_metadata = _local_metadata(f"Gemini indisponível: {exc}")
            return self._rule_based_diagnosis(report)

    def _build_prompt(self, report: QualityReport, context: dict) -> str:
        return (
            "Você é o DataQualityAgent de um projeto de DataOps. "
            "Responda apenas JSON válido com estes campos: "
            "agent_name, severity, summary, probable_causes, recommended_actions, "
            "needs_investigation_agent. "
            "A severity deve ser low, medium, high ou critical. "
            "Escreva summary, probable_causes e recommended_actions em português do Brasil, "
            "com acentos e cedilha quando fizer sentido. Use tom direto e natural, sem cara de texto genérico de IA. "
            "Não cite nomes internos em inglês como value, dataset ou scenario_01_null_values; "
            "prefira termos como valor, base e cenário testado. "
            "Use as ferramentas disponíveis se precisar confirmar detalhes antes do diagnóstico.\n\n"
            f"QUALITY_REPORT={report.model_dump_json()}\n"
            f"CONTEXT={json.dumps(context, ensure_ascii=False)}"
        )

    def _rule_based_diagnosis(self, report: QualityReport) -> AgentDiagnosis:
        failed = report.failed_checks
        failed_names = {issue.check_name for issue in failed}
        missing_schema = _has_missing_column_issue(report)
        type_issue = _has_type_issue(report)

        if not failed:
            return AgentDiagnosis(
                agent_name="DataQualityAgent",
                severity="low",
                summary="Nenhum incidente de qualidade foi encontrado.",
                probable_causes=["A saída da pipeline bate com as regras de qualidade esperadas."],
                recommended_actions=["Continuar monitorando as próximas execuções da pipeline."],
                needs_investigation_agent=False,
            )

        severity = "medium"
        if missing_schema or type_issue:
            severity = "high"
        if any(issue.rows_affected >= max(1, report.total_rows // 2) for issue in failed):
            severity = "critical"

        causes = []
        if missing_schema:
            causes.append("Mudança de schema entre a saída da transformação e o contrato esperado.")
        if type_issue:
            causes.append("Falha na conversão de tipo da coluna de valor antes da carga.")
        if "check_nulls" in failed_names:
            causes.append("Valores ausentes vindos da API ou introduzidos na transformação.")
        if "check_duplicates" in failed_names:
            causes.append("Extração ou carga repetida, possivelmente sem regra de idempotência.")
        if "check_anomalies" in failed_names:
            causes.append("Falha ao converter valor numérico ou valor inesperado vindo da origem.")

        return AgentDiagnosis(
            agent_name="DataQualityAgent",
            severity=severity,
            summary=f"Foram encontradas {len(failed)} falha(s) de qualidade na base {report.dataset_name}.",
            probable_causes=causes or ["Uma regra de qualidade falhou e precisa ser revisada."],
            recommended_actions=[
                "Olhar o arquivo bruto, o CSV transformado e os logs da pipeline.",
                "Revisar os detalhes das validações antes de usar essa base em etapas seguintes.",
                "Usar a investigação desta execução para confirmar a causa.",
            ],
            needs_investigation_agent=severity in {"high", "critical"},
        )


def _has_missing_column_issue(report: QualityReport) -> bool:
    return any(
        issue.check_name == "check_schema" and "não existe" in issue.details
        for issue in report.failed_checks
    )


def _has_type_issue(report: QualityReport) -> bool:
    return any(
        issue.check_name == "check_types"
        for issue in report.failed_checks
    )


def _local_metadata(reason: str) -> LLMMetadata:
    return LLMMetadata(
        provider="local",
        api="regras_locais",
        prompt_version=PROMPT_VERSION,
        fallback_reason=reason,
    )


def _gemini_tools() -> list[dict]:
    return [
        {
            "type": "function",
            "name": "consultar_relatorio_qualidade",
            "description": "Retorna o relatório completo das validações de qualidade desta execução.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
        {
            "type": "function",
            "name": "consultar_contexto_execucao",
            "description": "Retorna contexto operacional da execução, como cenário, run_id e carga.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    ]


def _tool_handlers(report: QualityReport, context: dict) -> dict:
    return {
        "consultar_relatorio_qualidade": lambda args: report.model_dump(mode="json"),
        "consultar_contexto_execucao": lambda args: context,
    }
