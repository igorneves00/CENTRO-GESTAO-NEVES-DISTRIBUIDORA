from __future__ import annotations

import pandas as pd
import streamlit as st

from services.vendas import vendas_validas
from services.vendas import abc_by_group, compare_periods
from utils.formatacao import brl


def render(ctx: dict) -> None:
    st.title("Clientes")
    vendas = vendas_validas(ctx["frames"].get("vendas", pd.DataFrame()))
    clientes = ctx["frames"].get("clientes", pd.DataFrame())
    if clientes.empty:
        st.warning("Cadastro de clientes ausente.")
        return
    ref = max(pd.to_datetime(clientes["ULTIMA_COMPRA"], errors="coerce").max(), vendas["DATA_VENDA"].max() if not vendas.empty else pd.NaT)
    clientes = clientes.copy()
    clientes["DIAS_SEM_COMPRAR"] = (ref - pd.to_datetime(clientes["ULTIMA_COMPRA"], errors="coerce")).dt.days
    clientes["STATUS"] = pd.cut(
        clientes["DIAS_SEM_COMPRAR"].fillna(99999),
        bins=[-1, 30, 59, 89, 999999],
        labels=["Ativo", "Em risco", "Inativo", "Muito inativo"],
    )
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de clientes", clientes["COD_CLIENTE"].nunique())
    col2.metric("Ativos", int((clientes["STATUS"] == "Ativo").sum()))
    col3.metric("Em risco", int((clientes["STATUS"] == "Em risco").sum()))
    col4.metric("Inativos", int(clientes["STATUS"].isin(["Inativo", "Muito inativo"]).sum()))
    if not vendas.empty:
        key = "COD_CLIENTE"
        if "COD_CLIENTE" not in vendas or not vendas["COD_CLIENTE"].astype(str).str.strip().any():
            key = "RAZAO_SOCIAL"
        rank = vendas.groupby(key).agg(FATURAMENTO=("VALOR_ITEM", "sum"), PEDIDOS=("VENDA", "nunique"), QTDE=("QTDE", "sum")).reset_index()
        if key == "COD_CLIENTE":
            rank = rank.merge(clientes, on="COD_CLIENTE", how="left")
        elif "CIDADE" in vendas:
            cidades = vendas.groupby(key)["CIDADE"].agg(lambda s: s.dropna().iloc[0] if not s.dropna().empty else "").reset_index()
            rank = rank.merge(cidades, on=key, how="left")
        st.subheader("Ranking de clientes")
        st.dataframe(rank.sort_values("FATURAMENTO", ascending=False), width="stretch", hide_index=True)
        st.subheader("Clientes para acao comercial")
        curva = abc_by_group(vendas, key)
        if not curva.empty:
            st.write("Curva ABC de clientes")
            st.dataframe(curva.head(30), width="stretch", hide_index=True)
        queda = compare_periods(vendas, key)
        if not queda.empty:
            queda = queda[(queda["ANTERIOR"] > 0) & (queda["VARIACAO"] < 0)].sort_values("VARIACAO").head(20)
            st.write("Clientes que reduziram compra")
            st.dataframe(queda, width="stretch", hide_index=True)
        inativos = clientes[clientes["STATUS"].isin(["Inativo", "Muito inativo"])].sort_values("DIAS_SEM_COMPRAR", ascending=False)
        st.write("Clientes inativos do cadastro")
        st.dataframe(inativos[["COD_CLIENTE", "RAZAO_SOCIAL", "CIDADE", "TELEFONE", "ULTIMA_COMPRA", "DIAS_SEM_COMPRAR", "STATUS"]].head(50), width="stretch", hide_index=True)
        selected = st.selectbox("Ficha individual", rank[key].astype(str).tolist())
        ficha = rank[rank[key].astype(str) == selected].iloc[0]
        st.write(f"**Cliente:** {ficha.get('RAZAO_SOCIAL', selected)}")
        st.write(f"**Cidade:** {ficha.get('CIDADE', '')} | **Telefone:** {ficha.get('TELEFONE', '')}")
        st.write(f"**Faturamento:** {brl(ficha['FATURAMENTO'])} | **Pedidos:** {int(ficha['PEDIDOS'])}")
        message = "Ola, tudo bem? Aqui e da Neves Distribuidora. Notamos que ja faz algum tempo desde sua ultima compra. Separei algumas oportunidades nos produtos que voce costuma utilizar. Posso enviar as condicoes?"
        st.text_area("Mensagem de WhatsApp", message, height=120)
    else:
        st.dataframe(clientes, width="stretch", hide_index=True)

