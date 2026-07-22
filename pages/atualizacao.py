from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
import streamlit as st

from services.importacao import import_initial_data
from services.tratamento_dados import load_clientes, load_estoque, load_generic_csv, load_produtos, load_vendas


def render(ctx: dict) -> None:
    st.title("Adicionar arquivos")
    st.caption("Esta e a unica area de upload do sistema.")
    tipo = st.selectbox("Tipo de arquivo", ["Vendas", "Estoque", "Produtos", "Clientes", "Compras", "Fornecedores", "Metas"])
    modo = st.radio("Modo de importacao", ["Substituir os dados", "Acrescentar novos registros"], horizontal=True)
    uploaded = st.file_uploader("Enviar arquivo CSV", type=["csv"])
    preview = st.checkbox("Visualizar previa", value=True)
    validate = st.checkbox("Validar antes de importar", value=True)
    if uploaded and preview:
        preview_path = ctx["root"] / "data" / "_preview_upload.csv"
        preview_path.write_bytes(uploaded.getvalue())
        loader = {
            "Vendas": load_vendas,
            "Estoque": load_estoque,
            "Produtos": load_produtos,
            "Clientes": load_clientes,
            "Compras": load_generic_csv,
            "Fornecedores": load_generic_csv,
            "Metas": load_generic_csv,
        }[tipo]
        try:
            df_preview, meta_preview = loader(preview_path)
            dates = pd.Series(dtype="datetime64[ns]")
            for col in ["DATA_VENDA", "DATA", "ULTIMA_COMPRA"]:
                if col in df_preview:
                    dates = pd.to_datetime(df_preview[col], errors="coerce").dropna()
                    if not dates.empty:
                        break
            conferencia = pd.DataFrame(
                [
                    {
                        "nome do arquivo": uploaded.name,
                        "total de linhas": meta_preview.get("linhas_lidas", len(df_preview)),
                        "colunas identificadas": ", ".join(map(str, df_preview.columns)),
                        "periodo dos dados": f"{dates.min().date()} a {dates.max().date()}" if not dates.empty else "",
                        "situacao da leitura": meta_preview.get("situacao_leitura", "OK"),
                        "erros encontrados": "; ".join(meta_preview.get("erros", [])),
                    }
                ]
            )
            st.dataframe(conferencia, width="stretch", hide_index=True)
        except Exception as exc:
            st.error(f"Erro ao validar {uploaded.name}: {type(exc).__name__}: {exc}")
        finally:
            if preview_path.exists():
                preview_path.unlink()
    if uploaded and st.button("Importar arquivo", type="primary"):
        target_names = {
            "Vendas": "vendas 01.13.csv",
            "Estoque": "estoque 13.07.26.csv",
            "Produtos": "produtos 13.07.26.csv",
            "Clientes": "Listagem de clientes 13.07.26.csv",
            "Compras": "compras.csv",
            "Fornecedores": "fornecedores.csv",
            "Metas": "metas.csv",
        }
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

