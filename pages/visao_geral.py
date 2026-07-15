from __future__ import annotations

import pandas as pd
import streamlit as st

from services.vendas import daily_revenue, monthly_revenue, ranking, summary_metrics, vendas_validas
from utils.exportacao import dataframe_to_csv_bytes, dataframe_to_excel_bytes
from utils.formatacao import brl, number, pct
from utils.graficos import bar, line


def metric_card(title: str, value: str, note: str = "", status: str = "ok") -> None:
    css = {"ok": "status-ok", "warn": "status-warn", "danger": "status-danger"}.get(status, "status-ok")
    st.markdown(f"<div class='metric-card'><small>{title}</small><h3>{value}</h3><p class='{css}'>{note}</p></div>", unsafe_allow_html=True)


def render(ctx: dict) -> None:
    st.markdown("<h1 class='neves-title'>Centro de Gestao - Neves Distribuidora</h1>", unsafe_allow_html=True)
    frames = ctx["frames"]
    vendas = frames.get("vendas", pd.DataFrame())
    estoque = frames.get("estoque", pd.DataFrame())
    clientes = frames.get("clientes", pd.DataFrame())
    metrics = summary_metrics(vendas, estoque, clientes, ctx["meta_mensal"])

    cols = st.columns(4)
    with cols[0]:
        metric_card("Faturamento", brl(metrics["faturamento"]), f"{pct(metrics['percentual_meta'])} da meta", "ok" if metrics["percentual_meta"] >= 100 else "warn")
    with cols[1]:
        metric_card("Meta mensal", brl(metrics["meta_mensal"]), f"Falta {brl(metrics['falta_meta'])}", "ok" if metrics["falta_meta"] == 0 else "warn")
    with cols[2]:
        metric_card("Pedidos", number(metrics["pedidos"]), f"Ticket medio {brl(metrics['ticket_medio'])}", "ok")
    with cols[3]:
        metric_card("Clientes atendidos", number(metrics["clientes_atendidos"]), f"{number(metrics['clientes_inativos'])} inativos", "warn" if metrics["clientes_inativos"] else "ok")

    cols = st.columns(4)
    with cols[0]:
        metric_card("Produtos vendidos", number(metrics["produtos_vendidos"]), "Soma da QTDE")
    with cols[1]:
        metric_card("Produtos sem estoque", number(metrics["produtos_sem_estoque"]), "Estoque <= 0", "danger" if metrics["produtos_sem_estoque"] else "ok")
    with cols[2]:
        metric_card("Valor total do estoque", brl(metrics["valor_estoque"]), "Deposito + balcao")
    with cols[3]:
        validas = vendas_validas(vendas)
        dias = validas["DATA_VENDA"].dt.date.nunique() if not validas.empty else 0
        proj = metrics["faturamento"] if dias == 0 else metrics["faturamento"] / max(dias, 1) * 30
        metric_card("Projecao de faturamento", brl(proj), "Baseada na media diaria")

    st.subheader("Resumo do Gestor")
    frases = []
    if not vendas.empty:
        top_vendedor = ranking(vendas, "VENDEDOR", top=1)
        if not top_vendedor.empty:
            frases.append(f"O vendedor {top_vendedor.iloc[0]['VENDEDOR']} apresentou o maior faturamento no periodo filtrado.")
        if metrics["clientes_inativos"]:
            frases.append(f"Existem {metrics['clientes_inativos']} clientes sem comprar ha 60 dias ou mais.")
        if metrics["produtos_sem_estoque"]:
            frases.append(f"Existem {metrics['produtos_sem_estoque']} produtos com estoque zerado ou negativo.")
        frases.append(f"O faturamento do periodo filtrado e {brl(metrics['faturamento'])}.")
    if not frases:
        frases.append("Nao existem dados suficientes para gerar um resumo confiavel.")
    for frase in frases:
        st.info(frase)

    tab1, tab2, tab3 = st.tabs(["Graficos", "Rankings", "Diagnostico"])
    with tab1:
        d = daily_revenue(vendas)
        m = monthly_revenue(vendas)
        if not d.empty:
            st.plotly_chart(line(d, "DATA", "FATURAMENTO", "Faturamento diario"), width="stretch")
        if not m.empty:
            st.plotly_chart(bar(m, "MES", "FATURAMENTO", "Faturamento mensal"), width="stretch")
    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            rv = ranking(vendas, "VENDEDOR")
            st.dataframe(rv, width="stretch", hide_index=True)
        with col2:
            rg = ranking(vendas, "GRUPO")
            st.dataframe(rg, width="stretch", hide_index=True)
        rc = ranking(vendas, "RAZAO_SOCIAL")
        st.dataframe(rc, width="stretch", hide_index=True)
    with tab3:
        st.write("Relacionamentos")
        st.json(ctx["relationship"])
        st.write("Arquivos")
        st.dataframe(pd.DataFrame(ctx["metas"]).T, width="stretch")

    st.download_button("Exportar vendas filtradas CSV", dataframe_to_csv_bytes(vendas), "vendas_filtradas.csv", "text/csv")
    st.download_button("Exportar vendas filtradas Excel", dataframe_to_excel_bytes(vendas), "vendas_filtradas.xlsx")

