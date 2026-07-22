from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from utils.formatacao import clean_text, normalize_column_name, only_digits_code, parse_date_series, parse_decimal_series

ENCODINGS = ("utf-8", "utf-8-sig", "latin1", "cp1252")
SEPARATORS = (";", ",")
DEFAULT_VALID_STATUSES = ["FATURADO", "PAGO"]


def detect_encoding(path: Path) -> str:
    for encoding in ENCODINGS:
        try:
            path.read_text(encoding=encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    return "latin1"


def read_csv_flexible(path: Path, header: int | None = 0) -> tuple[pd.DataFrame, dict]:
    attempts = []
    best: tuple[pd.DataFrame, dict] | None = None
    for encoding in ENCODINGS:
        for sep in SEPARATORS:
            try:
                df = pd.read_csv(path, sep=sep, encoding=encoding, header=header, dtype=str, engine="python")
                meta = {
                    "arquivo": path.name,
                    "encoding": encoding,
                    "separador": sep,
                    "linhas_originais": len(df),
                    "colunas_originais": list(map(str, df.columns)),
                    "tentativas_leitura": attempts.copy(),
                    "situacao_leitura": "OK",
                }
                if best is None or len(df.columns) > len(best[0].columns):
                    best = (df, meta)
            except Exception as exc:
                attempts.append(f"{encoding}/{sep}: {type(exc).__name__}: {exc}")
    if best is None:
        raise ValueError(f"Nao foi possivel ler {path.name}. Tentativas: {' | '.join(attempts)}")
    best[1]["tentativas_leitura"] = attempts
    return best


def find_header_row(path: Path, required_terms: list[str]) -> int:
    encoding = detect_encoding(path)
    lines = path.read_text(encoding=encoding, errors="replace").splitlines()
    normalized_terms = [normalize_column_name(term) for term in required_terms]
    for idx, line in enumerate(lines):
        normalized_line = normalize_column_name(line)
        if all(term in normalized_line for term in normalized_terms):
            return idx
    return 0


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [normalize_column_name(col) for col in df.columns]
    df = df.loc[:, ~df.columns.str.match(r"^UNNAMED")]
    df = df.dropna(axis=1, how="all")
    return df


def get_column(df: pd.DataFrame, column: str) -> pd.Series:
    if column in df.columns:
        return df[column]
    return pd.Series([""] * len(df), index=df.index, dtype="string")


def require_columns(df: pd.DataFrame, required: list[str], meta: dict) -> None:
    missing = [col for col in required if col not in df.columns]
    meta["colunas_reconhecidas"] = list(df.columns)
    meta["colunas_obrigatorias_ausentes"] = missing
    if missing:
        meta["situacao_leitura"] = "ATENCAO"
        meta["erros"] = [f"Coluna obrigatoria ausente: {col}" for col in missing]
    else:
        meta.setdefault("erros", [])


def add_discard_reasons(df: pd.DataFrame) -> pd.DataFrame:
    reasons = []
    for _, row in df.iterrows():
        reason = []
        if pd.isna(row.get("DATA_VENDA")):
            reason.append("data invalida")
        if not bool(row.get("VENDA_VALIDA", False)):
            reason.append("status fora dos calculos")
        if pd.isna(row.get("VALOR_ITEM")):
            reason.append("valor invalido")
        reasons.append("; ".join(reason))
    out = df.copy()
    out["MOTIVO_DESCARTE"] = reasons
    return out


def load_vendas(path: Path, valid_statuses: list[str] | None = None) -> tuple[pd.DataFrame, dict]:
    valid_statuses = valid_statuses or DEFAULT_VALID_STATUSES
    raw, meta = read_csv_flexible(path)
    df = clean_columns(raw)
    if "VENDEDOR" not in df.columns and "DATA" not in df.columns:
        header = find_header_row(path, ["Data", "Numero", "Nome do cliente", "Pagto"])
        raw, meta = read_csv_flexible(path, header=header)
        df = clean_columns(raw)
        meta["cabecalho_linha"] = header + 1
    rename = {
        "DATA": "DATA_VENDA",
        "NUMERO": "VENDA",
        "NOME_DO_CLIENTE": "RAZAO_SOCIAL",
        "PAGTO": "STATUS",
        "VDDR": "VENDEDOR",
        "TOT_VENDA": "TOTAL_VENDA",
        "TOT_FINAL": "VALOR_TOTAL",
        "DESC_PAG": "DESCONTO",
        "RAZAO_SOCIAL": "RAZAO_SOCIAL",
        "DATA_VENDA": "DATA_VENDA",
        "COD_PRODUTO": "COD_PRODUTO",
        "DESCRICAO": "DESCRICAO_VENDA",
        "VALOR_UNITARIO": "VALOR_UNITARIO",
        "VALOR_TOTAL": "VALOR_TOTAL",
        "TOTAL_VENDA": "TOTAL_VENDA",
        "CUSTO_MEDIO": "CUSTO_MEDIO",
        "CUSTO_NF": "CUSTO_NF",
        "CUSTO_CHEIO": "CUSTO_CHEIO",
        "CUSTO_BASE": "CUSTO_BASE",
    }
    df = df.rename(columns=rename)
    if "DATA" in df.columns:
        df = df.rename(columns={"DATA": "DATA_VENDA"})
    require_columns(df, ["DATA_VENDA", "VENDA", "STATUS"], meta)
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].map(clean_text)
    df["COD_CLIENTE"] = get_column(df, "CLIENTE").map(only_digits_code)
    df["COD_PRODUTO"] = get_column(df, "COD_PRODUTO").map(only_digits_code)
    df["VENDA"] = get_column(df, "VENDA").map(only_digits_code)
    df["DATA_VENDA"] = parse_date_series(get_column(df, "DATA_VENDA"))
    money_cols = ["QTDE", "VALOR_UNITARIO", "VALOR_TOTAL", "CUSTO_NF", "CUSTO_MEDIO", "CUSTO_CHEIO", "CUSTO_BASE", "DESCONTO", "TOTAL_VENDA"]
    for col in money_cols:
        if col in df.columns:
            df[col] = parse_decimal_series(df[col])
    if "QTDE" not in df.columns:
        df["QTDE"] = 0
    if "VALOR_UNITARIO" not in df.columns:
        df["VALOR_UNITARIO"] = 0
    if "TOTAL_VENDA" not in df.columns and "VALOR_TOTAL" in df.columns:
        df["TOTAL_VENDA"] = df["VALOR_TOTAL"]
    if "VALOR_TOTAL" not in df.columns or df["VALOR_TOTAL"].isna().all():
        df["VALOR_TOTAL"] = df["QTDE"].fillna(0) * df["VALOR_UNITARIO"].fillna(0)
    df["VALOR_ITEM"] = df["VALOR_TOTAL"].fillna(df["QTDE"].fillna(0) * df["VALOR_UNITARIO"].fillna(0))
    df["STATUS_NORMALIZADO"] = get_column(df, "STATUS").astype(str).str.upper().str.strip()
    df["STATUS_VALIDO"] = df["STATUS_NORMALIZADO"].isin([s.upper() for s in valid_statuses])
    df["VENDA_VALIDA"] = df["STATUS_VALIDO"] & df["DATA_VENDA"].notna() & df["VALOR_ITEM"].notna()
    df["ARQUIVO_ORIGEM"] = path.name
    df["CHAVE_VENDA"] = (
        df["VENDA"].astype(str)
        + "|"
        + df["DATA_VENDA"].astype(str)
        + "|"
        + get_column(df, "RAZAO_SOCIAL").astype(str)
        + "|"
        + df["COD_PRODUTO"].astype(str)
        + "|"
        + df["QTDE"].astype(str)
        + "|"
        + df["VALOR_ITEM"].astype(str)
    )
    for col in ["VENDEDOR", "RAZAO_SOCIAL", "DESCRICAO_VENDA", "UNIDADE", "GRUPO", "FORNECEDOR"]:
        if col not in df.columns:
            df[col] = ""
    df = add_discard_reasons(df)
    meta.update(
        linhas_lidas=len(df),
        registros_validos=int(df["VENDA_VALIDA"].sum()),
        registros_invalidos=int((~df["VENDA_VALIDA"]).sum()),
        linhas_descartadas=int((~df["VENDA_VALIDA"]).sum()),
        motivos_descarte=df.loc[~df["VENDA_VALIDA"], "MOTIVO_DESCARTE"].value_counts().to_dict(),
        quantidade_clientes=int(df["COD_CLIENTE"].replace("", pd.NA).dropna().nunique() or df["RAZAO_SOCIAL"].replace("", pd.NA).dropna().nunique()),
        quantidade_produtos=int(df["COD_PRODUTO"].replace("", pd.NA).dropna().nunique()),
        quantidade_vendas=int(df["VENDA"].replace("", pd.NA).dropna().nunique()),
        menor_data=str(df["DATA_VENDA"].min()) if df["DATA_VENDA"].notna().any() else "",
        maior_data=str(df["DATA_VENDA"].max()) if df["DATA_VENDA"].notna().any() else "",
        datas_invalidas=int(df["DATA_VENDA"].isna().sum()),
        valores_invalidos=int(df[["QTDE", "VALOR_ITEM"]].isna().any(axis=1).sum()),
        duplicidades=int(df.duplicated(subset=["CHAVE_VENDA"]).sum()),
        faturamento_arquivo=float(df.loc[df["VENDA_VALIDA"], "VALOR_ITEM"].fillna(0).sum()),
        status_validos=", ".join(valid_statuses),
    )
    return df, meta


