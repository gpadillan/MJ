import pandas as pd
import streamlit as st
import plotly.express as px
import unicodedata
import re
from datetime import datetime

# ---------- UI ----------
def render_card(title, value, color):
    return f"""
        <div style="background-color:{color}; padding:16px; border-radius:12px;
                    text-align:center; box-shadow: 0 4px 8px rgba(0,0,0,0.1)">
            <h4 style="margin-bottom:0.5em; white-space:nowrap; overflow:hidden; text-overflow:ellipsis">{title}</h4>
            <h2 style="margin:0">{value}</h2>
        </div>
    """

def _tiles_html_from_series(series: pd.Series) -> str:
    """
    Crea los 'cuadraditos' por área en UNA sola fila, SIN scroll horizontal.
    Se usa CSS Grid con tantas columnas como áreas. Cada tile se encoge
    de forma proporcional para caber, manteniendo un mínimo visual.
    """
    if series is None or series.empty:
        return "<div style='color:#0b2e6b'>Sin áreas</div>"

    # Orden preferente y resto al final
    orden = ["RRHH", "SAP", "DPO", "EERR", "IA", "PYTHON", "FULL STACK", "BIM", "LOGISTICA"]
    s = series.copy()
    presentes = [a for a in orden if a in s.index]
    resto = [a for a in s.sort_values(ascending=False).index if a not in presentes]
    indices = presentes + resto
    n = max(1, len(indices))

    # Contenedor grid: una fila con n columnas
    # minmax(90px, 1fr) asegura que, si hay muchas áreas o la pantalla es estrecha,
    # se reduzcan los anchos pero sigan cabiendo en una sola fila.
    container_open = f"""
      <div style="
        display:grid; grid-auto-flow:column;
        grid-template-columns: repeat({n}, minmax(90px, 1fr));
        gap:8px; width:100%;
      ">
    """

    tiles = []
    for area in indices:
        cnt = int(s.get(area, 0))
        tiles.append(f"""
        <div style="
            background:rgba(255,255,255,.55);
            border:1px solid #9ec5fe; border-radius:10px;
            padding:8px 10px; display:flex; flex-direction:column; gap:4px;
            min-width:0; /* permite que el contenido se reduzca */
        ">
          <div style="font-weight:700; color:#0b2e6b; font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
            {area}
          </div>
          <div style="font-size:18px; font-weight:900; color:#00335c; line-height:1;">
            {cnt}
          </div>
        </div>
        """)

    return container_open + "".join(tiles) + "</div>"

def render_objectives_card(total_alumnos: int, area_counts: pd.Series) -> str:
    tiles_html = _tiles_html_from_series(area_counts)
    return f"""
      <div style="
          background:#bbdefb; border-radius:12px; padding:16px;
          box-shadow:0 4px 8px rgba(0,0,0,0.08);">
        <div style="text-align:center; margin-bottom:10px">
          <div style="font-size:14px; font-weight:700; color:#0b2e6b; letter-spacing:.3px;">
            Alumnado total
          </div>
          <div style="font-size:28px; font-weight:900; color:#00335c; margin-top:2px;">
            {int(total_alumnos)}
          </div>
        </div>

        <div style="font-size:13px; font-weight:700; color:#0b2e6b; margin:6px 0 8px;">
          Alumnado por área
        </div>
        {tiles_html}
      </div>
    """

# ---------- Helpers ----------
MESES_ES = {
    "enero":"01","febrero":"02","marzo":"03","abril":"04","mayo":"05","junio":"06",
    "julio":"07","agosto":"08","septiembre":"09","setiembre":"09","octubre":"10",
    "noviembre":"11","diciembre":"12"
}
INVALID_TXT = {"", "NO ENCONTRADO", "NAN", "NULL", "NONE"}

