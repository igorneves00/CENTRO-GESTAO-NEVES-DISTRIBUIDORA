from __future__ import annotations

import pandas as pd
import streamlit as st

from services.vendas import faturamento_sem_duplicar_total_pedido, vendas_validas
from utils.formatacao import brl


def render(ctx: dict) -> None:
    st.title("Auditoria dos Dados")
    raw_frames = ctx.get("raw_frames", {})
    frames = ctx.get("frames", {})
    metas = ctx.get("metas", {})
    vendas_raw = raw_frames.get("vendas", pd.DataFrame())
    vendas_filtradas = frames.get("vendas", pd.DataFrame())

    col1, col2, col3 = st.columns(3)
    col1.metric("Registros totais de vendas", len(vendas_raw))
    col2.metric("Registros apos filtros", len(vendas_filtradas))
    col3.metric("Arquivos monitorados", len(metas))

    validas_raw = vendas_validas(vendas_raw)
    faturamento_dashboard = faturamento_sem_duplicar_total_pedido(validas_raw)
    faturamento_arquivo = float(metas.get("vendas", {}).get("faturamento_arquivo", 0) or 0)
    st.subheader("Conferencia de faturamento")
    st.write(f"Faturamento direto do arquivo tratado: **{brl(faturamento_arquivo)}**")
    st.write(f"Faturamento usado no dashboard sem filtros: **{brl(faturamento_dashboard)}**")
    if round(faturamento_arquivo, 2) == round(faturamento_dashboard, 2):
        st.success("Os valores conferem quando nao ha filtros selecionados.")
    else:
        st.error(f"Diferenca encontrada: {brl(faturamento_dashboard - faturamento_arquivo)}")

    st.subheader("Confianca da base")
    col_a, col_b, col_c, col_d = st.columns(4)
    vendas_meta = metas.get("vendas", {})
    col_a.metric("Vendas", vendas_meta.get("situacao_leitura", ""))
    col_b.metric("Faturamento", "OK" if round(faturamento_arquivo, 2) == round(faturamento_dashboard, 2) else "Verificar")
    col_c.metric("Compras", metas.get("compras", {}).get("situacao_leitura", "AUSENTE"))
    col_d.metric("Fornecedores", metas.get("fornecedores", {}).get("situacao_leitura", "AUSENTE"))
    if not vendas_raw.empty and not vendas_raw.get("COD_PRODUTO", pd.Series(dtype=str)).astype(str).str.strip().any():
        st.warning("A base atual de vendas nao contem produto/codigo do produto. Analises de produtos ficam limitadas.")

    st.subheader("Arquivos utilizados")
    rows = []
    for tipo, meta in metas.items():
        rows.append(
            {
                "tipo": tipo,
                "arquivo": meta.get("arquivo", ""),
                "situacao": meta.get("situacao_leitura", ""),
                "linhas_originais": meta.get("linhas_originais", 0),
                "linhas_lidas": meta.get("linhas_lidas", 0),
                "validas": meta.get("registros_validos", 0),
                "descartadas": meta.get("linhas_descartadas", meta.get("registros_invalidos", 0)),
                "menor_data": meta.get("menor_data", ""),
                "maior_data": meta.get("maior_data", ""),
                "erros": "; ".join(meta.get("erros", [])) if isinstance(meta.get("erros", []), list) else meta.get("erros", ""),
            }
        )
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    st.subheader("Colunas reconhecidas e ausentes")
    selected = st.selectbox("Arquivo", list(metas.keys()))
    meta = metas.get(selected, {})
    st.write("Colunas reconhecidas")
    st.write(meta.get("colunas_reconhecidas", meta.get("colunas_originais", [])))
    st.write("Colunas obrigatorias ausentes")
    missing = meta.get("colunas_obrigatorias_ausentes", [])
    if missing:
        st.error(", ".join(missing))
    else:
        st.success("Nenhuma coluna obrigatoria ausente.")

    st.subheader("Linhas descartadas")
    motivos = meta.get("motivos_descarte", {})
    if motivos:
        st.dataframe(pd.DataFrame([{"motivo": k, "linhas": v} for k, v in motivos.items()]), width="stretch", hide_index=True)
    else:
        st.info("Nenhuma linha descartada nesta carga.")

    st.subheader("Ultima atualizacao")
    data_dir = ctx["root"] / "dados"
    files = list(data_dir.glob("*.csv"))
    if files:
        last = max(files, key=lambda p: p.stat().st_mtime)
        st.write(f"{last.name}: {pd.Timestamp.fromtimestamp(last.stat().st_mtime)}")
