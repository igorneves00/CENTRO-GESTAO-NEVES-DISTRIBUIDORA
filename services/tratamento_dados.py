from __future__ import annotations

import csv
import logging
from pathlib import Path

import pandas as pd

from utils.formatacao import clean_text, normalize_column_name, only_digits_code, parse_date_series, parse_decimal_series

ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin1")
DEFAULT_VALID_STATUSES = ["FATURADO", "PAGO"]


def detect_encoding(path: Path) -> str:
    for encoding in ENCODINGS:
        try:
            path.read_text(encoding=encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    return "latin1"


def detect_separator(path: Path, encoding: str) -> str:
    sample = path.read_text(encoding=encoding, errors="replace")[:12000]
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,|\t").delimiter
    except csv.Error:
        return ";"


def read_csv_flexible(path: Path, header: int | None = 0) -> tuple[pd.DataFrame, dict]:
    encoding = detect_encoding(path)
    sep = detect_separator(path, encoding)
    df = pd.read_csv(path, sep=sep, encoding=encoding, header=header, dtype=str, engine="python")
    meta = {"arquivo": path.name, "encoding": encoding, "separador": sep, "linhas_originais": len(df)}
    return df, meta


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


def load_vendas(path: Path, valid_statuses: list[str] | None = None) -> tuple[pd.DataFrame, dict]:
    valid_statuses = valid_statuses or DEFAULT_VALID_STATUSES
    raw, meta = read_csv_flexible(path)
    df = clean_columns(raw)
    rename = {
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
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].map(clean_text)
    df["COD_CLIENTE"] = df.get("CLIENTE", "").map(only_digits_code)
    df["COD_PRODUTO"] = df.get("COD_PRODUTO", "").map(only_digits_code)
    df["VENDA"] = df.get("VENDA", "").map(only_digits_code)
    df["DATA_VENDA"] = parse_date_series(df.get("DATA_VENDA", pd.Series(dtype=str)))
    money_cols = ["QTDE", "VALOR_UNITARIO", "VALOR_TOTAL", "CUSTO_NF", "CUSTO_MEDIO", "CUSTO_CHEIO", "CUSTO_BASE", "DESCONTO", "TOTAL_VENDA"]
    for col in money_cols:
        if col in df.columns:
            df[col] = parse_decimal_series(df[col])
    if "VALOR_TOTAL" not in df.columns or df["VALOR_TOTAL"].isna().all():
        df["VALOR_TOTAL"] = df["QTDE"].fillna(0) * df["VALOR_UNITARIO"].fillna(0)
    df["VALOR_ITEM"] = df["VALOR_TOTAL"].fillna(df["QTDE"].fillna(0) * df["VALOR_UNITARIO"].fillna(0))
    df["STATUS_NORMALIZADO"] = df.get("STATUS", "").astype(str).str.upper().str.strip()
    df["VENDA_VALIDA"] = df["STATUS_NORMALIZADO"].isin([s.upper() for s in valid_statuses])
    meta.update(
        linhas_lidas=len(df),
        registros_validos=int(df["VENDA_VALIDA"].sum()),
        registros_invalidos=int((~df["VENDA_VALIDA"]).sum()),
        datas_invalidas=int(df["DATA_VENDA"].isna().sum()),
        valores_invalidos=int(df[["QTDE", "VALOR_ITEM"]].isna().any(axis=1).sum()),
        duplicidades=int(df.duplicated(subset=["VENDA", "COD_PRODUTO", "QTDE", "VALOR_ITEM"]).sum()),
        status_validos=", ".join(valid_statuses),
    )
    return df, meta


def load_estoque(path: Path) -> tuple[pd.DataFrame, dict]:
    raw, meta = read_csv_flexible(path)
    df = clean_columns(raw)
    df = df.rename(columns={"CODIGO": "COD_PRODUTO", "DESCRICAO": "DESCRICAO_ESTOQUE"})
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].map(clean_text)
    df["COD_PRODUTO"] = df.get("COD_PRODUTO", "").map(only_digits_code)
    for col in ["DEPOSITO", "BALCAO", "CUSTO", "CUSTO_NF", "VENDA", "OFERTA_1", "OFERTA_2", "OFERTA_3"]:
        if col in df.columns:
            df[col] = parse_decimal_series(df[col])
    df["CURVA"] = df.get("CURVA", "").astype(str).str.replace("\x00", "", regex=False).str.strip().str.upper()
    df["ESTOQUE_TOTAL"] = df.get("DEPOSITO", 0).fillna(0) + df.get("BALCAO", 0).fillna(0)
    df["VALOR_ESTOQUE"] = df["ESTOQUE_TOTAL"] * df.get("CUSTO", 0).fillna(0)
    meta.update(
        linhas_lidas=len(df),
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
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].map(clean_text)
    df = df[get_column(df, "COD_PRODUTO").astype(str).str.strip().ne("")]
    df["COD_PRODUTO"] = get_column(df, "COD_PRODUTO").map(only_digits_code)
    meta.update(cabecalho_linha=header + 1, linhas_lidas=len(df), duplicidades=int(df.duplicated(subset=["COD_PRODUTO"]).sum()))
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
        datas_invalidas=int(df["ULTIMA_COMPRA"].isna().sum() if "ULTIMA_COMPRA" in df else 0),
        duplicidades=int(df.duplicated(subset=["COD_CLIENTE"]).sum()),
    )
    return df, meta


