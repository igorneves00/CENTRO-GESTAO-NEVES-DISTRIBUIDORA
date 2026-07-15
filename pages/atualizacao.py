from __future__ import annotations

import shutil

import pandas as pd
import streamlit as st

from services.importacao import import_initial_data


def render(ctx: dict) -> None:
    st.title("Atualizacao de Dados")
    st.caption("Esta e a unica area de upload do sistema.")
    tipo = st.selectbox("Tipo de arquivo", ["Vendas", "Estoque", "Produtos", "Clientes", "Metas", "Compras futuramente", "Fornecedores futuramente", "Cotacoes futuramente"])
    modo = st.radio("Modo de importacao", ["Substituir os dados", "Acrescentar novos registros"], horizontal=True)
    uploaded = st.file_uploader("Enviar arquivo CSV", type=["csv"])
    preview = st.checkbox("Visualizar previa", value=True)
    validate = st.checkbox("Validar antes de importar", value=True)
    if uploaded and preview:
        st.write({"Nome do arquivo": uploaded.name, "Tamanho": uploaded.size, "Modo": modo, "Validar": validate})
    if uploaded and st.button("Importar arquivo", type="primary"):
        target_names = {
            "Vendas": "vendas 01.13.csv",
            "Estoque": "estoque 13.07.26.csv",
            "Produtos": "produtos 13.07.26.csv",
            "Clientes": "Listagem de clientes 13.07.26.csv",
        }
        if tipo not in target_names:
            st.warning("Este tipo de arquivo esta preparado para uma etapa futura.")
            return
        target = ctx["root"] / "dados" / target_names[tipo]
        with target.open("wb") as f:
            shutil.copyfileobj(uploaded, f)
        frames, metas, relationship = import_initial_data(ctx["root"])
        st.success("Arquivo importado e banco atualizado.")
        st.dataframe(pd.DataFrame(metas).T, width="stretch")
        st.json(relationship)
        st.cache_data.clear()

    st.subheader("Historico e diagnostico da carga atual")
    st.dataframe(pd.DataFrame(ctx["metas"]).T, width="stretch")
    st.json(ctx["relationship"])
    if st.button("Reprocessar arquivos atuais"):
        frames, metas, relationship = import_initial_data(ctx["root"])
        st.success("Arquivos reprocessados no SQLite.")
        st.dataframe(pd.DataFrame(metas).T, width="stretch")
        st.json(relationship)
        st.cache_data.clear()

