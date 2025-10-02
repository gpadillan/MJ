import pandas as pd
import streamlit as st
import plotly.express as px
import unicodedata
import re
from datetime import datetime
import html

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
    if series is None or series.empty:
        return "<div style='color:#0b2e6b'>Sin áreas</div>"

    orden = ["RRHH", "SAP", "DPO", "EERR", "IA", "PYTHON", "FULL STACK", "BIM", "LOGISTICA"]
    s = series.copy()
    presentes = [a for a in orden if a in s.index]
    resto = [a for a in s.sort_values(ascending=False).index if a not in presentes]
    indices = presentes + resto
    n = max(1, len(indices))

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
            min-width:0;
        ">
          <div style="font-weight:700; color:#0b2e6b; font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
            {html.escape(str(area))}
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
        # Provincias
        "PROVINCIA 1": ["PROVINCIA 1", "PROVINCIA1", "PROVINCIA_1", "PROVINCIA UNO"],
        "PROVINCIA 2": ["PROVINCIA 2", "PROVINCIA2", "PROVINCIA_2", "PROVINCIA DOS"],
    }
    norm_lookup = { _norm_colname(c): c for c in cols }
    colmap = {}
    for canon, aliases in expected.items():
        found = None
        alias_norm = None
        for alias in aliases:
            alias_norm = _norm_colname(alias)
            if alias_norm in norm_lookup:
                found = norm_lookup[alias_norm]; break
        if not found and alias_norm is not None:
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

# ---------- HTML tables (fixed layout, no horizontal scroll) ----------
def _html_table(df: pd.DataFrame, col_widths: list[str], align_nums: bool = True, small: bool = True) -> str:
    """Render a fixed-layout responsive table to avoid horizontal scroll."""
    if df is None or df.empty:
        return "<div style='color:#5f6368'>Sin datos</div>"

    cols = list(df.columns)
    widths = col_widths if (col_widths and len(col_widths) == len(cols)) else [f"{100//len(cols)}%"] * len(cols)

    ths = []
    for c, w in zip(cols, widths):
        ths.append(
            f"<th style='width:{w}; padding:8px 8px; text-align:left; "
            f"white-space:normal; overflow-wrap:break-word;'>{html.escape(str(c))}</th>"
        )

    rows_html = []
    for _, row in df.iterrows():
        tds = []
        for c, w in zip(cols, widths):
            val = row[c]
            if isinstance(val, (int,)):
                txt = f"{val:,}".replace(",", ".")
            elif isinstance(val, float):
                txt = f"{val:,.0f}".replace(",", ".")
            else:
                txt = str(val)
            txt = html.escape(txt)
            style_num = "text-align:center;" if align_nums and c != cols[0] else "text-align:left;"
            tds.append(
                f"<td style='width:{w}; padding:6px 8px; {style_num} "
                f"white-space:normal; overflow-wrap:break-word;'>{txt}</td>"
            )
        rows_html.append("<tr>" + "".join(tds) + "</tr>")

    font_size = "12px" if small else "14px"
    table = f"""
    <div style="width:100%;">
      <table style="width:100%; border-collapse:collapse; table-layout:fixed; font-size:{font_size};">
        <thead style="background:#f3f6fb;">
          <tr>{''.join(ths)}</tr>
        </thead>
        <tbody>
          {''.join(rows_html)}
        </tbody>
      </table>
    </div>
    """
    return table

def _mix_color(c1, c2, t: float):
    """Mezcla c1->c2 con t in [0,1] y devuelve hex."""
    t = max(0.0, min(1.0, float(t)))
    r = int(round(c1[0]*(1-t) + c2[0]*t))
    g = int(round(c1[1]*(1-t) + c2[1]*t))
    b = int(round(c1[2]*(1-t) + c2[2]*t))
    return f"#{r:02x}{g:02x}{b:02x}"

