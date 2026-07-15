from __future__ import annotations

import streamlit as st


def render(ctx: dict) -> None:
    st.title("Compras")
    st.info("O modulo de compras precisa do historico detalhado dos itens comprados, dos fornecedores e das cotacoes.")
    st.write("Estrutura preparada para ultimas compras, melhor fornecedor, comparacao de precos, aumento de custos, economia, prazos, pedidos atrasados e produtos sem cotacao.")

