from __future__ import annotations

from pathlib import Path
import json
import logging
import os
from secrets import compare_digest

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from dataops_ai.agents.orchestrator import AgentOrchestrator
from dataops_ai.config import Settings, load_settings
from dataops_ai.scenarios import SCENARIOS
from dataops_ai.tools.api_tools import get_api_status
from dataops_ai.tools.database_tools import DatabaseClient
from dataops_ai.tools.incident_tools import (
    read_incident_history,
    read_incident_history_from_database,
    read_run_diagnosis_from_disk,
)
import datetime


PROJECT_ROOT = Path(__file__).resolve().parents[2]
logger = logging.getLogger(__name__)

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


class GeminiStatusResponse(BaseModel):
    configurado: bool
    modelo: str
    interactions_ativas: bool


class EnvironmentStatusResponse(BaseModel):
    provedor: str
    regiao: str
    servico: str | None = None
    quarantine_bucket: str | None = None


class StatusResponse(BaseModel):
    banco: DatabaseStatusResponse
    api_banco_central: ApiStatusResponse
    gemini: GeminiStatusResponse
    ambiente: EnvironmentStatusResponse | None = None


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
    quarantined: bool = False
    audit_hash: str | None = None
    collaboration_status: str | None = None
    collaboration_summary: str | None = None
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
    quarentenado: bool = False
    caminho_quarentena: str | None = None
    audit_hash: str = ""
    collaboration_status: str | None = None
    collaboration_summary: str | None = None
    collaboration: dict | None = None
    provedor_llm: str
    modelo_llm: str | None = None
    api_llm: str | None = None
    interaction_id: str | None = None
    previous_interaction_id: str | None = None
    formato_resposta: str | None = None
    prompt_version: str | None = None
    latencia_llm_ms: int | None = None
    tools_disponiveis: list[str] = Field(default_factory=list)
    tools_chamadas: list[str] = Field(default_factory=list)
    motivo_fallback: str | None = None
    precisa_revisao_manual: bool
    resumo: str
    relatorio_diagnostico: str
    relatorio_incidente: str


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or load_settings(PROJECT_ROOT)
    environment = os.getenv("APP_ENV", "development").strip().lower()
    is_production = environment in {"prod", "production"}
    allowed_origins = [
        origin.strip()
        for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173").split(",")
        if origin.strip()
    ]
    if is_production and (not app_settings.api_key or "*" in allowed_origins):
        raise RuntimeError("Produção exige DATAOPS_API_KEY e CORS_ALLOWED_ORIGINS explícito.")

    app = FastAPI(
        title="DataOps AI",
        version="0.1.0",
        docs_url=None if is_production else "/docs",
        redoc_url=None if is_production else "/redoc",
        openapi_url=None if is_production else "/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-API-Key"],
    )

    @app.get("/", response_model=RootResponse, summary="Resumo da API")
    def root() -> RootResponse:
        return {
            "projeto": "DataOps AI",
            "status": "online",
            "endpoints": [
                "/saude",
                "/status",
                "/cenarios",
                "/historico",
                "/execucoes",
                "/dados/gold",
                "/dados/quarentena",
                *([] if is_production else ["/docs"]),
            ],
        }

    @app.get("/saude", response_model=HealthResponse, summary="Verifica se a API está online")
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
        except RuntimeError:
            database_status = {"conectado": False}

        api_status = get_api_status(
            app_settings.bcb_series_code,
            app_settings.bcb_start_date,
            app_settings.bcb_end_date,
            timeout_seconds=5,
        )

        is_cloud_run = bool(os.getenv("K_SERVICE"))
        return {
            "banco": database_status,
            "api_banco_central": api_status,
            "gemini": {
                "configurado": bool(app_settings.gemini_api_key),
                "modelo": app_settings.gemini_model,
                "interactions_ativas": app_settings.gemini_store_interactions,
            },
            "ambiente": {
                "provedor": "Google Cloud Run" if is_cloud_run else "Local (Docker)",
                "regiao": os.getenv("GCP_REGION", "us-central1" if is_cloud_run else "local"),
                "servico": os.getenv("K_SERVICE"),
                "quarantine_bucket": app_settings.gcs_quarantine_bucket,
            },
        }

    @app.get("/cenarios", response_model=ScenariosResponse, summary="Lista os cenários disponíveis")
    def list_scenarios() -> ScenariosResponse:
        return {"cenarios": _public_scenarios()}

    @app.get("/historico", response_model=HistoryResponse, summary="Lista execuções recentes")
    def list_history(limit: int = Query(default=5, ge=1, le=50)) -> HistoryResponse:
        return {"historico": _read_history(app_settings, limit)}

    @app.get("/execucoes/{run_id}/diagnostico", summary="Retorna o diagnóstico completo e diálogo da execução")
    def get_execution_diagnosis(
        run_id: str,
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ) -> dict:
        if is_production and (not x_api_key or not compare_digest(x_api_key, app_settings.api_key or "")):
            raise HTTPException(status_code=401, detail="Acesso não autorizado.")
        return read_run_diagnosis_from_disk(run_id, app_settings.curated_dir)

    @app.get("/dados/gold", summary="Retorna os registros armazenados na camada Gold (tabela oficial)")
    def get_gold_data(limit: int = Query(default=100, ge=1, le=500)) -> dict:
        try:
            database = DatabaseClient(app_settings.database_url)
            if not database.table_exists("bcb_timeseries"):
                return {"total": 0, "registros": []}
            query = f"SELECT date, value, series_code, source FROM bcb_timeseries ORDER BY date DESC LIMIT {limit};"
            df = database.query_database(query)
            if df.empty:
                return {"total": 0, "registros": []}
            records = []
            for _, row in df.iterrows():
                d = str(row.get("date"))[:10]
                records.append({
                    "date": d,
                    "value": float(row.get("value", 0.0)),
                    "series_code": int(row.get("series_code", 11)),
                    "source": str(row.get("source", "API BCB SGS")),
                })
            records_chrono = sorted(records, key=lambda x: x["date"])
            return {"total": len(records), "registros": records_chrono}
        except Exception:
            logger.exception("Falha ao consultar a camada Gold")
            return {"total": 0, "registros": []}

    @app.get("/dados/quarentena", summary="Retorna os lotes isolados na Quarentena (DLQ)")
    def get_quarantine_data() -> dict:
        try:
            csv_files = sorted(app_settings.dlq_dir.glob("quarantine_*.csv"), key=lambda f: f.stat().st_mtime, reverse=True)
            batches = []
            for f in csv_files:
                stat = f.stat()
                dt = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
                try:
                    lines = f.read_text(encoding="utf-8").splitlines()
                    rows_count = max(0, len(lines) - 1)
                except Exception:
                    rows_count = 0
                batches.append({
                    "arquivo": f.name,
                    "isolado_em": dt,
                    "tamanho_bytes": stat.st_size,
                    "linhas_rejeitadas": rows_count,
                })
            return {"total_lotes": len(batches), "lotes": batches}
        except Exception:
            logger.exception("Falha ao consultar a quarentena")
            return {"total_lotes": 0, "lotes": []}

    @app.post("/execucoes", response_model=RunResponse, summary="Executa a pipeline")
    def run_pipeline(
        request: RunRequest,
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ) -> RunResponse:
        # valida a api key se estiver configurada
        if app_settings.api_key and (not x_api_key or not compare_digest(x_api_key, app_settings.api_key)):
            raise HTTPException(status_code=401, detail="Acesso não autorizado: chave de API inválida.")

        try:
            scenario = _normalize_scenario(request.scenario)
            result = AgentOrchestrator(app_settings).run(scenario, _scenario_label(scenario))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            # limpa excecoes e protege contra vazamento
            raise HTTPException(
                status_code=503,
                detail="Erro ao executar a pipeline. Verifique os logs para detalhes.",
            ) from exc

        return {
            "run_id": result.run_id,
            "cenario": _scenario_label(result.scenario),
            "linhas_carregadas": result.rows_loaded,
            "validacoes_com_falha": len(result.quality_report.failed_checks),
            "gravidade": result.diagnosis.severity,
            "motor_do_diagnostico": result.diagnosis_engine,
            "quarentenado": result.quarantined,
            "caminho_quarentena": _relative_path(result.quarantine_path, app_settings.project_root) if result.quarantine_path else None,
            "audit_hash": result.audit_hash,
            "collaboration_status": result.collaboration.status,
            "collaboration_summary": result.collaboration.supervisor_decision,
            "collaboration": result.collaboration.model_dump() if result.collaboration else None,
            "provedor_llm": result.llm_metadata.provider,
            "modelo_llm": result.llm_metadata.model,
            "api_llm": result.llm_metadata.api,
            "interaction_id": result.llm_metadata.interaction_id,
            "previous_interaction_id": result.llm_metadata.previous_interaction_id,
            "formato_resposta": result.llm_metadata.response_format,
            "prompt_version": result.llm_metadata.prompt_version,
            "latencia_llm_ms": result.llm_metadata.latency_ms,
            "tools_disponiveis": result.llm_metadata.tool_names,
            "tools_chamadas": result.llm_metadata.tool_calls,
            "motivo_fallback": result.llm_metadata.fallback_reason,
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
    raise ValueError(f"Cenário inválido: {raw_scenario}")


def _public_scenarios() -> list[dict]:
    return [
        {"nome": "sem_incidente", "descricao": "roda a pipeline sem forçar erro"},
        {"nome": "valores_nulos", "descricao": "insere valor nulo"},
        {"nome": "mudanca_estrutura", "descricao": "renomeia uma coluna esperada"},
        {"nome": "timeout_api", "descricao": "simula demora ou falha na origem da API"},
        {"nome": "registros_duplicados", "descricao": "duplica uma linha"},
        {"nome": "tipo_invalido", "descricao": "insere texto onde deveria ter número"},
    ]


def _scenario_label(scenario: str) -> str:
    labels = {
        "none": "sem incidente",
        "scenario_01_null_values": "valores nulos",
        "scenario_02_schema_drift": "mudança de estrutura",
        "scenario_03_api_timeout": "timeout na API",
        "scenario_04_duplicate_records": "registros duplicados",
        "scenario_05_invalid_type": "tipo inválido",
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
