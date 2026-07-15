from __future__ import annotations

from pathlib import Path

import pandas as pd

from services.database import init_db, replace_table, write_import_history
from services.tratamento_dados import build_relationship_diagnostics, load_all_data


def import_initial_data(project_root: Path, valid_statuses: list[str] | None = None) -> tuple[dict[str, pd.DataFrame], dict[str, dict], dict]:
    init_db(project_root / "data" / "neves_gestao.db")
    frames, metas = load_all_data(project_root / "dados", valid_statuses)
    for name, df in frames.items():
        if not df.empty:
            replace_table(name, df, project_root / "data" / "neves_gestao.db")
    relationship = build_relationship_diagnostics(frames)
    history = []
    for name, meta in metas.items():
        period = ""
        if name == "vendas" and not frames[name].empty:
            dates = frames[name]["DATA_VENDA"].dropna()
            if not dates.empty:
                period = f"{dates.min().date()} a {dates.max().date()}"
        history.append(
            {
                "tipo": name,
                "arquivo": meta.get("arquivo", ""),
                "linhas": int(meta.get("linhas_lidas", 0) or meta.get("linhas_originais", 0) or 0),
                "registros_validos": int(meta.get("registros_validos", meta.get("linhas_lidas", 0)) or 0),
                "registros_invalidos": int(meta.get("registros_invalidos", 0) or 0),
                "duplicidades": int(meta.get("duplicidades", 0) or 0),
                "periodo": period,
                "erros_relacionamento": str(relationship),
            }
        )
    write_import_history(history, project_root / "data" / "neves_gestao.db")
    return frames, metas, relationship

