from __future__ import annotations

import os

import pandas as pd
import requests
import streamlit as st


API_URL = os.getenv("DATAOPS_API_URL", "http://127.0.0.1:8000").rstrip("/")


st.set_page_config(page_title="DataOps AI", page_icon="DA", layout="wide")


def main() -> None:
    st.title("DataOps AI")

    status = _get_json("/status")
    history = _get_json("/historico?limit=10")
    scenarios = _get_json("/cenarios")

    _render_status(status)
    _render_run_form(scenarios)
    _render_history(history)


def _render_status(status: dict | None) -> None:
    st.subheader("Status")
    col_db, col_api = st.columns(2)

    if not status:
        col_db.metric("Banco", "indisponivel")
        col_api.metric("API Banco Central", "indisponivel")
        return

    database = status.get("banco", {})
    bcb_api = status.get("api_banco_central", {})

    db_label = "ok" if database.get("conectado") else "falhou"
    api_label = "ok" if bcb_api.get("available") else "falhou"

    col_db.metric("Banco", db_label, database.get("tipo") or "")
    col_api.metric(
        "API Banco Central",
        api_label,
        f"HTTP {bcb_api.get('status_code')}" if bcb_api.get("status_code") else "",
    )


def _render_run_form(scenarios: dict | None) -> None:
    st.subheader("Execucao")
    scenario_items = scenarios.get("cenarios", []) if scenarios else []
    scenario_names = [item["nome"] for item in scenario_items]

    with st.form("run_pipeline_form"):
        selected = st.selectbox("Cenario", scenario_names, index=0 if scenario_names else None)
        submitted = st.form_submit_button("Executar")

    if submitted and selected:
        response = _post_json("/execucoes", {"scenario": selected})
        if not response:
            st.error("Nao foi possivel executar a pipeline.")
            return

        st.success(f"Execucao finalizada: {response['run_id']}")
        st.json(response)


def _render_history(history: dict | None) -> None:
    st.subheader("Historico")
    records = history.get("historico", []) if history else []

    if not records:
        st.info("Nenhuma execucao encontrada.")
        return

    df = pd.DataFrame(records)
    visible_columns = [
        "run_id",
        "scenario",
        "failed_checks",
        "severity",
        "diagnosis_engine",
        "requires_manual_review",
        "summary",
    ]
    st.dataframe(df[visible_columns], use_container_width=True, hide_index=True)


def _get_json(path: str) -> dict | None:
    try:
        response = requests.get(f"{API_URL}{path}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def _post_json(path: str, payload: dict) -> dict | None:
    try:
        response = requests.post(f"{API_URL}{path}", json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


if __name__ == "__main__":
    main()
