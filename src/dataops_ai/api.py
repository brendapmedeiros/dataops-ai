from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from dataops_ai.agents.orchestrator import AgentOrchestrator
from dataops_ai.config import Settings, load_settings
from dataops_ai.scenarios import SCENARIOS
from dataops_ai.tools.api_tools import get_api_status
from dataops_ai.tools.database_tools import DatabaseClient
from dataops_ai.tools.incident_tools import read_incident_history, read_incident_history_from_database


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SCENARIO_ALIASES = {
    "sem_incidente": "none",
    "valores_nulos": "scenario_01_null_values",
    "mudanca_estrutura": "scenario_02_schema_drift",
    "mudanca_schema": "scenario_02_schema_drift",
    "timeout_api": "scenario_03_api_timeout",
    "registros_duplicados": "scenario_04_duplicate_records",
    "tipo_invalido": "scenario_05_invalid_type",
    **{scenario: scenario for scenario in SCENARIOS},
}


class RunRequest(BaseModel):
    scenario: str = Field(default="sem_incidente", examples=["timeout_api"])


class RootResponse(BaseModel):
    projeto: str
    status: str
    endpoints: list[str]


class HealthResponse(BaseModel):
    status: str
    projeto: str


class DatabaseStatusResponse(BaseModel):
    conectado: bool
    tipo: str | None = None
    erro: str | None = None


class ApiStatusResponse(BaseModel):
    available: bool
    status_code: int | None = None
    source: str
    error: str | None = None


class StatusResponse(BaseModel):
    banco: DatabaseStatusResponse
    api_banco_central: ApiStatusResponse


class ScenarioResponse(BaseModel):
    nome: str
    descricao: str


class ScenariosResponse(BaseModel):
    cenarios: list[ScenarioResponse]


class HistoryRecordResponse(BaseModel):
    run_id: str
    recorded_at: str | None = None
    scenario: str
    dataset: str
    rows_checked: int
    failed_checks: int
    severity: str
    diagnosis_engine: str
    requires_manual_review: bool
    summary: str
    diagnosis_report_path: str
    incident_report_path: str


class HistoryResponse(BaseModel):
    historico: list[HistoryRecordResponse]


class RunResponse(BaseModel):
    run_id: str
    cenario: str
    linhas_carregadas: int
    validacoes_com_falha: int
    gravidade: str
    motor_do_diagnostico: str
    precisa_revisao_manual: bool
    resumo: str
    relatorio_diagnostico: str
    relatorio_incidente: str


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or load_settings(PROJECT_ROOT)
    app = FastAPI(title="DataOps AI", version="0.1.0")

    @app.get("/", response_model=RootResponse, summary="Resumo da API")
    def root() -> RootResponse:
        return {
            "projeto": "DataOps AI",
            "status": "online",
            "endpoints": ["/saude", "/status", "/cenarios", "/historico", "/execucoes", "/docs"],
        }

    @app.get("/saude", response_model=HealthResponse, summary="Verifica se a API esta online")
    def health_check() -> HealthResponse:
        return {"status": "ok", "projeto": "DataOps AI"}

    @app.get("/status", response_model=StatusResponse, summary="Verifica banco e API do Banco Central")
    def status_check() -> StatusResponse:
        database = DatabaseClient(app_settings.database_url)
        try:
            database.ping()
            database_status = {
                "conectado": True,
                "tipo": "PostgreSQL" if app_settings.database_url.startswith("postgresql") else "SQLite",
            }
        except RuntimeError as exc:
            database_status = {"conectado": False, "erro": str(exc)}

        api_status = get_api_status(
            app_settings.bcb_series_code,
            app_settings.bcb_start_date,
            app_settings.bcb_end_date,
            timeout_seconds=5,
        )

        return {
            "banco": database_status,
            "api_banco_central": api_status,
        }

    @app.get("/cenarios", response_model=ScenariosResponse, summary="Lista os cenarios disponiveis")
    def list_scenarios() -> ScenariosResponse:
        return {"cenarios": _public_scenarios()}

    @app.get("/historico", response_model=HistoryResponse, summary="Lista execucoes recentes")
    def list_history(limit: int = Query(default=5, ge=1, le=50)) -> HistoryResponse:
        return {"historico": _read_history(app_settings, limit)}

    @app.post("/execucoes", response_model=RunResponse, summary="Executa a pipeline")
    def run_pipeline(request: RunRequest) -> RunResponse:
        try:
            scenario = _normalize_scenario(request.scenario)
            result = AgentOrchestrator(app_settings).run(scenario, _scenario_label(scenario))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        return {
            "run_id": result.run_id,
            "cenario": _scenario_label(result.scenario),
            "linhas_carregadas": result.rows_loaded,
            "validacoes_com_falha": len(result.quality_report.failed_checks),
            "gravidade": result.diagnosis.severity,
            "motor_do_diagnostico": result.diagnosis_engine,
            "precisa_revisao_manual": result.resolution.requires_manual_review,
            "resumo": result.resolution.summary,
            "relatorio_diagnostico": _relative_path(result.diagnosis_report_path, app_settings.project_root),
            "relatorio_incidente": _relative_path(result.incident_report_path, app_settings.project_root),
        }

    return app


def _normalize_scenario(raw_scenario: str) -> str:
    scenario = SCENARIO_ALIASES.get(raw_scenario)
    if scenario:
        return scenario
    raise ValueError(f"Cenario invalido: {raw_scenario}")


def _public_scenarios() -> list[dict]:
    return [
        {"nome": "sem_incidente", "descricao": "roda a pipeline sem forcar erro"},
        {"nome": "valores_nulos", "descricao": "insere valor nulo"},
        {"nome": "mudanca_estrutura", "descricao": "renomeia uma coluna esperada"},
        {"nome": "timeout_api", "descricao": "simula demora ou falha na origem da API"},
        {"nome": "registros_duplicados", "descricao": "duplica uma linha"},
        {"nome": "tipo_invalido", "descricao": "insere texto onde deveria ter numero"},
    ]


def _scenario_label(scenario: str) -> str:
    labels = {
        "none": "sem incidente",
        "scenario_01_null_values": "valores nulos",
        "scenario_02_schema_drift": "mudanca de estrutura",
        "scenario_03_api_timeout": "timeout na API",
        "scenario_04_duplicate_records": "registros duplicados",
        "scenario_05_invalid_type": "tipo invalido",
    }
    return labels.get(scenario, scenario)


def _read_history(settings: Settings, limit: int) -> list[dict]:
    try:
        records = read_incident_history_from_database(settings.database_url, limit=limit)
    except RuntimeError:
        records = []

    if records:
        return records

    return read_incident_history(settings.curated_dir, limit=limit)


def _relative_path(path: str, project_root: Path) -> str:
    full_path = Path(path)
    try:
        return full_path.relative_to(project_root).as_posix()
    except ValueError:
        return full_path.name


app = create_app()
