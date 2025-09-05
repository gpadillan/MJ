# principal.py

import os
import pandas as pd
import streamlit as st
from datetime import datetime
from pages.academica.sharepoint_utils import get_access_token, get_site_id, download_excel
from streamlit_folium import folium_static
import folium
from utils.geo_utils import normalize_text, PROVINCIAS_COORDS, PAISES_COORDS, geolocalizar_pais
import unicodedata
import re

# ===================== UTILS GENERALES =====================

def format_euro(value: float) -> str:
    try:
        v = float(value)
    except Exception:
        v = 0.0
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def render_info_card(title, value1, value2, color="#e3f2fd"):
    return f"""
        <div style='padding: 8px; background-color: {color}; border-radius: 8px;
                    font-size: 13px; text-align: center; border: 1px solid #ccc;
                    box-shadow: 1px 1px 5px rgba(0,0,0,0.1);'>
            <strong>{title}</strong><br>
            👥 Matrículas: <strong>{value1}</strong><br>
            💶 Importe: <strong>{value2} €</strong>
        </div>
    """

def render_import_card(title, value, color="#ede7f6"):
    return f"""
        <div style='padding: 8px; background-color: {color}; border-radius: 8px;
                    font-size: 13px; text-align: center; border: 1px solid #ccc;
                    box-shadow: 1px 1px 5px rgba(0,0,0,0.1);'>
            <strong>{title}</strong><br>
            <strong>{value}</strong>
        </div>
    """

# Tarjeta compacta tipo "barra" para Gestión de Cobro (EIP)
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

# ===================== HELPERS DE EMPLEO (MISMOS QUE EN cierre_expediente_total.py) =====================

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

