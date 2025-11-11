# principal.py
# -*- coding: utf-8 -*-
import os
import re
import time
import unicodedata
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import requests
from urllib.parse import quote, unquote

UPLOAD_FOLDER = "uploaded_admisiones"
ARCHIVO_DESARROLLO = os.path.join(UPLOAD_FOLDER, "desarrollo_profesional.xlsx")
NBSP = "\u00A0"

# =============== Utils básicos ===============
def _norm_spaces(text: str) -> str:
    s = unicodedata.normalize("NFKC", str(text)).replace(NBSP, " ")
    return " ".join(s.strip().split())

def clean_headers(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [
        _norm_spaces(col).upper() if _norm_spaces(col) != "" else f'UNNAMED_{i}'
        for i, col in enumerate(df.columns)
    ]
    if len(df.columns) != len(set(df.columns)):
        st.warning("⚠️ Se encontraron columnas duplicadas. Se eliminarán automáticamente.")
        df = df.loc[:, ~df.columns.duplicated()]
    return df

def es_vacio(valor):
    if pd.isna(valor):
        return True
    v = unicodedata.normalize("NFKC", str(valor)).replace(NBSP, " ").strip().upper()
    return v == ""

def limpiar_riesgo(valor) -> float:
    if isinstance(valor, (int, float)):
        return float(valor)
    if pd.isna(valor):
        return 0.0
    v = re.sub(r"[^\d,\.]", "", str(valor))
    v = v.replace(".", "").replace(",", ".")
    try:
        return float(v)
    except Exception:
        return 0.0

def _booly(v) -> bool:
    """Normaliza valores booleanos escritos como Sí/No/True/False/1/0, etc."""
    if pd.isna(v):
        return False
    s = str(v).strip().lower()
    return s in {"true","1","1.0","sí","si","verdadero","x","✓","check","ok","s"}

# ======== Helpers de color y tabla con degradado por área ========
AREA_COLORS = {
    "SAP": "#1f77b4",
    "RRHH": "#2ca02c",
    "IA": "#9467bd",
    "CIBER": "#d62728",
    "DPO": "#17becf",
    "EERR": "#8c654b",
    "DF": "#da3fab",
    "FULLSTACK": "#bcbd22",
    "Logística": "#009e42",
    "BIM": "#ff7f0e",
    "MENORES": "#FFE600",
    "TOTAL": "#b3b3b3",
}

def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return "#{:02x}{:02x}{:02x}".format(max(0,min(255,r)), max(0,min(255,g)), max(0,min(255,b)))

def _mix_with_white(hex_color: str, t: float) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    r = int(255*(1-t) + r*t)
    g = int(255*(1-t) + g*t)
    b = int(255*(1-t) + b*t)
    return _rgb_to_hex(r, g, b)

def _area_gradient_table(df_pivot: pd.DataFrame) -> go.Figure:
    if df_pivot is None or df_pivot.empty:
        return go.Figure()

    df = df_pivot.copy()
    if "Área" not in df.columns:
        raise ValueError("La tabla pivote debe tener columna 'Área'.")

    year_cols = [c for c in df.columns if isinstance(c, int)]
    cols = ["Área"] + year_cols + (["Total"] if "Total" in df.columns else [])
    df = df[cols].reset_index(drop=True)
    n_rows = df.shape[0]
    cell_colors_by_col: list[list[str]] = []

    # Columna Área
    col_area_colors = []
    for i in range(n_rows):
        area = df.at[i, "Área"]
        base = AREA_COLORS.get(area, "#446adb")
        col_area_colors.append(_mix_with_white(base, 0.2))
    cell_colors_by_col.append(col_area_colors)

    # Columnas de año (degradado por fila)
    for y in year_cols:
        col_colors = []
        for i in range(n_rows):
            area = df.at[i, "Área"]
            base = AREA_COLORS.get(area, "#446adb")
            row_vals = [float(df.at[i, yy]) for yy in year_cols if pd.notna(df.at[i, yy])]
            if not row_vals:
                col_colors.append("#f2f2f2")
                continue
            v = float(df.at[i, y])
            vmin, vmax = min(row_vals), max(row_vals)
            if vmax == vmin:
                t = 0.15 if vmax == 0 else 0.6
            else:
                norm = (v - vmin) / (vmax - vmin)
                t = 0.15 + 0.85 * norm
            col_colors.append(_mix_with_white(base, t))
        cell_colors_by_col.append(col_colors)

    # Columna Total
    if "Total" in df.columns:
        col_total_colors = []
        for i in range(n_rows):
            area = df.at[i, "Área"]
            base = AREA_COLORS.get(area, "#446adb")
            col_total_colors.append(_mix_with_white(base, 0.75))
        cell_colors_by_col.append(col_total_colors)

    # Valores
    cell_values = [df[c].tolist() for c in df.columns]

    def _fmt_col(col_vals):
        out = []
        for v in col_vals:
            try:
                iv = int(v)
                out.append(f"{iv:,}".replace(",", "."))
            except Exception:
                out.append(v)
        return out

    formatted_values = []
    for c, vals in zip(df.columns, cell_values):
        if c == "Área":
            formatted_values.append(vals)
        else:
            formatted_values.append(_fmt_col(vals))

    fig = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=[f"<b>{c}</b>" for c in df.columns],
                    fill_color="#e9ecef",
                    align="center",
                    font=dict(color="#111", size=13),
                    height=34,
                ),
                cells=dict(
                    values=formatted_values,
                    fill_color=cell_colors_by_col,
                    align="center",
                    font=dict(color="#111", size=12),
                    height=32,
                ),
                columnwidth=[160] + [80 for _ in year_cols] + ([90] if "Total" in df.columns else []),
            )
        ]
    )
    fig.update_layout(margin=dict(l=0, r=0, t=6, b=0), height=38 + 35 + 32 * max(1, n_rows))
    return fig

