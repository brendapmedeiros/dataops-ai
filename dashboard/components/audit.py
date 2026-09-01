from __future__ import annotations

import pandas as pd
import streamlit as st


def render_audit_drawer(history_df: pd.DataFrame) -> None:
    """Renders the expandable audit trail drawer with complete execution logs and SHA-256 proofs."""
    with st.expander("Trilha Completa de Auditoria Imutável (Histórico Detalhado)", expanded=False):
        if history_df.empty:
            st.info("Nenhuma execução gravada no histórico de auditoria.")
            return

        table_columns = [
            "run_id",
            "cenário",
            "falhas",
            "gravidade",
            "quarentena",
            "audit_hash",
            "motor",
            "revisão_manual",
            "resumo",
        ]
        available_columns = [col for col in table_columns if col in history_df.columns]
        table = history_df[available_columns]

        st.dataframe(
            table,
            use_container_width=True,
            hide_index=True,
            height=280,
        )