def _strip_accents(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def _norm_colname(s: str) -> str:
    s = str(s)
    s = _strip_accents(s).upper()
    s = s.replace('\u00A0', ' ')
    s = re.sub(r'[\.\-_/]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'[^A-Z0-9 ]', '', s)
    return s

def _norm_text_cell(x: object, upper: bool = False, deaccent: bool = False) -> str:
    if pd.isna(x):
        s = ""
    else:
        s = str(x).replace('\u00A0', ' ')
    s = re.sub(r'\s+', ' ', s).strip()
    if deaccent:
        s = _strip_accents(s)
    if upper:
        s = s.upper()
    return s

def _build_colmap(cols):
    expected = {
        "CONSECUCION GE": ["CONSECUCION GE"],
        "DEVOLUCION GE": ["DEVOLUCION GE"],
        "INAPLICACION GE": ["INAPLICACION GE"],
        "MODALIDAD PRACTICAS": ["MODALIDAD PRACTICAS", "MODALIDAD PRACTICA"],
        "CONSULTOR EIP": ["CONSULTOR EIP"],
        "PRACTICAS_GE": ["PRACTICAS GE", "PRACTICAS/GE", "PRACTCAS/GE"],
        "EMPRESA PRACT": ["EMPRESA PRACT", "EMPRESA PRACTICAS", "EMPRESA PRACTICA", "EMPRESA PRACT."],
        "EMPRESA GE": ["EMPRESA GE"],
        "AREA": ["AREA"],
        "ANIO": ["ANO", "ANIO", "AÑO"],
        "NOMBRE": ["NOMBRE"],
        "APELLIDOS": ["APELLIDOS"],
        "FECHA CIERRE": ["FECHA CIERRE", "FECHA_CIERRE", "F CIERRE"],
    }
    norm_lookup = { _norm_colname(c): c for c in cols }
    colmap = {}
    for canon, aliases in expected.items():
        found = None
        for alias in aliases:
            alias_norm = _norm_colname(alias)
            if alias_norm in norm_lookup:
                found = norm_lookup[alias_norm]; break
        if not found:
            for norm_key, real in norm_lookup.items():
                if alias_norm in norm_key:
                    found = real; break
        if found:
            colmap[canon] = found
    return colmap

def _to_bool(x):
    if isinstance(x, bool): return x
    if isinstance(x, (int, float)) and not pd.isna(x): return bool(x)
    if isinstance(x, str): return x.strip().lower() in ('true','verdadero','sí','si','1','x')
    return False

def _clean_series(s: pd.Series) -> pd.Series:
    s = s.dropna().astype(str).apply(lambda v: _norm_text_cell(v, upper=True, deaccent=True))
    return s[~s.isin(INVALID_TXT)]

def _parse_fecha_es(value):
    if pd.isna(value): return None
    if isinstance(value, (int, float)): return value
    s = str(value).strip()
    if not s: return None
    s_low = _strip_accents(s.lower())
    s_low = re.sub(r'\bde\b', ' ', s_low)
    s_low = re.sub(r'\s+', ' ', s_low).strip()
    for mes, num in MESES_ES.items():
        s_low = re.sub(rf'\b{mes}\b', num, s_low)
    m = re.match(r'^(\d{1,2})\s+(\d{2})\s+(\d{4})$', s_low)
    if m:
        d, mm, yyyy = m.groups()
        d = d.zfill(2)
        return f"{d}/{mm}/{yyyy}"
    return s

def _is_blank(x) -> bool:
    if x is None: return True
    if isinstance(x, float) and pd.isna(x): return True
    if isinstance(x, str) and x.strip() == "": return True
    return pd.isna(x)

# ---------- App ----------
def render(df):
    st.title("Informe de Cierre de Expedientes")
    st.button("🔄 Recargar / limpiar caché", on_click=st.cache_data.clear)

    # Detecta columnas
    colmap = _build_colmap(df.columns)
    required = ["CONSECUCION GE","DEVOLUCION GE","INAPLICACION GE","CONSULTOR EIP",
                "PRACTICAS_GE","EMPRESA PRACT","EMPRESA GE","AREA","NOMBRE","APELLIDOS","FECHA CIERRE"]
    missing = [k for k in required if k not in colmap]
    if missing:
        st.error("Faltan columnas requeridas: " + ", ".join(missing))
        st.stop()

    # Renombra
    df = df.rename(columns={colmap[k]:k for k in colmap})

    # Limpieza valores
    df["AREA"] = df["AREA"].apply(lambda v: _norm_text_cell(v, upper=True, deaccent=True))
    for c in ["PRACTICAS_GE","EMPRESA PRACT","EMPRESA GE","NOMBRE","APELLIDOS"]:
        df[c] = df[c].apply(_norm_text_cell)
    df["CONSULTOR EIP"] = df["CONSULTOR EIP"].apply(_norm_text_cell).replace('', 'Otros').fillna('Otros')
    df = df[df["CONSULTOR EIP"].str.upper()!="NO ENCONTRADO"]

    # FECHA CIERRE robusta
    col_fc = "FECHA CIERRE"
    if not pd.api.types.is_numeric_dtype(df[col_fc]):
        df[col_fc] = df[col_fc].apply(_parse_fecha_es)
    if pd.api.types.is_numeric_dtype(df[col_fc]):
        dt = pd.to_datetime(df[col_fc], unit="D", origin="1899-12-30", errors="coerce")
    else:
        dt = pd.to_datetime(df[col_fc], errors="coerce", dayfirst=True)
    df[col_fc] = dt
    anio = df[col_fc].dt.year
    mask = (anio.isin([1899, 1970]) | ((anio < 2015) & (anio != 2000)) | (anio > 2035))
    df.loc[mask, col_fc] = pd.NaT
    df["AÑO_CIERRE"] = df[col_fc].dt.year

    # Booleanos
    df["CONSECUCION_BOOL"]=df["CONSECUCION GE"].apply(_to_bool)
    df["INAPLICACION_BOOL"]=df["INAPLICACION GE"].apply(_to_bool)
    df["DEVOLUCION_BOOL"]=df["DEVOLUCION GE"].apply(_to_bool)

    # Selector informe (AÑO)
    anios = sorted(df["AÑO_CIERRE"].dropna().unique().astype(int)) if "AÑO_CIERRE" in df else []
    visibles = [a for a in anios if a != 2000]
    opciones = [f"Cierre Expediente Año {a}" for a in visibles] + ["Cierre Expediente Total"] if visibles else ["Cierre Expediente Total"]
    opcion = st.selectbox("Selecciona el tipo de informe:", opciones)
    df_base = df.copy() if "Total" in opcion else df[df["AÑO_CIERRE"]==int(opcion.split()[-1])].copy()

    # Filtro consultor
    consultores = df_base["CONSULTOR EIP"].dropna().apply(_norm_text_cell)
    consultores = consultores[~consultores.str.upper().isin(list(INVALID_TXT))]
    consultores_unicos = sorted(consultores.unique())
    sel = st.multiselect("Filtrar por Consultor:", options=consultores_unicos, default=consultores_unicos)

    # Dataset ligado a año + consultor
    df_f = df_base[df_base["CONSULTOR EIP"].isin(sel)].copy()

    # Normaliza área
    df_f["AREA_N"] = df_f["AREA"].apply(lambda v: _norm_text_cell(v, upper=True, deaccent=True))
    df_f.loc[df_f["AREA_N"] == "", "AREA_N"] = "SIN ÁREA"

    # Selector de área (condiciona TODO lo de abajo)
    areas = ['TODAS'] + sorted(df_f["AREA_N"].unique())
    area_sel = st.selectbox(" Empresas por área:", areas)
    df_scope = df_f if area_sel == 'TODAS' else df_f[df_f["AREA_N"] == area_sel].copy()

    # Flag de prácticas en curso (para otros usos; el KPI 2025 se calcula por df + sel)
    df_scope["PRACTICAS_BOOL"] = (
        (df_scope["PRACTICAS_GE"].str.upper()=="GE") &
        (~df_scope["EMPRESA PRACT"].str.upper().isin(["","NO ENCONTRADO"])) &
        (~df_scope["CONSECUCION_BOOL"]) &
        (~df_scope["DEVOLUCION_BOOL"]) &
        (~df_scope["INAPLICACION_BOOL"])
    )

    # ---------- Tarjetas principales (ligadas a df_scope)
    tot_con = int(df_scope["CONSECUCION_BOOL"].sum())
    tot_inap = int(df_scope["INAPLICACION_BOOL"].sum())
    tot_emp_ge = int(_clean_series(df_scope["EMPRESA GE"]).shape[0])
    tot_emp_pr = int(_clean_series(df_scope["EMPRESA PRACT"]).shape[0])

    with st.container():
        if "Total" in opcion:
            c1, c2, c3 = st.columns(3)
            c1.markdown(render_card("CONSECUCIÓN", tot_con, "#e3f2fd"), unsafe_allow_html=True)
            c2.markdown(render_card("INAPLICACIÓN", tot_inap, "#fce4ec"), unsafe_allow_html=True)
            c3.markdown(render_card("TOTAL PRÁCTICAS", tot_emp_ge, "#ede7f6"), unsafe_allow_html=True)
        else:
            anio_txt = opcion.split()[-1]
            if anio_txt == "2025":
                c1, c2, c3, c4 = st.columns(4)
                c1.markdown(render_card("CONSECUCIÓN 2025", tot_con, "#e3f2fd"), unsafe_allow_html=True)
                c2.markdown(render_card("INAPLICACIÓN 2025", tot_inap, "#fce4ec"), unsafe_allow_html=True)
                c3.markdown(render_card("Prácticas 2025", tot_emp_pr, "#f3e5f5"), unsafe_allow_html=True)

                # >>> NO TOCAR: cálculo clásico que te funcionaba <<<
                df_cons = df[df["CONSULTOR EIP"].isin(sel)].copy()
                m_sin_fecha = df_cons["FECHA CIERRE"].isna()
                emp = df_cons["EMPRESA PRACT"].apply(_norm_text_cell)
                m_emp_ok = ~(emp.eq("") | emp.str.upper().isin(list(INVALID_TXT)))
                m_con_blank  = df_cons["CONSECUCION GE"].apply(_is_blank)
                m_inap_blank = df_cons["INAPLICACION GE"].apply(_is_blank)
                m_dev_blank  = df_cons["DEVOLUCION GE"].apply(_is_blank)
                en_curso = int((m_sin_fecha & m_emp_ok & m_con_blank & m_inap_blank & m_dev_blank).sum())

                c4.markdown(render_card("Prácticas en curso", en_curso, "#fff3e0"), unsafe_allow_html=True)
            else:
                c1, c2, c3 = st.columns(3)
                c1.markdown(render_card(f"CONSECUCIÓN {anio_txt}", tot_con, "#e3f2fd"), unsafe_allow_html=True)
                c2.markdown(render_card(f"INAPLICACIÓN {anio_txt}", tot_inap, "#fce4ec"), unsafe_allow_html=True)
                c3.markdown(render_card(f"Prácticas {anio_txt}", tot_emp_pr, "#f3e5f5"), unsafe_allow_html=True)

    # ---------- Pie: cierres por consultor (ligado a df_scope)
    st.markdown("")
    df_cierre = pd.concat([
        df_scope[df_scope["CONSECUCION_BOOL"]][["CONSULTOR EIP","NOMBRE","APELLIDOS"]].assign(CIERRE="CONSECUCIÓN"),
        df_scope[df_scope["INAPLICACION_BOOL"]][["CONSULTOR EIP","NOMBRE","APELLIDOS"]].assign(CIERRE="INAPLICACIÓN"),
    ], ignore_index=True)
    resumen = df_cierre.groupby("CONSULTOR EIP").size().reset_index(name="TOTAL_CIERRES")
    if not resumen.empty:
        fig = px.pie(resumen, names="CONSULTOR EIP", values="TOTAL_CIERRES", title="")
        fig.update_traces(textinfo="label+value")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay cierres para los filtros seleccionados.")

    # ---------- Resumen por área + Listados de empresas (todo ligado a df_scope)
    st.markdown("")
    df_tmp = df_scope.copy()
    if "AREA_N" not in df_tmp:
        df_tmp["AREA_N"] = df_tmp["AREA"].apply(lambda v: _norm_text_cell(v, upper=True, deaccent=True))
        df_tmp.loc[df_tmp["AREA_N"] == "", "AREA_N"] = "SIN ÁREA"

    areas_idx = sorted(df_tmp["AREA_N"].unique())

    con_area  = df_tmp[df_tmp["CONSECUCION_BOOL"]].groupby("AREA_N").size()
    inap_area = df_tmp[df_tmp["INAPLICACION_BOOL"]].groupby("AREA_N").size()
    emp_pr_norm = df_tmp["EMPRESA PRACT"].apply(lambda v: _norm_text_cell(v, upper=True, deaccent=True))
    mask_pract  = ~emp_pr_norm.isin(INVALID_TXT)
    prac_area   = df_tmp[mask_pract].groupby("AREA_N").size()

    resumen_area = pd.DataFrame(index=areas_idx)
    resumen_area["TOTAL CONSECUCIÓN"]  = con_area.reindex(areas_idx, fill_value=0)
    resumen_area["TOTAL INAPLICACIÓN"] = inap_area.reindex(areas_idx, fill_value=0)
    resumen_area["TOTAL PRÁCTICAS"]    = prac_area.reindex(areas_idx, fill_value=0)
    resumen_area.index.name = "AREA"
    resumen_area = (
        resumen_area.reset_index()
                    .astype({"TOTAL CONSECUCIÓN": int,
                             "TOTAL INAPLICACIÓN": int,
                             "TOTAL PRÁCTICAS": int})
                    .sort_values(by="TOTAL CONSECUCIÓN", ascending=False)
    )

    total_row = {
        "AREA": "Total",
        "TOTAL CONSECUCIÓN":  int(resumen_area["TOTAL CONSECUCIÓN"].sum()),
        "TOTAL INAPLICACIÓN": int(resumen_area["TOTAL INAPLICACIÓN"].sum()),
        "TOTAL PRÁCTICAS":    int(resumen_area["TOTAL PRÁCTICAS"].sum()),
    }
    resumen_area = pd.concat([resumen_area, pd.DataFrame([total_row])], ignore_index=True)

    styled = (resumen_area.style
        .background_gradient(subset=["TOTAL CONSECUCIÓN"], cmap="Greens")
        .background_gradient(subset=["TOTAL INAPLICACIÓN"], cmap="Reds")
        .background_gradient(subset=["TOTAL PRÁCTICAS"], cmap="Blues")
    )

    s_ge = _clean_series(df_scope["EMPRESA GE"])
    emp_ge = s_ge.value_counts().reset_index()
    emp_ge.columns = ["EMPRESA GE", "EMPLEOS"]

    s_pr = _clean_series(df_scope["EMPRESA PRACT"])
    emp_pr = s_pr.value_counts().reset_index()
    emp_pr.columns = ["EMPRESA PRÁCT.", "EMPLEOS"]

    col_res, col_ge, col_pr = st.columns([1.6, 1, 1])
    with col_res:
        st.markdown("#### Empresas por área (resumen)")
        st.dataframe(styled, use_container_width=True)
    with col_ge:
        st.markdown("#### EMPRESAS GE")
        st.dataframe(emp_ge.style.background_gradient(subset=["EMPLEOS"], cmap="YlOrBr"),
                     use_container_width=True)
    with col_pr:
        st.markdown("#### EMPRESAS PRÁCTICAS")
        st.dataframe(emp_pr.style.background_gradient(subset=["EMPLEOS"], cmap="PuBu"),
                     use_container_width=True)

    # ---------- OBJETIVOS + tiles de alumnado por área (todo ligado a df_scope)
    df_valid = df_scope[(df_scope["NOMBRE"].str.upper()!="NO ENCONTRADO") &
                        (df_scope["APELLIDOS"].str.upper()!="NO ENCONTRADO")].copy()
    total_al = df_valid[["NOMBRE","APELLIDOS"]].drop_duplicates().shape[0]

    if "AREA_N" not in df_valid:
        df_valid["AREA_N"] = df_valid["AREA"].apply(lambda v: _norm_text_cell(v, upper=True, deaccent=True))
        df_valid.loc[df_valid["AREA_N"] == "", "AREA_N"] = "SIN ÁREA"

    area_counts = (
        df_valid.drop_duplicates(subset=["AREA_N","NOMBRE","APELLIDOS"])
                .groupby("AREA_N").size()
    )

    st.markdown("## 👥 OBJETIVOS")
    st.markdown(render_objectives_card(total_al, area_counts), unsafe_allow_html=True)

    # KPIs (empleo, cierre DP, prácticas, conversión) ligados a df_scope
    st.markdown("")
    df_valid["EMP_PRACT_N"] = df_valid["EMPRESA PRACT"].apply(lambda v: _norm_text_cell(v, upper=True, deaccent=True))
    df_valid["EMP_GE_N"]    = df_valid["EMPRESA GE"].apply(lambda v: _norm_text_cell(v, upper=True, deaccent=True))

    insercion_empleo = df_valid[df_valid["CONSECUCION_BOOL"]]
    pct_empleo = round((insercion_empleo[["NOMBRE","APELLIDOS"]].drop_duplicates().shape[0] / total_al) * 100, 2) if total_al else 0.0

    cond_cierre_dp = df_valid[["CONSECUCION_BOOL","DEVOLUCION_BOOL","INAPLICACION_BOOL"]].any(axis=1)
    pct_cierre_dp = round((df_valid.loc[cond_cierre_dp, ["NOMBRE","APELLIDOS"]].drop_duplicates().shape[0] / total_al) * 100, 2) if total_al else 0.0

    practicas_realizadas = df_valid[~df_valid["EMP_PRACT_N"].isin(INVALID_TXT)]
    pct_practicas = round((practicas_realizadas[["NOMBRE","APELLIDOS"]].drop_duplicates().shape[0] / total_al) * 100, 2) if total_al else 0.0

    denom = practicas_realizadas[["NOMBRE","APELLIDOS"]].drop_duplicates().shape[0]
    conversion = practicas_realizadas[practicas_realizadas["EMP_PRACT_N"] == practicas_realizadas["EMP_GE_N"]]
    pct_conversion = round((conversion[["NOMBRE","APELLIDOS"]].drop_duplicates().shape[0] / denom) * 100, 2) if denom else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(render_card("Inserción laboral Empleo", f"{pct_empleo}%", "#c8e6c9"), unsafe_allow_html=True)
    c2.markdown(render_card("Cierre expediente Desarrollo Profesional", f"{pct_cierre_dp}%", "#dfcbb2"), unsafe_allow_html=True)
    c3.markdown(render_card("Inserción Laboral Prácticas", f"{pct_practicas}%", "#ffe082"), unsafe_allow_html=True)
    c4.markdown(render_card("Conversión prácticas a empresa", f"{pct_conversion}%", "#f8bbd0"), unsafe_allow_html=True)