# =============== Graph / SharePoint helpers ===============
def _secrets_ok(sec: dict) -> bool:
    req = ["client_id", "tenant_id", "client_secret", "domain", "site_name"]
    return all(k in sec and str(sec[k]).strip() for k in req)

def _http_get_with_retry(url: str, headers: dict, timeout: int = 30, retries: int = 3) -> requests.Response:
    for i in range(retries):
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(1.5 * (i + 1))
            continue
        r.raise_for_status()
        return r
    r.raise_for_status()
    return r

@st.cache_data(ttl=3300)
def _graph_get_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
        "scope": "https://graph.microsoft.com/.default",
    }
    r = requests.post(url, data=data, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]

def _graph_get(url: str, token: str) -> dict:
    r = _http_get_with_retry(url, headers={"Authorization": f"Bearer {token}"})
    return r.json()

@st.cache_data(ttl=3600)
def _get_site_id(domain: str, site_name: str, token: str) -> str:
    url = f"https://graph.microsoft.com/v1.0/sites/{domain}:/sites/{quote(site_name)}?$select=id,webUrl"
    data = _graph_get(url, token)
    return data["id"]

@st.cache_data(ttl=3600)
def _get_drive_id(site_id: str, token: str) -> str:
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive?$select=id,webUrl"
    data = _graph_get(url, token)
    return data["id"]

@st.cache_data(ttl=300)
def _list_folder_children(drive_id: str, folder_path: str, token: str) -> list[dict]:
    encoded_path = quote(folder_path.strip("/"), safe="/")
    base = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{encoded_path}"
    _ = _graph_get(base, token)
    url = base + ":/children?$top=200&$select=name,webUrl,lastModifiedDateTime,folder,file,size"
    items = []
    while url:
        data = _graph_get(url, token)
        for it in data.get("value", []):
            is_folder = "folder" in it and it["folder"] is not None
            items.append({
                "name": it.get("name", ""),
                "webUrl": it.get("webUrl", ""),
                "lastModified": it.get("lastModifiedDateTime", ""),
                "isFolder": is_folder,
                "size": (None if is_folder else it.get("size", 0)),
                "mime": ("" if is_folder else it.get("file", {}).get("mimeType", "")),
            })
        url = data.get("@odata.nextLink")
    items.sort(key=lambda x: (not x["isFolder"], x["name"].lower()))
    return items

# ---------- Búsqueda y extracción convenios ----------
@st.cache_data(ttl=900)
def _get_item_id_by_path(drive_id: str, folder_path: str, token: str) -> str:
    encoded_path = quote(folder_path.strip("/"), safe="/")
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{encoded_path}"
    data = _graph_get(url, token)
    return data["id"]

@st.cache_data(ttl=300)
def _search_in_folder(drive_id: str, item_id: str, token: str, query: str) -> list[dict]:
    """Busca `query` dentro de una carpeta por su item_id (si el tenant lo permite)."""
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/search(q='{quote(query)}')"
    results = []
    while url:
        data = _graph_get(url, token)
        for it in data.get("value", []):
            is_file = ("file" in it) and (it["file"] is not None)
            results.append({
                "name": it.get("name", ""),
                "webUrl": it.get("webUrl", ""),
                "lastModified": it.get("lastModifiedDateTime", ""),
                "isFile": is_file
            })
        url = data.get("@odata.nextLink")
    return results

