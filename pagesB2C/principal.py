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
        val_txt = f"{format_euro(value)} €"
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

# --------- PENDIENTE ---------

def _split_pending_like_pages(df: pd.DataFrame, anio_actual: int, aliases: list[str]) -> tuple[float, float, float]:
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

# ===================== PV-FE (detector y totales) =====================

def _norm_filename(s: str) -> str:
    return _strip_accents(str(s)).lower().replace(" ", "")

def _find_pvfe_file(candidates: list[str], folders_for_pattern: list[str]) -> str | None:
    for p in candidates:
        if p and os.path.exists(p):
            return p
    for folder in folders_for_pattern:
        if os.path.isdir(folder):
            for fn in os.listdir(folder):
                n = _norm_filename(fn)
                if n.startswith("listadofacturacionficticia"):
                    return os.path.join(folder, fn)
    return None

def _to_number_es(x) -> float:
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    if not s or s.lower() in {"nan", "none"}:
        return 0.0
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1]
    s = s.replace("\u00A0", " ")
    s = re.sub(r"[^0-9,\.\-\s]", "", s).replace(" ", "")
    if s.count(",") == 1 and s.rfind(",") > s.rfind("."):
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        v = float(s)
    except Exception:
        v = 0.0
    return -abs(v) if neg else v

def _resolve_pvfe_columns(cols) -> dict:
    norm_map = { _norm_key(c): c for c in cols }
    keys = list(norm_map.keys())
    def find_any(patterns):
        for p in patterns:
            if p in norm_map: return norm_map[p]
        for p in patterns:
            for k in keys:
                if p in k: return norm_map[k]
        return None
    razon  = find_any(["RAZON SOCIAL","RAZON_SOCIAL","CLIENTE","ACCOUNT NAME","NOMBRE CLIENTE","RAZON"])
    pend   = find_any(["PENDIENTE","IMPORTE PENDIENTE","PEND","SALDO PENDIENTE","DEUDA"])
    total  = find_any(["TOTAL","IMPORTE TOTAL","SUMA TOTAL"])
    estado = find_any(["ESTADO","FASE","ETAPA"])
    comer  = find_any(["COMERCIAL","PROPIETARIO","ASESOR","AGENTE","OWNER","VENDEDOR","RESPONSABLE"])
    fecha  = find_any(["FECHA FACTURA","FECHA_FACTURA","FECHA DE FACTURA","EMISION","FECHA EMISION","FECHA"])
    return {"razon":razon,"pend":pend,"total":total,"estado":estado,"comer":comer,"fecha":fecha}

def _pvfe_totals(path: str) -> tuple[float, float]:
    if not path or not os.path.exists(path):
        return 0.0, 0.0
    try:
        df = pd.read_excel(path)
    except Exception:
        return 0.0, 0.0
    cols = _resolve_pvfe_columns(df.columns)
    if not cols["total"]:
        return 0.0, 0.0
    ser = df[cols["total"]].apply(_to_number_es)
    importe_total = float(ser.sum())
    cifra_negocio = float(ser[ser > 0].sum())
    return importe_total, cifra_negocio