def normalizar_like_cierre(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Normaliza EXACTAMENTE como cierre_expediente_total.py."""
    df = df_raw.copy()
    colmap = _build_colmap(df.columns)
    df = df.rename(columns={colmap[k]:k for k in colmap})
    df["AREA"] = df.get("AREA", pd.Series(index=df.index)).apply(lambda v: _norm_text_cell(v, upper=True, deaccent=True))
    for c in ["PRACTICAS_GE","EMPRESA PRACT","EMPRESA GE","NOMBRE","APELLIDOS","CONSULTOR EIP"]:
        if c in df.columns:
            df[c] = df[c].apply(_norm_text_cell)
    if "CONSULTOR EIP" in df.columns:
        df["CONSULTOR EIP"] = df["CONSULTOR EIP"].replace('', 'Otros').fillna('Otros')
        df = df[df["CONSULTOR EIP"].str.upper()!="NO ENCONTRADO"]

    col_fc = "FECHA CIERRE"
    if col_fc in df.columns:
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
    else:
        df["FECHA CIERRE"] = pd.NaT
        df["AÑO_CIERRE"] = pd.NA

    if "CONSECUCION GE" in df.columns:
        df["CONSECUCION_BOOL"]=df["CONSECUCION GE"].apply(_to_bool)
    else:
        df["CONSECUCION_BOOL"]=False
    if "INAPLICACION GE" in df.columns:
        df["INAPLICACION_BOOL"]=df["INAPLICACION GE"].apply(_to_bool)
    else:
        df["INAPLICACION_BOOL"]=False
    if "DEVOLUCION GE" in df.columns:
        df["DEVOLUCION_BOOL"]=df["DEVOLUCION GE"].apply(_to_bool)
    else:
        df["DEVOLUCION_BOOL"]=False
    return df

# ===================== CARGA DE DATOS (SharePoint) =====================

def load_academica_data():
    if "academica_excel_data" not in st.session_state:
        try:
            config = st.secrets["academica"]
            token = get_access_token(config)
            site_id = get_site_id(config, token)
            file = download_excel(config, token, site_id)
            excel_data = pd.read_excel(file, sheet_name=None)
            st.session_state["academica_excel_data"] = excel_data
        except Exception as e:
            st.warning("⚠️ No se pudo cargar datos académicos automáticamente.")
            st.exception(e)

def load_empleo_df_raw():
    try:
        config = st.secrets["empleo"]
        token = get_access_token(config)
        site_id = get_site_id(config, token)
        file = download_excel(config, token, site_id)
        df_empleo = pd.read_excel(file, sheet_name="GENERAL")
        return df_empleo
    except Exception as e:
        st.error("❌ No pude cargar Empleo desde SharePoint. Revisa st.secrets['empleo'].")
        st.exception(e)
        return pd.DataFrame()

# ===================== PÁGINA PRINCIPAL =====================

def principal_page():
    st.title("📊 Panel Principal")

    if st.button("🔄 Recargar datos manualmente"):
        for key in ["academica_excel_data", "excel_data", "df_ventas", "df_preventas", "df_gestion", "df_empleo_informe"]:
            if key in st.session_state:
                del st.session_state[key]
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("Caché limpiada y datos recargados.")

    load_academica_data()

    # Ficheros locales
    UPLOAD_FOLDER = "uploaded_admisiones"
    GESTION_FOLDER = "uploaded"
    VENTAS_FILE = os.path.join(UPLOAD_FOLDER, "ventas.xlsx")
    PREVENTAS_FILE = os.path.join(UPLOAD_FOLDER, "preventas.xlsx")
    GESTION_FILE = os.path.join(GESTION_FOLDER, "archivo_cargado.xlsx")

    traduccion_meses = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
        7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }

    anio_actual = datetime.now().year
    total_matriculas = 0
    total_preventas = 0
    total_preventas_importe = 0
    matriculas_por_mes, importes_por_mes = {}, {}

    # ===== VENTAS =====
    if os.path.exists(VENTAS_FILE):
        df_ventas = pd.read_excel(VENTAS_FILE)
        df_ventas.columns = df_ventas.columns.str.strip().str.lower()
        if "fecha de cierre" in df_ventas.columns:
            df_ventas['fecha de cierre'] = pd.to_datetime(df_ventas['fecha de cierre'], errors='coerce')
            df_ventas = df_ventas.dropna(subset=['fecha de cierre'])
            df_ventas = df_ventas[df_ventas['fecha de cierre'].dt.year == anio_actual]
            if 'importe' not in df_ventas.columns:
                df_ventas['importe'] = 0
            else:
                df_ventas['importe'] = pd.to_numeric(df_ventas['importe'], errors='coerce').fillna(0)
            df_ventas['mes'] = df_ventas['fecha de cierre'].dt.month
            total_matriculas = len(df_ventas)
            for m in range(1, 12+1):
                df_mes = df_ventas[df_ventas['mes'] == m]
                matriculas_por_mes[m] = len(df_mes)
                importes_por_mes[m] = df_mes['importe'].sum()

    # ===== PREVENTAS =====
    if os.path.exists(PREVENTAS_FILE):
        df_preventas = pd.read_excel(PREVENTAS_FILE)
        df_preventas.columns = df_preventas.columns.str.strip().str.lower()
        total_preventas = len(df_preventas)
        columnas_importe = [c for c in df_preventas.columns if "importe" in c]
        if columnas_importe:
            total_preventas_importe = df_preventas[columnas_importe].sum(numeric_only=True).sum()

    # ===== GESTIÓN DE COBRO (EIP) =====
    st.markdown("---")
    st.markdown("## 💼 Gestión de Cobro (EIP)")

    df_gestion = None
    if "excel_data_eip" in st.session_state and st.session_state["excel_data_eip"] is not None:
        df_gestion = st.session_state["excel_data_eip"].copy()
    elif os.path.exists(GESTION_FILE):
        df_gestion = pd.read_excel(GESTION_FILE)

    if df_gestion is None or df_gestion.empty:
        st.info("No hay datos de Gestión de Cobro disponibles.")
    else:
        df_gestion.columns = [c.strip() for c in df_gestion.columns]
        col_estado = next((c for c in df_gestion.columns if c.strip().lower() == "estado"), None)

        if not col_estado:
            st.error("❌ El archivo no contiene la columna 'Estado'.")
        else:
            columnas_validas = []
            for anio in range(2018, anio_actual):
                col = f"Total {anio}"
                if col in df_gestion.columns:
                    columnas_validas.append(col)
            for mes_num in range(1, 13):
                col_mes = f"{traduccion_meses[mes_num]} {anio_actual}"
                if col_mes in df_gestion.columns:
                    columnas_validas.append(col_mes)

            if not columnas_validas:
                st.info("No se encontraron columnas de totales/meses en el archivo de Gestión de Cobro.")
            else:
                df_gestion[columnas_validas] = df_gestion[columnas_validas].apply(pd.to_numeric, errors="coerce").fillna(0)
                df_resumen = (
                    df_gestion.groupby(col_estado)[columnas_validas]
                              .sum()
                              .reset_index()
                              .rename(columns={col_estado: "Estado"})
                )
                df_resumen["Total"] = df_resumen[columnas_validas].sum(axis=1)

                # === Totales por estado (robusto con acentos) ===
                def _norm_estado(s):
                    s = ''.join(ch for ch in unicodedata.normalize('NFD', str(s)) if unicodedata.category(ch) != 'Mn')
                    s = re.sub(r'\s+', ' ', s).strip().upper()
                    return s

                tot_por_estado = {_norm_estado(r["Estado"]): float(r["Total"]) for _, r in df_resumen.iterrows()}

                cobrado          = tot_por_estado.get("COBRADO", 0.0)
                domic_confirmada = tot_por_estado.get("DOMICILIACION CONFIRMADA", 0.0)
                pendiente        = tot_por_estado.get("PENDIENTE", 0.0)
                dudoso           = tot_por_estado.get("DUDOSO COBRO", 0.0)
                incobrable       = tot_por_estado.get("INCROBRABLE", tot_por_estado.get("INCOBRABLE", 0.0))
                domic_emitida    = tot_por_estado.get("DOMICILIACION EMITIDA", 0.0)
                no_cobrado       = tot_por_estado.get("NO COBRADO", 0.0)

                total_generado = cobrado + domic_confirmada

                # Paleta como en tu mock
                COLORS = {
                    "COBRADO": "#E3F2FD",
                    "CONFIRMADA": "#FFE0B2",
                    "TOTAL": "#D3F9D8",
                    "PENDIENTE": "#E6FCF5",
                    "DUDOSO": "#FFEBEE",
                    "INCOBRABLE": "#FCE4EC",
                    "EMITIDA": "#FFF9C4",
                    "NOCOBRADO": "#ECEFF1",
                }

                # ===== Fila 1: Cobrado | Domiciliación Confirmada | Total generado =====
                c1, c2, c3 = st.columns(3)
                c1.markdown(render_bar_card("Cobrado", cobrado, COLORS["COBRADO"], "🟦"), unsafe_allow_html=True)
                c2.markdown(render_bar_card("Domiciliación Confirmada", domic_confirmada, COLORS["CONFIRMADA"], "🟧"), unsafe_allow_html=True)
                c3.markdown(render_bar_card("Total Generado", total_generado, COLORS["TOTAL"], "💰"), unsafe_allow_html=True)

                # ===== Fila 2: Pendiente | Dudoso Cobro | Incobrable | Domiciliación Emitida | No Cobrado =====
                b1, b2, b3, b4, b5 = st.columns(5)
                b1.markdown(render_bar_card("Pendiente", pendiente, COLORS["PENDIENTE"], "⏳"), unsafe_allow_html=True)
                b2.markdown(render_bar_card("Dudoso Cobro", dudoso, COLORS["DUDOSO"], "❗"), unsafe_allow_html=True)
                b3.markdown(render_bar_card("Incobrable", incobrable, COLORS["INCOBRABLE"], "⛔"), unsafe_allow_html=True)
                b4.markdown(render_bar_card("Domiciliación Emitida", domic_emitida, COLORS["EMITIDA"], "📤"), unsafe_allow_html=True)
                b5.markdown(render_bar_card("No Cobrado", no_cobrado, COLORS["NOCOBRADO"], "🧾"), unsafe_allow_html=True)

    # ===== ADMISIONES =====
    st.markdown("## 📥 Admisiones")
    st.markdown(f"### 📅 Matrículas por Mes ({anio_actual})")
    for i in range(0, 12, 4):
        cols = st.columns(4)
        for j in range(4):
            mes_num = i + j + 1
            if mes_num > 12: continue
            mes = traduccion_meses[mes_num]
            matriculas = matriculas_por_mes.get(mes_num, 0)
            importe = format_euro(importes_por_mes.get(mes_num, 0))
            cols[j].markdown(render_info_card(mes, matriculas, importe), unsafe_allow_html=True)

    st.markdown("### Total General")
    col1, col2 = st.columns(2)
    col1.markdown(render_info_card("Matrículas Totales", total_matriculas, format_euro(sum(importes_por_mes.values())), "#c8e6c9"), unsafe_allow_html=True)
    col2.markdown(render_info_card("Preventas", total_preventas, format_euro(total_preventas_importe), "#ffe0b2"), unsafe_allow_html=True)

    # ===== ACADÉMICA =====
    if "academica_excel_data" in st.session_state:
        data = st.session_state["academica_excel_data"]
        hoja = "CONSOLIDADO ACADÉMICO"
        if hoja in data:
            df = data[hoja]
            st.markdown("---")
            st.markdown("## 🎓 Indicadores Académicos")
            try:
                indicadores = [
                    ("🧑‍🎓 Alumnos/as", int(df.iloc[1, 1])),
                    ("🎯 Éxito académico", f"{df.iloc[2, 2]:.2%}".replace(".", ",")),
                    ("🚫 Absentismo", f"{df.iloc[3, 2]:.2%}".replace(".", ",")),
                    ("⚠️ Riesgo", f"{df.iloc[4, 2]:.2%}".replace(".", ",")),
                    ("📅 Cumpl. Fechas Docente", f"{df.iloc[5, 2]:.0%}".replace(".", ",")),
                    ("📅 Cumpl. Fechas Alumnado", f"{df.iloc[6, 2]:.0%}".replace(".", ",")),
                    ("📄 Cierre Exp. Académico", f"{df.iloc[7, 2]:.2%}".replace(".", ",")),
                    ("😃 Satisfacción Alumnado", f"{df.iloc[8, 2]:.2%}".replace(".", ",")),
                    ("⭐ Reseñas", f"{df.iloc[9, 2]:.2%}".replace(".", ",")),
                    ("📢 Recomendación Docente", int(df.iloc[10, 2])),
                    ("📣 Reclamaciones", int(df.iloc[11, 2]))
                ]
                for i in range(0, len(indicadores), 4):
                    cols = st.columns(4)
                    for j, (titulo, valor) in enumerate(indicadores[i:i+4]):
                        cols[j].markdown(render_import_card(titulo, valor, "#f0f4c3"), unsafe_allow_html=True)
                st.markdown("### 🏅 Certificaciones")
                total_cert = int(df.iloc[13, 2])
                st.markdown(render_import_card("🎖️ Total Certificaciones", total_cert, "#dcedc8"), unsafe_allow_html=True)
            except Exception as e:
                st.warning("⚠️ Error al procesar los indicadores académicos.")
                st.exception(e)

    # ===== DESARROLLO PROFESIONAL =====
    st.markdown("---")
    st.markdown("## 🔧 Indicadores de Empleo")
    try:
        anio_obj = datetime.now().year
        if "df_empleo_informe" in st.session_state:
            df_empleo_norm = st.session_state["df_empleo_informe"].copy()
        else:
            df_empleo_src = load_empleo_df_raw()
            if df_empleo_src.empty:
                st.info("Sin datos de empleo para mostrar.")
                df_empleo_norm = pd.DataFrame()
            else:
                df_empleo_norm = normalizar_like_cierre(df_empleo_src)
                st.session_state["df_empleo_informe"] = df_empleo_norm.copy()

        if not df_empleo_norm.empty:
            df_y = df_empleo_norm[df_empleo_norm["AÑO_CIERRE"] == anio_obj].copy()
            tot_con = int(df_y["CONSECUCION_BOOL"].sum()) if "CONSECUCION_BOOL" in df_y else 0
            tot_inap = int(df_y["INAPLICACION_BOOL"].sum()) if "INAPLICACION_BOOL" in df_y else 0
            emp_pr_norm_y = df_y["EMPRESA PRACT"].apply(lambda v: _norm_text_cell(v, upper=True, deaccent=True)) if "EMPRESA PRACT" in df_y else pd.Series([], dtype=str)
            mask_pr_y = ~emp_pr_norm_y.isin(INVALID_TXT)
            tot_pract = int(mask_pr_y.sum())

            if not df_empleo_norm.empty:
                m_sin_fecha = df_empleo_norm["FECHA CIERRE"].isna()
                emp = df_empleo_norm["EMPRESA PRACT"].apply(_norm_text_cell) if "EMPRESA PRACT" in df_empleo_norm else pd.Series([], dtype=str)
                m_emp_ok = ~(emp.eq("") | emp.str.upper().isin(list(INVALID_TXT)))
                m_con_blank  = df_empleo_norm["CONSECUCION GE"].apply(_is_blank) if "CONSECUCION GE" in df_empleo_norm else pd.Series([], dtype=bool)
                m_inap_blank = df_empleo_norm["INAPLICACION GE"].apply(_is_blank) if "INAPLICACION GE" in df_empleo_norm else pd.Series([], dtype=bool)
                m_dev_blank  = df_empleo_norm["DEVOLUCION GE"].apply(_is_blank) if "DEVOLUCION GE" in df_empleo_norm else pd.Series([], dtype=bool)
                tot_en_curso = int((m_sin_fecha & m_emp_ok & m_con_blank & m_inap_blank & m_dev_blank).sum())
            else:
                tot_en_curso = 0

            cols = st.columns(4)
            cols[0].markdown(render_import_card(f"✅ CONSECUCIÓN {anio_obj}", tot_con, "#e3f2fd"), unsafe_allow_html=True)
            cols[1].markdown(render_import_card(f"🚫 INAPLICACIÓN {anio_obj}", tot_inap, "#fce4ec"), unsafe_allow_html=True)
            cols[2].markdown(render_import_card(f"🎓 Prácticas {anio_obj}", tot_pract, "#ede7f6"), unsafe_allow_html=True)
            cols[3].markdown(render_import_card(f"🛠️ Prácticas en curso {anio_obj}", tot_en_curso, "#fff3e0"), unsafe_allow_html=True)
        else:
            st.info("Sin datos de empleo para mostrar.")
    except Exception as e:
        st.warning("⚠️ No se pudieron cargar los indicadores de Desarrollo Profesional.")
        st.exception(e)

    # ===== MAPA =====
    st.markdown("---")
    if 'excel_data' not in st.session_state or st.session_state['excel_data'] is None:
        st.markdown("## 🌍 Global Alumnos")
        st.warning("⚠️ No hay archivo cargado desde deuda.")
    else:
        df_mapa = st.session_state['excel_data']
        required_cols = ['Cliente', 'Provincia', 'País']
        if not all(col in df_mapa.columns for col in required_cols):
            st.markdown("## 🌍 Global Alumnos")
            st.error("❌ El archivo debe tener columnas: Cliente, Provincia, País.")
        else:
            if "coords_cache" not in st.session_state:
                st.session_state["coords_cache"] = {}

            df_u = df_mapa.drop_duplicates(subset=['Cliente', 'Provincia', 'País']).copy()
            df_u['Provincia'] = df_u['Provincia'].apply(normalize_text).str.title().str.strip()
            df_u['País'] = df_u['País'].apply(normalize_text).str.title().str.strip()

            df_esp = df_u[(df_u['País'].str.upper() == 'ESPAÑA') & (df_u['Provincia'].isin(PROVINCIAS_COORDS))]
            df_ext = df_u[(df_u['Provincia'].isna()) | (~df_u['Provincia'].isin(PROVINCIAS_COORDS)) | (df_u['País'] == "Gibraltar")]

            count_prov = df_esp['Provincia'].value_counts().reset_index()
            count_prov.columns = ['Entidad', 'Alumnos']

            count_pais = df_ext['País'].value_counts().reset_index()
            count_pais.columns = ['Entidad', 'Alumnos']

            total_alumnos = count_prov['Alumnos'].sum() + count_pais['Alumnos'].sum()

            st.markdown(f"""
                <div style='display: flex; align-items: center; justify-content: space-between;'>
                    <h3>🌍 Global Alumnos</h3>
                    <div style='padding: 4px 12px; background-color: #e3f2fd; border-radius: 6px;
                                font-weight: bold; color: #1565c0;'>
                        👥 Total: {total_alumnos}
                    </div>
                </div>
            """, unsafe_allow_html=True)

            mapa = folium.Map(location=[25, 0], zoom_start=2, width="100%", height="700px", max_bounds=True)

            for _, row in count_prov.iterrows():
                entidad, alumnos = row['Entidad'], row['Alumnos']
                coords = PROVINCIAS_COORDS.get(entidad)
                if coords:
                    folium.Marker(
                        location=coords,
                        popup=f"<b>{entidad}</b><br>Alumnos: {alumnos}",
                        tooltip=f"{entidad} ({alumnos})",
                        icon=folium.Icon(color="blue", icon="user", prefix="fa")
                    ).add_to(mapa)

            total_espana = count_prov['Alumnos'].sum()
            coords_espana = [40.4268, -3.7138]
            folium.Marker(
                location=coords_espana,
                popup=f"<b>España (provincias)</b><br>Total alumnos: {total_espana}",
                tooltip=f"España (provincias) ({total_espana})",
                icon=folium.Icon(color="red", icon="flag", prefix="fa")
            ).add_to(mapa)

            def get_flag_emoji(pais_nombre):
                FLAGS = {
                    "Francia": "🇫🇷", "Portugal": "🇵🇹", "Italia": "🇮🇹",
                    "Alemania": "🇩🇪", "Reino Unido": "🇬🇧", "Marruecos": "🇲🇦",
                    "Argentina": "🇦🇷", "México": "🇲🇽", "Colombia": "🇨🇴",
                    "Chile": "🇨🇱", "Brasil": "🇧🇷", "Perú": "🇵🇪",
                    "Uruguay": "🇺🇾", "Venezuela": "🇻🇪", "Ecuador": "🇪🇨",
                    "Gibraltar": "🇬🇮"
                }
                return FLAGS.get(pais_nombre.title(), "🌍")

            for _, row in count_pais.iterrows():
                entidad, alumnos = row['Entidad'], row['Alumnos']
                if entidad.upper() == "ESPAÑA":
                    continue
                coords = PAISES_COORDS.get(entidad) or st.session_state["coords_cache"].get(entidad)
                if not coords:
                    coords = geolocalizar_pais(entidad)
                    if coords:
                        st.session_state["coords_cache"][entidad] = coords
                if coords:
                    bandera = get_flag_emoji(entidad)
                    folium.Marker(
                        location=coords,
                        popup=f"<b>{bandera} {entidad}</b><br>Alumnos: {alumnos}",
                        tooltip=f"{bandera} {entidad} ({alumnos})",
                        icon=folium.Icon(color="red", icon="globe", prefix="fa")
                    ).add_to(mapa)

            folium_static(mapa)

    # ===== CLIENTES ESPAÑA INCOMPLETOS =====
    st.markdown("---")
    st.markdown("## 🧾 Clientes únicos en España con Provincia o Localidad vacías")

    if 'excel_data' not in st.session_state or st.session_state['excel_data'] is None:
        st.warning("⚠️ No hay archivo cargado para revisar clientes incompletos.")
        return

    df_mapa = st.session_state['excel_data']
    required_cols_check = ['Cliente', 'Provincia', 'Localidad', 'Nacionalidad', 'País', 'Comercial']
    missing_cols = [col for col in required_cols_check if col not in df_mapa.columns]

    if missing_cols:
        st.warning(f"⚠️ Faltan las siguientes columnas en el archivo para mostrar la tabla: {', '.join(missing_cols)}")
    else:
        df_filtrado = df_mapa[df_mapa['País'].astype(str).str.strip().str.upper() == "ESPAÑA"].copy()
        df_incompletos = df_filtrado[
            df_filtrado['Provincia'].isna() | (df_filtrado['Provincia'].astype(str).str.strip() == '') |
            df_filtrado['Localidad'].isna() | (df_filtrado['Localidad'].astype(str).str.strip() == '')
        ][['Cliente', 'Provincia', 'Localidad', 'Nacionalidad', 'País', 'Comercial']]

        df_incompletos = df_incompletos.drop_duplicates(subset=["Cliente"]).sort_values(by="Cliente").reset_index(drop=True)

        if df_incompletos.empty:
            st.success("✅ No hay registros en España con Provincia o Localidad vacías.")
        else:
            st.dataframe(df_incompletos, use_container_width=True)

            from io import BytesIO
            import base64

            def to_excel_bytes(df_):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_.to_excel(writer, index=False, sheet_name='Incompletos')
                return output.getvalue()

            excel_data = to_excel_bytes(df_incompletos)
            b64 = base64.b64encode(excel_data).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="clientes_incompletos.xlsx">📥 Descargar Excel</a>'
            st.markdown(href, unsafe_allow_html=True)
