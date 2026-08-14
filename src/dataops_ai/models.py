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
