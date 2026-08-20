from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


IssueStatus = Literal["pass", "fail", "warning"]
Severity = Literal["low", "medium", "high", "critical"]


class QualityIssue(BaseModel):
    check_name: str
    status: IssueStatus
    column: str | None = None
    rows_affected: int = 0
    details: str


class QualityReport(BaseModel):
    dataset_name: str
    checked_at: datetime
    total_rows: int
    issues: list[QualityIssue] = Field(default_factory=list)

    @property
    def failed_checks(self) -> list[QualityIssue]:
        return [issue for issue in self.issues if issue.status == "fail"]


class AgentDiagnosis(BaseModel):
    agent_name: str
    severity: Severity
    summary: str
    probable_causes: list[str]
    recommended_actions: list[str]
    needs_investigation_agent: bool


class LLMMetadata(BaseModel):
    provider: str = "local"
    model: str | None = None
    api: str | None = None
    interaction_id: str | None = None
    previous_interaction_id: str | None = None
    response_format: str | None = None
    prompt_version: str | None = None
    store_interaction: bool = False
    latency_ms: int | None = None
    step_types: list[str] = Field(default_factory=list)
    tool_names: list[str] = Field(default_factory=list)
    tool_calls: list[str] = Field(default_factory=list)
    fallback_reason: str | None = None


class InvestigationReport(BaseModel):
    agent_name: str
    summary: str
    evidence: list[str]
    hypothesis: str
    next_steps: list[str]


class ResolutionPlan(BaseModel):
    agent_name: str
    summary: str
    impact: str
    correction_steps: list[str]
    prevention_steps: list[str]
    requires_manual_review: bool


class PipelineRunResult(BaseModel):
    run_id: str
    scenario: str
    rows_loaded: int
    diagnosis_engine: str
    llm_metadata: LLMMetadata = Field(default_factory=LLMMetadata)
    quality_report: QualityReport
    diagnosis: AgentDiagnosis
    investigation: InvestigationReport
    resolution: ResolutionPlan
    diagnosis_report_path: str
    incident_report_path: str
    history_path: str
