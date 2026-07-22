from __future__ import annotations

import pandas as pd
import streamlit as st

from services.alertas import gerar_alertas
from services.database import get_connection
from utils.exportacao import dataframe_to_csv_bytes


def render(ctx: dict) -> None:
    st.title("Alertas")
    alertas = gerar_alertas(ctx["frames"].get("vendas", pd.DataFrame()), ctx["frames"].get("estoque", pd.DataFrame()), ctx["frames"].get("clientes", pd.DataFrame()), ctx["relationship"], ctx["meta_mensal"])
    if alertas.empty:
        st.success("Nenhum alerta automatico gerado com os filtros atuais.")
        return
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Alertas", len(alertas))
    col2.metric("Criticos", int((alertas["Gravidade"] == "Critica").sum()))
    col3.metric("Alta", int((alertas["Gravidade"] == "Alta").sum()))
    col4.metric("Media/Baixa", int(alertas["Gravidade"].isin(["Media", "Baixa"]).sum()))
    st.dataframe(alertas, width="stretch", hide_index=True)
    selected = st.selectbox("Transformar alerta em tarefa", alertas["Titulo"].astype(str).tolist())
    if st.button("Enviar para Plano de Acao", type="primary"):
        row = alertas[alertas["Titulo"].astype(str) == selected].iloc[0]
        with get_connection(ctx["db_path"]) as conn:
            conn.execute(
                """
                INSERT INTO plano_acao(problema, acao, area, responsavel, data_criacao, prazo, prioridade, status, observacao, resultado_esperado, resultado_alcancado)
                VALUES (?, ?, ?, ?, date('now'), ?, ?, 'A fazer', ?, ?, '')
                """,
                (
                    row["Titulo"],
                    row["Acao recomendada"],
                    row["Area"],
                    row["Responsavel"],
                    row["Prazo"],
                    row["Gravidade"],
                    row["Descricao"],
                    row["Impacto"],
                ),
            )
            conn.commit()
        st.success("Alerta enviado para o Plano de Acao.")
    st.download_button("Exportar alertas CSV", dataframe_to_csv_bytes(alertas), "alertas.csv")