def _html_table_grad(df: pd.DataFrame, col_widths: list[str],
                     grad_cols: dict) -> str:
    """
    Tabla HTML sin scroll con degradado por columna.
    grad_cols = {
        "TOTAL CONSECUCIÓN": ( (r,g,b), strength ),
        "TOTAL INAPLICACIÓN": ( (r,g,b), strength ),
        "TOTAL PRÁCTICAS": ( (r,g,b), strength ),
    }
    strength ~ cuánto se acerca al color base (0..1).
    """
    if df is None or df.empty:
        return "<div style='color:#5f6368'>Sin datos</div>"

    cols = list(df.columns)
    widths = col_widths if (col_widths and len(col_widths) == len(cols)) else [f"{100//len(cols)}%"] * len(cols)

    # vmax por columna numérica con degradado
    vmax = {}
    for c in grad_cols.keys():
        if c in df.columns:
            vmax[c] = max(1, float(pd.to_numeric(df[c], errors="coerce").fillna(0).max()))
        else:
            vmax[c] = 1.0

    white = (255, 255, 255)

    ths = []
    for c, w in zip(cols, widths):
        ths.append(
            f"<th style='width:{w}; padding:8px 8px; text-align:left; "
            f"white-space:normal; overflow-wrap:break-word;'>{html.escape(str(c))}</th>"
        )

    rows_html = []
    for _, row in df.iterrows():
        tds = []
        for c, w in zip(cols, widths):
            val = row[c]
            # Texto
            if isinstance(val, (int,)):
                txt = f"{val:,}".replace(",", ".")
            elif isinstance(val, float):
                txt = f"{val:,.0f}".replace(",", ".")
            else:
                txt = str(val)
            txt = html.escape(txt)

            # Estilo
            base_style = f"width:{w}; padding:6px 8px; white-space:normal; overflow-wrap:break-word;"
            align = "text-align:center;" if (c != cols[0]) else "text-align:left;"
            bg_style = ""
            if c in grad_cols:
                color, strength = grad_cols[c]
                try:
                    num = float(val)
                except:
                    num = 0.0
                t = (num / vmax[c]) * strength  # 0..strength
                bg = _mix_color(white, color, t)
                bg_style = f"background:{bg};"
            tds.append(f"<td style='{base_style} {align} {bg_style}'>{txt}</td>")
        rows_html.append("<tr>" + "".join(tds) + "</tr>")

    table = f"""
    <div style="width:100%;">
      <table style="width:100%; border-collapse:collapse; table-layout:fixed; font-size:12px;">
        <thead style="background:#f3f6fb;">
          <tr>{''.join(ths)}</tr>
        </thead>
        <tbody>
          {''.join(rows_html)}
        </tbody>
      </table>
    </div>
    """
    return table

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

    # Limpieza
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

    # Selector de área
    areas = ['TODAS'] + sorted(df_f["AREA_N"].unique())
    area_sel = st.selectbox(" Empresas por área:", areas)
    df_scope = df_f if area_sel == 'TODAS' else df_f[df_f["AREA_N"] == area_sel].copy()

    # Flag prácticas
    df_scope["PRACTICAS_BOOL"] = (
        (df_scope["PRACTICAS_GE"].str.upper()=="GE") &
        (~df_scope["EMPRESA PRACT"].str.upper().isin(["","NO ENCONTRADO"])) &
        (~df_scope["CONSECUCION_BOOL"]) &
        (~df_scope["DEVOLUCION_BOOL"]) &
        (~df_scope["INAPLICACION_BOOL"])
    )

    # Tarjetas
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

    # Pie: cierres por consultor
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

    # Resumen por área + listados
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

    s_ge = _clean_series(df_scope["EMPRESA GE"])
    emp_ge = s_ge.value_counts().reset_index()
    emp_ge.columns = ["EMPRESA GE", "EMPLEOS"]

    s_pr = _clean_series(df_scope["EMPRESA PRACT"])
    emp_pr = s_pr.value_counts().reset_index()
    emp_pr.columns = ["EMPRESA PRÁCT.", "EMPLEOS"]

    col_res, col_ge, col_pr = st.columns([1.6, 1, 1])
    with col_res:
        st.markdown("#### Empresas por área")
        # HTML sin scroll horizontal + degradado por columna
        # Colores base (suaves):
        GREEN = (76, 175, 80)    # Consecu.
        RED   = (239, 83, 80)    # Inaplic.
        BLUE  = (66, 165, 245)   # Prácticas
        st.markdown(
            _html_table_grad(
                resumen_area,
                col_widths=["36%", "21%", "21%", "22%"],  # AREA + 3 totales
                grad_cols={
                    "TOTAL CONSECUCIÓN":  (GREEN, 0.75),
                    "TOTAL INAPLICACIÓN": (RED,   0.75),
                    "TOTAL PRÁCTICAS":    (BLUE,  0.75),
                }
            ),
            unsafe_allow_html=True
        )
    with col_ge:
        st.markdown("#### EMPRESAS GE")
        st.dataframe(
            emp_ge.style.background_gradient(subset=["EMPLEOS"], cmap="YlOrBr"),
            use_container_width=True
        )
    with col_pr:
        st.markdown("#### EMPRESAS PRÁCTICAS")
        st.dataframe(
            emp_pr.style.background_gradient(subset=["EMPLEOS"], cmap="PuBu"),
            use_container_width=True
        )

    # OBJETIVOS + tiles
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

    # KPIs
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

    # ==============================
    # Resumen por PROVINCIA (HTML sin scroll)
    # ==============================
    st.markdown("---")
    st.markdown("### 📍 Resumen por Provincia y Estado (alumnado único)")

    prov1_exists = "PROVINCIA 1" in df.columns
    prov2_exists = "PROVINCIA 2" in df.columns

    def _norm_prov_col(series):
        s = series.apply(lambda v: _norm_text_cell(v, upper=True, deaccent=True))
        s = s.replace("", "SIN PROVINCIA")
        return s

    def _tabla_provincias_df(df_in: pd.DataFrame, prov_col: str) -> pd.DataFrame:
        tmp = df_in.copy()
        tmp[prov_col] = _norm_prov_col(tmp[prov_col])

        def estado_row(r):
            if bool(r.get("CONSECUCION_BOOL", False)):  return "CONSECUCIÓN"
            if bool(r.get("INAPLICACION_BOOL", False)): return "INAPLICACIÓN"
            if bool(r.get("DEVOLUCION_BOOL", False)):   return "DEVOLUCIÓN"
            return "SIN ESTADO"

        tmp["ESTADO"] = tmp.apply(estado_row, axis=1)
        tmp["ALUMNO_KEY"] = (tmp["NOMBRE"].str.upper().str.strip() + "|" +
                             tmp["APELLIDOS"].str.upper().str.strip())
        tmp = tmp[tmp["ALUMNO_KEY"] != "|"]

        base = tmp.drop_duplicates(subset=[prov_col, "ALUMNO_KEY"])
        tabla = (base.groupby([prov_col, "ESTADO"]).size()
                     .unstack(fill_value=0)
                     .reset_index()
                     .rename(columns={prov_col: "PROVINCIA"}))

        for col in ["CONSECUCIÓN","INAPLICACIÓN","DEVOLUCIÓN","SIN ESTADO"]:
            if col not in tabla.columns:
                tabla[col] = 0

        tabla["TOTAL ALUMNOS"] = tabla[["CONSECUCIÓN","INAPLICACIÓN","DEVOLUCIÓN","SIN ESTADO"]].sum(axis=1)
        tabla = tabla.sort_values(by="TOTAL ALUMNOS", ascending=False)
        return tabla

    col_a, col_b = st.columns(2)
    with col_a:
        if prov1_exists:
            tabla1 = _tabla_provincias_df(df_scope, "PROVINCIA 1")
            st.markdown("**Provincia 1**")
            st.markdown(
                _html_table(
                    tabla1,
                    # PROVINCIA, CONS, INAP, DEV, SIN, TOTAL
                    col_widths=["34%", "13%", "13%", "13%", "13%", "14%"],
                    align_nums=True, small=True
                ),
                unsafe_allow_html=True
            )
        else:
            st.info("No se encontró **PROVINCIA 1**.")
    with col_b:
        if prov2_exists:
            tabla2 = _tabla_provincias_df(df_scope, "PROVINCIA 2")
            st.markdown("**Provincia 2**")
            st.markdown(
                _html_table(
                    tabla2,
                    col_widths=["34%", "13%", "13%", "13%", "13%", "14%"],
                    align_nums=True, small=True
                ),
                unsafe_allow_html=True
            )
        else:
            st.info("No se encontró **PROVINCIA 2**.")