def _extract_company_from_weburl(web_url: str, area_folder: str) -> str:
    """
    Extrae la subcarpeta (empresa) inmediatamente bajo el área a partir del webUrl.
    Busca: /Documentos compartidos/EMPLEO/_PRÁCTICAS/Convenios firmados/{area}/<AQUI>
    """
    if not web_url:
        return ""
    try:
        url = unquote(web_url)
        pivot = "/Documentos compartidos/"
        if pivot not in url:
            return ""
        tail = url.split(pivot, 1)[1]
        marker = f"EMPLEO/_PRÁCTICAS/Convenios firmados/{area_folder}/"
        if marker not in tail:
            marker_alt = f"EMPLEO/_Prácticas/Convenios firmados/{area_folder}/"
            marker_alt2 = f"EMPLEO/_PRÁCTICAS/Convenios firmados/{area_folder}".rstrip("/") + "/"
            if marker_alt in tail:
                marker = marker_alt
            elif marker_alt2 in tail:
                marker = marker_alt2
            else:
                return ""
        rest = tail.split(marker, 1)[1]
        segs = rest.split("/")
        return segs[0] if segs else ""
    except Exception:
        return ""

def _walk_and_collect_convenios(drive_id: str, area_path: str, token: str, kw="CONVENI") -> list[dict]:
    """
    Recorre recursivamente la carpeta `area_path` y devuelve archivos con `kw`
    incluyendo lastModified y la carpeta (empresa) bajo el área.
    """
    from collections import deque
    q = deque([area_path])
    out = []
    area_path_norm = area_path.strip("/")

    while q:
        current = q.popleft()
        try:
            children = _list_folder_children(drive_id, current, token)
        except Exception:
            continue
        # empresa = primer segmento tras el área dentro de 'current'
        rel = current.strip("/")[len(area_path_norm):].lstrip("/")
        empresa = rel.split("/")[0] if rel else "(raíz)"
        for it in children:
            if it.get("isFolder", False):
                q.append(f"{current.rstrip('/')}/{it['name']}")
            else:
                name_up = (it.get("name") or "").upper()
                if kw in name_up:
                    out.append({
                        "name": it.get("name", ""),
                        "lastModified": it.get("lastModified", ""),
                        "webUrl": it.get("webUrl", ""),
                        "empresa": empresa
                    })
    return out

@st.cache_data(ttl=600, show_spinner=False)
def _convenios_por_area_y_ano(drive_id: str, base_path: str, areas_map: dict[str, str],
                              token: str) -> pd.DataFrame:
    """
    Devuelve un pivote: filas = Área, columnas = Años, valores = nº de convenios.
    Usa búsqueda (rápida) y si falla permisos/resultados, recorre recursivamente.
    """
    rows = []
    all_years = set()
    for area_label, area_folder in areas_map.items():
        area_path = f"{base_path}/{area_folder}"
        year_counts = {}

        # 1) Intento rápido con SEARCH
        try:
            area_id = _get_item_id_by_path(drive_id, area_path, token)
            found = _search_in_folder(drive_id, area_id, token, "conveni")
            hits = [
                it for it in found
                if it.get("isFile") and ("CONVENI" in (it.get("name", "").upper()))
            ]
            if hits:
                years = pd.to_datetime(
                    [h.get("lastModified") for h in hits],
                    errors="coerce", utc=True
                ).dropna().year
                for y, c in years.value_counts().items():
                    y = int(y)
                    year_counts[y] = year_counts.get(y, 0) + int(c)
        except Exception:
            pass

        # 2) Fallback si no hubo resultados o permisos
        if not year_counts:
            convs = _walk_and_collect_convenios(drive_id, area_path, token, kw="CONVENI")
            if convs:
                years = pd.to_datetime(
                    [c.get("lastModified") for c in convs],
                    errors="coerce", utc=True
                ).dropna().year
                for y, c in years.value_counts().items():
                    y = int(y)
                    year_counts[y] = year_counts.get(y, 0) + int(c)

        all_years.update(year_counts.keys())
        row = {"Área": area_label}
        row.update({int(y): int(year_counts.get(y, 0)) for y in year_counts})
        rows.append(row)

    if not rows:
        return pd.DataFrame(columns=["Área"])
    df = pd.DataFrame(rows).fillna(0)
    for y in sorted(all_years):
        if y not in df.columns:
            df[y] = 0
    year_cols = sorted([c for c in df.columns if isinstance(c, int)], reverse=True)
    df = df[["Área"] + year_cols]
    df["Total"] = df[year_cols].sum(axis=1)
    df = df.sort_values(["Total", "Área"], ascending=[False, True]).reset_index(drop=True)
    df = df.astype({c: int for c in year_cols + ["Total"]})
    return df