def load_vendas_files(paths: list[Path], valid_statuses: list[str] | None = None) -> tuple[pd.DataFrame, dict]:
    frames = []
    file_metas = []
    errors = []
    for path in paths:
        try:
            df, meta = load_vendas(path, valid_statuses)
            frames.append(df)
            file_metas.append(meta)
        except Exception as exc:
            errors.append(f"{path.name}: {type(exc).__name__}: {exc}")
            file_metas.append({"arquivo": path.name, "situacao_leitura": "ERRO", "erros": [str(exc)]})
    if not frames:
        return pd.DataFrame(), {"arquivo": ", ".join(p.name for p in paths), "situacao_leitura": "ERRO", "erros": errors}
    combined = pd.concat(frames, ignore_index=True)
    before = len(combined)
    combined = combined.drop_duplicates(subset=["CHAVE_VENDA"], keep="first")
    after = len(combined)
    meta = {
        "arquivo": ", ".join(p.name for p in paths),
        "arquivos_utilizados": [p.name for p in paths],
        "arquivos_detalhe": file_metas,
        "situacao_leitura": "OK" if not errors else "ATENCAO",
        "erros": errors,
        "linhas_originais": int(sum(m.get("linhas_originais", 0) for m in file_metas)),
        "linhas_lidas": int(after),
        "linhas_antes_deduplicacao": int(before),
        "duplicidades": int(before - after),
        "registros_validos": int(combined["VENDA_VALIDA"].sum()),
        "registros_invalidos": int((~combined["VENDA_VALIDA"]).sum()),
        "linhas_descartadas": int((~combined["VENDA_VALIDA"]).sum()),
        "motivos_descarte": combined.loc[~combined["VENDA_VALIDA"], "MOTIVO_DESCARTE"].value_counts().to_dict(),
        "quantidade_clientes": int(combined["COD_CLIENTE"].replace("", pd.NA).dropna().nunique() or combined["RAZAO_SOCIAL"].replace("", pd.NA).dropna().nunique()),
        "quantidade_produtos": int(combined["COD_PRODUTO"].replace("", pd.NA).dropna().nunique()),
        "quantidade_vendas": int(combined["VENDA"].replace("", pd.NA).dropna().nunique()),
        "menor_data": str(combined["DATA_VENDA"].min()) if combined["DATA_VENDA"].notna().any() else "",
        "maior_data": str(combined["DATA_VENDA"].max()) if combined["DATA_VENDA"].notna().any() else "",
        "faturamento_arquivo": float(combined.loc[combined["VENDA_VALIDA"], "VALOR_ITEM"].fillna(0).sum()),
    }
    return combined, meta


