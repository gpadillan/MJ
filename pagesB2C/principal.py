# pagesB2C/principal.py

import os
import re
import unicodedata
from datetime import datetime

import pandas as pd
import streamlit as st

# ===================== UTILIDADES UI =====================

def format_euro(value: float) -> str:
    try:
        v = float(value)
    except Exception:
        v = 0.0
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def render_bar_card(title: str, value, color="#E3F2FD", icon: str = ""):
    if isinstance(value, (int, float)):
        val_txt = f"€ {format_euro(value)}"
    else:
        val_txt = str(value)
    return f"""
    <div style="
        background:{color};
        border:1px solid #e6e9ef;
        border-radius:14px;
        padding:12px 14px;
        box-shadow:0 2px 8px rgba(0,0,0,.06);
        display:flex;flex-direction:column;align-items:center;justify-content:center;
        min-height:64px; gap:6px;">
        <div style="font-size:14px;font-weight:800;opacity:.9;white-space:nowrap">{icon} {title}</div>
        <div style="font-size:16px;font-weight:900">{val_txt}</div>
    </div>
    """

# ===================== LECTURA DE ARCHIVOS =====================

MESES_NOMBRE = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

def _strip_accents(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def _norm_key(s: str) -> str:
    s = _strip_accents(str(s)).upper()
    s = re.sub(r'\s+', ' ', s).strip()
    return s

@st.cache_data(show_spinner=False)
def _read_excel_cached(path: str, mtime: float) -> pd.DataFrame:
    """Lee excel con caché invalidada por la fecha de modificación (mtime)."""
    return pd.read_excel(path, dtype=str)

def _load_any_from_session_or_files(session_key: str, fallbacks: list[str]) -> pd.DataFrame | None:
    """
    1) Si hay DF en sesión, lo usa.
    2) Si no, recorre rutas fallback; si existe, lo lee con caché por mtime.
    """
    df = st.session_state.get(session_key)
    if isinstance(df, pd.DataFrame) and not df.empty:
        return df.copy()

    for path in fallbacks:
        if os.path.exists(path):
            try:
                mtime = os.path.getmtime(path)
                df = _read_excel_cached(path, mtime)
                # Guarda en sesión para el resto de páginas
                st.session_state[session_key] = df.copy()
                return df
            except Exception:
                continue
    return None

def _detect_period_columns(df: pd.DataFrame, anio_actual: int) -> list[str]:
    cols = []
    # Totales históricos (2018..año-1)
    for anio in range(2018, anio_actual):
        c = f"Total {anio}"
        if c in df.columns:
            cols.append(c)
    # Meses año actual
    for mes in range(1, 13):
        c = f"{MESES_NOMBRE[mes]} {anio_actual}"
        if c in df.columns:
            cols.append(c)
    return cols

def _totales_por_estado(df: pd.DataFrame, anio_actual: int) -> dict[str, float]:
    """
    Suma importes por 'Estado' sobre columnas de totales y meses del año actual.
    Devuelve un dict con claves normalizadas (sin acentos y en mayúsculas).
    """
    if df is None or df.empty or ("Estado" not in df.columns):
        return {}

    cols = _detect_period_columns(df, anio_actual)
    if not cols:
        return {}

    df = df.copy()
    df[cols] = df[cols].apply(pd.to_numeric, errors="coerce").fillna(0)

    df_group = (
        df.groupby("Estado", dropna=False)[cols]
          .sum()
          .reset_index()
          .rename(columns={"Estado": "EstadoRaw"})
    )
    df_group["Estado"] = df_group["EstadoRaw"].apply(_norm_key)
    df_group["Total"] = df_group[cols].sum(axis=1)

    return { row["Estado"]: float(row["Total"]) for _, row in df_group.iterrows() }

# ===================== PÁGINA =====================

def principal_page():
    st.title("Mainjobs B2C")

    # Botón de recarga manual por si el usuario quiere forzar refresco
    if st.button("🔄 Recargar datos (B2C)"):
        for k in ("excel_data", "excel_data_eim"):
            if k in st.session_state:
                del st.session_state[k]
        st.cache_data.clear()
        st.success("Caché limpiada. Datos recargados al vuelo.")

    COLORS = {
        "COBRADO": "#E3F2FD",
        "CONFIRMADA": "#FFE0B2",
        "EMITIDA": "#FFF9C4",
        "TOTAL": "#D3F9D8",
        "PENDIENTE": "#E6FCF5",
        "DUDOSO": "#FFEBEE",
        "INCOBRABLE": "#FCE4EC",
        "NOCOBRADO": "#ECEFF1",
    }

    anio_actual = datetime.now().year

    # Rutas reales publicadas por EIP/EIM
    EIP_FALLBACKS = [os.path.join("uploaded", "archivo_cargado.xlsx")]
    EIM_FALLBACKS = [
        os.path.join("uploaded_eim", "archivo_cargado.xlsx"),       # ruta que guarda EIM
        os.path.join("uploaded", "archivo_cargado_eim.xlsx"),       # compatibilidad
    ]

    # Cargar DF EIP y EIM (si no hay en sesión, lee directamente de disco)
    df_eip = _load_any_from_session_or_files("excel_data", EIP_FALLBACKS)
    df_eim = _load_any_from_session_or_files("excel_data_eim", EIM_FALLBACKS)

    # Calcular totales por estado para ambos
    tot_eip = _totales_por_estado(df_eip, anio_actual) if df_eip is not None else {}
    tot_eim = _totales_por_estado(df_eim, anio_actual) if df_eim is not None else {}

    def val(dic, key, *alias):
        keys = (key,) + alias
        for k in keys:
            if k in dic:
                return dic[k]
        return 0.0

    # ---- EIP ----
    cob_eip   = val(tot_eip, "COBRADO")
    conf_eip  = val(tot_eip, "DOMICILIACION CONFIRMADA")
    emit_eip  = val(tot_eip, "DOMICILIACION EMITIDA")
    pend_eip  = val(tot_eip, "PENDIENTE")
    dudo_eip  = val(tot_eip, "DUDOSO COBRO")
    inco_eip  = val(tot_eip, "INCOBRABLE", "INCROBRABLE")
    noco_eip  = val(tot_eip, "NO COBRADO")
    total_gen_eip = cob_eip + conf_eip + emit_eip

    # ---- EIM ----
    cob_eim   = val(tot_eim, "COBRADO")
    conf_eim  = val(tot_eim, "DOMICILIACION CONFIRMADA")
    emit_eim  = val(tot_eim, "DOMICILIACION EMITIDA")
    pend_eim  = val(tot_eim, "PENDIENTE")
    dudo_eim  = val(tot_eim, "DUDOSO COBRO")
    inco_eim  = val(tot_eim, "INCOBRABLE", "INCROBRABLE")
    noco_eim  = val(tot_eim, "NO COBRADO")
    total_gen_eim = cob_eim + conf_eim + emit_eim

    # ---- SUMA B2C (EIP + EIM) ----
    cob_sum   = cob_eip  + cob_eim
    conf_sum  = conf_eip + conf_eim
    emit_sum  = emit_eip + emit_eim
    pend_sum  = pend_eip + pend_eim
    dudo_sum  = dudo_eip + dudo_eim
    inco_sum  = inco_eip + inco_eim
    noco_sum  = noco_eip + noco_eim
    total_gen_sum = cob_sum + conf_sum + emit_sum

    # ===================== UI: TARJETAS COMBINADAS =====================
    st.markdown("### 💼 Gestión de Cobro — **Suma EIP + EIM**")
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(render_bar_card("Cobrado", cob_sum, COLORS["COBRADO"], "💵​"), unsafe_allow_html=True)
    c2.markdown(render_bar_card("Domiciliación Confirmada", conf_sum, COLORS["CONFIRMADA"], "💷​"), unsafe_allow_html=True)
    c3.markdown(render_bar_card("Domiciliación Emitida", emit_sum, COLORS["EMITIDA"], "📤"), unsafe_allow_html=True)
    c4.markdown(render_bar_card("Total Generado", total_gen_sum, COLORS["TOTAL"], "💰"), unsafe_allow_html=True)

    b1, b2, b3, b4 = st.columns(4)
    b1.markdown(render_bar_card("Pendiente",        pend_sum, COLORS["PENDIENTE"], "⏳"), unsafe_allow_html=True)
    b2.markdown(render_bar_card("Dudoso Cobro",     dudo_sum, COLORS["DUDOSO"],    "❗"), unsafe_allow_html=True)
    b3.markdown(render_bar_card("Incobrable",       inco_sum, COLORS["INCOBRABLE"],"⛔"), unsafe_allow_html=True)
    b4.markdown(render_bar_card("No Cobrado",       noco_sum, COLORS["NOCOBRADO"], "🧾"), unsafe_allow_html=True)

    # ===================== DETALLE POR ÁMBITO (Opcional en expanders) =====================
    with st.expander("📊 Ver detalle EIP"):
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(render_bar_card("Cobrado (EIP)", cob_eip, COLORS["COBRADO"]), unsafe_allow_html=True)
        c2.markdown(render_bar_card("Confirmada (EIP)", conf_eip, COLORS["CONFIRMADA"]), unsafe_allow_html=True)
        c3.markdown(render_bar_card("Emitida (EIP)", emit_eip, COLORS["EMITIDA"]), unsafe_allow_html=True)
        c4.markdown(render_bar_card("Total Generado (EIP)", total_gen_eip, COLORS["TOTAL"]), unsafe_allow_html=True)

        d1, d2, d3, d4 = st.columns(4)
        d1.markdown(render_bar_card("Pendiente (EIP)",  pend_eip, COLORS["PENDIENTE"]), unsafe_allow_html=True)
        d2.markdown(render_bar_card("Dudoso (EIP)",     dudo_eip, COLORS["DUDOSO"]), unsafe_allow_html=True)
        d3.markdown(render_bar_card("Incobrable (EIP)", inco_eip, COLORS["INCOBRABLE"]), unsafe_allow_html=True)
        d4.markdown(render_bar_card("No Cobrado (EIP)", noco_eip, COLORS["NOCOBRADO"]), unsafe_allow_html=True)

    with st.expander("📊 Ver detalle EIM"):
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(render_bar_card("Cobrado (EIM)", cob_eim, COLORS["COBRADO"]), unsafe_allow_html=True)
        c2.markdown(render_bar_card("Confirmada (EIM)", conf_eim, COLORS["CONFIRMADA"]), unsafe_allow_html=True)
        c3.markdown(render_bar_card("Emitida (EIM)", emit_eim, COLORS["EMITIDA"]), unsafe_allow_html=True)
        c4.markdown(render_bar_card("Total Generado (EIM)", total_gen_eim, COLORS["TOTAL"]), unsafe_allow_html=True)

        d1, d2, d3, d4 = st.columns(4)
        d1.markdown(render_bar_card("Pendiente (EIM)",  pend_eim, COLORS["PENDIENTE"]), unsafe_allow_html=True)
        d2.markdown(render_bar_card("Dudoso (EIM)",     dudo_eim, COLORS["DUDOSO"]), unsafe_allow_html=True)
        d3.markdown(render_bar_card("Incobrable (EIM)", inco_eim, COLORS["INCOBRABLE"]), unsafe_allow_html=True)
        d4.markdown(render_bar_card("No Cobrado (EIM)", noco_eim, COLORS["NOCOBRADO"]), unsafe_allow_html=True)

    # Nota: Por petición, NO se incluye mapa ni tabla de clientes incompletos en B2C.
