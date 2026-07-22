from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.formatacao import brl


def render(ctx: dict) -> None:
    st.title("Compras")
    compras = ctx["frames"].get("compras", pd.DataFrame())
    fornecedores = ctx["frames"].get("fornecedores", pd.DataFrame())
    estoque = ctx["frames"].get("estoque", pd.DataFrame())
    metas = ctx.get("metas", {})

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Registros de compras", len(compras))
    col2.metric("Fornecedores", len(fornecedores))
    col3.metric("Produtos zerados", int((estoque["ESTOQUE_TOTAL"] <= 0).sum()) if not estoque.empty else 0)
    col4.metric("Valor do estoque", brl(estoque["VALOR_ESTOQUE"].sum()) if not estoque.empty else brl(0))

    if not compras.empty:
        st.subheader("Compras carregadas")
        st.dataframe(compras, width="stretch", hide_index=True)
    else:
        st.warning("Nenhum arquivo real de compras foi carregado. A pagina nao usa dados ficticios.")

    if not fornecedores.empty:
        st.subheader("Fornecedores carregados")
        st.dataframe(fornecedores, width="stretch", hide_index=True)
    else:
        st.info("Nenhum arquivo real de fornecedores foi carregado.")

    st.subheader("Prioridade de reposicao pelo estoque atual")
    if estoque.empty:
        st.warning("Arquivo de estoque ausente. Nao ha base para sugerir prioridades.")
        return
    prioridade = estoque.copy()
    prioridade["PRIORIDADE"] = "Monitorar"
    prioridade.loc[prioridade["ESTOQUE_TOTAL"] <= 0, "PRIORIDADE"] = "Conferir compra"
    prioridade = prioridade.sort_values(["ESTOQUE_TOTAL", "VALOR_ESTOQUE"], ascending=[True, False])
    st.dataframe(
        prioridade[["COD_PRODUTO", "DESCRICAO_ESTOQUE", "CURVA", "ESTOQUE_TOTAL", "CUSTO", "VALOR_ESTOQUE", "PRIORIDADE"]].head(80),
        width="stretch",
        hide_index=True,
    )

    st.subheader("Status dos arquivos")
    rows = []
    for key in ["compras", "fornecedores"]:
        meta = metas.get(key, {})
        rows.append(
            {
                "arquivo": key,
                "situacao": meta.get("situacao_leitura", "AUSENTE"),
                "linhas": meta.get("linhas_lidas", 0),
                "erros": "; ".join(meta.get("erros", [])) if isinstance(meta.get("erros", []), list) else meta.get("erros", ""),
            }
        )
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