def load_estoque(path: Path) -> tuple[pd.DataFrame, dict]:
    raw, meta = read_csv_flexible(path)
    df = clean_columns(raw)
    df = df.rename(columns={"CODIGO": "COD_PRODUTO", "DESCRICAO": "DESCRICAO_ESTOQUE"})
    require_columns(df, ["COD_PRODUTO", "DESCRICAO_ESTOQUE"], meta)
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].map(clean_text)
    df["COD_PRODUTO"] = get_column(df, "COD_PRODUTO").map(only_digits_code)
    for col in ["DEPOSITO", "BALCAO", "CUSTO", "CUSTO_NF", "VENDA", "OFERTA_1", "OFERTA_2", "OFERTA_3"]:
        if col in df.columns:
            df[col] = parse_decimal_series(df[col])
    df["CURVA"] = get_column(df, "CURVA").astype(str).str.replace("\x00", "", regex=False).str.strip().str.upper()
    df["ESTOQUE_TOTAL"] = get_column(df, "DEPOSITO").replace("", 0).fillna(0).astype(float) + get_column(df, "BALCAO").replace("", 0).fillna(0).astype(float)
    df["VALOR_ESTOQUE"] = df["ESTOQUE_TOTAL"] * get_column(df, "CUSTO").replace("", 0).fillna(0).astype(float)
    meta.update(
        linhas_lidas=len(df),
        registros_validos=int(df["COD_PRODUTO"].astype(str).str.strip().ne("").sum()),
        registros_invalidos=int(df["COD_PRODUTO"].astype(str).str.strip().eq("").sum()),
        linhas_descartadas=0,
        motivos_descarte={},
        quantidade_produtos=int(df["COD_PRODUTO"].replace("", pd.NA).dropna().nunique()),
        produtos_negativos=int((df["ESTOQUE_TOTAL"] < 0).sum()),
        produtos_zerados=int((df["ESTOQUE_TOTAL"] == 0).sum()),
        valores_invalidos=int(df[["ESTOQUE_TOTAL", "CUSTO"]].isna().any(axis=1).sum() if "CUSTO" in df else 0),
        duplicidades=int(df.duplicated(subset=["COD_PRODUTO"]).sum()),
    )
    return df, meta


