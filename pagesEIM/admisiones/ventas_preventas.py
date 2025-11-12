# pagesEIM/ventas_preventas.py
# -*- coding: utf-8 -*-
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import os
import unicodedata
import re
from datetime import datetime
from io import BytesIO
from responsive import get_screen_size

# =========================
# RUTAS / CONSTANTES (EIM)
# =========================
UPLOAD_FOLDER   = "uploaded_eim"
VENTAS_FILE     = os.path.join(UPLOAD_FOLDER, "ventas_eim.xlsx")
PREVENTAS_FILE  = os.path.join(UPLOAD_FOLDER, "preventas_eim.xlsx")
PVFE_FILE       = os.path.join(UPLOAD_FOLDER, "pv_fe_eim.xlsx")   # si no existe busco por 'listadoFacturacionFicticia*'
ANIO_ACTUAL     = datetime.now().year  # ← año en curso

# Tamaño de los "cuadrados" (tiles)
TILE_WIDTH_PX   = 160
TILE_HEIGHT_PX  = 64
TILE_PAD_V      = 8
TILE_PAD_H      = 10
TILE_RADIUS_PX  = 10

# Pasteles (ajusta si quieres aún más claro)
OWNER_HEADER_LIGHTEN = 0.82
OWNER_BLOCK_LIGHTEN  = 0.92

# ===== Colores configurables por programa (opcional) =====
PROGRAM_COLOR_MAP = {
    "MÁSTER IA": "#3B82F6",
    "MÁSTER CIBERSEGURIDAD": "#EF4444",
    "MÁSTER RRHH": "#10B981",
    "MÁSTER DPO": "#F65CE2",
    "MÁSTER EERR": "#F59E0B",
    "CERTIFICACIÓN SAP S/4HANA": "#7C3AED",
    "MBA + RRHH": "#14B8A6",
    "PROGRAMA CALIFORNIA": "#F97316",
}

# =========================
# UTILIDADES
# =========================
def _strip_accents_lower(s: str) -> str:
    if not isinstance(s, str): return ""
    s = s.strip().lower()
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def _norm(s: str) -> str:
    s = s or ""
    s = str(s).strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    s = re.sub(r"\s+", " ", s)
    return s

def _alias_comercial(s: str) -> str:
    if not isinstance(s, str): return ""
    raw = s.strip()
    if " " not in raw:
        return raw.lower()
    parts = _norm(raw).split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1]).lower()
    return parts[0].lower()

def month_label(ts: pd.Timestamp | None) -> str:
    if pd.isna(ts): return ""
    meses = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}
    return f"{meses[ts.month]} {ts.year}"

def euro_es(n) -> str:
    try:
        f = float(n)
    except Exception:
        return "0 €"
    s = f"{f:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if s.endswith(",00"): s = s[:-3]
    return f"{s} €"

def lighten_hex(hex_color: str, factor: float = 0.85) -> str:
    try:
        h = hex_color.lstrip("#")
        if len(h) == 3:
            h = "".join([c*2 for c in h])
        r = int(h[0:2], 16); g = int(h[2:4], 16); b = int(h[4:6], 16)
        rl = int(r + (255 - r) * factor)
        gl = int(g + (255 - g) * factor)
        bl = int(b + (255 - b) * factor)
        return f"#{rl:02x}{gl:02x}{bl:02x}"
    except Exception:
        return "#f5f7fa"

# ========= Abreviar nombres de programa (para tiles y gráficos) EN MAYÚSCULAS =========
def abreviar_programa(nombre: str) -> str:
    base = _strip_accents_lower(nombre)
    if "ciber" in base or "hacking" in base or "ofensiva" in base:
        return "CIBER"
    if "sap" in base or "s/4hana" in base or "s 4 hana" in base:
        return "SAP"
    if "inteligencia artificial" in base or base.startswith("master ia") or base.startswith("máster ia") or base == "ia":
        return "IA"
    if "dpo" in base or "proteccion de datos" in base or "compliance" in base:
        return "DPO"
    if "rrhh" in base or "recursos humanos" in base:
        return "RRHH"
    if "energ" in base or "eerr" in base or "renovabl" in base:
        return "EERR"
    if "blackwell" in base:
        return "BLACKWELL"
    return nombre.upper() if isinstance(nombre, str) else nombre

# =========================
# CATEGORÍAS (para nombre_unificado)
# =========================
CATEGORIAS_KEYWORDS = {
    "MÁSTER CIBERSEGURIDAD": ["ciber","ciberseguridad","hacking","etico","seguridad ofensiva","seguridad informatica","ethical hacking","ofensiva"],
    "MÁSTER RRHH": ["rrhh","recursos humanos","gestion laboral","human resources"],
    "MÁSTER EERR": ["eerr","energias","energia","renovables","energetica"],
    "MÁSTER DPO": ["dpo","delegado de proteccion de datos","proteccion de datos","privacidad","rgpd","gdpr"],
    "MÁSTER IA": ["ia","inteligencia artificial","machine learning","aprendizaje automatico"],
    "CERTIFICACIÓN SAP S/4HANA": ["sap","s/4hana","certificacion sap","sap s4hana","sap s 4 hana"],
    "MBA + RRHH": ["mba rrhh","mba + rrhh","mba y rrhh","mba recursos humanos"],
    "PROGRAMA CALIFORNIA": ["california","programa california"],
}
def unificar_nombre(valor_original: str) -> str:
    if not isinstance(valor_original, str) or not valor_original.strip(): return valor_original
    base = _strip_accents_lower(valor_original)
    for categoria, kws in CATEGORIAS_KEYWORDS.items():
        for kw in kws:
            if kw in base: return categoria
    return valor_original

# =========================
# RESOLVER COLUMNAS PV-FE (robusto)
# =========================
def _resolver_columnas(cols):
    norm_map = {_norm(c): c for c in cols}
    keys = list(norm_map.keys())

    def find_any(patterns):
        for p in patterns:
            if p in norm_map: return norm_map[p]
        for p in patterns:
            for k in keys:
                if p in k: return norm_map[k]
        return None

    razon   = find_any(["razon social","razon_social","cliente","account name","nombre cliente","razon"])
    pend    = find_any(["pendiente","importe pendiente","pend","saldo pendiente","deuda"])
    total   = find_any(["total","importe total","suma total"])
    estado  = find_any(["estado","fase","etapa"])
    comer   = find_any(["comercial","propietario","asesor","agente","owner","vendedor","responsable"])
    fecha   = find_any(["fecha factura","fecha_factura","fecha de factura","emision","fecha emision"])
    proy    = find_any(["proyecto","nombre proyecto","proyecto/curso","curso","programa","producto","concepto","nombre del curso","nombre del programa"])

    return {
        "razon": razon, "pend": pend, "total": total, "estado": estado,
        "comer": comer, "fecha": fecha, "proy": proy
    }