def load_all_data(data_dir: Path, valid_statuses: list[str] | None = None) -> tuple[dict[str, pd.DataFrame], dict[str, dict]]:
    loaders = {
        "vendas": ("vendas 01.13.csv", load_vendas),
        "estoque": ("estoque 13.07.26.csv", load_estoque),
        "produtos": ("produtos 13.07.26.csv", load_produtos),
        "clientes": ("Listagem de clientes 13.07.26.csv", load_clientes),
    }
    frames: dict[str, pd.DataFrame] = {}
    metas: dict[str, dict] = {}
    for name, (filename, loader) in loaders.items():
        path = data_dir / filename
        if not path.exists():
            frames[name] = pd.DataFrame()
            metas[name] = {"arquivo": filename, "erro": "Arquivo ausente"}
            continue
        try:
            if name == "vendas":
                frames[name], metas[name] = loader(path, valid_statuses)
            else:
                frames[name], metas[name] = loader(path)
        except Exception as exc:
            logging.exception("Erro ao ler %s", filename)
            frames[name] = pd.DataFrame()
            metas[name] = {"arquivo": filename, "erro": str(exc)}
    return frames, metas


def build_relationship_diagnostics(frames: dict[str, pd.DataFrame]) -> dict:
    vendas = frames.get("vendas", pd.DataFrame())
    clientes = frames.get("clientes", pd.DataFrame())
    estoque = frames.get("estoque", pd.DataFrame())
    produtos = frames.get("produtos", pd.DataFrame())
    if vendas.empty:
        return {}
    venda_clientes = set(vendas.get("COD_CLIENTE", pd.Series(dtype=str)).dropna().astype(str))
    cad_clientes = set(clientes.get("COD_CLIENTE", pd.Series(dtype=str)).dropna().astype(str)) if not clientes.empty else set()
    venda_produtos = set(vendas.get("COD_PRODUTO", pd.Series(dtype=str)).dropna().astype(str))
    est_produtos = set(estoque.get("COD_PRODUTO", pd.Series(dtype=str)).dropna().astype(str)) if not estoque.empty else set()
    cad_produtos = set(produtos.get("COD_PRODUTO", pd.Series(dtype=str)).dropna().astype(str)) if not produtos.empty else set()
    return {
        "clientes_encontrados": len(venda_clientes & cad_clientes),
        "clientes_sem_correspondencia": len(venda_clientes - cad_clientes),
        "produtos_em_estoque_encontrados": len(venda_produtos & est_produtos),
        "produtos_sem_estoque_correspondente": len(venda_produtos - est_produtos),
        "produtos_cadastro_encontrados": len(venda_produtos & cad_produtos),
        "produtos_sem_cadastro_correspondente": len(venda_produtos - cad_produtos),
    }