def load_produtos(path: Path) -> tuple[pd.DataFrame, dict]:
    header = find_header_row(path, ["Codigo", "Descricao", "Referencia", "UND"])
    raw, meta = read_csv_flexible(path, header=header)
    df = clean_columns(raw)
    df = df.dropna(how="all")
    df = df.rename(columns={"CODIGO": "COD_PRODUTO", "DESCRICAO": "DESCRICAO_PRODUTO", "UND": "UNIDADE"})
    require_columns(df, ["COD_PRODUTO", "DESCRICAO_PRODUTO"], meta)
    before = len(df)
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].map(clean_text)
    df = df[get_column(df, "COD_PRODUTO").astype(str).str.strip().ne("")]
    df["COD_PRODUTO"] = get_column(df, "COD_PRODUTO").map(only_digits_code)
    meta.update(
        cabecalho_linha=header + 1,
        linhas_lidas=len(df),
        registros_validos=len(df),
        registros_invalidos=before - len(df),
        linhas_descartadas=before - len(df),
        motivos_descarte={"codigo vazio": int(before - len(df))} if before - len(df) else {},
        quantidade_produtos=int(df["COD_PRODUTO"].replace("", pd.NA).dropna().nunique()),
        duplicidades=int(df.duplicated(subset=["COD_PRODUTO"]).sum()),
    )
    return df, meta


