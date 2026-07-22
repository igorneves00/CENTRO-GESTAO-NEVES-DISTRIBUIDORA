from __future__ import annotations

import pandas as pd
import streamlit as st

from services.alertas import gerar_alertas
from services.inteligencia import responder
from services.vendas import ranking


def render(ctx: dict) -> None:
    st.title("Inteligência")
    st.caption("Neves IA baseada nos dados reais carregados, sem API paga.")
    vendas = ctx["frames"].get("vendas", pd.DataFrame())
    estoque = ctx["frames"].get("estoque", pd.DataFrame())
    clientes = ctx["frames"].get("clientes", pd.DataFrame())
    alertas = gerar_alertas(vendas, estoque, clientes, ctx["relationship"], ctx["meta_mensal"])

    col1, col2, col3 = st.columns(3)
    col1.metric("Alertas ativos", len(alertas))
    col2.metric("Vendedores analisados", ranking(vendas, "VENDEDOR", top=1000)["VENDEDOR"].nunique() if not vendas.empty else 0)
    col3.metric("Produtos em estoque", estoque["COD_PRODUTO"].nunique() if not estoque.empty else 0)

    st.subheader("O que precisa de atenção")
    if alertas.empty:
        st.success("Nenhum alerta automatico foi gerado com os filtros atuais.")
    else:
        st.dataframe(alertas.head(8), width="stretch", hide_index=True)

    pergunta = st.text_input("Pergunte algo", placeholder="O que precisa da minha atencao hoje?")
    if st.button("Responder", type="primary") or pergunta:
        r = responder(pergunta, vendas, estoque, clientes, ctx["meta_mensal"])
        st.subheader("Resposta direta")
        st.write(r["resposta"])
        st.subheader("Dados utilizados")
        st.text(r["dados"])
        st.subheader("Acao recomendada")
        st.write(r["acao"])
        st.write(f"**Prioridade:** {r['prioridade']}")
        st.caption(f"Data da analise: {pd.Timestamp.today().date()}")

