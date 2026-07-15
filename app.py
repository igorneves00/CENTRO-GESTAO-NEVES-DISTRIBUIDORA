from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import streamlit as st

from pages import alertas, atualizacao, cidades, clientes, comercial, compras, configuracoes, estoque, inteligencia, plano_acao, produtos, visao_geral
from services.database import get_config, init_db
from services.tratamento_dados import DEFAULT_VALID_STATUSES, build_relationship_diagnostics, load_all_data

PROJECT_ROOT = Path(__file__).parent
DB_PATH = PROJECT_ROOT / "data" / "neves_gestao.db"
LOG_PATH = PROJECT_ROOT / "logs" / "app.log"
LOG_PATH.parent.mkdir(exist_ok=True)
logging.basicConfig(filename=LOG_PATH, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


st.set_page_config(page_title="Centro de Gestao - Neves Distribuidora", page_icon="ND", layout="wide")


def load_css() -> None:
    css = PROJECT_ROOT / "assets" / "style.css"
    if css.exists():
        st.markdown(f"<style>{css.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def cached_load(valid_statuses: tuple[str, ...]):
    frames, metas = load_all_data(PROJECT_ROOT / "dados", list(valid_statuses))
    relationship = build_relationship_diagnostics(frames)
    return frames, metas, relationship


def apply_global_filters(frames: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    vendas = frames.get("vendas", pd.DataFrame()).copy()
    estoque_df = frames.get("estoque", pd.DataFrame()).copy()
    clientes_df = frames.get("clientes", pd.DataFrame()).copy()
    if vendas.empty:
        return frames

    st.sidebar.markdown("### Filtros globais")
    min_date = vendas["DATA_VENDA"].dropna().min()
    max_date = vendas["DATA_VENDA"].dropna().max()
    start = st.sidebar.date_input("Data inicial", min_date.date() if pd.notna(min_date) else None)
    end = st.sidebar.date_input("Data final", max_date.date() if pd.notna(max_date) else None)

    def multiselect(label: str, col: str):
        if col not in vendas:
            return []
        options = sorted([x for x in vendas[col].dropna().unique().tolist() if str(x).strip()])
        return st.sidebar.multiselect(label, options)

    vendedores = multiselect("Vendedor", "VENDEDOR")
    clientes_sel = multiselect("Cliente", "RAZAO_SOCIAL")
    produtos_sel = multiselect("Produto", "DESCRICAO_VENDA")
    cod_produtos = multiselect("Codigo do produto", "COD_PRODUTO")
    grupos = multiselect("Grupo", "GRUPO")
    fornecedores = multiselect("Fornecedor", "FORNECEDOR")
    status = multiselect("Status da venda", "STATUS_NORMALIZADO")
    curva = []
    if not estoque_df.empty and "CURVA" in estoque_df:
        curva = st.sidebar.multiselect("Curva ABC do cadastro", sorted(estoque_df["CURVA"].dropna().unique().tolist()))
    stock_mode = st.sidebar.selectbox("Produto com estoque", ["Todos", "Com estoque", "Sem estoque"])
    inactivity = st.sidebar.selectbox("Faixa de inatividade", ["Todas", "Ate 30 dias", "31 a 59 dias", "60 a 89 dias", "90 dias ou mais"])

    col_a, col_b = st.sidebar.columns(2)
    apply = col_a.button("Aplicar filtros", width="stretch")
    clear = col_b.button("Limpar filtros", width="stretch")
    st.sidebar.button("Comparar periodo anterior", width="stretch")
    st.sidebar.button("Atualizar painel", width="stretch")

    if clear:
        st.cache_data.clear()
        st.rerun()
    if apply or True:
        mask = pd.Series(True, index=vendas.index)
        if start:
            mask &= vendas["DATA_VENDA"] >= pd.Timestamp(start)
        if end:
            mask &= vendas["DATA_VENDA"] <= pd.Timestamp(end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        for selected, col in [
            (vendedores, "VENDEDOR"),
            (clientes_sel, "RAZAO_SOCIAL"),
            (produtos_sel, "DESCRICAO_VENDA"),
            (cod_produtos, "COD_PRODUTO"),
            (grupos, "GRUPO"),
            (fornecedores, "FORNECEDOR"),
            (status, "STATUS_NORMALIZADO"),
        ]:
            if selected:
                mask &= vendas[col].isin(selected)
        vendas = vendas[mask].copy()

    if curva and not estoque_df.empty:
        estoque_df = estoque_df[estoque_df["CURVA"].isin(curva)].copy()
        vendas = vendas[vendas["COD_PRODUTO"].isin(estoque_df["COD_PRODUTO"])].copy()
    if stock_mode != "Todos" and not estoque_df.empty:
        codes = estoque_df.loc[estoque_df["ESTOQUE_TOTAL"].gt(0) if stock_mode == "Com estoque" else estoque_df["ESTOQUE_TOTAL"].le(0), "COD_PRODUTO"]
        vendas = vendas[vendas["COD_PRODUTO"].isin(codes)].copy()
    if inactivity != "Todas" and not clientes_df.empty and "ULTIMA_COMPRA" in clientes_df:
        ref = vendas["DATA_VENDA"].max() if not vendas.empty else pd.Timestamp.today()
        days = (ref - pd.to_datetime(clientes_df["ULTIMA_COMPRA"], errors="coerce")).dt.days
        ranges = {
            "Ate 30 dias": days <= 30,
            "31 a 59 dias": (days >= 31) & (days <= 59),
            "60 a 89 dias": (days >= 60) & (days <= 89),
            "90 dias ou mais": days >= 90,
        }
        clientes_df = clientes_df[ranges[inactivity]].copy()
        vendas = vendas[vendas["COD_CLIENTE"].isin(clientes_df["COD_CLIENTE"])].copy()

    out = frames.copy()
    out["vendas"] = vendas
    out["estoque"] = estoque_df
    out["clientes"] = clientes_df
    return out


def main() -> None:
    load_css()
    init_db(DB_PATH)
    st.sidebar.markdown("## Neves Distribuidora")
    st.sidebar.caption("Centro de Gestao")
    logo = PROJECT_ROOT / "assets" / "logo.png"
    if logo.exists():
        st.sidebar.image(str(logo), width="stretch")
    valid_statuses = st.sidebar.multiselect("Status validos para calculo", ["FATURADO", "PAGO", "CANCELADO", "DEVOLVIDO"], default=DEFAULT_VALID_STATUSES)
    frames, metas, relationship = cached_load(tuple(valid_statuses or DEFAULT_VALID_STATUSES))
    frames = apply_global_filters(frames)
    meta_mensal = float(get_config("meta_mensal_empresa", "500000", DB_PATH) or 500000)

    page = st.sidebar.radio(
        "Menu",
        [
            "Visao Geral",
            "Comercial",
            "Clientes",
            "Produtos",
            "Estoque",
            "Cidades",
            "Compras",
            "Inteligencia",
            "Alertas",
            "Plano de Acao",
            "Atualizacao de Dados",
            "Configuracoes",
        ],
    )
    context = {"root": PROJECT_ROOT, "db_path": DB_PATH, "frames": frames, "metas": metas, "relationship": relationship, "meta_mensal": meta_mensal}
    routes = {
        "Visao Geral": visao_geral.render,
        "Comercial": comercial.render,
        "Clientes": clientes.render,
        "Produtos": produtos.render,
        "Estoque": estoque.render,
        "Cidades": cidades.render,
        "Compras": compras.render,
        "Inteligencia": inteligencia.render,
        "Alertas": alertas.render,
        "Plano de Acao": plano_acao.render,
        "Atualizacao de Dados": atualizacao.render,
        "Configuracoes": configuracoes.render,
    }
    routes[page](context)


if __name__ == "__main__":
    main()