def load_clientes(path: Path) -> tuple[pd.DataFrame, dict]:
    header = find_header_row(path, ["Cod", "Razao Social", "Nome", "Cidade", "Telefone", "Ult"])
    raw, meta = read_csv_flexible(path, header=header)
    df = clean_columns(raw)
    df = df.dropna(how="all")
    df = df.rename(
        columns={
            "COD": "COD_CLIENTE",
            "RAZAO_SOCIAL": "RAZAO_SOCIAL",
            "NOME": "NOME_CLIENTE",
            "CIDADE": "CIDADE",
            "TELEFONE": "TELEFONE",
            "ULT_COMPRA": "ULTIMA_COMPRA",
        }
    )
    require_columns(df, ["COD_CLIENTE", "RAZAO_SOCIAL"], meta)
    before = len(df)
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].map(clean_text)
    df = df[get_column(df, "COD_CLIENTE").astype(str).str.strip().ne("")]
    df["COD_CLIENTE"] = get_column(df, "COD_CLIENTE").map(only_digits_code)
    if "ULTIMA_COMPRA" in df.columns:
        df["ULTIMA_COMPRA"] = parse_date_series(df["ULTIMA_COMPRA"])
    meta.update(
        cabecalho_linha=header + 1,
        linhas_lidas=len(df),
        registros_validos=len(df),
        registros_invalidos=before - len(df),
        linhas_descartadas=before - len(df),
        motivos_descarte={"codigo vazio": int(before - len(df))} if before - len(df) else {},
        quantidade_clientes=int(df["COD_CLIENTE"].replace("", pd.NA).dropna().nunique()),
        menor_data=str(df["ULTIMA_COMPRA"].min()) if "ULTIMA_COMPRA" in df and df["ULTIMA_COMPRA"].notna().any() else "",
        maior_data=str(df["ULTIMA_COMPRA"].max()) if "ULTIMA_COMPRA" in df and df["ULTIMA_COMPRA"].notna().any() else "",
        datas_invalidas=int(df["ULTIMA_COMPRA"].isna().sum() if "ULTIMA_COMPRA" in df else 0),
        duplicidades=int(df.duplicated(subset=["COD_CLIENTE"]).sum()),
    )
    return df, meta


def load_generic_csv(path: Path) -> tuple[pd.DataFrame, dict]:
    raw, meta = read_csv_flexible(path)
    df = clean_columns(raw)
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].map(clean_text)
    meta.update(
        linhas_lidas=len(df),
        registros_validos=len(df),
        registros_invalidos=0,
        linhas_descartadas=0,
        motivos_descarte={},
        colunas_reconhecidas=list(df.columns),
        colunas_obrigatorias_ausentes=[],
        erros=[],
    )
    return df, meta