def _pvfe_month_options_and_sums(path: str):
    opciones = ["Todos"]
    sums_by_key = {"Todos": (0.0, 0.0)}
    if not path or not os.path.exists(path):
        return opciones, sums_by_key

    try:
        df = pd.read_excel(path)
    except Exception:
        return opciones, sums_by_key

    cols = _resolve_pvfe_columns(df.columns)
    if not cols["total"]:
        return opciones, sums_by_key

    ser_total = df[cols["total"]].apply(_to_number_es)
    sums_by_key["Todos"] = (float(ser_total.sum()), float(ser_total[ser_total > 0].sum()))

    if not cols["fecha"]:
        return opciones, sums_by_key

    g = df.copy()
    g["_fecha"] = pd.to_datetime(g[cols["fecha"]], errors="coerce", dayfirst=True)
    g = g.dropna(subset=["_fecha"])
    if g.empty:
        return opciones, sums_by_key

    g["_key_mes"] = g["_fecha"].dt.month.map(MESES_NOMBRE) + " " + g["_fecha"].dt.year.astype(int).astype(str)
    g["_total_num"] = g[cols["total"]].apply(_to_number_es)

    sums = (
        g.groupby("_key_mes")["_total_num"]
         .agg(importe_total="sum", cifra_negocio=lambda s: s[s > 0].sum())
         .reset_index()
    )

    def _mm(key):
        try:
            mes, anio = key.split()
            return int(anio), MONTH_NAME_TO_NUM.get(mes, 0)
        except Exception:
            return (0, 0)
    sums["_sort"] = sums["_key_mes"].apply(_mm)
    sums = sums.sort_values(by="_sort", ascending=False).drop(columns="_sort")

    for _, r in sums.iterrows():
        k = r["_key_mes"]
        opciones.append(k)
        sums_by_key[k] = (float(r["importe_total"]), float(r["cifra_negocio"]))

    return opciones, sums_by_key

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
        "PVFE_TOTAL": "#E8EAF6",
        "PVFE_CIFRA": "#E0F2F1",
    }

    anio_actual = datetime.now().year

    EIP_FALLBACKS = [os.path.join("uploaded", "archivo_cargado.xlsx")]
    EIM_FALLBACKS = [
        os.path.join("uploaded_eim", "archivo_cargado.xlsx"),
        os.path.join("uploaded", "archivo_cargado_eim.xlsx"),
    ]

    df_eip = _load_any_from_session_or_files("excel_data", EIP_FALLBACKS)
    df_eim = _load_any_from_session_or_files("excel_data_eim", EIM_FALLBACKS)

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

    cob_eip   = total_estado_b2x(df_eip, "COBRADO")
    conf_eip  = total_estado_b2x(df_eip, "DOMICILIACION CONFIRMADA")
    emit_eip  = total_estado_b2x(df_eip, "DOMICILIACION EMITIDA")
    dudo_eip  = total_estado_b2x(df_eip, "DUDOSO COBRO")
    inco_eip  = total_estado_b2x(df_eip, "INCOBRABLE")
    noco_eip  = total_estado_b2x(df_eip, "NO COBRADO")

    cob_eim   = total_estado_b2x(df_eim, "COBRADO")
    conf_eim  = total_estado_b2x(df_eim, "DOMICILIACION CONFIRMADA")
    emit_eim  = total_estado_b2x(df_eim, "DOMICILIACION EMITIDA")
    dudo_eim  = total_estado_b2x(df_eim, "DUDOSO COBRO")
    inco_eim  = total_estado_b2x(df_eim, "INCOBRABLE")
    noco_eim  = total_estado_b2x(df_eim, "NO COBRADO")

    p_con_eip, p_fut_eip, p_tot_eip = _split_pending_like_pages(df_eip, anio_actual, STATE_ALIASES["PENDIENTE"])
    p_con_eim, p_fut_eim, p_tot_eim = _split_pending_like_pages(df_eim, anio_actual, STATE_ALIASES["PENDIENTE"])

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

    st.markdown("### 💼 Gestión de Cobro — **Suma EIP + EIM**")
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(render_bar_card("Cobrado", cob_sum, COLORS["COBRADO"], "💵"), unsafe_allow_html=True)
    c2.markdown(render_bar_card("Domiciliación Confirmada", conf_sum, COLORS["CONFIRMADA"], "💷"), unsafe_allow_html=True)
    c3.markdown(render_bar_card("Domiciliación Emitida", emit_sum, COLORS["EMITIDA"], "📤"), unsafe_allow_html=True)
    c4.markdown(render_bar_card("Total Generado", total_gen_sum, COLORS["TOTAL"], "💰"), unsafe_allow_html=True)

    b1, b2, b3, b4 = st.columns(4)
    b1.markdown(render_bar_card("Pendiente", pendiente_con_deuda, COLORS["PENDIENTE"], "⏳"), unsafe_allow_html=True)
    b2.markdown(render_bar_card("Dudoso Cobro", dudo_sum, COLORS["DUDOSO"], "❗"), unsafe_allow_html=True)
    b3.markdown(render_bar_card("Incobrable",   inco_sum, COLORS["INCOBRABLE"], "⛔"), unsafe_allow_html=True)
    b4.markdown(render_bar_card("No Cobrado",   noco_sum, COLORS["NOCOBRADO"], "🧾"), unsafe_allow_html=True)

    st.markdown(
        f"**📌 Pendiente con deuda:** {format_euro(pendiente_con_deuda)} €&nbsp;&nbsp;|&nbsp;&nbsp;"
        f"**🔮 Pendiente futuro:** {format_euro(pendiente_futuro)} €&nbsp;&nbsp;|&nbsp;&nbsp;"
        f"**🧮 TOTAL pendiente:** {format_euro(pend_sum)} €"
    )

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
        d1.markdown(render_bar_card(f"Pendiente ({scope_label})",  pend_con_deuda, COLORS["PENDIENTE"]), unsafe_allow_html=True)
        d2.markdown(render_bar_card(f"Dudoso ({scope_label})",     dudo,       COLORS["DUDOSO"]),    unsafe_allow_html=True)
        d3.markdown(render_bar_card(f"Incobrable ({scope_label})", inco,       COLORS["INCOBRABLE"]),unsafe_allow_html=True)
        d4.markdown(render_bar_card(f"No Cobrado ({scope_label})", noco,       COLORS["NOCOBRADO"]), unsafe_allow_html=True)

        st.markdown(
            f"**📌 Pendiente con deuda ({scope_label}):** {format_euro(p_con)} €&nbsp;&nbsp;|&nbsp;&nbsp;"
            f"**🔮 Pendiente futuro ({scope_label}):** {format_euro(p_fut)} €&nbsp;&nbsp;|&nbsp;&nbsp;"
            f"**🧮 TOTAL pendiente ({scope_label}):** {format_euro(p_tot)} €"
        )

    with st.expander("📊 Ver detalle EIP", expanded=False):
        render_scope_grid(
            "EIP",
            cob_eip, conf_eip, emit_eip, total_gen_eip,
            p_con_eip, dudo_eip, inco_eip, noco_eip,
            p_con_eip, p_fut_eip, p_tot_eip
        )

    with st.expander("📊 Ver detalle EIM", expanded=False):
        render_scope_grid(
            "EIM",
            cob_eim, conf_eim, emit_eim, total_gen_eim,
            p_con_eim, dudo_eim, inco_eim, noco_eim,
            p_con_eim, p_fut_eim, p_tot_eim
        )

    # ============= PV-FE CON DESPLEGABLE POR MESES (debajo de EIM) =============
    eip_pvfe_candidates = [
        os.path.join("uploaded_admisiones", "pv_fe.xlsx"),
        os.path.join("uploaded", "pv_fe.xlsx"),
    ]
    eim_pvfe_candidates = [
        os.path.join("uploaded_eim", "pv_fe_eim.xlsx"),
        os.path.join("uploaded_eim", "pv_fe.xlsx"),
    ]
    eip_pvfe = _find_pvfe_file(eip_pvfe_candidates, folders_for_pattern=["uploaded_admisiones","uploaded"])
    eim_pvfe = _find_pvfe_file(eim_pvfe_candidates, folders_for_pattern=["uploaded_eim"])

    eip_opts, eip_sums = _pvfe_month_options_and_sums(eip_pvfe)
    eim_opts, eim_sums = _pvfe_month_options_and_sums(eim_pvfe)

    meses_all = set(eip_opts + eim_opts)
    meses_all.discard("Todos")
    def _sort_key_month(mk: str):
        try:
            mes, anio = mk.split()
            return (int(anio), MONTH_NAME_TO_NUM.get(mes, 0))
        except Exception:
            return (0, 0)
    opciones_combinadas = ["Todos"] + sorted(meses_all, key=_sort_key_month, reverse=True)

    st.markdown("### 📄 Facturación Ficticia (PV-FE) — **EIP + EIM**")
    st.caption("Filtra por mes (detectado por la fecha de factura). Si el archivo no tiene fecha, solo aparece ‘Todos’.")
    sel_mes = st.selectbox("Selecciona mes PV-FE:", opciones_combinadas, index=0)

    eip_imp, eip_cifra = eip_sums.get(sel_mes, eip_sums.get("Todos", (0.0, 0.0)))
    eim_imp, eim_cifra = eim_sums.get(sel_mes, eim_sums.get("Todos", (0.0, 0.0)))

    pvfe_importe_total_sum = (eip_imp or 0.0) + (eim_imp or 0.0)
    pvfe_cifra_sum         = (eip_cifra or 0.0) + (eim_cifra or 0.0)

    k1, k2 = st.columns(2)
    k1.markdown(
        render_bar_card(f"Cifra de Negocio (EIP+EIM) — {sel_mes}", pvfe_importe_total_sum, COLORS["PVFE_TOTAL"], "🧾"),
        unsafe_allow_html=True
    )
    k2.markdown(
        render_bar_card(f"Importe Total FE (EIP+EIM) — {sel_mes}", pvfe_cifra_sum, COLORS["PVFE_CIFRA"], "🏷️"),
        unsafe_allow_html=True
    )

    # ---- Desglose: MISMO ORDEN EN AMBOS LADOS (Importe total FE -> Cifra de negocio)
    with st.expander("Ver desglose por ámbito (PV-FE)", expanded=False):
        c1, c2 = st.columns(2)
        # EIP
        c1.markdown(render_bar_card(f"EIP · Cifra de negocio — {sel_mes}", eip_imp, "#F3DAF7"), unsafe_allow_html=True)
        c1.markdown(render_bar_card(f"EIP · Importe total FE — {sel_mes}", eip_cifra, "#DBFFFD"), unsafe_allow_html=True)
        # EIM
        c2.markdown(render_bar_card(f"EIM · Cifra de negocio  — {sel_mes}", eim_imp, "#F3DAF7"), unsafe_allow_html=True)
        c2.markdown(render_bar_card(f"EIM · Importe total FE — {sel_mes}", eim_cifra, "#DBFFFD"), unsafe_allow_html=True)
