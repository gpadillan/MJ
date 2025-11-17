import pandas as pd
import streamlit as st
import plotly.express as px
import unicodedata
import re
from datetime import datetime
import html

# ========== UI ==========

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

    # ✅ Añadimos MENORES para priorizar su visualización si existe
    orden = ["RRHH", "SAP", "DPO", "EERR", "IA", "PYTHON", "FULL STACK", "BIM", "LOGISTICA", "MENORES"]
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

# ========== Helpers ==========

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
        # Provincias:
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

# ========== HTML tables (genéricas) ==========

def _html_table(df: pd.DataFrame, col_widths: list[str], align_nums: bool = True, small: bool = True) -> str:
    """Tabla fija sin scroll horizontal."""
    if df is None or df.empty:
        return "<div style='color:#5f6368'>Sin datos</div>"

    cols = list(df.columns)
    widths = col_widths if (col_widths and len(col_widths) == len(cols)) else [f"{100//len(cols)}%"] * len(cols)

    # --- Encabezados SIN salto de línea ---
    ths = []
    for c, w in zip(cols, widths):
        ths.append(
    f"<th style='width:{w}; padding:8px 8px; text-align:left; "
    f"white-space:nowrap; overflow:visible; text-overflow:clip;'>{html.escape(str(c))}</th>"
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

def _html_table_grad(df: pd.DataFrame, col_widths: list[str], grad_cols: dict) -> str:
    """
    Tabla sin scroll con degradado por columna.
    grad_cols = { "COL": ( (r,g,b), strength ), ... }
    """
    if df is None or df.empty:
        return "<div style='color:#5f6368'>Sin datos</div>"

    cols = list(df.columns)
    widths = col_widths if (col_widths and len(col_widths) == len(cols)) else [f"{100//len(cols)}%"] * len(cols)

    vmax = {}
    for c in grad_cols.keys():
        if c in df.columns:
            vmax[c] = max(1, float(pd.to_numeric(df[c], errors="coerce").fillna(0).max()))
        else:
            vmax[c] = 1.0

    white = (255, 255, 255)

    def _mix_color(c1, c2, t: float):
        t = max(0.0, min(1.0, float(t)))
        r = int(round(c1[0]*(1-t) + c2[0]*t))
        g = int(round(c1[1]*(1-t) + c2[1]*t))
        b = int(round(c1[2]*(1-t) + c2[2]*t))
        return f"#{r:02x}{g:02x}{b:02x}"

    # --- Encabezados SIN salto de línea ---
    ths = []
    for c, w in zip(cols, widths):
        ths.append(
            f"<th style='width:{w}; padding:8px 8px; text-align:left; "
            f"white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>{html.escape(str(c))}</th>"
        )

    rows_html = []
    for _, row in df.iterrows():
        tds = []
        for c, w in zip(cols, widths):
            val = row[c]
            # Texto a mostrar
            if isinstance(val, (int,)):
                txt = f"{val:,}".replace(",", ".")
            elif isinstance(val, float):
                txt = f"{val:,.0f}".replace(",", ".")
            else:
                txt = str(val)
            txt = html.escape(txt)

            # Estilo + color de fondo
            base_style = f"width:{w}; padding:6px 8px; white-space:normal; overflow-wrap:break-word;"
            align = "text-align:center;" if (c != cols[0]) else "text-align:left;"
            bg_style = ""
            if c in grad_cols:
                color, strength = grad_cols[c]
                # 🔢 Intentamos extraer un número para el gradiente (soporta "147 (36,8%)")
                raw = str(val)
                mnum = re.search(r"[-+]?\d+(\.\d+)?", raw.replace(",", "."))
                try:
                    num = float(mnum.group()) if mnum else 0.0
                except:
                    num = 0.0
                mix = _mix_color(white, color, (num / vmax.get(c, 1.0)) * strength)
                bg_style = f"background:{mix};"
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

def _html_table_cols_color(df: pd.DataFrame, col_widths: list[str], col_bg: dict,
                           align_nums: bool = True, small: bool = True) -> str:
    """
    Tabla sin scroll donde puedes colorear columnas concretas (fondo fijo).
    col_bg = { "CONSECUCIÓN": "#308446", "INAPLICACIÓN": "#eeeeee", "DEVOLUCIÓN": "#fff3e0", ... }
    """
    if df is None or df.empty:
        return "<div style='color:#5f6368'>Sin datos</div>"

    cols = list(df.columns)
    widths = col_widths if (col_widths and len(col_widths) == len(cols)) else [f"{100//len(cols)}%"] * len(cols)

    # --- Encabezados SIN salto de línea ---
    ths = []
    for c, w in zip(cols, widths):
        ths.append(
            f"<th style='width:{w}; padding:8px 8px; text-align:left; "
            f"white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>{html.escape(str(c))}</th>"
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
            bg = f"background:{col_bg.get(c, 'transparent')};"
            tds.append(
                f"<td style='width:{w}; padding:6px 8px; {style_num} {bg} "
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

# ========== Mapeo España (comunidades y provincias) ==========

COMM_KEYS = {
    "ANDALUCIA":"Andalucía", "ARAGON":"Aragón", "ASTURIAS":"Asturias",
    "ISLAS BALEARES":"Illes Balears","ILLES BALEARS":"Illes Balears","BALEARES":"Illes Balears",
    "CANARIAS":"Canarias", "CANTABRIA":"Cantabria",
    "CASTILLA Y LEON":"Castilla y León","CASTILLA LA MANCHA":"Castilla-La Mancha",
    "CATALUNA":"Cataluña","CATALUNYA":"Cataluña",
    "COMUNIDAD VALENCIANA":"Comunidad Valenciana","VALENCIANA":"Comunidad Valenciana",
    "EXTREMADURA":"Extremadura","GALICIA":"Galicia",
    "MADRID":"Comunidad de Madrid","COMUNIDAD DE MADRID":"Comunidad de Madrid",
    "MURCIA":"Región de Murcia","REGION DE MURCIA":"Región de Murcia",
    "NAVARRA":"Comunidad Foral de Navarra","COMUNIDAD FORAL DE NAVARRA":"Comunidad Foral de Navarra",
    "PAIS VASCO":"País Vasco","EUSKADI":"País Vasco",
    "LA RIOJA":"La Rioja","CEUTA":"Ceuta","MELILLA":"Melilla",
    "ESPAÑA":"España","ESPANA":"España","ESPAÑA (INDEF.)":"España","ESPANA (INDEF.)":"España",
    "FUERA DE ESPAÑA":"Fuera de España"
}

def _n(s): return _norm_text_cell(s, upper=True, deaccent=True)

def _map_prov_to_comm(raw_name: str) -> tuple[str, str, str, str]:
    if pd.isna(raw_name): 
        return ("","","","")
    x = _n(raw_name)

    if re.match(r"^REMOTO", x):
        return ("SIN COMUNIDAD", "Sin comunidad", "REMOTO", "Remoto")

    if x in COMM_KEYS:
        lbl = COMM_KEYS[x]
        if x.startswith("ESPA"):
            return ("ESPAÑA", "España", "ESPAÑA", "España")
        if "FUERA" in x:
            return ("FUERA DE ESPAÑA", "Fuera de España", "FUERA DE ESPAÑA", "Fuera de España")
        return (x, lbl, x, lbl)

    if re.search(r"\bESPANA\b|\bESPAÑA\b|\bPROVINCIAS ESPAÑA\b|\bESPAÑA \(INDEF\.\)", x):
        return ("ESPAÑA", "España", "ESPAÑA", "España")

    if re.search(r"\b(PERU|HOLANDA|PORTUGAL|FRANCIA|ALEMANIA)\b", x):
        return ("FUERA DE ESPAÑA", "Fuera de España", x, raw_name.strip())

    patterns = [
        (r"\b(ALMERIA|C[ÁA]DIZ|CORDOBA|GRANADA|HUELVA|JA[ÉE]N|M[ÁA]LAGA|SEVILLA)\b", "ANDALUCIA", "Andalucía"),
        (r"\b(HUESCA|TERUEL|ZARAGOZA)\b", "ARAGON", "Aragón"),
        (r"\b(ASTURIAS|OVIEDO|GIJ[ÓO]N)\b", "ASTURIAS", "Asturias"),
        (r"\b(ILLES BALEARS|BALEARS|BALEARES|MALLORCA|PALMA|IBIZA)\b", "ISLAS BALEARES", "Illes Balears"),
        (r"\b(LAS PALMAS|PALMAS, LAS|GRAN CANARIA|SANTA CRUZ DE TENERIFE|STA\.? CRUZ DE TENERIFE|TENERIFE|TELDE|ARRECIFE)\b", "CANARIAS", "Canarias"),
        (r"\b(CANTABRIA|SANTANDER)\b", "CANTABRIA", "Cantabria"),
        (r"\b(ÁVILA|AVILA|BURGOS|LE[ÓO]N|PALENCIA|SALAMANCA|SEGOVIA|SORIA|VALLADOLID|ZAMORA)\b", "CASTILLA Y LEON", "Castilla y León"),
        (r"\b(ALBACETE|CIUDAD REAL|CUENCA|GUADALAJARA|TOLEDO|TALAVERA DE LA REINA)\b", "CASTILLA LA MANCHA", "Castilla-La Mancha"),
        (r"\b(BARCELONA|GIRONA|GERONA|LLEIDA|L[ÉE]RIDA|TARRAGONA|HOSPITALET|L'HOSPITALET|CORNELL[ÀA]|BADALONA|SABADELL|TERRASSA|MATAR[ÓO]|RUB[ÍI]|REUS)\b",
         "CATALUNA", "Cataluña"),
        (r"\b(ALICANTE|ALACANT|CASTELL[ÓO]N|CASTELL[OÓ]|VALENCIA|VAL[ÈE]NCIA|TORREVIEJA|ORIHUELA|ELDA|BENIDORM)\b",
         "COMUNIDAD VALENCIANA", "Comunidad Valenciana"),
        (r"\b(BADAJOZ|C[ÁA]CERES)\b", "EXTREMADURA", "Extremadura"),
        (r"\b(A CORU[NÑ]A|LA CORU[NÑ]A|CORU[NÑ]A, A|CORUNA, A|LUGO|OURENSE|ORENSE|PONTEVEDRA|VIGO|SANTIAGO DE COMPOSTELA|FERROL)\b",
         "GALICIA", "Galicia"),
        (r"\b(MADRID|ALCAL[ÁA] DE HENARES|FUENLABRADA|GETAFE|ALCORC[ÓO]N|M[ÓO]STOLES|PARLA|LEGAN[ÉE]S)\b", "MADRID", "Comunidad de Madrid"),
        (r"\b(MURCIA|CARTAGENA)\b", "MURCIA", "Región de Murcia"),
        (r"\b(NAVARRA|PAMPLONA)\b", "NAVARRA", "Comunidad Foral de Navarra"),
        (r"\b(VIZCAYA|BIZKAIA|GIPUZKOA|GUIPUZCOA|[ÁA]LAVA|ARABA|BILBAO|VITORIA|DONOSTIA|SAN SEBASTI[ÁA]N|BARAKALDO)\b",
         "PAIS VASCO", "País Vasco"),
        (r"\b(RIOJA, LA|LA RIOJA|RIOJA|LOGRO[NÑ]O)\b", "LA RIOJA", "La Rioja"),
        (r"\b(CEUTA)\b", "CEUTA", "Ceuta"),
        (r"\b(MELILLA)\b", "MELILLA", "Melilla"),
        (r"\b(M[ÁA]LAGA|M[ÁA]RBELLA|ALMER[ÍI]A|HUELVA|C[ÓO]RDOBA|C[ÁA]DIZ|J[ÉE]REZ|JA[ÉE]N|SAN FERNANDO|ALGECIRAS|ROQUETAS DE MAR)\b",
         "ANDALUCIA", "Andalucía"),
        (r"\b(ZAMORA|LE[ÓO]N|BURGOS|PALENCIA|SALAMANCA|SEGOVIA|SORIA|VALLADOLID|PONFERRADA)\b",
         "CASTILLA Y LEON", "Castilla y León"),
    ]
    for pat, comm_k, comm_lbl in patterns:
        if re.search(pat, x):
            prov_label = raw_name.strip()
            prov_key   = _n(prov_label)
            return (comm_k, comm_lbl, prov_key, prov_label)

    return ("","","","")

# ========== APP ==========

def render(df: pd.DataFrame):
    st.title("Informe de Cierre de Expedientes")
    st.button("🔄 Recargar / limpiar caché", on_click=st.cache_data.clear)

    # Detecta columnas base
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
            c2.markdown(render_card("INAPLICACIÓN", tot_inap, "#eeeeee"), unsafe_allow_html=True)
            c3.markdown(render_card("TOTAL PRÁCTICAS", tot_emp_ge, "#ede7f6"), unsafe_allow_html=True)
        else:
            anio_txt = opcion.split()[-1]
            if anio_txt == "2025":
                c1, c2, c3, c4 = st.columns(4)
                c1.markdown(render_card("CONSECUCIÓN 2025", tot_con, "#e3f2fd"), unsafe_allow_html=True)
                c2.markdown(render_card("INAPLICACIÓN 2025", tot_inap, "#eeeeee"), unsafe_allow_html=True)
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
                c2.markdown(render_card(f"INAPLICACIÓN {anio_txt}", tot_inap, "#eeeeee"), unsafe_allow_html=True)
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

    # ========== Resumen por área + listados (con % integrado) ==========

    st.markdown("")
    df_tmp = df_scope.copy()
    if "AREA_N" not in df_tmp:
        df_tmp["AREA_N"] = df_tmp["AREA"].apply(lambda v: _norm_text_cell(v, upper=True, deaccent=True))
        df_tmp.loc[df_tmp["AREA_N"] == "", "AREA_N"] = "SIN ÁREA"

    # Clave alumno
    df_tmp["ALUMNO_KEY"] = (
        df_tmp["NOMBRE"].astype(str).str.upper().str.strip()
        + "|"
        + df_tmp["APELLIDOS"].astype(str).str.upper().str.strip()
    )

    areas_idx = sorted(df_tmp["AREA_N"].unique())

    con_area  = df_tmp[df_tmp["CONSECUCION_BOOL"]].groupby("AREA_N").size()
    inap_area = df_tmp[df_tmp["INAPLICACION_BOOL"]].groupby("AREA_N").size()
    emp_pr_norm = df_tmp["EMPRESA PRACT"].apply(lambda v: _norm_text_cell(v, upper=True, deaccent=True))
    mask_pract  = ~emp_pr_norm.isin(INVALID_TXT)
    prac_area   = df_tmp[mask_pract].groupby("AREA_N").size()
    alumnos_area = df_tmp.groupby("AREA_N")["ALUMNO_KEY"].nunique()

    resumen_area = pd.DataFrame(index=areas_idx)
    resumen_area["TOTAL ALUMNOS"]      = alumnos_area.reindex(areas_idx, fill_value=0)
    resumen_area["TOTAL CONSECUCIÓN"]  = con_area.reindex(areas_idx, fill_value=0)
    resumen_area["TOTAL INAPLICACIÓN"] = inap_area.reindex(areas_idx, fill_value=0)
    resumen_area["TOTAL PRÁCTICAS"]    = prac_area.reindex(areas_idx, fill_value=0)

    resumen_area.index.name = "AREA"
    resumen_area = (
        resumen_area.reset_index()
                    .astype({
                        "TOTAL ALUMNOS": int,
                        "TOTAL CONSECUCIÓN": int,
                        "TOTAL INAPLICACIÓN": int,
                        "TOTAL PRÁCTICAS": int,
                    })
                    .sort_values(by="TOTAL CONSECUCIÓN", ascending=False)
    )

    total_row = {
        "AREA": "Total",
        "TOTAL ALUMNOS":      int(resumen_area["TOTAL ALUMNOS"].sum()),
        "TOTAL CONSECUCIÓN":  int(resumen_area["TOTAL CONSECUCIÓN"].sum()),
        "TOTAL INAPLICACIÓN": int(resumen_area["TOTAL INAPLICACIÓN"].sum()),
        "TOTAL PRÁCTICAS":    int(resumen_area["TOTAL PRÁCTICAS"].sum()),
    }
    resumen_area = pd.concat([resumen_area, pd.DataFrame([total_row])], ignore_index=True)

    # Construimos versión display con porcentajes dentro de las celdas
    def _fmt_count_pct(row, col):
        total_alum = row["TOTAL ALUMNOS"]
        count = int(row[col])
        if total_alum <= 0:
            return str(count)
        pct = (count / total_alum) * 100
        pct_str = f"{pct:.1f}".replace(".", ",")
        return f"{count} ({pct_str}%)"

    resumen_disp = resumen_area.copy()
    resumen_disp["AREA"] = resumen_disp.apply(
        lambda r: f"{r['AREA']} ({r['TOTAL ALUMNOS']})", axis=1
    )
    resumen_disp["TOTAL CONSECUCIÓN"]  = resumen_disp.apply(lambda r: _fmt_count_pct(r, "TOTAL CONSECUCIÓN"), axis=1)
    resumen_disp["TOTAL INAPLICACIÓN"] = resumen_disp.apply(lambda r: _fmt_count_pct(r, "TOTAL INAPLICACIÓN"), axis=1)
    # TOTAL PRÁCTICAS solo número
    resumen_disp["TOTAL PRÁCTICAS"]    = resumen_disp["TOTAL PRÁCTICAS"].astype(int).astype(str)

    s_ge = _clean_series(df_scope["EMPRESA GE"])
    emp_ge = s_ge.value_counts().reset_index()
    emp_ge.columns = ["EMPRESA GE", "EMPLEOS"]

    s_pr = _clean_series(df_scope["EMPRESA PRACT"])
    emp_pr = s_pr.value_counts().reset_index()
    emp_pr.columns = ["EMPRESA PRÁCT.", "EMPLEOS"]

    col_res, col_ge, col_pr = st.columns([1.6, 1, 1])
    with col_res:
        st.markdown("#### Empresas por área")

        GREEN = (76, 175, 80)
        GRAY  = (189, 189, 189)
        BLUE  = (66, 165, 245)

        resumen_counts_disp = resumen_disp[["AREA", "TOTAL CONSECUCIÓN", "TOTAL INAPLICACIÓN", "TOTAL PRÁCTICAS"]]

        st.markdown(
            _html_table_grad(
                resumen_counts_disp,
                col_widths=["36%", "21%", "21%", "22%"],
                grad_cols={
                    "TOTAL CONSECUCIÓN":  (GREEN, 0.75),
                    "TOTAL INAPLICACIÓN": (GRAY,  0.75),
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

    # ========== Comunidades Autónomas – resumen y detalle ==========

    st.markdown("---")
    st.markdown("### 🗺️ Comunidades Autónomas – resumen y detalle (con provincias)")

    prov1_exists = "PROVINCIA 1" in df.columns
    prov2_exists = "PROVINCIA 2" in df.columns
    if not (prov1_exists or prov2_exists):
        st.info("No se encontraron columnas **PROVINCIA 1** / **PROVINCIA 2**.")
        return

    def _estado_row(r):
        if bool(r.get("CONSECUCION_BOOL", False)):  return "CONSECUCIÓN"
        if bool(r.get("INAPLICACION_BOOL", False)): return "INAPLICACIÓN"
        if bool(r.get("DEVOLUCION_BOOL", False)):   return "DEVOLUCIÓN"
        return "SIN ESTADO"

    dfp = df_scope.copy()
    dfp["ESTADO"] = dfp.apply(_estado_row, axis=1)
    dfp["ALUMNO_KEY"] = (dfp["NOMBRE"].str.upper().str.strip() + "|" +
                         dfp["APELLIDOS"].str.upper().str.strip())

    rows = []
    for _, r in dfp.iterrows():
        if r["ALUMNO_KEY"] == "|":
            continue
        candidatos = []
        if prov1_exists and pd.notna(r["PROVINCIA 1"]): candidatos.append(r["PROVINCIA 1"])
        if prov2_exists and pd.notna(r["PROVINCIA 2"]): candidatos.append(r["PROVINCIA 2"])
        if not candidatos:
            continue
        for raw in set(candidatos):
            comm_k, comm_lbl, prov_k, prov_lbl = _map_prov_to_comm(raw)
            if comm_k:
                rows.append((comm_k, comm_lbl, prov_k, prov_lbl, r["ALUMNO_KEY"], r["ESTADO"]))

    long_df = pd.DataFrame(rows, columns=["COMM_K","COMM_LABEL","PROV_K","PROV_LABEL","ALUMNO_KEY","ESTADO"])
    if long_df.empty:
        st.info("No hay datos geográficos mapeables.")
        return

    base_prov_unique = long_df.drop_duplicates(["PROV_K","ALUMNO_KEY"])
    prov_total = (base_prov_unique.groupby(["COMM_K","PROV_K","PROV_LABEL"])["ALUMNO_KEY"]
                  .nunique().rename("Total").reset_index())

    base_prov_state = long_df.drop_duplicates(["PROV_K","ALUMNO_KEY","ESTADO"])
    prov_state = (base_prov_state.groupby(["COMM_K","PROV_K","PROV_LABEL","ESTADO"])["ALUMNO_KEY"]
                  .nunique().reset_index())
    prov_state_pivot = prov_state.pivot_table(
        index=["COMM_K","PROV_K","PROV_LABEL"], columns="ESTADO",
        values="ALUMNO_KEY", aggfunc="sum", fill_value=0
    ).reset_index()

    prov_full = prov_total.merge(prov_state_pivot, on=["COMM_K","PROV_K","PROV_LABEL"], how="left")
    for c in ["CONSECUCIÓN","INAPLICACIÓN","DEVOLUCIÓN","SIN ESTADO"]:
        if c not in prov_full.columns: prov_full[c] = 0
    prov_full = prov_full[["COMM_K","PROV_K","PROV_LABEL","CONSECUCIÓN","INAPLICACIÓN","DEVOLUCIÓN","SIN ESTADO","Total"]]

    comm_sum = (prov_full.groupby(["COMM_K"])
                [["CONSECUCIÓN","INAPLICACIÓN","DEVOLUCIÓN","SIN ESTADO","Total"]]
                .sum().reset_index())
    labels = long_df.drop_duplicates(["COMM_K","COMM_LABEL"])[["COMM_K","COMM_LABEL"]]
    comm_sum = comm_sum.merge(labels, on="COMM_K", how="left").rename(columns={"COMM_LABEL":"COMM_NAME"})
    comm_sum = comm_sum.sort_values("Total", ascending=False)

    PROV_COLORS = {
        "CONSECUCIÓN":  "#e3f2fd",
        "INAPLICACIÓN": "#eeeeee",
        "DEVOLUCIÓN":   "#ffe0e0",
    }

    chip_css = "display:flex; flex-wrap:wrap; gap:8px; margin:8px 0 10px;"

    def chip(bg, text):
        return f"<span style='background:{bg}; padding:6px 8px; border-radius:8px; font-weight:700;'>{text}</span>"

    cols_cards = st.columns(2)
    for i, row in comm_sum.iterrows():
        comm_k   = row["COMM_K"]
        comm_nm  = row["COMM_NAME"] or "Sin comunidad"
        total    = int(row["Total"])
        cons     = int(row["CONSECUCIÓN"])
        inap     = int(row["INAPLICACIÓN"])
        dev      = int(row["DEVOLUCIÓN"])
        sinest   = int(row["SIN ESTADO"])

        sub = prov_full[prov_full["COMM_K"] == comm_k].copy().sort_values("Total", ascending=False)
        tabla = sub.rename(columns={"PROV_LABEL":"Provincia"})[
            ["Provincia","CONSECUCIÓN","INAPLICACIÓN","DEVOLUCIÓN","Total"]
        ]

        tabla_html = _html_table_cols_color(
            tabla,
            col_widths=["20%","20%","20%","20%","20%"],
            col_bg=PROV_COLORS,
            align_nums=True, small=True
        ) if not tabla.empty else "<div style='color:#5f6368'>Sin provincias</div>"

        chips = (
            "<div style='" + chip_css + "'>"
            + chip("#d7f7d9",  f"📗 Consecución: {cons}")
            + chip("#eeeeee",  f"📰 Inaplicación: {inap}")
            + chip("#ffc7c7",  f"📕 Devolución: {dev}")
            + chip("#f5f5f5",  f" Sin estado: {sinest}")
            + "</div>"
        )

        card_html = (
            "<div style='border:1px solid #e3e8ef; border-radius:12px; padding:12px; margin-bottom:12px;"
            "box-shadow:0 1px 3px rgba(0,0,0,0.05); background:#fff;'>"
            "<div style='display:flex; justify-content:space-between; align-items:baseline;'>"
            f"<div style='font-weight:800; color:#0b2e6b; font-size:18px;'>{comm_nm}</div>"
            f"<div style='font-weight:900; color:#00335c;'>Total alumnos: {total}</div>"
            "</div>"
            + chips
            + tabla_html
            + "</div>"
        )
        cols_cards[i % 2].markdown(card_html, unsafe_allow_html=True)