def load_all_data(data_dir: Path, valid_statuses: list[str] | None = None) -> tuple[dict[str, pd.DataFrame], dict[str, dict]]:
    loaders = {
        "estoque": (["estoque*.csv"], load_estoque),
        "produtos": (["produtos*.csv"], load_produtos),
        "clientes": (["*clientes*.csv", "Listagem de clientes*.csv"], load_clientes),
        "compras": (["compras*.csv"], load_generic_csv),
        "fornecedores": (["fornecedores*.csv"], load_generic_csv),
    }
    frames: dict[str, pd.DataFrame] = {}
    metas: dict[str, dict] = {}
    vendas_paths = sorted({p for p in data_dir.glob("*vendas*.csv")})
    if vendas_paths:
        frames["vendas"], metas["vendas"] = load_vendas_files(vendas_paths, valid_statuses)
    else:
        frames["vendas"] = pd.DataFrame()
        metas["vendas"] = {"arquivo": "*vendas*.csv", "situacao_leitura": "AUSENTE", "erro": "Arquivo ausente", "erros": ["Nenhum arquivo de vendas encontrado"]}
    for name, (patterns, loader) in loaders.items():
        paths = []
        for pattern in patterns:
            paths.extend(data_dir.glob(pattern))
        paths = sorted(set(paths))
        if not paths:
            frames[name] = pd.DataFrame()
            metas[name] = {"arquivo": ", ".join(patterns), "situacao_leitura": "AUSENTE", "erro": "Arquivo ausente", "erros": [f"Nenhum arquivo encontrado para {name}"]}
            continue
        try:
            if len(paths) == 1:
                frames[name], metas[name] = loader(paths[0])
            else:
                loaded = [loader(path) for path in paths]
                frames[name] = pd.concat([item[0] for item in loaded], ignore_index=True)
                metas[name] = {
                    "arquivo": ", ".join(path.name for path in paths),
                    "arquivos_utilizados": [path.name for path in paths],
                    "arquivos_detalhe": [item[1] for item in loaded],
                    "situacao_leitura": "OK",
                    "linhas_originais": int(sum(item[1].get("linhas_originais", 0) for item in loaded)),
                    "linhas_lidas": int(len(frames[name])),
                    "registros_validos": int(sum(item[1].get("registros_validos", 0) for item in loaded)),
                    "registros_invalidos": int(sum(item[1].get("registros_invalidos", 0) for item in loaded)),
                    "linhas_descartadas": int(sum(item[1].get("linhas_descartadas", 0) for item in loaded)),
                    "erros": [],
                }
        except Exception as exc:
            filename = ", ".join(path.name for path in paths)
            frames[name] = pd.DataFrame()
            metas[name] = {"arquivo": filename, "situacao_leitura": "ERRO", "erro": f"{type(exc).__name__}: {exc}", "erros": [f"{filename}: {type(exc).__name__}: {exc}"]}
    return frames, metas


def build_relationship_diagnostics(frames: dict[str, pd.DataFrame]) -> dict:
    vendas = frames.get("vendas", pd.DataFrame())
    clientes = frames.get("clientes", pd.DataFrame())
    estoque = frames.get("estoque", pd.DataFrame())
    produtos = frames.get("produtos", pd.DataFrame())
    if vendas.empty:
        return {}
    venda_clientes = {x for x in vendas.get("COD_CLIENTE", pd.Series(dtype=str)).dropna().astype(str) if x.strip()}
    cad_clientes = {x for x in clientes.get("COD_CLIENTE", pd.Series(dtype=str)).dropna().astype(str) if x.strip()} if not clientes.empty else set()
    venda_produtos = {x for x in vendas.get("COD_PRODUTO", pd.Series(dtype=str)).dropna().astype(str) if x.strip()}
    est_produtos = {x for x in estoque.get("COD_PRODUTO", pd.Series(dtype=str)).dropna().astype(str) if x.strip()} if not estoque.empty else set()
    cad_produtos = {x for x in produtos.get("COD_PRODUTO", pd.Series(dtype=str)).dropna().astype(str) if x.strip()} if not produtos.empty else set()
    return {
        "clientes_encontrados": len(venda_clientes & cad_clientes),
        "clientes_sem_correspondencia": len(venda_clientes - cad_clientes),
        "produtos_em_estoque_encontrados": len(venda_produtos & est_produtos),
        "produtos_sem_estoque_correspondente": len(venda_produtos - est_produtos),
        "produtos_cadastro_encontrados": len(venda_produtos & cad_produtos),
        "produtos_sem_cadastro_correspondente": len(venda_produtos - cad_produtos),
    }

