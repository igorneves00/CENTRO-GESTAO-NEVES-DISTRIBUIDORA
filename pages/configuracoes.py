from __future__ import annotations

import streamlit as st

from services.database import get_config, set_config


def render(ctx: dict) -> None:
    st.title("Configuracoes")
    current = float(get_config("meta_mensal_empresa", "500000", ctx["db_path"]) or 500000)
    meta = st.number_input("Meta mensal da empresa", min_value=0.0, value=current, step=1000.0)
    if st.button("Salvar configuracoes", type="primary"):
        set_config("meta_mensal_empresa", str(meta), ctx["db_path"])
        st.success("Configuracao salva. Atualize o painel para recalcular.")
    st.write("Status validos iniciais: FATURADO e PAGO. Eles tambem podem ser ajustados no menu lateral.")

