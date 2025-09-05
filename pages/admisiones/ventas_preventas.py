import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import os
import unicodedata
import re
from datetime import datetime
from responsive import get_screen_size

# =========================
# RUTAS / CONSTANTES
# =========================
UPLOAD_FOLDER   = "uploaded_admisiones"
VENTAS_FILE     = os.path.join(UPLOAD_FOLDER, "ventas.xlsx")
PREVENTAS_FILE  = os.path.join(UPLOAD_FOLDER, "preventas.xlsx")
PVFE_FILE       = os.path.join(UPLOAD_FOLDER, "pv_fe.xlsx")   # si no existe busco por 'listadoFacturacionFicticia*'
ANIO_ACTUAL     = 2025

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
    try: f = float(n)
    except Exception: return "0 €"
    s = f"{f:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if s.endswith(",00"): s = s[:-3]
    return f"{s} €"

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
        # exactos
        for p in patterns:
            if p in norm_map: return norm_map[p]
        # subcadenas
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
# APP
# =========================
def app():
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

    if not os.path.exists(VENTAS_FILE):
        st.warning("⚠️ No se ha encontrado el archivo 'ventas.xlsx'.")
        return

    # ======= VENTAS =======
    df_ventas = pd.read_excel(VENTAS_FILE)
    df_ventas.rename(columns={c: _strip_accents_lower(c) for c in df_ventas.columns}, inplace=True)
    if "nombre" not in df_ventas.columns or "propietario" not in df_ventas.columns:
        st.warning("❌ El archivo de ventas debe tener columnas 'nombre' y 'propietario'.")
        return

    if "importe" in df_ventas.columns:
        df_ventas["importe"] = pd.to_numeric(df_ventas["importe"], errors="coerce").fillna(0)

    if "fecha de cierre" not in df_ventas.columns:
        st.warning("❌ El archivo de ventas no contiene la columna 'fecha de cierre'.")
        return

    df_ventas["fecha de cierre"] = pd.to_datetime(df_ventas["fecha de cierre"], errors="coerce")
    df_ventas = df_ventas[df_ventas["fecha de cierre"].dt.year == ANIO_ACTUAL]
    if df_ventas.empty:
        st.warning(f"❌ No hay datos de ventas para el año seleccionado ({ANIO_ACTUAL}).")
        return

    df_ventas["mes"]     = df_ventas["fecha de cierre"].dt.month_name().map(traducciones_meses)
    df_ventas["mes_num"] = df_ventas["fecha de cierre"].dt.month
    df_ventas["nombre_unificado"] = df_ventas["nombre"].apply(unificar_nombre)

    # ======= PREVENTAS (opcional) =======
    if os.path.exists(PREVENTAS_FILE):
        df_preventas = pd.read_excel(PREVENTAS_FILE)
        df_preventas.rename(columns={c: _strip_accents_lower(c) for c in df_preventas.columns}, inplace=True)
        # (ARREGLO) columnas de importe:
        columnas_importe = [col for col in df_preventas.columns if "importe" in col]
        total_preventas_importe = df_preventas[columnas_importe].sum(numeric_only=True).sum() if columnas_importe else 0
        total_preventas_count   = df_preventas.shape[0]
    else:
        df_preventas = None
        total_preventas_importe = 0
        total_preventas_count   = 0

    df_ventas_original = df_ventas.copy()

    # ======= UI =======
    st.subheader("📊 Ventas y Preventas")
    meses_disponibles = (
        df_ventas[["mes","mes_num"]].dropna().drop_duplicates().sort_values(["mes_num"], ascending=False)
    )
    opciones_meses = ["Todos"] + meses_disponibles["mes"].tolist()
    mes_seleccionado = st.selectbox("Selecciona un Mes:", opciones_meses)
    if mes_seleccionado != "Todos":
        df_ventas = df_ventas[df_ventas["mes"] == mes_seleccionado]
    st.markdown(f"### {mes_seleccionado}")

    # ======= CÁLCULO RÁPIDO FE (para tarjetas superiores) =======
    pvfe_total_importe_filtrado = 0.0
    pvfe_path_preview = _encontrar_archivo_pvfe()
    if pvfe_path_preview and os.path.exists(pvfe_path_preview):
        try:
            _df_pvfe_prev = pd.read_excel(pvfe_path_preview)
            _cols_prev = _resolver_columnas(_df_pvfe_prev.columns)
            _dfp_prev = _df_pvfe_prev.copy()
            if _cols_prev["fecha"]:
                _dfp_prev["_fecha"] = pd.to_datetime(_dfp_prev[_cols_prev["fecha"]], errors="coerce", dayfirst=True)
                _dfp_prev["_mes_es"] = _dfp_prev["_fecha"].dt.month_name().map(traducciones_meses)
                if mes_seleccionado != "Todos":
                    _dfp_prev = _dfp_prev[_dfp_prev["_mes_es"] == mes_seleccionado]
            if _cols_prev["total"]:
                pvfe_total_importe_filtrado = pd.to_numeric(_dfp_prev[_cols_prev["total"]], errors="coerce").fillna(0).sum()
        except Exception:
            pvfe_total_importe_filtrado = 0.0

    # ======= RESUMEN & COLORES (para gráficos) =======
    resumen = df_ventas.groupby(["nombre_unificado","propietario"]).size().reset_index(name="Total Matrículas")
    totales_propietario = resumen.groupby("propietario")["Total Matrículas"].sum().reset_index()
    totales_propietario["propietario_display"] = totales_propietario.apply(
        lambda r: f"{r['propietario']} ({r['Total Matrículas']})", axis=1
    )
    resumen = resumen.merge(totales_propietario[["propietario","propietario_display"]], on="propietario", how="left")

    orden_propietarios = (
        totales_propietario.sort_values(by="Total Matrículas", ascending=False)["propietario_display"].tolist()
    )
    orden_masters = (
        resumen.groupby("nombre_unificado")["Total Matrículas"].sum().sort_values(ascending=False).index.tolist()
    )

    color_palette = px.colors.qualitative.Plotly + px.colors.qualitative.D3 + px.colors.qualitative.Alphabet
    propietarios_display = sorted(resumen["propietario_display"].dropna().unique())
    color_map_display = {p: color_palette[i % len(color_palette)] for i, p in enumerate(propietarios_display)}
    owner_color_map = {p.split(" (")[0]: color_map_display[p] for p in propietarios_display}
    owners_in_chart = set(resumen["propietario"].unique())

    # ======= GRÁFICOS =======
    if mes_seleccionado == "Todos":
        df_bar = df_ventas.groupby(["mes","propietario"], dropna=False).size().reset_index(name="Total Matrículas")
        df_bar = df_bar.merge(totales_propietario[["propietario","propietario_display"]], on="propietario", how="left")
        tot_mes = df_bar.groupby("mes")["Total Matrículas"].sum().to_dict()
        df_bar["mes_etiqueta"] = df_bar["mes"].apply(lambda m: f"{m} ({tot_mes.get(m,0)})" if pd.notna(m) else m)
        orden_mes_etiqueta = [f"{m} ({tot_mes[m]})" for m in orden_meses if m in tot_mes]

        fig = px.bar(df_bar, x="mes_etiqueta", y="Total Matrículas",
                     color="propietario_display", color_discrete_map=color_map_display,
                     barmode="group", text="Total Matrículas",
                     title="Distribución Mensual de Matrículas por Propietario",
                     width=width, height=height)
        fig.update_traces(textposition="outside")
        fig.update_layout(xaxis_title="Mes", yaxis_title="Total Matrículas",
                          margin=dict(l=20,r=20,t=40,b=140),
                          xaxis=dict(categoryorder="array", categoryarray=orden_mes_etiqueta),
                          legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5))
        st.plotly_chart(fig)
    else:
        fig = px.scatter(resumen, x="nombre_unificado", y="propietario_display",
                         size="Total Matrículas", color="propietario_display",
                         color_discrete_map=color_map_display, text="Total Matrículas",
                         size_max=60, width=width, height=height)
        fig.update_traces(textposition="middle center", textfont_size=12, textfont_color="white",
                          marker=dict(line=dict(color="black", width=1.2)))
        fig.update_layout(xaxis_title="Máster / Programa (Unificado)", yaxis_title="Propietario",
                          legend=dict(orientation="v", yanchor="top", y=0.98, xanchor="left", x=1.02),
                          margin=dict(l=20,r=20,t=40,b=80))
        fig.update_yaxes(categoryorder="array", categoryarray=orden_propietarios[::-1])
        fig.update_xaxes(categoryorder="array", categoryarray=orden_masters)
        st.plotly_chart(fig)

    # ======= TARJETAS DE TOTALES (arriba) =======
    total_importe_clientify = float(df_ventas["importe"].sum()) if "importe" in df_ventas.columns else 0.0
    total_importe_fe = float(pvfe_total_importe_filtrado) if pvfe_total_importe_filtrado else 0.0
    matriculas_count = int(df_ventas.shape[0] if mes_seleccionado != "Todos" else df_ventas_original.shape[0])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
            <div style='padding:1rem;background:#f1f3f6;border-left:5px solid #1f77b4;border-radius:8px;'>
                <h4 style='margin:0'>Importe total Clientify</h4>
                <p style='font-size:1.5rem;font-weight:700;margin:0'>{euro_es(total_importe_clientify)}</p>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div style='padding:1rem;background:#f1f3f6;border-left:5px solid #7f3fbf;border-radius:8px;'>
                <h4 style='margin:0'>Importe total FE</h4>
                <p style='font-size:1.5rem;font-weight:700;margin:0'>{euro_es(total_importe_fe)}</p>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        titulo_matriculas = f"Matrículas ({mes_seleccionado})" if mes_seleccionado != "Todos" else f"Matrículas ({ANIO_ACTUAL})"
        st.markdown(f"""
            <div style='padding:1rem;background:#f1f3f6;border-left:5px solid #2ca02c;border-radius:8px;'>
                <h4 style='margin:0'>{titulo_matriculas}</h4>
                <p style='font-size:1.5rem;font-weight:700;margin:0'>{matriculas_count}</p>
            </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
            <div style='padding:1rem;background:#f1f3f6;border-left:5px solid #1f77b4;border-radius:8px;'>
                <h4 style='margin:0'>Preventas</h4>
                <p style='font-size:1.5rem;font-weight:700;margin:0'>{euro_es(total_preventas_importe)} ({total_preventas_count})</p>
            </div>
        """, unsafe_allow_html=True)

    # ======================================================================
    #        FACTURACIÓN FICTICIA + CLIENTIFY POR COMERCIAL (robusto)
    # ======================================================================
    st.markdown("---")
    st.markdown("#### Facturación Ficticia + Clientify por Comercial")

    pvfe_path = _encontrar_archivo_pvfe()
    df_pvfe_all = None
    if pvfe_path and os.path.exists(pvfe_path):
        try:
            df_pvfe_all = pd.read_excel(pvfe_path)
        except Exception as e:
            st.error(f"No se pudo leer Facturación Ficticia: {e}")

    pvfe_summary, pvfe_details_html, details_rows = {}, {}, {}
    if df_pvfe_all is not None and not df_pvfe_all.empty:
        cols = _resolver_columnas(df_pvfe_all.columns)
        dfp = df_pvfe_all.copy()

        # FECHA / MES
        if cols["fecha"]:
            dfp["_fecha"] = pd.to_datetime(dfp[cols["fecha"]], errors="coerce", dayfirst=True)
            dfp["_mes_es"] = dfp["_fecha"].dt.month_name().map(traducciones_meses)
        else:
            dfp["_fecha"] = pd.NaT
            dfp["_mes_es"] = ""
        if mes_seleccionado != "Todos":
            dfp = dfp[dfp["_mes_es"] == mes_seleccionado]

        # NUMÉRICOS
        dfp["_pend"]  = pd.to_numeric(dfp[cols["pend"]], errors="coerce").fillna(0) if cols["pend"] else 0
        dfp["_total"] = pd.to_numeric(dfp[cols["total"]], errors="coerce").fillna(0) if cols["total"] else 0

        # COMERCIAL
        if cols["comer"]:
            dfp["_alias"] = dfp[cols["comer"]].astype(str).apply(_alias_comercial)
        else:
            dfp["_alias"] = "-"

        # ==== helpers
        def _join_unique(iterable):
            out, seen = [], set()
            for x in iterable:
                sx = str(x).strip()
                if sx and sx not in seen:
                    out.append(sx); seen.add(sx)
            return " / ".join(out)

        def _join_estado(s: pd.Series) -> str:
            if not cols["estado"]: return ""
            return _join_unique([x for x in s.dropna()])

        def _fmt_totals(series: pd.Series):
            if series is None or series.empty: return ""
            vals, total = [], 0.0
            for v in series.dropna():
                try: f = float(v); vals.append(f); total += f
                except: pass
            if not vals: return ""
            parts = [f"{int(v)}" if abs(v-int(v))<1e-9 else f"{v:g}" for v in vals]
            return f"{' / '.join(parts)} = {euro_es(total)}"

        # Resumen por alias
        pvfe_summary = (
            dfp.groupby("_alias", dropna=False)
               .agg(pv_regs=("_alias","size"), pv_pend=("_pend","sum"), pv_total=("_total","sum"))
               .reset_index()
        )
        pvfe_summary = dict(pvfe_summary.set_index("_alias")[["pv_regs","pv_pend","pv_total"]].T.to_dict())

        # --------- Detalle por razón social (con PROYECTO) ----------
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
                proyecto = _join_unique(gg[cols["proy"]].dropna()) if cols["proy"] else ""
                pend = gg["_pend"].max() if cols["pend"] else 0
                totals_text = _fmt_totals(gg["_total"]) if cols["total"] else ""
                estado = _join_estado(gg[cols["estado"]]) if cols["estado"] else ""
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

    # Ventas/Preventas por alias
    ventas_by_alias = (
        df_ventas.assign(_alias=df_ventas["propietario"].astype(str).apply(_alias_comercial))
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
            imp_cols = [c for c in df_preventas.columns if "importe" in c]
            dft = df_preventas.copy()
            dft["_alias"] = dft[ocol].astype(str).apply(_alias_comercial)
            dft["_imp"] = dft[imp_cols].sum(axis=1, numeric_only=True) if imp_cols else 0
            preventas_by_alias = (
                dft.groupby("_alias").agg(prev_count=(ocol,"size"), prev_importe=("_imp","sum")).reset_index()
            )
            preventas_by_alias = dict(preventas_by_alias.set_index("_alias")[["prev_count","prev_importe"]].T.to_dict())

    # alias -> owner name
    owners_all = df_ventas_original["propietario"].dropna().unique().tolist()
    alias_to_owner = {_alias_comercial(o): o for o in owners_all}

    # orden: primero con clientify (ventas o preventas), luego solo PV-FE
    all_aliases = set(pvfe_summary.keys()) | set(ventas_by_alias.keys()) | set(preventas_by_alias.keys())
    aliases_clientify = [a for a in all_aliases if (a in ventas_by_alias or a in preventas_by_alias)]
    # (ARREGLO) línea correcta:
    aliases_solo_pvfe = [a for a in all_aliases if a not in aliases_clientify]
    ordered_aliases = aliases_clientify + aliases_solo_pvfe

    # ======= TARJETAS (UNA POR FILA) =======
    for alias in ordered_aliases:
        owner_name = alias_to_owner.get(alias, alias)
        tiene_clientify = (alias in ventas_by_alias) or (alias in preventas_by_alias)

        # Colores (gris si no hay clientify/ventas)
        ring_color = owner_color_map.get(owner_name, "#1f77b4") if owner_name in owners_in_chart else ("#1f77b4" if tiene_clientify else "#888")
        if tiene_clientify:
            card_bg, title_color, text_color, clientify_bg = "#fff", "#000", "#000", "#f2f2f2"
        else:
            card_bg, title_color, text_color, clientify_bg = "#4a4a4a", "#fff", "#fff", "#2b2b2b"

        pv = pvfe_summary.get(alias, {"pv_regs":0,"pv_pend":0,"pv_total":0})
        ve = ventas_by_alias.get(alias, {"ventas_count":0,"ventas_importe":0})
        pr = preventas_by_alias.get(alias, {"prev_count":0,"prev_importe":0})
        detail_html = pvfe_details_html.get(alias, "<i>Sin registros</i>")
        nrows = details_rows.get(alias, 1)

        # Diferencia FE−Clientify (píldora)
        pv_total = float(pv.get("pv_total", 0) or 0)
        ve_importe = float(ve.get("ventas_importe", 0) or 0)
        diff_fe_cli = pv_total - ve_importe
        diff_badge = (
            f"<span style='margin-left:10px;background:#000;color:#fff;"
            f"border-radius:8px;padding:3px 8px;font-weight:800;white-space:nowrap;'>"
            f"FE−Clientify: {euro_es(diff_fe_cli)}</span>"
        )

        ff_block = f"""
            <div style="background:#eef7ff;border:1px solid #d9eaff;border-radius:8px;padding:10px;margin-bottom:8px;color:#000;">
                <div style="font-weight:900;margin-bottom:4px">Facturación Ficticia</div>
                <div style="font-weight:700">Registros: <b>{int(pv['pv_regs'])}</b></div>
                <div style="font-weight:700">Pendiente: <b>{euro_es(pv['pv_pend'])}</b></div>
                <div style="font-weight:700">Total: <b>{euro_es(pv_total)}</b></div>
            </div>
        """

        clientify_block = f"""
            <div style="background:{clientify_bg};border:1px solid #e5e5e5;border-radius:8px;padding:10px;margin-bottom:8px;color:{'#000' if tiene_clientify else '#fff'};">
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
          <div style="background:{card_bg};border:3px solid {ring_color};border-radius:12px;padding:14px;color:{text_color};
                      box-shadow:0 2px 6px rgba(0,0,0,.06); overflow:hidden;">
            <div style="background:{ring_color};color:#fff;border-radius:10px;padding:10px 12px;
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

    # =========================
    # VISTA RÁPIDA PV-FE (blindada)
    # =========================
    st.markdown("---")
    st.subheader("📄 Facturación Ficticia — Vista rápida")

    if df_pvfe_all is not None and not df_pvfe_all.empty:
        try:
            cols = _resolver_columnas(df_pvfe_all.columns)
            vista = df_pvfe_all.copy()
            if cols["fecha"]:
                vista["_fecha"] = pd.to_datetime(vista[cols["fecha"]], errors="coerce", dayfirst=True)
                vista["_mes_es"] = vista["_fecha"].dt.month_name().map(traducciones_meses)
                if mes_seleccionado != "Todos":
                    vista = vista[vista["_mes_es"] == mes_seleccionado]
                vista["Fecha Factura"] = vista["_fecha"].dt.strftime("%d/%m/%Y")
            else:
                vista["Fecha Factura"] = ""
            if cols["pend"]:
                vista["Pendiente"] = pd.to_numeric(vista[cols["pend"]], errors="coerce").fillna(0)
            else:
                vista["Pendiente"] = 0
            if cols["total"]:
                vista["_total_num"] = pd.to_numeric(vista[cols["total"]], errors="coerce").fillna(0)
            else:
                vista["_total_num"] = 0

            # Construir filas con PROYECTO
            rows = []
            key_razon = cols["razon"] if cols["razon"] else None
            def _join_unique(iterable):
                out, seen = [], set()
                for x in iterable:
                    sx = str(x).strip()
                    if sx and sx not in seen:
                        out.append(sx); seen.add(sx)
                return " / ".join(out)

            if key_razon:
                vista["_key"] = vista[key_razon].astype(str).str.strip().str.lower()
                giter = vista.groupby("_key", dropna=False)
            else:
                giter = [(i, gg) for i, gg in enumerate([vista])]
            for _, g in giter:
                razon = g[key_razon].dropna().astype(str).str.strip().iloc[0] if key_razon else ""
                proyecto = _join_unique(g[cols["proy"]].dropna()) if cols["proy"] else ""
                fechas = g["Fecha Factura"].dropna().tolist()
                fechas_text = " / ".join(sorted(set([f for f in fechas if f])))
                pendiente = g["Pendiente"].max()
                totales = g["_total_num"].dropna().tolist()
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
                    "Pendiente": pendiente,
                    "Total": total_text,
                    "Estado": estado,
                    "Comercial": comercial,
                })

            if rows:
                final = pd.DataFrame(rows).sort_values(by="Pendiente", ascending=False, na_position="last")
                st.dataframe(final, use_container_width=True)
            else:
                st.info("📭 No hay registros de Facturación Ficticia para el mes seleccionado.")
        except Exception as e:
            st.error(f"No se pudo procesar Facturación Ficticia: {e}")
    else:
        st.info("📭 No hay archivo de Facturación Ficticia en la carpeta.")

# Para ejecución directa
if __name__ == "__main__":
    app()
