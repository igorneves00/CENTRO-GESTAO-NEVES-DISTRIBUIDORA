from __future__ import annotations

import pandas as pd
import streamlit as st

from services.inteligencia import responder


def render(ctx: dict) -> None:
    st.title("Neves IA")
    st.caption("Primeira versao baseada em Pandas, regras e consultas pre-configuradas, sem API paga.")
    pergunta = st.text_input("Pergunte algo", placeholder="O que precisa da minha atencao hoje?")
    if st.button("Responder", type="primary") or pergunta:
        r = responder(pergunta, ctx["frames"].get("vendas", pd.DataFrame()), ctx["frames"].get("estoque", pd.DataFrame()), ctx["frames"].get("clientes", pd.DataFrame()), ctx["meta_mensal"])
        st.subheader("Resposta direta")
        st.write(r["resposta"])
        st.subheader("Dados utilizados")
        st.text(r["dados"])
        st.subheader("Acao recomendada")
        st.write(r["acao"])
        st.write(f"**Prioridade:** {r['prioridade']}")
        st.caption(f"Data da analise: {pd.Timestamp.today().date()}")

