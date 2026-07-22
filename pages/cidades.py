from __future__ import annotations

import pandas as pd
import streamlit as st

from services.vendas import vendas_validas
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
    rank = df.groupby("CIDADE").agg(FATURAMENTO=("VALOR_ITEM", "sum"), PEDIDOS=("VENDA", "nunique"), CLIENTES=("COD_CLIENTE", "nunique"), QTDE=("QTDE", "sum")).sort_values("FATURAMENTO", ascending=False).reset_index()
    rank["TICKET_MEDIO"] = rank["FATURAMENTO"] / rank["PEDIDOS"].replace(0, pd.NA)
    st.plotly_chart(bar(rank.head(15), "CIDADE", "FATURAMENTO", "Ranking de cidades"), width="stretch")
    st.dataframe(rank, width="stretch", hide_index=True)

