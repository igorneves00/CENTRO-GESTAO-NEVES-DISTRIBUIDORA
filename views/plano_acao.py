from __future__ import annotations

import pandas as pd
import streamlit as st

from services.database import get_connection


def render(ctx: dict) -> None:
    st.title("Plano de Ação")
    with st.form("nova_tarefa"):
        problema = st.text_input("Problema")
        acao = st.text_input("Acao")
        area = st.selectbox("Area", ["Comercial", "Estoque", "Dados", "Compras", "Gestao"])
        responsavel = st.text_input("Responsavel")
        prazo = st.date_input("Prazo")
        prioridade = st.selectbox("Prioridade", ["Critica", "Alta", "Media", "Baixa"])
        status = st.selectbox("Status", ["A fazer", "Em andamento", "Concluido", "Atrasado"])
        obs = st.text_area("Observacao")
        esperado = st.text_input("Resultado esperado")
        alcancado = st.text_input("Resultado alcancado")
        submitted = st.form_submit_button("Salvar tarefa", type="primary")
    if submitted:
        with get_connection(ctx["db_path"]) as conn:
            conn.execute(
                """
                INSERT INTO plano_acao(problema, acao, area, responsavel, data_criacao, prazo, prioridade, status, observacao, resultado_esperado, resultado_alcancado)
                VALUES (?, ?, ?, ?, date('now'), ?, ?, ?, ?, ?, ?)
                """,
                (problema, acao, area, responsavel, str(prazo), prioridade, status, obs, esperado, alcancado),
            )
            conn.commit()
        st.success("Tarefa salva.")
    with get_connection(ctx["db_path"]) as conn:
        df = pd.read_sql_query("SELECT * FROM plano_acao ORDER BY id DESC", conn)
    for col in ["A fazer", "Em andamento", "Concluido", "Atrasado"]:
        st.subheader(col)
        st.dataframe(df[df["status"] == col] if not df.empty else df, width="stretch", hide_index=True)