def _encontrar_archivo_pvfe():
    if os.path.exists(PVFE_FILE): return PVFE_FILE
    if os.path.isdir(UPLOAD_FOLDER):
        for fn in os.listdir(UPLOAD_FOLDER):
            if _norm(fn).startswith("listadofacturacionficticia"):
                return os.path.join(UPLOAD_FOLDER, fn)
    return None

# =========================
# MODO PV-FE SOLO (si no hay ventas/preventas)
# =========================
def _pvfe_only_mode():
    st.subheader("📊 Facturación Ficticia — EIM (modo PV-FE)")

    traducciones_meses = {
        "January":"Enero","February":"Febrero","March":"Marzo","April":"Abril",
        "May":"Mayo","June":"Junio","July":"Julio","August":"Agosto",
        "September":"Septiembre","October":"Octubre","November":"Noviembre","December":"Diciembre"
    }

    pvfe_path = _encontrar_archivo_pvfe()
    if not pvfe_path or not os.path.exists(pvfe_path):
        st.info("📭 Sube el archivo PV-FE (EIM) para ver los datos.")
        return

    try:
        df = pd.read_excel(pvfe_path)
    except Exception as e:
        st.error(f"No se pudo leer PV-FE: {e}")
        return

    cols = _resolver_columnas(df.columns)
    vista = df.copy()

    # Fecha y mes
    if cols["fecha"]:
        vista["_fecha"]  = pd.to_datetime(vista[cols["fecha"]], errors="coerce", dayfirst=True)
        vista["_mes_es"] = vista["_fecha"].dt.month_name().map(traducciones_meses)
    else:
        vista["_fecha"] = pd.NaT
        vista["_mes_es"] = ""

    # Comercial (alias)
    if cols["comer"]:
        vista["_alias"] = vista[cols["comer"]].astype(str).apply(_alias_comercial)
    else:
        vista["_alias"] = "-"

    # Importes
    vista["_pend"]  = pd.to_numeric(vista[cols["pend"]], errors="coerce").fillna(0) if cols["pend"] else 0
    vista["_total"] = pd.to_numeric(vista[cols["total"]], errors="coerce").fillna(0) if cols["total"] else 0

    # Selectores (mes / comercial) basados SOLO en PV-FE
    meses = ["Todos"] + [m for m in vista["_mes_es"].dropna().unique().tolist() if m]
    mes_sel = st.selectbox("Filtrar por mes:", meses, index=0)

    vista_mes = vista if mes_sel == "Todos" else vista[vista["_mes_es"] == mes_sel].copy()
    comerciales = ["Todos"] + sorted(vista_mes["_alias"].dropna().unique().tolist())
    com_sel = st.selectbox("Filtrar por comercial:", comerciales, index=0)

    if com_sel != "Todos":
        vista_mes = vista_mes[vista_mes["_alias"] == com_sel]

    # KPIs
    regs = int(vista_mes.shape[0])
    pendiente = float(vista_mes["_pend"].sum())
    total_fe = float(vista_mes["_total"].sum())
    cifra_negocio = float(vista_mes.loc[vista_mes["_total"] > 0, "_total"].sum())

    k1,k2,k3,k4 = st.columns(4)
    with k1:
        st.markdown(f"<div style='padding:1rem;background:#f1f3f6;border-left:5px solid #7f3fbf;border-radius:8px;'><h4 style='margin:0'>Registros FE</h4><p style='font-size:1.5rem;font-weight:700;margin:0'>{regs}</p></div>", unsafe_allow_html=True)
    with k2:
        st.markdown(f"<div style='padding:1rem;background:#f1f3f6;border-left:5px solid #0ea5e9;border-radius:8px;'><h4 style='margin:0'>Importe total FE</h4><p style='font-size:1.5rem;font-weight:700;margin:0'>{euro_es(total_fe)}</p></div>", unsafe_allow_html=True)
    with k3:
        st.markdown(f"<div style='padding:1rem;background:#f1f3f6;border-left:5px solid #2ca02c;border-radius:8px;'><h4 style='margin:0'>Cifra de negocio</h4><p style='font-size:1.5rem;font-weight:700;margin:0'>{euro_es(cifra_negocio)}</p></div>", unsafe_allow_html=True)
    with k4:
        st.markdown(f"<div style='padding:1rem;background:#f1f3f6;border-left:5px solid #ef4444;border-radius:8px;'><h4 style='margin:0'>Pendiente</h4><p style='font-size:1.5rem;font-weight:700;margin:0'>{euro_es(pendiente)}</p></div>", unsafe_allow_html=True)

    # Tabla resumida por Razón Social (similar a tu vista rápida)
    rows = []
    key_razon = cols["razon"] if cols["razon"] else None

    def _join_unique(iterable):
        out, seen = [], set()
        for x in iterable:
            sx = str(x).strip()
            if sx and sx not in seen:
                out.append(sx); seen.add(sx)
        return " / ".join(out)

    base = vista_mes.copy()
    if key_razon:
        base["_key"] = base[key_razon].astype(str).str.strip().str.lower()
        groups = base.groupby("_key", dropna=False)
    else:
        groups = [(i, gg) for i, gg in enumerate([base])]

    for _, g in groups:
        razon = g[key_razon].dropna().astype(str).str.strip().iloc[0] if key_razon else ""
        proyecto = _join_unique(g[cols["proy"]].dropna()) if cols["proy"] else ""
        fechas = g["_fecha"].dropna().dt.strftime("%d/%m/%Y").tolist()
        fechas_text = " / ".join(sorted(set([f for f in fechas if f])))
        pendiente_g = g["_pend"].sum()
        totales = g["_total"].dropna().tolist()
        if totales:
            suma = sum(totales)
            parts = [f"{int(v)}" if abs(v-int(v))<1e-9 else f"{v:g}" for v in totales]
            total_text = f"{' / '.join(parts)} = {euro_es(suma)}"
        else:
            total_text = ""
        estado = ""
        if cols["estado"]:
            estados = [str(x).strip().upper() for x in g[cols["estado"]].dropna() if str(x).strip()]
            estado = " / ".join(sorted(set(estados)))
        comercial = ""
        if cols["comer"]:
            alias_vals = [_alias_comercial(x) for x in g[cols["comer"]].dropna().astype(str) if x.strip()]
            comercial = " / ".join(sorted(set(alias_vals)))

        rows.append({
            "Razón Social": razon,
            "Proyecto": proyecto,
            "Fecha Factura": fechas_text,
            "Pendiente": pendiente_g,
            "Total": total_text,
            "Estado": estado,
            "Comercial (alias)": comercial,
        })

    if rows:
        final = pd.DataFrame(rows).sort_values(by="Pendiente", ascending=False, na_position="last")
        st.dataframe(final, use_container_width=True)

    # Export por comercial
    resumen_alias = (
        base.groupby("_alias", dropna=False)
            .agg(
                pv_regs=("_alias","size"),
                pv_pend=("_pend","sum"),
                pv_total=("_total","sum"),
            ).reset_index()
    )
    resumen_alias["pv_cifra"] = (
        base.groupby("_alias")["_total"].apply(lambda s: s[s>0].sum()).reindex(resumen_alias["_alias"]).reset_index(drop=True)
    )

    if not resumen_alias.empty:
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
            resumen_alias.rename(columns={
                "_alias":"Comercial (alias)",
                "pv_regs":"FE - Registros",
                "pv_pend":"FE - Pendiente (€)",
                "pv_total":"FE - Importe total (€)",
                "pv_cifra":"FE - Cifra de negocio (€)"
            }).to_excel(w, index=False, sheet_name="Resumen")
        st.download_button(
            "⬇️ Descargar resumen FE por comercial (Excel)",
            buf.getvalue(),
            "EIM_PVFE_por_comercial.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# =========================
# APP
# =========================
def app():
    st.subheader("📊 Ventas y Preventas — EIM")
    try:
        width, height = get_screen_size()
        if not width or not height: raise Exception()
    except Exception:
        width, height = 1000, 600

    traducciones_meses = {
        "January":"Enero","February":"Febrero","March":"Marzo","April":"Abril",
        "May":"Mayo","June":"Junio","July":"Julio","August":"Agosto",
        "September":"Septiembre","October":"Octubre","November":"Noviembre","December":"Diciembre"
    }
    orden_meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

    # ======= NUEVO: si no hay Ventas -> modo PV-FE SOLO (sin warnings) =======
    if not os.path.exists(VENTAS_FILE):
        _pvfe_only_mode()
        return

    # ======= VENTAS =======
    df_ventas = pd.read_excel(VENTAS_FILE)
    df_ventas.rename(columns={c: _strip_accents_lower(c) for c in df_ventas.columns}, inplace=True)
    if "nombre" not in df_ventas.columns or "propietario" not in df_ventas.columns:
        st.warning("❌ El archivo de ventas (EIM) debe tener columnas 'nombre' y 'propietario'.")
        return

    if "importe" in df_ventas.columns:
        df_ventas["importe"] = pd.to_numeric(df_ventas["importe"], errors="coerce").fillna(0)

    if "fecha de cierre" not in df_ventas.columns:
        st.warning("❌ El archivo de ventas (EIM) no contiene la columna 'fecha de cierre'.")
        return

    df_ventas["fecha de cierre"] = pd.to_datetime(df_ventas["fecha de cierre"], errors="coerce")
    df_ventas = df_ventas[df_ventas["fecha de cierre"].dt.year == ANIO_ACTUAL]
    if df_ventas.empty:
        st.warning(f"❌ No hay datos de ventas (EIM) para el año seleccionado ({ANIO_ACTUAL}).")
        return

    df_ventas["mes"]     = df_ventas["fecha de cierre"].dt.month_name().map(traducciones_meses)
    df_ventas["mes_num"] = df_ventas["fecha de cierre"].dt.month
    df_ventas["nombre_unificado"] = df_ventas["nombre"].apply(unificar_nombre)
    df_ventas["prog_corto"] = df_ventas["nombre_unificado"].apply(abreviar_programa)

    # ======= PREVENTAS (opcional) =======
    if os.path.exists(PREVENTAS_FILE):
        df_preventas = pd.read_excel(PREVENTAS_FILE)
        df_preventas.rename(columns={c: _strip_accents_lower(c) for c in df_preventas.columns}, inplace=True)
        columnas_importe = [col for col in df_preventas.columns if "importe" in col]
    else:
        df_preventas = None
        columnas_importe = []

    # ======= UI =======
    meses_disponibles = (
        df_ventas[["mes","mes_num"]].dropna().drop_duplicates().sort_values(["mes_num"], ascending=False)
    )
    opciones_meses = ["Todos"] + meses_disponibles["mes"].tolist()
    mes_seleccionado = st.selectbox("Selecciona un Mes:", opciones_meses)

    # Base por mes (para poblar propietarios del mes)
    df_ventas_filtrado_mes = df_ventas if mes_seleccionado == "Todos" else df_ventas[df_ventas["mes"] == mes_seleccionado].copy()
    propietarios_disponibles = sorted(df_ventas_filtrado_mes["propietario"].dropna().unique().tolist())

    selected_propietario = st.selectbox(
        "Selecciona propietario:",
        options=["Todos"] + propietarios_disponibles,
        index=0
    )
    is_all = (selected_propietario == "Todos")
    selected_alias = _alias_comercial(selected_propietario) if not is_all else None

    # Helpers de filtrado por propietario
    def _filtrar_por_propietario(df, col="propietario"):
        if is_all:
            return df
        if col in df.columns:
            return df[df[col] == selected_propietario]
        return df

    # Data para KPIs y gráficos
    df_ventas_all_owner = _filtrar_por_propietario(df_ventas.copy(), col="propietario")
    df_ventas_filtrado = _filtrar_por_propietario(df_ventas_filtrado_mes.copy(), col="propietario")

    titulo_periodo = mes_seleccionado if mes_seleccionado != "Todos" else f"Año {ANIO_ACTUAL}"
    st.markdown(f"### {titulo_periodo}")

    # ======= CÁLCULO RÁPIDO FE (KPIs, desde PV-FE) =======
    pvfe_total_importe_filtrado = 0.0
    pvfe_cifra_negocio_filtrado = 0.0
    pvfe_path_preview = _encontrar_archivo_pvfe()
    if pvfe_path_preview and os.path.exists(pvfe_path_preview):
        try:
            _df_pvfe_prev = pd.read_excel(pvfe_path_preview)
            _cols_prev = _resolver_columnas(_df_pvfe_prev.columns)
            _dfp_prev = _df_pvfe_prev.copy()

            # Fecha/Mes
            if _cols_prev["fecha"]:
                _dfp_prev["_fecha"] = pd.to_datetime(_dfp_prev[_cols_prev["fecha"]], errors="coerce", dayfirst=True)
                _dfp_prev["_mes_es"] = _dfp_prev["_fecha"].dt.month_name().map(traducciones_meses)
                if mes_seleccionado != "Todos":
                    _dfp_prev = _dfp_prev[_dfp_prev["_mes_es"] == mes_seleccionado]

            # Filtrado por propietario (alias)
            if _cols_prev["comer"] and not is_all:
                _dfp_prev["_alias"] = _dfp_prev[_cols_prev["comer"]].astype(str).apply(_alias_comercial)
                _dfp_prev = _dfp_prev[_dfp_prev["_alias"] == selected_alias]

            if _cols_prev["total"]:
                tot_series = pd.to_numeric(_dfp_prev[_cols_prev["total"]], errors="coerce").fillna(0)
                pvfe_total_importe_filtrado = float(tot_series.sum())
                pvfe_cifra_negocio_filtrado = float(tot_series[tot_series > 0].sum())
        except Exception:
            pvfe_total_importe_filtrado = 0.0
            pvfe_cifra_negocio_filtrado = 0.0

    # ======= TARJETAS DE TOTALES =======
    total_importe_clientify = float(df_ventas_filtrado["importe"].sum()) if "importe" in df_ventas_filtrado.columns else 0.0
    cifra_negocio = pvfe_cifra_negocio_filtrado
    total_importe_fe = pvfe_total_importe_filtrado
    matriculas_count = int(df_ventas_all_owner.shape[0]) if mes_seleccionado == "Todos" else int(df_ventas_filtrado.shape[0])

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f"""
            <div style='padding:1rem;background:#f1f3f6;border-left:5px solid #FF0000;border-radius:8px;'>
                <h4 style='margin:0'>Importe total Clientify</h4>
                <p style='font-size:1.5rem;font-weight:700;margin:0'>{euro_es(total_importe_clientify)}</p>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div style='padding:1rem;background:#f1f3f6;border-left:5px solid #0ea5e9;border-radius:8px;'>
                <h4 style='margin:0'>Importe total FE</h4>
                <p style='font-size:1.5rem;font-weight:700;margin:0'>{euro_es(cifra_negocio)}</p>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
            <div style='padding:1rem;background:#f1f3f6;border-left:5px solid #7f3fbf;border-radius:8px;'>
                <h4 style='margin:0'>Cifra de negocio</h4>
                <p style='font-size:1.5rem;font-weight:700;margin:0'>{euro_es(total_importe_fe)}</p>
            </div>
        """, unsafe_allow_html=True)
    with col4:
        titulo_matriculas = f"Matrículas ({mes_seleccionado})" if mes_seleccionado != "Todos" else f"Matrículas ({ANIO_ACTUAL})"
        st.markdown(f"""
            <div style='padding:1rem;background:#f1f3f6;border-left:5px solid #2ca02c;border-radius:8px;'>
                <h4 style='margin:0'>{titulo_matriculas}</h4>
                <p style='font-size:1.5rem;font-weight:700;margin:0'>{matriculas_count}</p>
            </div>
        """, unsafe_allow_html=True)
    with col5:
        if df_preventas is not None and not df_preventas.empty:
            dft_prev = df_preventas.copy()
            owner_cols_prev = [c for c in dft_prev.columns if any(x in c for x in ["propietario","comercial","asesor","owner","vendedor","responsable"])]
            if owner_cols_prev:
                ocol_prev = owner_cols_prev[0]
                dft_prev["_alias"] = dft_prev[ocol_prev].astype(str).apply(_alias_comercial)
                if not is_all:
                    dft_prev = dft_prev[dft_prev["_alias"] == selected_alias]
            columnas_importe_prev = [col for col in dft_prev.columns if "importe" in col]
            total_preventas_importe = dft_prev[columnas_importe_prev].sum(numeric_only=True).sum() if columnas_importe_prev else 0
            total_preventas_count   = dft_prev.shape[0]
        else:
            total_preventas_importe = 0
            total_preventas_count   = 0

        st.markdown(f"""
            <div style='padding:1rem;background:#f1f3f6;border-left:5px solid #BF00BF;border-radius:8px;'>
                <h4 style='margin:0'>Prematriculas</h4>
                <p style='font-size:1.5rem;font-weight:700;margin:0'>{euro_es(total_preventas_importe)} ({total_preventas_count})</p>
            </div>
        """, unsafe_allow_html=True)

    # ======= RESUMEN & COLORES =======
    df_ventas_filtrado["prog_corto"] = df_ventas_filtrado["nombre_unificado"].apply(abreviar_programa)
    resumen = df_ventas_filtrado.groupby(["prog_corto","propietario"]).size().reset_index(name="Total Matrículas")
    totales_propietario = resumen.groupby("propietario")["Total Matrículas"].sum().reset_index()
    totales_propietario["propietario_display"] = totales_propietario.apply(
        lambda r: f"{r['propietario']} ({r['Total Matrículas']})", axis=1
    )
    resumen = resumen.merge(totales_propietario[["propietario","propietario_display"]], on="propietario", how="left")

    orden_propietarios = (
        totales_propietario.sort_values(by="Total Matrículas", ascending=False)["propietario_display"].tolist()
    )
    orden_masters = (
        resumen.groupby("prog_corto")["Total Matrículas"].sum().sort_values(ascending=False).index.tolist()
    )

    base_palette = px.colors.qualitative.Plotly + px.colors.qualitative.D3 + px.colors.qualitative.Alphabet

    def _build_prog_color_map(programas):
        cmap = {}
        for p in programas:
            if p in PROGRAM_COLOR_MAP:
                cmap[p] = PROGRAM_COLOR_MAP[p]
        idx = 0
        for p in programas:
            if p not in cmap:
                cmap[p] = base_palette[idx % len(base_palette)]
                idx += 1
        return cmap

    resumen_prop_disp = sorted(resumen["propietario_display"].dropna().unique())
    color_map_display = {p: base_palette[i % len(base_palette)] for i, p in enumerate(resumen_prop_disp)}
    owner_color_map = {p.split(" (")[0]: color_map_display[p] for p in color_map_display}
    owners_in_chart = set(resumen["propietario"].unique())

    # ======= GRÁFICO =======
    if mes_seleccionado == "Todos":
        df_bar_base = df_ventas_all_owner.copy()
        df_bar = df_bar_base.groupby(["mes","propietario"], dropna=False).size().reset_index(name="Total Matrículas")
        tot_mes = df_bar.groupby("mes")["Total Matrículas"].sum().to_dict()
        df_bar["mes_etiqueta"] = df_bar["mes"].apply(lambda m: f"{m} ({tot_mes.get(m,0)})" if pd.notna(m) else m)
        orden_mes_etiqueta = [f"{m} ({tot_mes[m]})" for m in orden_meses if m in tot_mes]
        df_bar = df_bar.merge(totales_propietario[["propietario","propietario_display"]], on="propietario", how="left")

        fig = px.bar(
            df_bar, x="mes_etiqueta", y="Total Matrículas",
            color="propietario_display", color_discrete_map=color_map_display,
            barmode="group", text="Total Matrículas",
            title=f"Distribución Mensual de Matrículas por Propietario — {ANIO_ACTUAL}",
            width=width, height=height
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            xaxis_title="Mes", yaxis_title="Total Matrículas",
            margin=dict(l=20,r=20,t=40,b=140),
            xaxis=dict(categoryorder="array", categoryarray=orden_mes_etiqueta),
            legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        fig = px.scatter(
            resumen, x="prog_corto", y="propietario_display",
            size="Total Matrículas", color="propietario_display",
            color_discrete_map=color_map_display, text="Total Matrículas",
            size_max=60, width=width, height=height
        )
        fig.update_traces(
            textposition="middle center", textfont_size=12, textfont_color="white",
            marker=dict(line=dict(color="black", width=1.2))
        )
        fig.update_layout(
            xaxis_title="Programa (abreviado)", yaxis_title="Propietario",
            legend=dict(orientation="v", yanchor="top", y=0.98, xanchor="left", x=1.02),
            margin=dict(l=20,r=20,t=40,b=80)
        )
        fig.update_yaxes(categoryorder="array", categoryarray=orden_propietarios[::-1])
        fig.update_xaxes(categoryorder="array", categoryarray=orden_masters)
        st.plotly_chart(fig, use_container_width=True)

    # ==============================================================
    # IMPORTE POR MÁSTER / PROGRAMA + PANEL DERECHA
    # ==============================================================
    st.markdown("---")
    hdr_col, legend_col = st.columns([0.74, 0.26])
    with hdr_col:
        st.subheader("Importe por Programa / Clientify (EIM)")

    programas_all = sorted(df_ventas["nombre_unificado"].dropna().unique().tolist())
    prog_color_map = _build_prog_color_map(programas_all)

    # ----- Mini componentes HTML -----
    def _tile(programa_display: str, n: int, amount: float, color: str) -> str:
        return f"""
        <div style="
            display:inline-flex; flex-direction:column; justify-content:center;
            width:{TILE_WIDTH_PX}px; min-height:{TILE_HEIGHT_PX}px;
            padding:{TILE_PAD_V}px {TILE_PAD_H}px; margin:6px 8px 6px 0;
            border-radius:{TILE_RADIUS_PX}px; background:{color}; color:#fff;
            box-shadow:0 2px 6px rgba(0,0,0,.08); border:1px solid rgba(0,0,0,.15);">
            <div style="font-weight:900; font-size:.80rem; white-space:normal; word-break:break-word; line-height:1.15;">
                {programa_display}
            </div>
            <div style="display:flex; gap:8px; margin-top:6px; align-items:center; flex-wrap:wrap;">
                <span style="font-weight:800; font-size:.72rem; opacity:.95;">{int(n)} matr.</span>
                <span style="font-weight:900; font-size:.80rem;">{euro_es(amount)}</span>
            </div>
        </div>
        """

    def _total_tile(total_amount: float, total_count: int) -> str:
        return f"""
        <div style="
            display:inline-flex; flex-direction:column; justify-content:center;
            width:{TILE_WIDTH_PX}px; min-height:{TILE_HEIGHT_PX}px;
            padding:{TILE_PAD_V}px {TILE_PAD_H}px; margin:6px 0 6px 8px;
            border-radius:{TILE_RADIUS_PX}px; background:#fff; color:#111;
            box-shadow:0 2px 6px rgba(0,0,0,.14); border:1px solid rgba(0,0,0,.25);">
            <div style="font-weight:900; font-size:.80rem;">TOTAL</div>
            <div style="display:flex; gap:8px; margin-top:6px; align-items:center;">
                <span style="font-weight:800; font-size:.72rem;">{int(total_count)} matr.</span>
                <span style="font-weight:900; font-size:.80rem;">{euro_es(total_amount)}</span>
            </div>
        </div>
        """

    def _mes_header(mes: str) -> str:
        return f"""
        <div style="display:inline-flex; align-items:center; justify-content:center;
            height:{TILE_HEIGHT_PX}px; padding:{TILE_PAD_V}px {TILE_PAD_H}px; margin:6px 12px 6px 0;
            background:#eef0f4; color:#111; border:1px solid #e0e3e8; border-radius:{TILE_RADIUS_PX}px;
            min-width:110px; font-weight:900;">{mes}</div>
        """

    def _row_scroll(html_inside: str) -> str:
        return f"""
        <div style="display:flex; align-items:flex-start; gap:12px; overflow-x:auto; white-space:nowrap;
                    padding:4px 2px 10px 2px; border-bottom:1px solid #efefef;">
            {html_inside}
        </div>
        """

    # Panel derecho — devuelve también el orden de programas (por importe desc)
    def _legend_totales_panel(base_df: pd.DataFrame):
        order_prog = []
        if base_df.empty:
            legend_col.info("Sin datos.")
            return order_prog

        # --- Totales por programa (nombre completo) ---
        tmp_full = base_df.copy()
        tot_prog = (
            tmp_full.groupby("nombre_unificado")
                    .agg(matr=("nombre_unificado","size"), imp=("importe","sum"))
                    .reset_index()
                    .sort_values("imp", ascending=False)
        )
        order_prog = tot_prog["nombre_unificado"].tolist()

        items = []
        for _, r in tot_prog.iterrows():
            color = prog_color_map.get(r["nombre_unificado"], "#6c757d")
            items.append(f"""
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
              <span style="display:inline-block; width:14px; height:14px; border-radius:3px; background:{color}; border:1px solid rgba(0,0,0,.25);"></span>
              <div style="flex:1; font-size:.9rem; font-weight:700; line-height:1.15;">{r['nombre_unificado']}</div>
              <div style="font-size:.85rem; font-weight:800;">{int(r['matr'])} matr.</div>
              <div style="font-size:.85rem; font-weight:900; margin-left:8px;">{euro_es(float(r['imp']))}</div>
            </div>
            """)
        legend_col.markdown(
            f"""
            <div style="background:#fff; border:1px solid #e6e6e6; border-radius:12px; padding:12px;">
                <div style="font-weight:900; margin-bottom:8px;">Totales por programa</div>
                {''.join(items)}
            </div>
            """,
            unsafe_allow_html=True
        )

        # ---------- Promedio de PVP ----------
        try:
            imp_series_panel = pd.to_numeric(base_df.get("importe", pd.Series(dtype=float)), errors="coerce")
            valid_panel = imp_series_panel[imp_series_panel > 0]
            promedio_panel = float(valid_panel.mean()) if not valid_panel.empty else 0.0
            legend_col.markdown(
                f"""
                <div style="margin-top:10px; background:#eef0f4; color:#111; border-radius:12px; padding:12px; border:1px solid #e0e3e8;">
                    <div style="font-weight:900; margin-bottom:4px;">Promedio de PVP</div>
                    <div style="font-weight:900; font-size:1.2rem;">{euro_es(promedio_panel)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        except Exception:
            pass

        # ---------- Suma de PVP por Forma de Pago ----------
        fp_col = None
        for c in base_df.columns:
            if _norm(str(c)) == "forma de pago":
                fp_col = c
                break

        if fp_col is not None:
            tmp = base_df.copy()
            tmp["_fp"] = tmp[fp_col].astype(str).str.strip().replace(["","nan","NaN","NONE","None"], "(En Blanco)")
            tmp["importe"] = pd.to_numeric(tmp["importe"], errors="coerce").fillna(0)

            suma_por_fp = (
                tmp.groupby("_fp", as_index=False)["importe"]
                   .sum()
                   .sort_values("importe", ascending=False)
            )

            palette = px.colors.qualitative.Plotly + px.colors.qualitative.Safe + px.colors.qualitative.Set3
            color_map_fp = {fp: palette[i % len(palette)] for i, fp in enumerate(suma_por_fp["_fp"].tolist())}

            card_items = []
            for _, r in suma_por_fp.iterrows():
                fp = r["_fp"]; amt = float(r["importe"])
                card_items.append(f"""
                <div style="
                    border-radius:12px; background:{color_map_fp.get(fp, '#6c757d')}; color:#fff;
                    padding:10px 12px; margin:8px 0; display:flex; justify-content:space-between; align-items:center;
                    border:1px solid rgba(0,0,0,.15);">
                    <div style="font-weight:800;">{fp}</div>
                    <div style="font-weight:900;">{euro_es(amt)}</div>
                </div>
                """)
            legend_col.markdown(
                f"""
                <div style="margin-top:10px; background:#fff; border:1px solid #e6e6e6; border-radius:12px; padding:12px;">
                    <div style="font-weight:900; margin-bottom:6px;">Suma de PVP por Forma de Pago</div>
                    {''.join(card_items) if card_items else '<i>Sin datos</i>'}
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            legend_col.info("No se encontró la columna 'Forma de Pago'.")

        return order_prog

    # ==== BLOQUE PRINCIPAL: filas por mes + (si “Todos”) ====
    with hdr_col:
        if mes_seleccionado == "Todos":
            base = df_ventas_all_owner.copy()
            order_prog = _legend_totales_panel(base)

            if not base.empty:
                grp = (
                    base.groupby(["mes", "nombre_unificado"], dropna=False)
                        .agg(matr=("nombre_unificado", "size"), imp=("importe", "sum"))
                        .reset_index()
                )
                meses_con_datos = [m for m in orden_meses if m in grp["mes"].unique()]

                for mes in meses_con_datos:
                    gmes = grp[grp["mes"] == mes].copy()
                    if gmes.empty:
                        continue
                    if order_prog:
                        gmes["nombre_unificado"] = pd.Categorical(gmes["nombre_unificado"], categories=order_prog, ordered=True)
                        gmes = gmes.sort_values(["nombre_unificado"])
                    else:
                        gmes = gmes.sort_values("imp", ascending=False)

                    total_mes_importe = float(gmes["imp"].sum())
                    total_mes_count   = int(gmes["matr"].sum())

                    chips = [_mes_header(mes)]
                    for _, r in gmes.iterrows():
                        prog_display = abreviar_programa(r["nombre_unificado"])
                        chips.append(_tile(
                            prog_display,
                            int(r["matr"]),
                            float(r["imp"]),
                            prog_color_map.get(r["nombre_unificado"], "#6c757d")
                        ))
                    chips.append(_total_tile(total_mes_importe, total_mes_count))
                    st.markdown(_row_scroll("".join(chips)), unsafe_allow_html=True)

        else:
            base_mes = df_ventas_filtrado.copy()
            order_prog = _legend_totales_panel(base_mes)

            if base_mes.empty:
                st.info("No hay datos para este mes.")
            else:
                g = (
                    base_mes.groupby("nombre_unificado", dropna=False)
                            .agg(matr=("nombre_unificado","size"), imp=("importe","sum"))
                            .reset_index()
                )
                if order_prog:
                    g["nombre_unificado"] = pd.Categorical(g["nombre_unificado"], categories=order_prog, ordered=True)
                    g = g.sort_values(["nombre_unificado"])
                else:
                    g = g.sort_values("imp", ascending=False)

                total_mes_importe = float(g["imp"].sum())
                total_mes_count   = int(g["matr"].sum())

                chips = [_mes_header(mes_seleccionado)]
                for _, r in g.iterrows():
                    prog_display = abreviar_programa(r["nombre_unificado"])
                    chips.append(_tile(
                        prog_display,
                        int(r["matr"]), float(r["imp"]),
                        prog_color_map.get(r["nombre_unificado"], "#6c757d")
                    ))
                chips.append(_total_tile(total_mes_importe, total_mes_count))
                st.markdown(_row_scroll("".join(chips)), unsafe_allow_html=True)

    # ======================================================================
    # FACTURACIÓN FICTICIA + CLIENTIFY POR COMERCIAL  (con "Ver más")
    # ======================================================================
    st.markdown("---")
    st.markdown("#### Facturación Ficticia + Clientify por Comercial (EIM)")

    pvfe_path = _encontrar_archivo_pvfe()
    df_pvfe_all = None
    if pvfe_path and os.path.exists(pvfe_path):
        try:
            df_pvfe_all = pd.read_excel(pvfe_path)
        except Exception as e:
            st.error(f"No se pudo leer Facturación Ficticia (EIM): {e}")

    pvfe_summary, pvfe_details_html, details_rows = {}, {}, {}

    # Ventas/Preventas por alias
    ventas_by_alias = (
        df_ventas_filtrado.assign(_alias=df_ventas_filtrado["propietario"].astype(str).apply(_alias_comercial))
                 .groupby("_alias")
                 .agg(ventas_count=("propietario","size"), ventas_importe=("importe","sum"))
                 .reset_index()
    )
    ventas_by_alias = dict(ventas_by_alias.set_index("_alias")[["ventas_count","ventas_importe"]].T.to_dict())

    preventas_by_alias = {}
    if df_preventas is not None and not df_preventas.empty:
        owner_cols = [c for c in df_preventas.columns if any(x in c for x in ["propietario","comercial","asesor","owner","vendedor","responsable"])]
        if owner_cols:
            ocol = owner_cols[0]
            dft = df_preventas.copy()
            dft["_alias"] = dft[ocol].astype(str).apply(_alias_comercial)
            if not is_all:
                dft = dft[dft["_alias"] == selected_alias]
            imp_cols = [c for c in dft.columns if "importe" in c]
            dft["_imp"] = dft[imp_cols].sum(axis=1, numeric_only=True) if imp_cols else 0
            preventas_by_alias = (
                dft.groupby("_alias").agg(prev_count=(ocol,"size"), prev_importe=("_imp","sum")).reset_index()
            )
            preventas_by_alias = dict(preventas_by_alias.set_index("_alias")[["prev_count","prev_importe"]].T.to_dict())

    # alias -> owner name
    owners_all = df_ventas["propietario"].dropna().unique().tolist()
    alias_to_owner = {_alias_comercial(o): o for o in owners_all}

    # ======= PV-FE: resumen y detalle =======
    if df_pvfe_all is not None and not df_pvfe_all.empty:
        cols = _resolver_columnas(df_pvfe_all.columns)
        dfp = df_pvfe_all.copy()

        if cols["fecha"]:
            dfp["_fecha"] = pd.to_datetime(dfp[cols["fecha"]], errors="coerce", dayfirst=True)
            dfp["_mes_es"] = dfp["_fecha"].dt.month_name().map(traducciones_meses)
        else:
            dfp["_fecha"] = pd.NaT
            dfp["_mes_es"] = ""

        if cols["comer"]:
            dfp["_alias"] = dfp[cols["comer"]].astype(str).apply(_alias_comercial)
        else:
            dfp["_alias"] = "-"

        if mes_seleccionado != "Todos":
            dfp = dfp[dfp["_mes_es"] == mes_seleccionado]
        if not is_all:
            dfp = dfp[dfp["_alias"] == selected_alias]

        dfp["_pend"]  = pd.to_numeric(dfp[cols["pend"]], errors="coerce").fillna(0) if cols["pend"] else 0
        dfp["_total"] = pd.to_numeric(dfp[cols["total"]], errors="coerce").fillna(0) if cols["total"] else 0

        if not dfp.empty:
            g_alias = dfp.groupby("_alias", dropna=False)
            pvfe_summary_df = (
                g_alias.agg(
                    pv_regs=("_alias", "size"),
                    pv_pend=("_pend", "sum"),
                    pv_total=("_total","sum"),
                ).reset_index()
            )
            pvfe_cifra_por_alias = (
                g_alias["_total"].apply(lambda x: x[x > 0].sum())
                .rename("pv_cifra")
                .reset_index()
            )
            pvfe_summary_df = pvfe_summary_df.merge(pvfe_cifra_por_alias, on="_alias", how="left").fillna({"pv_cifra": 0})
            pvfe_summary = dict(pvfe_summary_df.set_index("_alias")[["pv_regs","pv_pend","pv_total","pv_cifra"]].T.to_dict())
        else:
            pvfe_summary = {}

        # --------- Detalle por razón social ----------
        pvfe_details_html = {}
        details_rows = {}
        key_razon = cols["razon"] if cols["razon"] else None
        for alias, g in dfp.groupby("_alias", dropna=False):
            rows = []
            if key_razon:
                g["_key"] = g[key_razon].astype(str).str.strip().str.lower()
                groups = g.groupby("_key", dropna=False)
            else:
                groups = [(i, gg) for i, gg in enumerate([g])]
            for _, gg in groups:
                razon = gg[key_razon].dropna().astype(str).str.strip().iloc[0] if key_razon else ""
                fechas = gg["_fecha"].dropna().dt.strftime("%d/%m/%Y").tolist()
                fechas_text = " / ".join(fechas)
                proyecto = " / ".join(dict.fromkeys([str(x).strip() for x in (gg[cols["proy"]] if cols["proy"] else []) if str(x).strip()]).keys()) if cols["proy"] else ""
                pend = gg["_pend"].sum() if cols["pend"] else 0
                totals = gg["_total"]
                if totals is not None and not totals.empty:
                    try:
                        vals = [float(v) for v in totals.dropna().tolist()]
                        parts = [f"{int(v)}" if abs(v-int(v))<1e-9 else f"{v:g}" for v in vals]
                        totals_text = f"{' / '.join(parts)} = {euro_es(sum(vals))}"
                    except Exception:
                        totals_text = ""
                else:
                    totals_text = ""
                estado = ""
                if cols["estado"]:
                    estados = [str(x).strip().upper() for x in gg[cols["estado"]].dropna() if str(x).strip()]
                    estado = " / ".join(sorted(set(estados)))
                rows.append((razon, proyecto, fechas_text, pend, totals_text, estado))

            details_rows[alias] = len(rows)
            if rows:
                header = (
                    "<table style='width:100%;table-layout:fixed;border-collapse:collapse;font-size:.9rem;'>"
                    "<thead><tr>"
                    "<th style='text-align:left;width:28%;padding:6px 8px'>Razón Social</th>"
                    "<th style='text-align:left;width:24%;padding:6px 8px'>Proyecto</th>"
                    "<th style='text-align:left;width:18%;padding:6px 8px'>Fecha(s)</th>"
                    "<th style='text-align:right;width:12%;padding:6px 8px'>Pendiente</th>"
                    "<th style='text-align:left;width:12%;padding:6px 8px'>Total</th>"
                    "<th style='text-align:left;width:6%;padding:6px 8px'>Estado</th>"
                    "</tr></thead><tbody>"
                )
                body = "".join(
                    f"<tr>"
                    f"<td style='padding:6px 8px;overflow-wrap:break-word;white-space:normal;'>{rz}</td>"
                    f"<td style='padding:6px 8px;overflow-wrap:break-word;white-space:normal;'>{prj}</td>"
                    f"<td style='padding:6px 8px;overflow-wrap:break-word;white-space:normal;'>{ff}</td>"
                    f"<td style='padding:6px 8px;text-align:right;white-space:nowrap;'>{euro_es(pn)}</td>"
                    f"<td style='padding:6px 8px;overflow-wrap:break-word;white-space:normal;'>{tt}</td>"
                    f"<td style='padding:6px 8px;overflow-wrap:break-word;white-space:normal;'>{es}</td>"
                    f"</tr>"
                    for (rz, prj, ff, pn, tt, es) in rows
                )
                pvfe_details_html[alias] = header + body + "</tbody></table>"
            else:
                pvfe_details_html[alias] = "<i>Sin registros</i>"

    # Orden de comerciales
    if df_pvfe_all is not None and not df_pvfe_all.empty:
        all_aliases = set(pvfe_summary.keys()) | set(ventas_by_alias.keys()) | set(preventas_by_alias.keys())
        aliases_clientify = [a for a in all_aliases if (a in ventas_by_alias or a in preventas_by_alias)]
        aliases_solo_pvfe = [a for a in all_aliases if a not in aliases_clientify]
        ordered_aliases = aliases_clientify + aliases_solo_pvfe
    else:
        ordered_aliases = list(ventas_by_alias.keys())  # solo ventas

    # ======= Export =======
    export_rows = []
    for alias in ordered_aliases:
        owner_name = alias_to_owner.get(alias, alias)
        pv = pvfe_summary.get(alias, {"pv_regs":0,"pv_pend":0,"pv_total":0,"pv_cifra":0})
        ve = ventas_by_alias.get(alias, {"ventas_count":0,"ventas_importe":0})
        pr = preventas_by_alias.get(alias, {"prev_count":0,"prev_importe":0})

        pv_total = float(pv.get("pv_total", 0) or 0)
        pv_cifra = float(pv.get("pv_cifra", 0) or 0)
        ve_importe = float(ve.get("ventas_importe", 0) or 0)
        diff_fe_cli = pv_total - ve_importe

        export_rows.append({
            "Comercial": owner_name,
            "FE - Registros": int(pv.get("pv_regs", 0)),
            "FE - Pendiente (€)": float(pv.get("pv_pend", 0) or 0),
            "FE - Cifra de negocio (€)": float(pv_cifra),
            "FE - Importe total (€)": float(pv_total),
            "Clientify - Matrículas": int(ve.get("ventas_count", 0)),
            "Clientify - Importe (€)": float(ve_importe),
            "Diferencia FE−Clientify (€)": float(diff_fe_cli),
            "Preventas - Oportunidades": int(pr.get("prev_count", 0)),
            "Preventas - Importe (€)": float(pr.get("prev_importe", 0) or 0),
            "Periodo": titulo_periodo,
        })

    if export_rows:
        df_export = pd.DataFrame(export_rows)
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df_export.to_excel(writer, index=False, sheet_name="Resumen")
        st.download_button(
            label="⬇️ Descargar resumen por comercial (Excel)",
            data=buffer.getvalue(),
            file_name="EIM_FF_Clientify_por_comercial.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # ======= "Ver más" =======
    with st.expander("Ver más: tarjetas por comercial (Facturación Ficticia + Clientify)", expanded=False):
        if not ordered_aliases:
            st.info("Sin comerciales que mostrar para el periodo seleccionado.")
        else:
            st.caption(f"Mostrando {len(ordered_aliases)} comerciales.")
            for alias in ordered_aliases:
                owner_name = alias_to_owner.get(alias, alias)
                base_color = owner_color_map.get(owner_name, "#1f77b4") if owner_name in owners_in_chart else "#888"
                header_bg = lighten_hex(base_color, OWNER_HEADER_LIGHTEN)
                block_bg  = lighten_hex(base_color, OWNER_BLOCK_LIGHTEN)
                ring_color = base_color
                text_color = "#111827"

                pv = pvfe_summary.get(alias, {"pv_regs":0,"pv_pend":0,"pv_total":0,"pv_cifra":0})
                ve = ventas_by_alias.get(alias, {"ventas_count":0,"ventas_importe":0})
                pr = preventas_by_alias.get(alias, {"prev_count":0,"prev_importe":0})
                detail_html = pvfe_details_html.get(alias, "<i>Sin registros</i>")
                nrows = details_rows.get(alias, 1) if 'details_rows' in locals() else 1

                pv_total = float(pv.get("pv_total", 0) or 0)
                pv_cifra = float(pv.get("pv_cifra", 0) or 0)
                ve_importe = float(ve.get("ventas_importe", 0) or 0)

                diff_fe_cli = pv_total - ve_importe
                diff_badge = (
                    f"<span style='margin-left:10px;background:#000;color:#fff;"
                    f"border-radius:8px;padding:3px 8px;font-weight:800;white-space:nowrap;'>"
                    f"FE−Clientify: {euro_es(diff_fe_cli)}</span>"
                )

                ff_block = f"""
                    <div style="background:{block_bg};border:1px solid {lighten_hex(base_color, 0.75)};border-radius:8px;padding:10px;margin-bottom:8px;color:{text_color};">
                        <div style="font-weight:900;margin-bottom:4px">Facturación Ficticia</div>
                        <div style="font-weight:700">Registros: <b>{int(pv['pv_regs'])}</b></div>
                        <div style="font-weight:700">Pendiente: <b>{euro_es(pv['pv_pend'])}</b></div>
                        <div style="font-weight:700">Cifra de negocio: <b>{euro_es(pv_cifra)}</b></div>
                        <div style="font-weight:700">Importe total FE: <b>{euro_es(pv_total)}</b></div>
                    </div>
                """

                clientify_block = f"""
                    <div style="background:#f6f7f9;border:1px solid #e5e5e5;border-radius:8px;padding:10px;margin-bottom:8px;color:{text_color};">
                        <div style="font-weight:900;margin-bottom:6px">Clientify</div>
                        <div style="margin-bottom:6px">
                            <div style="font-weight:800">Ventas</div>
                            <div style="font-weight:700">Matrículas: <b>{int(ve['ventas_count'])}</b></div>
                            <div style="font-weight:700">Importe: <b>{euro_es(ve_importe)}</b></div>
                        </div>
                        <div>
                            <div style="font-weight:800">Preventas</div>
                            <div style="font-weight:700">Oportunidades: <b>{int(pr['prev_count'])}</b></div>
                            <div style="font-weight:700">Importe: <b>{euro_es(pr['prev_importe'])}</b></div>
                        </div>
                    </div>
                """

                base_h = 260
                rows_h = 22 * int(nrows)
                height_guess = min(560, base_h + rows_h)

                card_html = f"""
                <div style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Helvetica,Arial,sans-serif;">
                  <div style="background:#fff;border:3px solid {ring_color};border-radius:12px;padding:14px;color:{text_color};
                              box-shadow:0 2px 6px rgba(0,0,0,.06); overflow:hidden;">
                    <div style="background:{header_bg};color:#111827;border-radius:10px;padding:10px 12px;
                                font-weight:900;margin:-6px -6px 12px -6px;display:flex;align-items:center;gap:6px;">
                      <span>{owner_name}</span>{diff_badge}
                    </div>
                    {ff_block}
                    {clientify_block}
                    <div style="background:#fafafa;border:1px solid #eee;border-radius:8px;padding:8px;color:#000;
                                max-height:320px; overflow-y:auto; overflow-x:hidden;
                                -webkit-overflow-scrolling: touch; overscroll-behavior: contain;">
                      {detail_html}
                    </div>
                  </div>
                </div>
                """
                components.html(card_html, height=height_guess, scrolling=True)

# Para ejecución directa
if __name__ == "__main__":
    app()
