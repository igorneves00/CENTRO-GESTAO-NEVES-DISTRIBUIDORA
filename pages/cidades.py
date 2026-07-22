from __future__ import annotations

import pandas as pd
import streamlit as st

from services.vendas import vendas_validas
from services.vendas import compare_periods
from utils.graficos import bar


def render(ctx: dict) -> None:
    st.title("Cidades")
    vendas = vendas_validas(ctx["frames"].get("vendas", pd.DataFrame()))
    clientes = ctx["frames"].get("clientes", pd.DataFrame())
    if vendas.empty:
        st.warning("Sao necessarias vendas para analisar cidades.")
        return
    if "CIDADE" in vendas and vendas["CIDADE"].astype(str).str.strip().any():
        df = vendas.copy()
    elif not clientes.empty and "COD_CLIENTE" in vendas:
        df = vendas.merge(clientes[["COD_CLIENTE", "CIDADE"]], on="COD_CLIENTE", how="left")
    else:
        st.warning("A base atual nao possui cidade suficiente para esta analise.")
        return
    df["CIDADE"] = df["CIDADE"].fillna("Sem cidade")
    cliente_col = "COD_CLIENTE" if "COD_CLIENTE" in df and df["COD_CLIENTE"].astype(str).str.strip().any() else "RAZAO_SOCIAL"
    rank = df.groupby("CIDADE").agg(FATURAMENTO=("VALOR_ITEM", "sum"), PEDIDOS=("VENDA", "nunique"), CLIENTES=(cliente_col, "nunique"), QTDE=("QTDE", "sum")).sort_values("FATURAMENTO", ascending=False).reset_index()
    rank["TICKET_MEDIO"] = rank["FATURAMENTO"] / rank["PEDIDOS"].replace(0, pd.NA)
    col1, col2, col3 = st.columns(3)
    if not rank.empty:
        col1.metric("Cidade lider", str(rank.iloc[0]["CIDADE"]))
        col2.metric("Maior ticket", str(rank.sort_values("TICKET_MEDIO", ascending=False).iloc[0]["CIDADE"]))
        col3.metric("Cidades atendidas", len(rank))
    st.plotly_chart(bar(rank.head(15), "CIDADE", "FATURAMENTO", "Ranking de cidades"), width="stretch")
    st.dataframe(rank, width="stretch", hide_index=True)
    comparativo = compare_periods(df, "CIDADE")
    if not comparativo.empty:
        st.subheader("Cidades que cresceram e cairam")
        col_a, col_b = st.columns(2)
        with col_a:
            st.write("Crescimento")
            st.dataframe(comparativo.sort_values("VARIACAO", ascending=False).head(10), width="stretch", hide_index=True)
        with col_b:
            st.write("Queda")
            st.dataframe(comparativo[comparativo["ANTERIOR"] > 0].sort_values("VARIACAO").head(10), width="stretch", hide_index=True)

