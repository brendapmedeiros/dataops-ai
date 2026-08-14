from __future__ import annotations

import json

from dataops_ai.llm.provider import GeminiClient
from dataops_ai.models import AgentDiagnosis, QualityReport


class DataQualityAgent:
    def __init__(self, gemini_api_key: str | None, gemini_model: str) -> None:
        self.gemini_api_key = gemini_api_key
        self.gemini_model = gemini_model

    def diagnose(self, report: QualityReport, context: dict) -> AgentDiagnosis:
        if not self.gemini_api_key:
            return self._rule_based_diagnosis(report)

        try:
            response = GeminiClient(self.gemini_api_key, self.gemini_model).generate_json(
                self._build_prompt(report, context)
            )
            return AgentDiagnosis(**response)
        except Exception:
            return self._rule_based_diagnosis(report)

    def _build_prompt(self, report: QualityReport, context: dict) -> str:
        return (
            "You are DataQualityAgent in a DataOps AI project. Return only valid JSON with: "
            "agent_name, severity, summary, probable_causes, recommended_actions, "
            "needs_investigation_agent. Severity must be low, medium, high, or critical.\n\n"
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
                summary="No data quality incident detected.",
                probable_causes=["Pipeline output matches the expected quality rules."],
                recommended_actions=["Keep monitoring future pipeline runs."],
                needs_investigation_agent=False,
            )

        severity = "medium"
        if "check_schema" in failed_names:
            severity = "high"
        if any(issue.rows_affected >= max(1, report.total_rows // 2) for issue in failed):
            severity = "critical"

        causes = []
        if "check_schema" in failed_names:
            causes.append("Schema drift between transform output and expected contract.")
        if "check_nulls" in failed_names:
            causes.append("Missing values introduced by the source API or transform step.")
        if "check_duplicates" in failed_names:
            causes.append("Repeated extraction/load or missing idempotency rule.")
        if "check_anomalies" in failed_names:
            causes.append("Invalid numeric parsing or unexpected source value.")

        return AgentDiagnosis(
            agent_name="DataQualityAgent",
            severity=severity,
            summary=f"{len(failed)} failed quality checks found in {report.dataset_name}.",
            probable_causes=causes or ["A data quality rule failed and needs review."],
            recommended_actions=[
                "Inspect raw payload, transformed CSV, and pipeline logs.",
                "Review failed check details before loading downstream datasets.",
                "Escalate to InvestigationAgent in V2 when root cause is not obvious.",
            ],
            needs_investigation_agent=severity in {"high", "critical"},
        )
