from __future__ import annotations

import pandas as pd
import streamlit as st

from services.estoque import estoque_parado
from services.vendas import vendas_validas
from utils.formatacao import brl


def render(ctx: dict) -> None:
    st.title("Estoque")
    estoque = ctx["frames"].get("estoque", pd.DataFrame())
    vendas = vendas_validas(ctx["frames"].get("vendas", pd.DataFrame()))
    if estoque.empty:
        st.warning("Arquivo de estoque ausente.")
        return
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Valor do estoque", brl(estoque["VALOR_ESTOQUE"].sum()))
    col2.metric("Quantidade total", f"{estoque['ESTOQUE_TOTAL'].sum():,.0f}".replace(",", "."))
    col3.metric("Produtos zerados", int((estoque["ESTOQUE_TOTAL"] == 0).sum()))
    col4.metric("Produtos negativos", int((estoque["ESTOQUE_TOTAL"] < 0).sum()))
    parado = estoque_parado(estoque, vendas)
    st.subheader("Estoque parado")
    st.dataframe(parado.sort_values("DIAS_SEM_VENDA", ascending=False, na_position="first"), width="stretch", hide_index=True)
    st.subheader("Estoque critico")
    days = st.number_input("Dias de cobertura desejada", min_value=1, value=30)
    safety = st.number_input("Dias de seguranca", min_value=0, value=7)
    lead = st.number_input("Prazo medio de entrega", min_value=0, value=7)
    if not vendas.empty and "COD_PRODUTO" in vendas and vendas["COD_PRODUTO"].astype(str).str.strip().any() and vendas["QTDE"].fillna(0).sum() > 0:
        period_days = max((vendas["DATA_VENDA"].max() - vendas["DATA_VENDA"].min()).days + 1, 1)
        consumo = vendas.groupby("COD_PRODUTO")["QTDE"].sum() / period_days
        crit = estoque.copy()
        crit["CONSUMO_MEDIO_DIARIO"] = crit["COD_PRODUTO"].map(consumo).fillna(0)
        crit["DIAS_COBERTURA"] = crit["ESTOQUE_TOTAL"] / crit["CONSUMO_MEDIO_DIARIO"].replace(0, pd.NA)
        crit["PONTO_REPOSICAO"] = crit["CONSUMO_MEDIO_DIARIO"] * (lead + safety)
        crit["QUANTIDADE_SUGERIDA"] = ((crit["CONSUMO_MEDIO_DIARIO"] * days) - crit["ESTOQUE_TOTAL"]).clip(lower=0)
        crit["PRIORIDADE"] = "Estoque adequado"
        crit.loc[crit["CONSUMO_MEDIO_DIARIO"].eq(0), "PRIORIDADE"] = "Produto parado"
        crit.loc[(crit["CONSUMO_MEDIO_DIARIO"].gt(0)) & (crit["ESTOQUE_TOTAL"].le(crit["PONTO_REPOSICAO"])), "PRIORIDADE"] = "Compra imediata"
        st.dataframe(crit[["COD_PRODUTO", "DESCRICAO_ESTOQUE", "ESTOQUE_TOTAL", "CONSUMO_MEDIO_DIARIO", "DIAS_COBERTURA", "PONTO_REPOSICAO", "QUANTIDADE_SUGERIDA", "PRIORIDADE"]], width="stretch", hide_index=True)
    else:
        st.warning("A base atual de vendas nao possui produto/quantidade por item. Sugestao automatica de compra por consumo fica limitada.")
        st.write("Produtos zerados ou abaixo de zero")
        st.dataframe(estoque[estoque["ESTOQUE_TOTAL"] <= 0].sort_values("VALOR_ESTOQUE"), width="stretch", hide_index=True)