def _append_total_global_row(df_pivot: pd.DataFrame) -> pd.DataFrame:
    """Añade una fila TOTAL con la suma de todas las áreas, incl. Total global."""
    if df_pivot is None or df_pivot.empty:
        return df_pivot
    out = df_pivot.copy()
    year_cols = [c for c in out.columns if isinstance(c, int)]
    total_row = {"Área": "TOTAL"}
    for y in year_cols:
        total_row[y] = int(out[y].sum())
    total_row["Total"] = int(out["Total"].sum())
    out = pd.concat([out, pd.DataFrame([total_row])], ignore_index=True)
    return out

@st.cache_data(ttl=600, show_spinner=False)
def _detalle_por_area_y_ano(drive_id: str, base_path: str, areas_map: dict[str, str],
                            token: str, year: int) -> pd.DataFrame:
    """
    Detalle de convenios para un AÑO concreto: Área, Carpeta, Archivo, Fecha, Link.
    Usa búsqueda y, si no, recorrido recursivo. Intenta obtener la carpeta-empresa.
    """
    rows = []
    for area_label, area_folder in areas_map.items():
        area_path = f"{base_path}/{area_folder}"
        try:
            area_id = _get_item_id_by_path(drive_id, area_path, token)
            found = _search_in_folder(drive_id, area_id, token, "conveni")
            for it in found:
                if not it.get("isFile"):
                    continue
                name = it.get("name", "")
                if "CONVENI" not in name.upper():
                    continue
                lm = pd.to_datetime(it.get("lastModified"), errors="coerce", utc=True)
                if pd.isna(lm) or int(lm.year) != int(year):
                    continue
                empresa = _extract_company_from_weburl(it.get("webUrl", ""), area_folder)
                rows.append({
                    "Área": area_label,
                    "Carpeta": empresa,
                    "Archivo": name,
                    "Fecha": lm.tz_convert(None) if hasattr(lm, "tz_convert") else lm,
                    "Link": it.get("webUrl", "")
                })
        except Exception:
            convs = _walk_and_collect_convenios(drive_id, area_path, token, kw="CONVENI")
            for c in convs:
                lm = pd.to_datetime(c.get("lastModified"), errors="coerce", utc=True)
                if pd.isna(lm) or int(lm.year) != int(year):
                    continue
                rows.append({
                    "Área": area_label,
                    "Carpeta": c.get("empresa", ""),
                    "Archivo": c.get("name", ""),
                    "Fecha": lm.tz_convert(None) if hasattr(lm, "tz_convert") else lm,
                    "Link": c.get("webUrl", "")
                })
    if not rows:
        return pd.DataFrame(columns=["Área", "Carpeta", "Archivo", "Fecha", "Link"])
    df = pd.DataFrame(rows)
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce").dt.date
    return df.sort_values(["Área", "Carpeta", "Archivo"]).reset_index(drop=True)

@st.cache_data(ttl=600, show_spinner=False)
def _detalle_area_all_years(drive_id: str, base_path: str, areas_map: dict[str, str],
                            token: str, area_label: str) -> pd.DataFrame:
    """
    Detalle de convenios para un ÁREA concreta en TODOS los años.
    Columnas: Área, Año, Carpeta, Archivo, Fecha, Link.
    """
    area_folder = areas_map.get(area_label)
    if not area_folder:
        return pd.DataFrame(columns=["Área", "Año", "Carpeta", "Archivo", "Fecha", "Link"])
    area_path = f"{base_path}/{area_folder}"

    rows = []
    try:
        area_id = _get_item_id_by_path(drive_id, area_path, token)
        found = _search_in_folder(drive_id, area_id, token, "conveni")
        for it in found:
            if not it.get("isFile"):
                continue
            name = it.get("name", "")
            if "CONVENI" not in name.upper():
                continue
            lm = pd.to_datetime(it.get("lastModified"), errors="coerce", utc=True)
            if pd.isna(lm):
                continue
            empresa = _extract_company_from_weburl(it.get("webUrl", ""), area_folder)
            rows.append({
                "Área": area_label,
                "Año": int(lm.year),
                "Carpeta": empresa,
                "Archivo": name,
                "Fecha": lm.tz_convert(None) if hasattr(lm, "tz_convert") else lm,
                "Link": it.get("webUrl", "")
            })
    except Exception:
        convs = _walk_and_collect_convenios(drive_id, area_path, token, kw="CONVENI")
        for c in convs:
            lm = pd.to_datetime(c.get("lastModified"), errors="coerce", utc=True)
            if pd.isna(lm):
                continue
            rows.append({
                "Área": area_label,
                "Año": int(lm.year),
                "Carpeta": c.get("empresa", ""),
                "Archivo": c.get("name", ""),
                "Fecha": lm.tz_convert(None) if hasattr(lm, "tz_convert") else lm,
                "Link": c.get("webUrl", "")
            })

    if not rows:
        return pd.DataFrame(columns=["Área", "Año", "Carpeta", "Archivo", "Fecha", "Link"])
    df = pd.DataFrame(rows)
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce").dt.date
    return df.sort_values(["Año", "Fecha"], ascending=[False, False]).reset_index(drop=True)

