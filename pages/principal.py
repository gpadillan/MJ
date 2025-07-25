import streamlit as st
import pandas as pd
import os
from datetime import datetime
from pages.academica.sharepoint_utils import get_access_token, get_site_id, download_excel
from google.oauth2 import service_account
import gspread
from streamlit_folium import folium_static
import folium
from utils.geo_utils import normalize_text, PROVINCIAS_COORDS, PAISES_COORDS, geolocalizar_pais

# === UTILS ===
def format_euro(value):
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

@st.cache_data(show_spinner=False)
def load_google_sheet(sheet_key):
    creds = st.secrets["google_service_account"]
    credentials = service_account.Credentials.from_service_account_info(
        creds, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    client = gspread.authorize(credentials)
    worksheet = client.open_by_key(sheet_key).get_worksheet(0)
    df = pd.DataFrame(worksheet.get_all_records())
    df.columns = df.columns.str.strip().str.upper()
    return df

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

def principal_page():
    st.title("📊 Panel Principal")

    if st.button("🔄 Recargar datos manualmente"):
        for key in ["academica_excel_data", "df_ventas", "df_preventas", "df_gestion"]:
            if key in st.session_state:
                del st.session_state[key]

    load_academica_data()

    UPLOAD_FOLDER = "uploaded_admisiones"
    GESTION_FOLDER = "uploaded"
    VENTAS_FILE = os.path.join(UPLOAD_FOLDER, "ventas.xlsx")
    PREVENTAS_FILE = os.path.join(UPLOAD_FOLDER, "preventas.xlsx")
    GESTION_FILE = os.path.join(GESTION_FOLDER, "archivo_cargado.xlsx")
    SHEET_KEY = "1CPhL56knpvaYZznGF-YgIuHWWCWPtWGpkSgbf88GJFQ"
    df_dev = load_google_sheet(SHEET_KEY)

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

    # === VENTAS ===
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

    # === PREVENTAS ===
    if os.path.exists(PREVENTAS_FILE):
        df_preventas = pd.read_excel(PREVENTAS_FILE)
        df_preventas.columns = df_preventas.columns.str.strip().str.lower()

        total_preventas = len(df_preventas)
        columnas_importe = [col for col in df_preventas.columns if "importe" in col]
        if columnas_importe:
            total_preventas_importe = df_preventas[columnas_importe].sum(numeric_only=True).sum()

    # === GESTIÓN DE COBRO ===
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

    # === ADMISIONES ===
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

    # === COBRO ===
    if estados:
        st.markdown("---")
        st.markdown("## 💼 Gestión de Cobro")
        st.markdown("### Totales por Estado")
        estado_items = sorted(estados.items(), key=lambda x: x[1], reverse=True)
        for i in range(0, len(estado_items), 4):
            cols = st.columns(4)
            for j, (estado, total) in enumerate(estado_items[i:i+4]):
                cols[j].markdown(
                    render_import_card(f"Estado: {estado}", format_euro(total), "#f3e5f5"),
                    unsafe_allow_html=True
                )

    # === ACADÉMICA ===
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

    # === DESARROLLO PROFESIONAL ===
    st.markdown("---")
    st.markdown("## 🔧 Indicadores de Empleo")
    try:
        df = df_dev
        df['CONSECUCIÓN_BOOL'] = df['CONSECUCIÓN GE'].astype(str).str.upper() == 'TRUE'
        df['INAPLICACIÓN_BOOL'] = df['INAPLICACIÓN GE'].astype(str).str.upper() == 'TRUE'
        df['PRACTICAS_BOOL'] = (
            (df['PRÁCTCAS/GE'].astype(str).str.upper() == 'GE') &
            (~df['EMPRESA PRÁCT.'].astype(str).isin(['', 'NO ENCONTRADO'])) &
            (df['CONSECUCIÓN GE'].astype(str).str.upper() == 'FALSE') &
            (df['DEVOLUCIÓN GE'].astype(str).str.upper() == 'FALSE') &
            (df['INAPLICACIÓN GE'].astype(str).str.upper() == 'FALSE')
        )

        total_consecucion = df['CONSECUCIÓN_BOOL'].sum()
        total_inaplicacion = df['INAPLICACIÓN_BOOL'].sum()
        total_alumnos_practicas = df[~df['EMPRESA PRÁCT.'].astype(str).isin(['', 'NO ENCONTRADO'])].shape[0]
        total_practicas_actuales = df['PRACTICAS_BOOL'].sum()

        cols = st.columns(4)
        cols[0].markdown(render_import_card("✅ Consecución", total_consecucion, "#e3f2fd"), unsafe_allow_html=True)
        cols[1].markdown(render_import_card("🚫 Inaplicación", total_inaplicacion, "#fce4ec"), unsafe_allow_html=True)
        cols[2].markdown(render_import_card("🎓 Alumnos en PRÁCTICAS", total_alumnos_practicas, "#ede7f6"), unsafe_allow_html=True)
        cols[3].markdown(render_import_card("🛠️ Prácticas actuales", total_practicas_actuales, "#e8f5e9"), unsafe_allow_html=True)

    except Exception as e:
        st.warning("⚠️ No se pudieron cargar los indicadores de Desarrollo Profesional.")
        st.exception(e)

    # === MAPA ===
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

            # ✅ Normalización estricta
            df_u['Provincia'] = df_u['Provincia'].apply(normalize_text).str.title().str.strip()
            df_u['País'] = df_u['País'].apply(normalize_text).str.title().str.strip()

            # Provincias válidas de España
            df_esp = df_u[
                (df_u['País'].str.upper() == 'ESPAÑA') &
                (df_u['Provincia'].isin(PROVINCIAS_COORDS))
            ]

            # Países (incluye Gibraltar y España solo si tiene provincia inválida)
            df_ext = df_u[
                (df_u['Provincia'].isna()) |
                (~df_u['Provincia'].isin(PROVINCIAS_COORDS))
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

            # 🔵 Provincias españolas en azul
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

            # 🔴 Marcador central "España (provincias)" - desplazado para no solapar Madrid
            total_espana = count_prov['Alumnos'].sum()
            coords_espana = [40.4268, -3.7138]  # Ligeramente al noroeste de Madrid
            folium.Marker(
                location=coords_espana,
                popup=f"<b>España (provincias)</b><br>Total alumnos: {total_espana}",
                tooltip=f"España (provincias) ({total_espana})",
                icon=folium.Icon(color="red", icon="flag", prefix="fa")
            ).add_to(mapa)

            # 🌍 Banderas por país
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

            # 🔴 Países extranjeros en rojo con globo + bandera
            for _, row in count_pais.iterrows():
                entidad, alumnos = row['Entidad'], row['Alumnos']

                if entidad.upper() == "ESPAÑA":
                    continue  # ❌ Evitar marcador duplicado para España como país

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


    # === CLIENTES EN ESPAÑA CON LOCALIDAD O PROVINCIA INCOMPLETA ===
    st.markdown("---")
    st.markdown("## 🧾 Clientes únicos en España con Provincia o Localidad vacías")

    required_cols_check = ['Cliente', 'Provincia', 'Localidad', 'Nacionalidad', 'País', 'Comercial']
    missing_cols = [col for col in required_cols_check if col not in df_mapa.columns]

    if missing_cols:
        st.warning(f"⚠️ Faltan las siguientes columnas en el archivo para mostrar la tabla: {', '.join(missing_cols)}")
    else:
        df_filtrado = df_mapa[
            df_mapa['País'].astype(str).str.strip().str.upper() == "ESPAÑA"
        ].copy()

        df_incompletos = df_filtrado[
            df_filtrado['Provincia'].isna() | (df_filtrado['Provincia'].astype(str).str.strip() == '') |
            df_filtrado['Localidad'].isna() | (df_filtrado['Localidad'].astype(str).str.strip() == '')
        ][['Cliente', 'Provincia', 'Localidad', 'Nacionalidad', 'País', 'Comercial']]

        df_incompletos = df_incompletos.drop_duplicates(subset=["Cliente"]).sort_values(by="Cliente").reset_index(drop=True)

        if df_incompletos.empty:
            st.success("✅ No hay registros en España con Provincia o Localidad vacías.")
        else:
            st.dataframe(df_incompletos, use_container_width=True)

            # Botón de descarga
            from io import BytesIO
            import base64

            def to_excel_bytes(df):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Incompletos')
                return output.getvalue()

            excel_data = to_excel_bytes(df_incompletos)
            b64 = base64.b64encode(excel_data).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="clientes_incompletos.xlsx">📥 Descargar Excel</a>'
            st.markdown(href, unsafe_allow_html=True)