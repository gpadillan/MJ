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

# ===================== LECTURA / NORMALIZACIÓN =====================

MESES_NOMBRE = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}
MONTH_NAME_TO_NUM = {v: k for k, v in MESES_NOMBRE.items()}
MESES_LIST = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
              "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

def _strip_accents(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def _norm_key(s: str) -> str:
    s = _strip_accents(str(s)).upper()
    s = re.sub(r'[^A-Z0-9 ]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

@st.cache_data(show_spinner=False)
def _read_excel_cached(path: str, mtime: float) -> pd.DataFrame:
    return pd.read_excel(path, dtype=str)

def _load_any_from_session_or_files(session_key: str, fallbacks: list[str]) -> pd.DataFrame | None:
    df = st.session_state.get(session_key)
    if isinstance(df, pd.DataFrame) and not df.empty:
        return df.copy()
    for path in fallbacks:
        if os.path.exists(path):
            try:
                mtime = os.path.getmtime(path)
                df = _read_excel_cached(path, mtime)
                st.session_state[session_key] = df.copy()
                return df
            except Exception:
                continue
    return None

def _detect_period_columns(df: pd.DataFrame, anio_actual: int) -> list[str]:
    cols = []
    for anio in range(2018, anio_actual):
        c = f"Total {anio}"
        if c in df.columns:
            cols.append(c)
    for mes in range(1, 13):
        c = f"{MESES_NOMBRE[mes]} {anio_actual}"
        if c in df.columns:
            cols.append(c)
    return cols

def _sum_by_state_aliases(df: pd.DataFrame, anio_actual: int, aliases: list[str]) -> float:
    """Suma por estado (para NO pendiente)."""
    if df is None or df.empty or ("Estado" not in df.columns):
        return 0.0
    cols = _detect_period_columns(df, anio_actual)
    if not cols:
        return 0.0
    tmp = df.copy()
    tmp["__ESTADO__"] = tmp["Estado"].apply(_norm_key)
    tmp[cols] = tmp[cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    mask = tmp["__ESTADO__"].isin([_norm_key(a) for a in aliases])
    if not mask.any():
        return 0.0
    return float(tmp.loc[mask, cols].sum().sum())

# --------- PENDIENTE: misma lógica que en las páginas de Pendiente ---------

def _split_pending_like_pages(df: pd.DataFrame, anio_actual: int, aliases: list[str]) -> tuple[float, float, float]:
    """
    Igual que en pages/deuda/pendiente.py y pagesEIM/deuda/pendiente_eim.py:
      - Pasados (< año actual): 'Total YYYY' si existe; si no, meses de ese año.
      - Año actual: meses hasta hoy -> con_deuda; meses posteriores -> futuro.
        Si no hay meses pero existe 'Total {año_actual}', se usa entero como con_deuda.
      - Futuros (> año actual): meses + (si existe) también 'Total YYYY'.
    """
    if df is None or df.empty or ("Estado" not in df.columns):
        return 0.0, 0.0, 0.0

    tmp = df.copy()
    tmp["__ESTADO__"] = tmp["Estado"].apply(_norm_key)
    mask_pend = tmp["__ESTADO__"].isin([_norm_key(a) for a in aliases])
    if not mask_pend.any():
        return 0.0, 0.0, 0.0

    all_cols = list(tmp.columns)

    def _year_from_total(col):
        try:
            return int(col.split()[-1])
        except Exception:
            return None

    col_totales = [c for c in all_cols if c.startswith("Total ") and c.split()[-1].isdigit()]
    years_totales = sorted({_year_from_total(c) for c in col_totales if _year_from_total(c) is not None})

    meses_por_año = {}
    for c in all_cols:
        for i, m in enumerate(MESES_LIST, start=1):
            if c.startswith(f"{m} "):
                try:
                    y = int(c.split()[-1])
                except Exception:
                    continue
                meses_por_año.setdefault(y, []).append((i, c))

    numeric_cols = col_totales[:]
    for y, lst in meses_por_año.items():
        numeric_cols += [col for _, col in lst]
    if numeric_cols:
        tmp[numeric_cols] = tmp[numeric_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

    mes_actual = datetime.now().month

    def _sum_cols(cols) -> float:
        if not cols:
            return 0.0
        return float(tmp.loc[mask_pend, cols].sum().sum())

    con_deuda = 0.0
    futuro    = 0.0

    all_years_present = sorted(set(years_totales) | set(meses_por_año.keys()))

    # Pasados
    for y in [yy for yy in all_years_present if yy < anio_actual]:
        if f"Total {y}" in tmp.columns:
            con_deuda += _sum_cols([f"Total {y}"])
        elif y in meses_por_año:
            cols = [col for _, col in sorted(meses_por_año[y])]
            con_deuda += _sum_cols(cols)

    # Año actual
    if anio_actual in all_years_present:
        cols_aa = [col for _, col in sorted(meses_por_año.get(anio_actual, []))]
        cols_actual  = [f"{m} {anio_actual}" for m in MESES_LIST[:mes_actual] if f"{m} {anio_actual}" in tmp.columns]
        cols_futuro  = [f"{m} {anio_actual}" for m in MESES_LIST[mes_actual:] if f"{m} {anio_actual}" in tmp.columns]

        if not cols_aa and f"Total {anio_actual}" in tmp.columns:
            con_deuda += _sum_cols([f"Total {anio_actual}"])
        else:
            con_deuda += _sum_cols(cols_actual)
            futuro    += _sum_cols(cols_futuro)

    # Futuros
    for y in [yy for yy in all_years_present if yy > anio_actual]:
        cols = []
        if y in meses_por_año:
            cols += [col for _, col in sorted(meses_por_año[y])]
        if f"Total {y}" in tmp.columns:
            cols.append(f"Total {y}")
        futuro += _sum_cols(cols)

    total = con_deuda + futuro
    return con_deuda, futuro, total

# ===================== PÁGINA =====================

def principal_page():
    st.title("Mainjobs B2C")

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

    # Rutas
    EIP_FALLBACKS = [os.path.join("uploaded", "archivo_cargado.xlsx")]
    EIM_FALLBACKS = [
        os.path.join("uploaded_eim", "archivo_cargado.xlsx"),
        os.path.join("uploaded", "archivo_cargado_eim.xlsx"),
    ]

    # Cargar DF
    df_eip = _load_any_from_session_or_files("excel_data", EIP_FALLBACKS)
    df_eim = _load_any_from_session_or_files("excel_data_eim", EIM_FALLBACKS)

    # Aliases por estado
    STATE_ALIASES = {
        "COBRADO": ["COBRADO", "COBRADO TRANSFERENCIA", "COBRADO TARJETA", "COBRO RECIBIDO"],
        "DOMICILIACION CONFIRMADA": ["DOMICILIACION CONFIRMADA", "CONFIRMADA"],
        "DOMICILIACION EMITIDA": ["DOMICILIACION EMITIDA", "EMITIDA"],
        "PENDIENTE": ["PENDIENTE", "PENDIENTE COBRO", "PENDIENTE DE COBRO", "PENDIENTE FACTURA",
                      "PENDIENTE EIM", "PENDIENTE EIP", "PENDIENTE ALUMNO"],
        "DUDOSO COBRO": ["DUDOSO COBRO", "DUDOSO"],
        "INCOBRABLE": ["INCOBRABLE", "INCROBRABLE"],
        "NO COBRADO": ["NO COBRADO", "NOCOBRADO"],
    }
    def total_estado_b2x(df: pd.DataFrame, estado_key: str) -> float:
        aliases = STATE_ALIASES.get(estado_key, [estado_key])
        return _sum_by_state_aliases(df, anio_actual, aliases)

    # Totales EIP (no pendiente)
    cob_eip   = total_estado_b2x(df_eip, "COBRADO")
    conf_eip  = total_estado_b2x(df_eip, "DOMICILIACION CONFIRMADA")
    emit_eip  = total_estado_b2x(df_eip, "DOMICILIACION EMITIDA")
    dudo_eip  = total_estado_b2x(df_eip, "DUDOSO COBRO")
    inco_eip  = total_estado_b2x(df_eip, "INCOBRABLE")
    noco_eip  = total_estado_b2x(df_eip, "NO COBRADO")

    # Totales EIM (no pendiente)
    cob_eim   = total_estado_b2x(df_eim, "COBRADO")
    conf_eim  = total_estado_b2x(df_eim, "DOMICILIACION CONFIRMADA")
    emit_eim  = total_estado_b2x(df_eim, "DOMICILIACION EMITIDA")
    dudo_eim  = total_estado_b2x(df_eim, "DUDOSO COBRO")
    inco_eim  = total_estado_b2x(df_eim, "INCOBRABLE")
    noco_eim  = total_estado_b2x(df_eim, "NO COBRADO")

    # ===== Pendiente (idéntico a las páginas) =====
    p_con_eip, p_fut_eip, p_tot_eip = _split_pending_like_pages(df_eip, anio_actual, STATE_ALIASES["PENDIENTE"])
    p_con_eim, p_fut_eim, p_tot_eim = _split_pending_like_pages(df_eim, anio_actual, STATE_ALIASES["PENDIENTE"])

    # SUMA B2C
    cob_sum   = (cob_eip or 0.0)  + (cob_eim or 0.0)
    conf_sum  = (conf_eip or 0.0) + (conf_eim or 0.0)
    emit_sum  = (emit_eip or 0.0) + (emit_eim or 0.0)
    dudo_sum  = (dudo_eip or 0.0) + (dudo_eim or 0.0)
    inco_sum  = (inco_eip or 0.0) + (inco_eim or 0.0)
    noco_sum  = (noco_eip or 0.0) + (noco_eim or 0.0)

    pendiente_con_deuda = (p_con_eip or 0.0) + (p_con_eim or 0.0)
    pendiente_futuro    = (p_fut_eip or 0.0) + (p_fut_eim or 0.0)
    pend_sum            = (p_tot_eip or 0.0) + (p_tot_eim or 0.0)
    total_gen_sum       = cob_sum + conf_sum + emit_sum

    total_gen_eip = cob_eip + conf_eip + emit_eip
    total_gen_eim = cob_eim + conf_eim + emit_eim

    # ============== TOP: SUMA EIP + EIM (8 tarjetas) ==============
    st.markdown("### 💼 Gestión de Cobro — **Suma EIP + EIM**")
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(render_bar_card("Cobrado", cob_sum, COLORS["COBRADO"], "💵​"), unsafe_allow_html=True)
    c2.markdown(render_bar_card("Domiciliación Confirmada", conf_sum, COLORS["CONFIRMADA"], "💷​"), unsafe_allow_html=True)
    c3.markdown(render_bar_card("Domiciliación Emitida", emit_sum, COLORS["EMITIDA"], "📤"), unsafe_allow_html=True)
    c4.markdown(render_bar_card("Total Generado", total_gen_sum, COLORS["TOTAL"], "💰"), unsafe_allow_html=True)

    b1, b2, b3, b4 = st.columns(4)
    # 👇 AHORA MOSTRAMOS *PENDIENTE CON DEUDA* EN LA TARJETA PRINCIPAL
    b1.markdown(render_bar_card("Pendiente", pendiente_con_deuda, COLORS["PENDIENTE"], "⏳"), unsafe_allow_html=True)
    b2.markdown(render_bar_card("Dudoso Cobro",     dudo_sum, COLORS["DUDOSO"],    "❗"), unsafe_allow_html=True)
    b3.markdown(render_bar_card("Incobrable",       inco_sum, COLORS["INCOBRABLE"],"⛔"), unsafe_allow_html=True)
    b4.markdown(render_bar_card("No Cobrado",       noco_sum, COLORS["NOCOBRADO"], "🧾"), unsafe_allow_html=True)

    # Línea del split pendiente combinado (informativa)
    st.markdown(
        f"**📌 Pendiente con deuda:** {format_euro(pendiente_con_deuda)} €&nbsp;&nbsp;|&nbsp;&nbsp;"
        f"**🔮 Pendiente futuro:** {format_euro(pendiente_futuro)} €&nbsp;&nbsp;|&nbsp;&nbsp;"
        f"**🧮 TOTAL pendiente:** {format_euro(pend_sum)} €"
    )

    # ===== Helper para bloques por ámbito =====
    def render_scope_grid(scope_label: str,
                          cob, conf, emit, total_gen,
                          pend_con_deuda, dudo, inco, noco,
                          p_con, p_fut, p_tot):
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(render_bar_card(f"Cobrado ({scope_label})", cob, COLORS["COBRADO"]), unsafe_allow_html=True)
        c2.markdown(render_bar_card(f"Confirmada ({scope_label})", conf, COLORS["CONFIRMADA"]), unsafe_allow_html=True)
        c3.markdown(render_bar_card(f"Emitida ({scope_label})", emit, COLORS["EMITIDA"]), unsafe_allow_html=True)
        c4.markdown(render_bar_card(f"Total Generado ({scope_label})", total_gen, COLORS["TOTAL"]), unsafe_allow_html=True)

        d1, d2, d3, d4 = st.columns(4)
        # 👇 EN DETALLE TAMBIÉN MOSTRAMOS *CON DEUDA* EN LA TARJETA “Pendiente (…)”
        d1.markdown(render_bar_card(f"Pendiente ({scope_label})",  pend_con_deuda, COLORS["PENDIENTE"]), unsafe_allow_html=True)
        d2.markdown(render_bar_card(f"Dudoso ({scope_label})",     dudo,       COLORS["DUDOSO"]),    unsafe_allow_html=True)
        d3.markdown(render_bar_card(f"Incobrable ({scope_label})", inco,       COLORS["INCOBRABLE"]),unsafe_allow_html=True)
        d4.markdown(render_bar_card(f"No Cobrado ({scope_label})", noco,       COLORS["NOCOBRADO"]), unsafe_allow_html=True)

        st.markdown(
            f"**📌 Pendiente con deuda ({scope_label}):** {format_euro(p_con)} €&nbsp;&nbsp;|&nbsp;&nbsp;"
            f"**🔮 Pendiente futuro ({scope_label}):** {format_euro(p_fut)} €&nbsp;&nbsp;|&nbsp;&nbsp;"
            f"**🧮 TOTAL pendiente ({scope_label}):** {format_euro(p_tot)} €"
        )

    # ===================== DETALLE POR ÁMBITO =====================
    with st.expander("📊 Ver detalle EIP", expanded=False):
        render_scope_grid(
            "EIP",
            cob_eip, conf_eip, emit_eip, total_gen_eip,
            p_con_eip, dudo_eip, inco_eip, noco_eip,   # <- tarjeta “Pendiente (EIP)” muestra con deuda
            p_con_eip, p_fut_eip, p_tot_eip
        )

    with st.expander("📊 Ver detalle EIM", expanded=False):
        render_scope_grid(
            "EIM",
            cob_eim, conf_eim, emit_eim, total_gen_eim,
            p_con_eim, dudo_eim, inco_eim, noco_eim,   # <- tarjeta “Pendiente (EIM)” muestra con deuda
            p_con_eim, p_fut_eim, p_tot_eim
        )
