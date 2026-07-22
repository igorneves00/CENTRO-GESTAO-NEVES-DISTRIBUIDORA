from __future__ import annotations

import logging
from pathlib import Path

import streamlit as st
import pandas as pd

from pages import alertas, auditoria, atualizacao, cidades, clientes, comercial, configuracoes, estoque, plano_acao, produtos, visao_geral
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

    st.sidebar.markdown("### Filtros")
    min_date = vendas["DATA_VENDA"].dropna().min()
    max_date = vendas["DATA_VENDA"].dropna().max()
    use_date = st.sidebar.checkbox("Filtrar por data", value=False)
    start = end = None
    if use_date:
        start = st.sidebar.date_input("Inicio", min_date.date() if pd.notna(min_date) else None)
        end = st.sidebar.date_input("Fim", max_date.date() if pd.notna(max_date) else None)

    def multiselect(label: str, col: str):
        if col not in vendas:
            return []
        options = sorted([x for x in vendas[col].dropna().unique().tolist() if str(x).strip()])
        return st.sidebar.multiselect(label, options)

    vendedores = multiselect("Vendedor", "VENDEDOR")
    status = multiselect("Status", "STATUS_NORMALIZADO")

    cidade = []
    if "CIDADE" in vendas and vendas["CIDADE"].astype(str).str.strip().any():
        cidade = st.sidebar.multiselect("Cidade", sorted([x for x in vendas["CIDADE"].dropna().unique().tolist() if str(x).strip()]))
    elif not clientes_df.empty and "CIDADE" in clientes_df:
        cidade = st.sidebar.multiselect("Cidade", sorted([x for x in clientes_df["CIDADE"].dropna().unique().tolist() if str(x).strip()]))

    with st.sidebar.expander("Mais filtros"):
        grupos = multiselect("Grupo", "GRUPO")
        fornecedores = multiselect("Fornecedor", "FORNECEDOR")
        produtos_sel = multiselect("Produto", "DESCRICAO_VENDA")
        cod_produtos = multiselect("Codigo", "COD_PRODUTO")
        curva = []
        if not estoque_df.empty and "CURVA" in estoque_df:
            curva = st.multiselect("Curva do cadastro", sorted(estoque_df["CURVA"].dropna().unique().tolist()))
        stock_mode = st.selectbox("Estoque", ["Todos", "Com estoque", "Sem estoque"])

    clear = st.sidebar.button("Limpar filtros", width="stretch")
    refresh = st.sidebar.button("Atualizar dados", width="stretch")

    if clear:
        st.cache_data.clear()
        st.rerun()
    if refresh:
        st.cache_data.clear()
        st.rerun()

    mask = pd.Series(True, index=vendas.index)
    if start:
        mask &= vendas["DATA_VENDA"] >= pd.Timestamp(start)
    if end:
        mask &= vendas["DATA_VENDA"] <= pd.Timestamp(end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    for selected, col in [
        (vendedores, "VENDEDOR"),
        (produtos_sel, "DESCRICAO_VENDA"),
        (cod_produtos, "COD_PRODUTO"),
        (grupos, "GRUPO"),
        (fornecedores, "FORNECEDOR"),
        (status, "STATUS_NORMALIZADO"),
    ]:
        if selected:
            mask &= vendas[col].isin(selected)
    vendas = vendas[mask].copy()

    if cidade and "CIDADE" in vendas:
        vendas = vendas[vendas["CIDADE"].isin(cidade)].copy()
    elif cidade and not clientes_df.empty:
        clientes_df = clientes_df[clientes_df["CIDADE"].isin(cidade)].copy()
        vendas = vendas[vendas["COD_CLIENTE"].isin(clientes_df["COD_CLIENTE"])].copy()

    if curva and not estoque_df.empty:
        estoque_df = estoque_df[estoque_df["CURVA"].isin(curva)].copy()
        vendas = vendas[vendas["COD_PRODUTO"].isin(estoque_df["COD_PRODUTO"])].copy()
    if stock_mode != "Todos" and not estoque_df.empty:
        codes = estoque_df.loc[estoque_df["ESTOQUE_TOTAL"].gt(0) if stock_mode == "Com estoque" else estoque_df["ESTOQUE_TOTAL"].le(0), "COD_PRODUTO"]
        vendas = vendas[vendas["COD_PRODUTO"].isin(codes)].copy()
    out = frames.copy()
    out["vendas"] = vendas
    out["estoque"] = estoque_df
    out["clientes"] = clientes_df
    return out


def main() -> None:
    load_css()
    init_db(DB_PATH)
    st.sidebar.markdown("## Centro de Gestao")
    st.sidebar.caption("Neves Distribuidora")
    logo = PROJECT_ROOT / "assets" / "logo.png"
    if logo.exists():
        st.sidebar.image(str(logo), width="stretch")
    valid_statuses = st.sidebar.multiselect("Status validos para calculo", ["FATURADO", "PAGO", "CANCELADO", "DEVOLVIDO"], default=DEFAULT_VALID_STATUSES)
    raw_frames, metas, relationship = cached_load(tuple(valid_statuses or DEFAULT_VALID_STATUSES))
    frames = apply_global_filters(raw_frames)
    meta_mensal = float(get_config("meta_mensal_empresa", "500000", DB_PATH) or 500000)
    raw_vendas = raw_frames.get("vendas", pd.DataFrame())
    filtered_vendas = frames.get("vendas", pd.DataFrame())
    period_source = filtered_vendas if not filtered_vendas.empty else raw_vendas
    if not period_source.empty and "DATA_VENDA" in period_source:
        dates = pd.to_datetime(period_source["DATA_VENDA"], errors="coerce").dropna()
        period = f"{dates.min().date()} ate {dates.max().date()}" if not dates.empty else "sem datas validas"
    else:
        period = "sem vendas carregadas"
    st.info(f"Registros carregados: {len(raw_vendas):,} | Registros apos filtros: {len(filtered_vendas):,} | Periodo: {period}".replace(",", "."))

    page = st.sidebar.radio(
        "Menu",
        [
            "Visao Geral",
            "Comercial",
            "Clientes",
            "Produtos",
            "Estoque",
            "Cidades",
            "Alertas",
            "Plano de Acao",
            "Adicionar arquivos",
            "Auditoria dos Dados",
            "Configuracoes",
        ],
    )
    context = {"root": PROJECT_ROOT, "db_path": DB_PATH, "frames": frames, "raw_frames": raw_frames, "metas": metas, "relationship": relationship, "meta_mensal": meta_mensal}
    routes = {
        "Visao Geral": visao_geral.render,
        "Comercial": comercial.render,
        "Clientes": clientes.render,
        "Produtos": produtos.render,
        "Estoque": estoque.render,
        "Cidades": cidades.render,
        "Alertas": alertas.render,
        "Plano de Acao": plano_acao.render,
        "Adicionar arquivos": atualizacao.render,
        "Auditoria dos Dados": auditoria.render,
        "Configuracoes": configuracoes.render,
    }
    routes[page](context)


if __name__ == "__main__":
    main()

