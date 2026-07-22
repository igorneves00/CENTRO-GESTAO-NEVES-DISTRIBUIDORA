from __future__ import annotations

import pandas as pd
import streamlit as st

from services.vendas import vendas_validas
from utils.calculos import calculate_abc


def render(ctx: dict) -> None:
    st.title("Produtos")
    vendas = vendas_validas(ctx["frames"].get("vendas", pd.DataFrame()))
    produtos = ctx["frames"].get("produtos", pd.DataFrame())
    estoque = ctx["frames"].get("estoque", pd.DataFrame())
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Produtos cadastrados", produtos["COD_PRODUTO"].nunique() if not produtos.empty else 0)
    col2.metric("Produtos vendidos", vendas["COD_PRODUTO"].nunique() if not vendas.empty else 0)
    col3.metric("Produtos com estoque zerado", int((estoque["ESTOQUE_TOTAL"] == 0).sum()) if not estoque.empty else 0)
    col4.metric("Produtos com estoque negativo", int((estoque["ESTOQUE_TOTAL"] < 0).sum()) if not estoque.empty else 0)
    tem_produto_venda = not vendas.empty and "COD_PRODUTO" in vendas and vendas["COD_PRODUTO"].astype(str).str.strip().any()
    abc = calculate_abc(vendas) if tem_produto_venda else pd.DataFrame()
    if not abc.empty:
        st.subheader("Curva ABC recalculada pelo periodo filtrado")
        if not estoque.empty:
            abc = abc.merge(estoque[["COD_PRODUTO", "ESTOQUE_TOTAL"]], on="COD_PRODUTO", how="left")
        st.dataframe(abc, width="stretch", hide_index=True)
    else:
        st.info("A base atual de vendas nao possui codigo de produto por item. Por isso a curva ABC de produtos nao e calculada nesta tela.")
    if not estoque.empty:
        st.subheader("Produtos sem estoque")
        st.dataframe(estoque[estoque["ESTOQUE_TOTAL"] <= 0].head(100), width="stretch", hide_index=True)
    st.subheader("Cadastro de produtos")
    st.dataframe(produtos, width="stretch", hide_index=True)