# ======= Tarjetas KPI (cuadradas) =======
def _kpi_card(title: str, main: str, sub: str | None = None, tone: str = "blue") -> str:
    """Card visual con tonos personalizados"""
    if tone == "green":  # Consecución
        bg = "#f0fdf4"; border = "#bbf7d0"; title_color = "#166534"; main_color = "#065f46"; sub_color = "#166534"
    elif tone == "grey":  # Inaplicación
        bg = "#f5f5f5"; border = "#e5e7eb"; title_color = "#374151"; main_color = "#111827"; sub_color = "#4b5563"
    elif tone == "pink":  # Prácticas totales
        bg = "#fdf2f8"; border = "#fbcfe8"; title_color = "#9d174d"; main_color = "#9d174d"; sub_color = "#9d174d"
    elif tone == "blue":  # Total alumnos y Cierre expediente
        bg = "#f1f6ff"; border = "#d6e4ff"; title_color = "#0b3a7a"; main_color = "#00335c"; sub_color = "#335b92"
    else:
        bg = "#ffffff"; border = "#cccccc"; title_color = "#333"; main_color = "#111"; sub_color = "#333"

    sub_html = f"<div style='font-size:12px;color:{sub_color};opacity:.9'>{sub}</div>" if sub else ""
    return f"""
    <div style="background:{bg};border:1px solid {border};border-radius:14px;
                padding:14px 16px;box-shadow:0 2px 6px rgba(0,0,0,0.06);
                display:flex;flex-direction:column;gap:6px;min-height:96px">
      <div style="font-weight:700;color:{title_color};font-size:13px">{title}</div>
      <div style="font-size:28px;font-weight:800;color:{main_color}">{main}</div>
      {sub_html}
    </div>
    """

