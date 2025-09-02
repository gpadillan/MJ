import pandas as pd
import unicodedata
import re
from datetime import datetime

NBSP = "\u00A0"

MESES = [
    "Enero","Febrero","Marzo","Abril","Mayo","Junio",
    "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"
]

def _norm_text(s: object) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = str(s).replace(NBSP, " ")
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def clean_headers(df: pd.DataFrame) -> pd.DataFrame:
    cols = []
    seen = set()
    for i, c in enumerate(df.columns):
        base = _norm_text(c)
        if base == "":
            base = f"UNNAMED_{i}"
        if base in seen:
            base = f"{base}_{i}"
        cols.append(base)
        seen.add(base)
    d = df.copy()
    d.columns = cols
    return d

def ensure_estado(df: pd.DataFrame) -> pd.DataFrame:
    if "Estado" in df.columns:
        d = df.copy()
        d["Estado"] = d["Estado"].astype(str).map(_norm_text).str.upper()
        return d
    return df

def months_for_year(year: int) -> list[str]:
    return [f"{m} {year}" for m in MESES]

def totals_until_year(max_year: int, min_year: int = 2018) -> list[str]:
    return [f"Total {y}" for y in range(min_year, max_year + 1)]

def coerce_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    d = df.copy()
    existing = [c for c in cols if c in d.columns]
    if existing:
        d[existing] = d[existing].apply(pd.to_numeric, errors="coerce").fillna(0)
    return d

def prepare_eim_df(raw: pd.DataFrame) -> pd.DataFrame:
    d = clean_headers(raw)
    d = ensure_estado(d)
    return d
