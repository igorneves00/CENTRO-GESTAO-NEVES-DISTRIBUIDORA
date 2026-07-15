from __future__ import annotations

import pandas as pd
import streamlit as st

from services.vendas import vendas_validas
from utils.graficos import bar


def render(ctx: dict) -> None:
    st.title("Cidades")
    vendas = vendas_validas(ctx["frames"].get("vendas", pd.DataFrame()))
    clientes = ctx["frames"].get("clientes", pd.DataFrame())
    if vendas.empty or clientes.empty:
        st.warning("Sao necessarios vendas e clientes para analisar cidades.")
        return
    df = vendas.merge(clientes[["COD_CLIENTE", "CIDADE"]], on="COD_CLIENTE", how="left")
    df["CIDADE"] = df["CIDADE"].fillna("Sem correspondencia")
    rank = df.groupby("CIDADE").agg(FATURAMENTO=("VALOR_ITEM", "sum"), PEDIDOS=("VENDA", "nunique"), CLIENTES=("COD_CLIENTE", "nunique"), QTDE=("QTDE", "sum")).sort_values("FATURAMENTO", ascending=False).reset_index()
    rank["TICKET_MEDIO"] = rank["FATURAMENTO"] / rank["PEDIDOS"].replace(0, pd.NA)
    st.plotly_chart(bar(rank.head(15), "CIDADE", "FATURAMENTO", "Ranking de cidades"), width="stretch")
    st.dataframe(rank, width="stretch", hide_index=True)