# =============== App principal ===============
def render(df: pd.DataFrame | None = None):
    st.title("📊 Principal - Área de Empleo")

    if st.button("🔄 Recargar / limpiar caché"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("Caché limpiada. Datos recargados.")

    # Carga Excel local si no se pasa df
    if df is None:
        if not os.path.exists(ARCHIVO_DESARROLLO):
            st.warning("⚠️ No se encontró el archivo.")
            return
        try:
            df = pd.read_excel(ARCHIVO_DESARROLLO, sheet_name="GENERAL")
        except Exception:
            df = pd.read_excel(ARCHIVO_DESARROLLO)

    df = clean_headers(df)

    # Aliases de columnas
    rename_alias = {
        "PRÁCTCAS/GE": "PRÁCTICAS/GE",
        "PRACTICAS/GE": "PRÁCTICAS/GE",
        "CONSULTOR_EIP": "CONSULTOR EIP"
    }
    df = df.rename(columns={k: v for k, v in rename_alias.items() if k in df.columns})

    # Requisitos
    cols_req = [
        "CONSECUCIÓN GE", "INAPLICACIÓN GE", "DEVOLUCIÓN GE",
        "AREA", "PRÁCTICAS/GE", "CONSULTOR EIP", "RIESGO ECONÓMICO", "FIN CONV",
        "NOMBRE", "APELLIDOS"
    ]
    faltantes = [c for c in cols_req if c not in df.columns]
    if faltantes:
        st.error(f"❌ Faltan columnas: {', '.join(faltantes)}")
        return

    # Activo = las 3 columnas de estado vacías
    df["ES_ACTIVO"] = (
        df["CONSECUCIÓN GE"].map(es_vacio) &
        df["INAPLICACIÓN GE"].map(es_vacio) &
        df["DEVOLUCIÓN GE"].map(es_vacio)
    )

    # Normalizaciones
    for col in ["PRÁCTICAS/GE", "CONSULTOR EIP", "AREA"]:
        df[col] = df[col].where(df[col].notna(), pd.NA).map(
            lambda x: _norm_spaces(x) if pd.notna(x) else x
        ).str.upper()

    # ✅ Solo activos (sin toggle)
    df_base = df[df["ES_ACTIVO"]].copy()

    # Filtra áreas válidas
    df_base = df_base[
        df_base["AREA"].notna() &
        (~df_base["AREA"].isin(["", "NO ENCONTRADO", "NAN", "<NA>"]))
    ]

    # Filtros que incluyen blancos por defecto
    opciones_practicas = sorted(
        df_base["PRÁCTICAS/GE"].fillna("(EN BLANCO)").unique().tolist()
    )
    opciones_consultores = sorted(
        df_base["CONSULTOR EIP"].fillna("(EN BLANCO)").unique().tolist()
    )

    c1, c2 = st.columns(2)
    with c1:
        seleccion_practicas = st.multiselect(
            "Selecciona PRÁCTICAS/GE:",
            opciones_practicas,
            default=opciones_practicas
        )
    with c2:
        seleccion_consultores = st.multiselect(
            "Selecciona CONSULTOR EIP:",
            opciones_consultores,
            default=opciones_consultores
        )

    df_filtrado = df_base.copy()
    df_filtrado["PRÁCTICAS/GE"] = df_filtrado["PRÁCTICAS/GE"].fillna("(EN BLANCO)")
    df_filtrado["CONSULTOR EIP"] = df_filtrado["CONSULTOR EIP"].fillna("(EN BLANCO)")

    df_filtrado = df_filtrado[
        df_filtrado["PRÁCTICAS/GE"].isin(seleccion_practicas) &
        df_filtrado["CONSULTOR EIP"].isin(seleccion_consultores)
    ].copy()

    if df_filtrado.empty:
        st.info("No hay datos disponibles para la selección realizada.")
        return

    # =================== Barras por área ===================
    conteo_area = df_filtrado["AREA"].value_counts().reset_index()
    conteo_area.columns = ["Área", "Cantidad"]

    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=conteo_area["Área"],
        y=conteo_area["Cantidad"],
        marker=dict(color=conteo_area["Cantidad"],
                    colorscale=[[0, "#6B6A6A"], [1, "#003cff"]],
                    line=dict(color="black", width=1.5)),
    ))
    for x, y in zip(conteo_area["Área"], conteo_area["Cantidad"]):
        fig_bar.add_annotation(x=x, y=y, text=f"<b>{y}</b>", showarrow=False, yshift=5,
                               font=dict(color="white", size=13), align="center",
                               bgcolor="black", borderpad=4)
    fig_bar.update_layout(height=500, xaxis_title="Área", yaxis_title="Número de Alumnos",
                          yaxis=dict(range=[0, max(conteo_area["Cantidad"]) * 1.2]),
                          plot_bgcolor="white")
    st.plotly_chart(fig_bar, use_container_width=True)

    # =================== KPIs (arriba) ===================
    total_alumnos_pend = len(df_filtrado)
    hoy = pd.to_datetime("today").normalize()

    df_ge_activos = df_filtrado[df_filtrado["PRÁCTICAS/GE"] == "GE"].copy()
    # Fechas europeas (dd/mm/yyyy)
    df_ge_activos["FIN CONV"] = pd.to_datetime(
        df_ge_activos["FIN CONV"], errors="coerce", dayfirst=True
    )
    df_ge_activos["FECHA_RIESGO"] = df_ge_activos["FIN CONV"] + pd.DateOffset(months=3)

    mask_riesgo = (df_ge_activos["FECHA_RIESGO"].notna() & (df_ge_activos["FECHA_RIESGO"] <= hoy))
    df_riesgo = df_ge_activos.loc[mask_riesgo].copy()
    df_riesgo["RIESGO ECONÓMICO"] = df_riesgo["RIESGO ECONÓMICO"].map(limpiar_riesgo)

    suma_riesgo = df_riesgo["RIESGO ECONÓMICO"].sum()
    suma_riesgo_fmt = f"{suma_riesgo:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
    total_ge_indicador = len(df_riesgo)

    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("👥 Alumnos pendiente", total_alumnos_pend)  # renombrado
    with k2:
        st.metric("📌 ALUMNO RIESGO TRIM", total_ge_indicador)
    with k3:
        st.metric("💰 RIESGO ECONÓMICO", suma_riesgo_fmt)

    # ======= TARJETAS EN UNA FILA (Total + % Consec + % Inapl + % Cierre + % Prácticas) =======
    st.markdown(" ")

    # Base global sin filtrar: NOMBRE y APELLIDOS no vacíos
    df_total = df.copy()
    df_total = df_total[~df_total["NOMBRE"].map(es_vacio) & ~df_total["APELLIDOS"].map(es_vacio)].copy()
    total_alumnos_global = len(df_total)

    pct_consec = 0.0
    pct_inap  = 0.0
    pct_cierre = 0.0
    pct_practicas_tot = 0.0

    if total_alumnos_global > 0:
        consec_true = df_total["CONSECUCIÓN GE"].map(_booly).sum()
        inap_true   = df_total["INAPLICACIÓN GE"].map(_booly).sum()
        devol_true  = df_total["DEVOLUCIÓN GE"].map(_booly).sum()

        pct_consec = round(100.0 * consec_true / total_alumnos_global, 2)
        pct_inap   = round(100.0 * inap_true / total_alumnos_global, 2)

        cierre_exp_n = int(((df_total["CONSECUCIÓN GE"].map(_booly)) |
                            (df_total["INAPLICACIÓN GE"].map(_booly)) |
                            (df_total["DEVOLUCIÓN GE"].map(_booly))).sum())
        pct_cierre = round(100.0 * cierre_exp_n / total_alumnos_global, 2)

        if "EMPRESA GE" in df_total.columns:
            emp_ge_no_vacio = (~df_total["EMPRESA GE"].map(es_vacio)).sum()
            pct_practicas_tot = round(100.0 * emp_ge_no_vacio / total_alumnos_global, 2)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        c1.markdown(_kpi_card("✅ % Consecución GE", f"{pct_consec} %", "Sobre total alumnos", tone="green"), unsafe_allow_html=True)
    with c2:
        c2.markdown(_kpi_card("⚙️ % Inaplicación GE", f"{pct_inap} %", "Sobre total alumnos", tone="grey"), unsafe_allow_html=True)
    with c3:
        c3.markdown(_kpi_card("👥 Total de alumnos", f"{total_alumnos_global:,}".replace(",", "."), "Con nombre y apellidos", tone="blue"), unsafe_allow_html=True)
    with c4:
        c4.markdown(_kpi_card("📁 % Cierre de expediente", f"{pct_cierre} %", "Consec./Inaplic./Devol.", tone="blue"), unsafe_allow_html=True)
    with c5:
        c5.markdown(_kpi_card("🧪 % Prácticas totales", f"{pct_practicas_tot} %", "EMPRESA GE no vacío", tone="pink"), unsafe_allow_html=True)

    # =================== Distribución ===================
    st.markdown("---")
    st.subheader("📊 Distribución")

    colpie1, colpie2 = st.columns(2)
    with colpie1:
        conteo_practicas = df_filtrado["PRÁCTICAS/GE"].value_counts().reset_index()
        conteo_practicas.columns = ["Tipo", "Cantidad"]
        fig_pie = px.pie(conteo_practicas, names="Tipo", values="Cantidad")
        fig_pie.update_traces(textposition="inside", textinfo="label+percent+value")
        fig_pie.update_layout(title="Distribución por Tipo", height=500)
        st.plotly_chart(fig_pie, use_container_width=True)

    with colpie2:
        df_filtrado_consultores = df_filtrado[
            df_filtrado["CONSULTOR EIP"].notna() &
            (df_filtrado["CONSULTOR EIP"].str.upper() != "NO ENCONTRADO")
        ]
        conteo_consultor = df_filtrado_consultores["CONSULTOR EIP"].value_counts().reset_index()
        conteo_consultor.columns = ["Consultor", "Cantidad"]
        fig_pie_consultor = px.pie(conteo_consultor, names="Consultor", values="Cantidad")
        fig_pie_consultor.update_traces(textposition="inside", textinfo="label+percent+value")
        fig_pie_consultor.update_layout(title="Alumnado por Consultor", height=500)
        st.plotly_chart(fig_pie_consultor, use_container_width=True)

    # =============== Detalle por Consultor ===============
    st.markdown("### 👥 Detalle por Consultor")
    consultores_detalle = sorted(df_filtrado["CONSULTOR EIP"].dropna().unique().tolist())
    sel_detalle = st.multiselect(
        "Filtrar tabla por Consultor:",
        options=consultores_detalle,
        default=consultores_detalle
    )
    df_tabla = df_filtrado[df_filtrado["CONSULTOR EIP"].isin(sel_detalle)][
        ["CONSULTOR EIP", "NOMBRE", "APELLIDOS", "AREA", "FIN CONV"]
    ].drop_duplicates().sort_values(["CONSULTOR EIP", "APELLIDOS", "NOMBRE"]).reset_index(drop=True)
    st.dataframe(df_tabla, use_container_width=True)

    # =================== Convenios por Área y Año (SharePoint) ===================
    st.markdown("---")
    st.subheader("📁 Convenios por Área")

    if "practicas" not in st.secrets or not _secrets_ok(st.secrets["practicas"]):
        st.info("Configura las credenciales en st.secrets['practicas'] para listar convenios por área.")
        return

    sec = st.secrets["practicas"]
    try:
        token = _graph_get_token(sec["tenant_id"], sec["client_id"], sec["client_secret"])
        site_id = _get_site_id(sec["domain"], sec["site_name"], token)
        drive_id = _get_drive_id(site_id, token)
    except Exception as e:
        st.error(f"No fue posible iniciar sesión en Graph/SharePoint: {e}")
        return

    BASE = "EMPLEO/_PRÁCTICAS/Convenios firmados"
    AREAS_PATHS = {
        "BIM": "BIM",
        "CIBER": "CIBER",
        "DF": "DF",
        "DPO": "DPO",
        "EERR": "EERR",
        "FULLSTACK": "FULLSTACK",
        "IA": "IA",
        "Logística": "Logística",
        "RRHH": "RRHH",
        "SAP": "SAP",
        "MENORES": "MENORES",
    }

    # Resumen por año + fila TOTAL
    try:
        df_pivot = _convenios_por_area_y_ano(drive_id, BASE, AREAS_PATHS, token)
        df_pivot_total = _append_total_global_row(df_pivot)

        # Tabla con degradado por área (incluye fila TOTAL)
        fig_grad = _area_gradient_table(df_pivot_total)
        st.plotly_chart(fig_grad, use_container_width=True)

        # KPI total global
        if "Total" in df_pivot_total.columns and "Área" in df_pivot_total.columns:
            try:
                total_global = int(df_pivot_total.loc[df_pivot_total["Área"] == "TOTAL", "Total"].iloc[0])
            except Exception:
                year_cols = [c for c in df_pivot_total.columns if isinstance(c, int)]
                total_global = int(df_pivot_total[year_cols].sum(axis=1).sum())
        else:
            year_cols = [c for c in df_pivot.columns if isinstance(c, int)]
            total_global = int(df_pivot[year_cols].sum(axis=1).sum())

        st.metric(" Total convenios ", f"{total_global:,}".replace(",", "."))
    except Exception as e:
        st.error(f"No fue posible construir el resumen de convenios por año: {e}")
        return

    # ---------- Detalle flexible (por AÑO y/o por ÁREA) ----------
    st.markdown("#### 🔎 Detalle ")
    mode = st.radio(
        "Modo de detalle:",
        options=["Por año", "Por área", "Por año y área"],
        index=0,
        horizontal=True
    )

    year_cols = [c for c in df_pivot.columns if isinstance(c, int)]
    areas_list = list(AREAS_PATHS.keys())

    if mode == "Por año":
        if not year_cols:
            st.info("No hay años detectados en los convenios.")
            return
        default_year = max(year_cols)
        anio_sel = st.selectbox(
            "Selecciona un año:",
            options=sorted(year_cols, reverse=True),
            index=sorted(year_cols, reverse=True).index(default_year)
        )
        try:
            df_det = _detalle_por_area_y_ano(drive_id, BASE, AREAS_PATHS, token, int(anio_sel))
            st.metric("Total convenios en el año seleccionado", int(len(df_det)))
            if df_det.empty:
                st.info(f"No se han encontrado convenios en {anio_sel}.")
            else:
                st.dataframe(df_det[["Área", "Carpeta", "Archivo", "Fecha", "Link"]],
                             use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"No fue posible obtener el detalle de {anio_sel}: {e}")

    elif mode == "Por área":
        area_sel = st.selectbox("Selecciona un área:", options=areas_list)
        try:
            df_area = _detalle_area_all_years(drive_id, BASE, AREAS_PATHS, token, area_sel)
            st.metric(f"Total convenios en {area_sel}", int(len(df_area)))
            if df_area.empty:
                st.info(f"No se han encontrado convenios en el área {area_sel}.")
            else:
                st.dataframe(df_area[["Área", "Año", "Carpeta", "Archivo", "Fecha", "Link"]],
                             use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"No fue posible obtener el detalle del área {area_sel}: {e}")

    else:  # "Por año y área"
        if not year_cols:
            st.info("No hay años detectados en los convenios.")
            return
        cA, cB = st.columns(2)
        with cA:
            area_sel = st.selectbox("Área:", options=areas_list, key="area_y_ano")
        with cB:
            anio_sel = st.selectbox("Año:", options=sorted(year_cols, reverse=True), key="ano_y_area")

        try:
            df_area = _detalle_area_all_years(drive_id, BASE, AREAS_PATHS, token, area_sel)
            df_area_year = df_area[df_area["Año"] == int(anio_sel)].copy()
            st.metric(f"Total convenios en {area_sel} durante {anio_sel}", int(len(df_area_year)))
            if df_area_year.empty:
                st.info(f"No se han encontrado convenios en {area_sel} durante {anio_sel}.")
            else:
                st.dataframe(df_area_year[["Área", "Año", "Carpeta", "Archivo", "Fecha", "Link"]],
                             use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"No fue posible obtener el detalle de {area_sel} en {anio_sel}: {e}")
