from __future__ import annotations

import pandas as pd
import streamlit as st

from services.vendas import ranking, vendas_validas
from utils.formatacao import brl
from utils.graficos import bar


def render(ctx: dict) -> None:
    st.title("Comercial")
    vendas = ctx["frames"].get("vendas", pd.DataFrame())
    validas = vendas_validas(vendas)
    if validas.empty:
        st.warning("Nao existem vendas validas para o periodo filtrado.")
        return
    sellers = ranking(vendas, "VENDEDOR", top=50)
    sellers["TICKET_MEDIO"] = sellers["FATURAMENTO"] / sellers["PEDIDOS"].replace(0, pd.NA)
    sellers["META"] = ctx["meta_mensal"] / max(len(sellers), 1)
    sellers["PERCENTUAL_META"] = sellers["FATURAMENTO"] / sellers["META"].replace(0, pd.NA) * 100
    sellers["STATUS"] = pd.cut(
        sellers["PERCENTUAL_META"].fillna(0),
        bins=[-1, 50, 80, 100, 10_000],
        labels=["Critico", "Atencao", "Dentro da meta", "Acima da meta"],
    )
    sellers.insert(0, "Posicao", range(1, len(sellers) + 1))
    st.info("A associacao vendedor-cliente e calculada pelo historico de vendas, pois nao veio diretamente do cadastro de clientes.")
    st.plotly_chart(bar(sellers.head(10), "VENDEDOR", "FATURAMENTO", "Ranking de vendedores"), width="stretch")
    st.dataframe(sellers, width="stretch", hide_index=True)
    st.caption(f"Faturamento total exibido: {brl(sellers['FATURAMENTO'].sum())}")

