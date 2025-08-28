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
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

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

# ===================== CARGA DE DATOS =====================

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

def load_empleo_df():
    """
    1) Usa el mismo DF que guarda el Informe en session_state (idéntico).
    2) Si no está, carga desde SharePoint (st.secrets['empleo']) y devuelve la hoja 'GENERAL' (ajústala si es otra).
    """
    if "df_empleo_informe" in st.session_state:
        return st.session_state["df_empleo_informe"].copy()
    try:
        config = st.secrets["empleo"]
        token = get_access_token(config)
        site_id = get_site_id(config, token)
        file = download_excel(config, token, site_id)
        return pd.read_excel(file, sheet_name="GENERAL")
    except Exception as e:
        st.error("❌ No pude cargar Empleo desde SharePoint ni desde session_state.\nAbre antes la página del Informe o revisa st.secrets['empleo'].")
        st.exception(e)
        return pd.DataFrame()

# ===================== HELPERS EMPLEO (ALINEADOS CON EL INFORME) =====================

def _strip_accents(s: str) -> str:
    if s is None:
        return ""
    return ''.join(c for c in unicodedata.normalize('NFD', str(s)) if unicodedata.category(c) != 'Mn')

def _norm_key(s: str) -> str:
    s = str(s).replace("\u00A0", " ")  # NBSP
    s = _strip_accents(s).upper()
    s = re.sub(r'[\.\-_/]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'[^A-Z0-9 ]', '', s)
    return s

def _find_column(cols, targets_norm):
    """
    Dada una lista de columnas reales y una lista de claves normalizadas objetivo,
    devuelve el nombre real de la primera coincidencia (igual o 'contiene').
    """
    norm_map = { _norm_key(c): c for c in cols }
    # Igualdad exacta
    for t in targets_norm:
        if t in norm_map:
            return norm_map[t]
    # Contiene (por si hay espacios raros)
    for t in targets_norm:
        for nk, real in norm_map.items():
            if t in nk:
                return real
    return None

def convertir_fecha_excel(valor):
    try:
        if pd.isna(valor):
            return pd.NaT
        if isinstance(valor, (int, float)):
            return pd.to_datetime("1899-12-30") + pd.to_timedelta(int(valor), unit="D")
        return pd.to_datetime(valor, errors="coerce", dayfirst=True)
    except Exception:
        return pd.NaT

def to_bool(x):
    if isinstance(x, bool):
        return x
    s = str(x).strip().lower()
    return s in ("true", "sí", "si", "1", "x", "verdadero")

def emp_pract_valida(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    invalid = {"", "NO ENCONTRADO", "NAN", "NULL", "NONE"}
    return (~s.str.upper().isin(invalid)) & series.notna()

def normalizar_df_empleo(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()

    # ===== Mapeo robusto de columnas (insensible a tildes/NBSP/variantes) =====
    col_consec = _find_column(df.columns, ["CONSECUCION GE"])
    col_inap   = _find_column(df.columns, ["INAPLICACION GE"])
    col_devol  = _find_column(df.columns, ["DEVOLUCION GE"])
    col_pr_ge  = _find_column(df.columns, ["PRACTICAS GE", "PRACTICAS/GE", "PRACTCAS/GE"])
    col_emp_pr = _find_column(df.columns, ["EMPRESA PRACT", "EMPRESA PRACT.", "EMPRESA PRACTICAS", "EMPRESA PRACTICA"])
    col_emp_ge = _find_column(df.columns, ["EMPRESA GE"])
    col_area   = _find_column(df.columns, ["AREA"])
    col_cons   = _find_column(df.columns, ["CONSULTOR EIP"])
    col_fc     = _find_column(df.columns, ["FECHA CIERRE"])
    col_nombre = _find_column(df.columns, ["NOMBRE"])
    col_apell  = _find_column(df.columns, ["APELLIDOS"])

    ren = {}
    if col_consec: ren[col_consec] = "CONSECUCIÓN GE"
    if col_inap:   ren[col_inap]   = "INAPLICACIÓN GE"
    if col_devol:  ren[col_devol]  = "DEVOLUCIÓN GE"
    if col_pr_ge:  ren[col_pr_ge]  = "PRÁCTICAS/GE"
    if col_emp_pr: ren[col_emp_pr] = "EMPRESA PRÁCT."
    if col_emp_ge: ren[col_emp_ge] = "EMPRESA GE"
    if col_area:   ren[col_area]   = "AREA"
    if col_cons:   ren[col_cons]   = "CONSULTOR EIP"
    if col_fc:     ren[col_fc]     = "FECHA CIERRE"
    if col_nombre: ren[col_nombre] = "NOMBRE"
    if col_apell:  ren[col_apell]  = "APELLIDOS"

    if ren:
        df = df.rename(columns=ren)

    # ===== Limpiezas alineadas con el informe =====
    if "CONSULTOR EIP" in df.columns:
        df["CONSULTOR EIP"] = df["CONSULTOR EIP"].astype(str).str.strip().replace("", "Otros")
        df = df[df["CONSULTOR EIP"].str.upper() != "NO ENCONTRADO"]

    # Fecha + Año
    if "FECHA CIERRE" in df.columns:
        df["FECHA CIERRE"] = df["FECHA CIERRE"].apply(convertir_fecha_excel)
        anio_fc = df["FECHA CIERRE"].dt.year
        mask_invalida = (
            anio_fc.isin([1899, 1970]) |
            ((anio_fc < 2015) & (anio_fc != 2000)) |
            (anio_fc > 2035)
        )
        df.loc[mask_invalida, "FECHA CIERRE"] = pd.NaT
        df["AÑO_CIERRE"] = df["FECHA CIERRE"].dt.year
    else:
        df["FECHA CIERRE"] = pd.NaT
        df["AÑO_CIERRE"] = pd.NA

    # Booleans (si no existen, crea False)
    if "CONSECUCIÓN GE" in df.columns:
        df["CONSECUCIÓN_BOOL"] = df["CONSECUCIÓN GE"].apply(to_bool)
    else:
        df["CONSECUCIÓN_BOOL"] = False

    if "INAPLICACIÓN GE" in df.columns:
        df["INAPLICACIÓN_BOOL"] = df["INAPLICACIÓN GE"].apply(to_bool)
    else:
        df["INAPLICACIÓN_BOOL"] = False

    if "DEVOLUCIÓN GE" in df.columns:
        df["DEVOLUCIÓN_BOOL"] = df["DEVOLUCIÓN GE"].apply(to_bool)
    else:
        df["DEVOLUCIÓN_BOOL"] = False

    # Asegura columnas de empresas por si vienen con otra grafía
    if "EMPRESA PRÁCT." not in df.columns:
        df["EMPRESA PRÁCT."] = pd.NA
    if "PRÁCTICAS/GE" not in df.columns:
        df["PRÁCTICAS/GE"] = pd.NA

    return df

def kpis_informe_like(df_src: pd.DataFrame, anio_obj: int,
                      practicas_en_curso_por_fecha_cierre: bool = False) -> tuple[int, int, int, int]:
    """
    Devuelve (consecución, inaplicación, prácticas, prácticas_en_curso)
    exactamente como en el informe para 'Cierre Expediente Año {anio_obj}'.

    - practicas_en_curso_por_fecha_cierre=False -> usa AÑO_CIERRE==2000 + EMPRESA PRÁCT. (tu informe de 52).
    - Si en el futuro cambias a FECHA CIERRE NaT para 'en curso', pon True.
    """
    df = normalizar_df_empleo(df_src)
    df_anio = df[df["AÑO_CIERRE"] == anio_obj].copy()

    total_consecucion    = int(df_anio["CONSECUCIÓN_BOOL"].sum())
    total_inaplicacion   = int(df_anio["INAPLICACIÓN_BOOL"].sum())
    total_practicas_anio = int(emp_pract_valida(df_anio["EMPRESA PRÁCT."]).sum())

    if practicas_en_curso_por_fecha_cierre:
        total_en_curso = int((df["FECHA CIERRE"].isna() & emp_pract_valida(df["EMPRESA PRÁCT."])).sum())
    else:
        total_en_curso = int(((df["AÑO_CIERRE"] == 2000) & emp_pract_valida(df["EMPRESA PRÁCT."])).sum())

    return total_consecucion, total_inaplicacion, total_practicas_anio, total_en_curso

# ===================== PÁGINA PRINCIPAL =====================

def principal_page():
    st.title("📊 Panel Principal")

    # 🔄 Recarga total: limpia session_state y cachés
    if st.button("🔄 Recargar datos manualmente"):
        for key in ["academica_excel_data", "excel_data", "df_ventas", "df_preventas", "df_gestion", "df_empleo_informe"]:
            if key in st.session_state:
                del st.session_state[key]
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("Caché limpiada y datos recargados.")

    load_academica_data()

    # --- Ficheros locales (ventas / preventas / gestión) ---
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
    columnas_validas = []
    matriculas_por_mes = {}
    importes_por_mes = {}
    estados = {}

    # ===================== VENTAS =====================
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

            for m in range(1, 13):
                df_mes = df_ventas[df_ventas['mes'] == m]
                matriculas_por_mes[m] = len(df_mes)
                importes_por_mes[m] = df_mes['importe'].sum()

    # ===================== PREVENTAS =====================
    if os.path.exists(PREVENTAS_FILE):
        df_preventas = pd.read_excel(PREVENTAS_FILE)
        df_preventas.columns = df_preventas.columns.str.strip().str.lower()

        total_preventas = len(df_preventas)
        columnas_importe = [col for col in df_preventas.columns if "importe" in col]
        if columnas_importe:
            total_preventas_importe = df_preventas[columnas_importe].sum(numeric_only=True).sum()

    # ===================== GESTIÓN DE COBRO =====================
    if os.path.exists(GESTION_FILE):
        df_gestion = pd.read_excel(GESTION_FILE)

        if "Estado" in df_gestion.columns:
            columnas_validas = []

            for anio in range(2018, anio_actual):
                col = f"Total {anio}"
                if col in df_gestion.columns:
                    columnas_validas.append(col)

            for mes_num in range(1, 13):
                nombre_mes = f"{traduccion_meses[mes_num]} {anio_actual}"
                if nombre_mes in df_gestion.columns:
                    columnas_validas.append(nombre_mes)

            if columnas_validas:
                df_gestion[columnas_validas] = df_gestion[columnas_validas].apply(pd.to_numeric, errors='coerce').fillna(0)
                df_estado_totales = df_gestion.groupby("Estado")[columnas_validas].sum()
                df_estado_totales["Total"] = df_estado_totales.sum(axis=1)
                estados = df_estado_totales["Total"].to_dict()

    # ===================== ADMISIONES =====================
    st.markdown("## 📥 Admisiones")
    st.markdown(f"### 📅 Matrículas por Mes ({anio_actual})")

    for i in range(0, 12, 4):
        cols = st.columns(4)
        for j in range(4):
            mes_num = i + j + 1
            if mes_num > 12:
                continue
            mes = traduccion_meses[mes_num]
            matriculas = matriculas_por_mes.get(mes_num, 0)
            importe = format_euro(importes_por_mes.get(mes_num, 0))
            cols[j].markdown(render_info_card(mes, matriculas, importe), unsafe_allow_html=True)

    st.markdown("### Total General")
    col1, col2 = st.columns(2)
    col1.markdown(render_info_card("Matrículas Totales", total_matriculas, format_euro(sum(importes_por_mes.values())), "#c8e6c9"), unsafe_allow_html=True)
    col2.markdown(render_info_card("Preventas", total_preventas, format_euro(total_preventas_importe), "#ffe0b2"), unsafe_allow_html=True)

    # ===================== ACADÉMICA =====================
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

    # ===================== DESARROLLO PROFESIONAL (MISMOS NÚMEROS QUE EL INFORME) =====================
    st.markdown("---")
    st.markdown("## 🔧 Indicadores de Empleo")
    try:
        anio_obj = datetime.now().year
        df_empleo_src = load_empleo_df()
        if df_empleo_src.empty:
            st.info("Sin datos de empleo para mostrar.")
        else:
            # OJO: usamos AÑO_CIERRE==2000 para 'en curso' (como el informe que te da 52)
            cons, inap, pract, pract_curso = kpis_informe_like(
                df_empleo_src,
                anio_obj,
                practicas_en_curso_por_fecha_cierre=False
            )

            cols = st.columns(4)
            cols[0].markdown(render_import_card(f"✅ Consecución {anio_obj}", cons, "#e3f2fd"), unsafe_allow_html=True)
            cols[1].markdown(render_import_card(f"🚫 Inaplicación {anio_obj}", inap, "#fce4ec"), unsafe_allow_html=True)
            cols[2].markdown(render_import_card(f"🎓 Prácticas {anio_obj}", pract, "#ede7f6"), use_container_width=True, unsafe_allow_html=True)
            cols[3].markdown(render_import_card(f"🛠️ Prácticas en curso {anio_obj}", pract_curso, "#fff3e0"), unsafe_allow_html=True)

    except Exception as e:
        st.warning("⚠️ No se pudieron cargar los indicadores de Desarrollo Profesional.")
        st.exception(e)

    # ===================== MAPA =====================
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

            df_esp = df_u[
                (df_u['País'].str.upper() == 'ESPAÑA') &
                (df_u['Provincia'].isin(PROVINCIAS_COORDS))
            ]
            df_ext = df_u[
                (df_u['Provincia'].isna()) |
                (~df_u['Provincia'].isin(PROVINCIAS_COORDS)) |
                (df_u['País'] == "Gibraltar")
            ]

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

            # 🔵 Provincias españolas
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

            # 🔴 España (provincias)
            total_espana = count_prov['Alumnos'].sum()
            coords_espana = [40.4268, -3.7138]
            folium.Marker(
                location=coords_espana,
                popup=f"<b>España (provincias)</b><br>Total alumnos: {total_espana}",
                tooltip=f"España (provincias) ({total_espana})",
                icon=folium.Icon(color="red", icon="flag", prefix="fa")
            ).add_to(mapa)

            # 🌍 Países
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

    # ===================== CLIENTES ESPAÑA INCOMPLETOS =====================
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
