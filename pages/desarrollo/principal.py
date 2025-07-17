import os
import unicodedata
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import folium
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

UPLOAD_FOLDER = "uploaded_admisiones"
ARCHIVO_DESARROLLO = os.path.join(UPLOAD_FOLDER, "desarrollo_profesional.xlsx")

PROVINCIAS_COORDS = {
    "A Coruña": (43.3623, -8.4115), "Álava": (42.8466, -2.6727), "Albacete": (38.9943, -1.8585),
    "Alicante": (38.3452, -0.4810), "Almería": (36.8340, -2.4637), "Asturias": (43.3619, -5.8494),
    "Ávila": (40.6565, -4.6816), "Badajoz": (38.8794, -6.9707), "Barcelona": (41.3851, 2.1734),
    "Bizkaia": (43.2630, -2.9350), "Burgos": (42.3439, -3.6969), "Cáceres": (39.4753, -6.3723),
    "Cádiz": (36.5164, -6.2994), "Cantabria": (43.1828, -3.9878), "Castellón": (39.9864, -0.0513),
    "Ciudad Real": (38.9860, -3.9272), "Córdoba": (37.8882, -4.7794), "Cuenca": (40.0704, -2.1374),
    "Girona": (41.9794, 2.8214), "Granada": (37.1773, -3.5986), "Guadalajara": (40.6333, -3.1667),
    "Guipúzcoa": (43.3128, -1.9744), "Huelva": (37.2614, -6.9447), "Huesca": (42.1362, -0.4089),
    "Jaén": (37.7796, -3.7849), "La Rioja": (42.4650, -2.4489), "Las Palmas": (28.1235, -15.4363),
    "León": (42.5987, -5.5671), "Lleida": (41.6176, 0.6200), "Lugo": (43.0097, -7.5560),
    "Madrid": (40.4168, -3.7038), "Málaga": (36.7213, -4.4214), "Murcia": (37.9922, -1.1307),
    "Navarra": (42.6954, -1.6761), "Ourense": (42.3364, -7.8640), "Palencia": (42.0095, -4.5241),
    "Pontevedra": (42.4310, -8.6444), "Salamanca": (40.9701, -5.6635), "Santa Cruz De Tenerife": (28.4636, -16.2518),
    "Segovia": (40.9481, -4.1184), "Sevilla": (37.3886, -5.9823), "Soria": (41.7666, -2.4799),
    "Tarragona": (41.1189, 1.2445), "Teruel": (40.3456, -1.1065), "Toledo": (39.8628, -4.0273),
    "Valencia": (39.4699, -0.3763), "Valladolid": (41.6523, -4.7245), "Zamora": (41.5033, -5.7446),
    "Zaragoza": (41.6488, -0.8891)
}

PAISES_COORDS = {
    "España": (40.4637, -3.7492), "Argentina": (-38.4161, -63.6167), "Colombia": (4.5709, -74.2973),
    "México": (23.6345, -102.5528), "Chile": (-35.6751, -71.5430), "Ecuador": (-1.8312, -78.1834),
    "Perú": (-9.1899, -75.0152), "Bolivia": (-16.2902, -63.5887), "Uruguay": (-32.5228, -55.7658),
    "Venezuela": (6.4238, -66.5897), "Estados Unidos": (37.0902, -95.7129), "Francia": (46.6034, 1.8883)
}

@st.cache_resource
def get_geolocator():
    return Nominatim(user_agent="geoapi_map")

def geolocalizar_pais(pais):
    geolocator = get_geolocator()
    try:
        loc = geolocator.geocode(pais, timeout=5)
        if loc:
            return (loc.latitude, loc.longitude)
    except (GeocoderTimedOut, GeocoderServiceError):
        return None
    return None

def normalize_text(text):
    if pd.isna(text):
        return ""
    text = str(text).strip().title()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    return {
        "Espana": "España", "Cordoba": "Córdoba", "Guipuzcoa": "Guipúzcoa", "Alava": "Álava"
    }.get(text, text)

def clean_headers(df):
    df.columns = [
        str(col).strip().upper() if str(col).strip() != '' else f'UNNAMED_{i}'
        for i, col in enumerate(df.columns)
    ]
    if len(df.columns) != len(set(df.columns)):
        st.warning("⚠️ Se encontraron columnas duplicadas. Se eliminarán automáticamente.")
        df = df.loc[:, ~df.columns.duplicated()]
    return df

def render_mapa_alumnos(df):
    st.subheader("🌍 Mapa de Alumnos (España + Internacional)")

    if not all(col in df.columns for col in ['Cliente', 'Provincia', 'País']):
        st.error("❌ El archivo debe tener columnas: Cliente, Provincia, País.")
        return

    if "coords_cache" not in st.session_state:
        st.session_state["coords_cache"] = {}

    df_u = df.drop_duplicates(subset=['Cliente', 'Provincia', 'País'])
    df_u['Provincia'] = df_u['Provincia'].apply(normalize_text)
    df_u['País'] = df_u['País'].apply(normalize_text)

    df_esp = df_u[df_u['Provincia'].isin(PROVINCIAS_COORDS)]
    df_ext = df_u[~df_u['Provincia'].isin(PROVINCIAS_COORDS)]

    count_prov = df_esp['Provincia'].value_counts().reset_index()
    count_prov.columns = ['Entidad', 'Alumnos']

    count_pais = df_ext['País'].value_counts().reset_index()
    count_pais.columns = ['Entidad', 'Alumnos']

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

    for _, row in count_pais.iterrows():
        entidad, alumnos = row['Entidad'], row['Alumnos']
        coords = PAISES_COORDS.get(entidad) or st.session_state["coords_cache"].get(entidad)
        if not coords:
            coords = geolocalizar_pais(entidad)
            if coords:
                st.session_state["coords_cache"][entidad] = coords
        if coords:
            folium.Marker(
                location=coords,
                popup=f"<b>{entidad}</b><br>Alumnos: {alumnos}",
                tooltip=f"{entidad} ({alumnos})",
                icon=folium.Icon(color="red", icon="globe", prefix="fa")
            ).add_to(mapa)

    folium_static(mapa)

def render(df=None):
    st.title("📊 Principal - Área de Empleo")

    if df is None:
        if not os.path.exists(ARCHIVO_DESARROLLO):
            st.warning("⚠️ No se encontró el archivo de desarrollo profesional.")
            return
        df = pd.read_excel(ARCHIVO_DESARROLLO)

    df = clean_headers(df)

    columnas_necesarias = [
        'CONSECUCIÓN GE', 'DEVOLUCIÓN GE', 'INAPLICACIÓN GE',
        'AREA', 'PRÁCTCAS/GE', 'CONSULTOR EIP', 'RIESGO ECONÓMICO',
        'MES 3M', 'FIN CONV'
    ]

    columnas_faltantes = [col for col in columnas_necesarias if col not in df.columns]
    if columnas_faltantes:
        st.error(f"❌ Faltan columnas necesarias: {', '.join(columnas_faltantes)}")
        return

    if st.checkbox("🔍 Ver columnas cargadas del Excel"):
        st.write(df.columns.tolist())

    for col in ['CONSECUCIÓN GE', 'DEVOLUCIÓN GE', 'INAPLICACIÓN GE']:
        df[col] = df[col].map(lambda x: str(x).strip().lower() in ['true', 'verdadero', 'sí', 'si', '1'])

    df['PRÁCTCAS/GE'] = df['PRÁCTCAS/GE'].astype(str).str.strip().str.upper()
    df['CONSULTOR EIP'] = df['CONSULTOR EIP'].astype(str).str.strip().str.upper()

    opciones_practicas = sorted(df['PRÁCTCAS/GE'].dropna().unique())
    opciones_consultores = sorted(df['CONSULTOR EIP'].dropna().unique())

    col_filtro1, col_filtro2 = st.columns(2)
    with col_filtro1:
        seleccion_practicas = st.multiselect("Selecciona PRÁCTCAS/GE:", opciones_practicas, default=opciones_practicas)
    with col_filtro2:
        seleccion_consultores = st.multiselect("Selecciona CONSULTOR EIP:", opciones_consultores, default=opciones_consultores)

    df_filtrado = df[
        (df['CONSECUCIÓN GE'] == False) &
        (df['DEVOLUCIÓN GE'] == False) &
        (df['INAPLICACIÓN GE'] == False)
    ]

    df_filtrado = df_filtrado[
        df_filtrado['AREA'].notna() &
        (df_filtrado['AREA'].str.strip() != "") &
        (df_filtrado['AREA'].str.strip().str.upper() != "NO ENCONTRADO")
    ]

    df_filtrado = df_filtrado[
        df_filtrado['PRÁCTCAS/GE'].isin(seleccion_practicas) &
        df_filtrado['CONSULTOR EIP'].isin(seleccion_consultores)
    ]

    if df_filtrado.empty:
        st.info("No hay datos disponibles para la selección realizada.")
        return

    conteo_area = df_filtrado['AREA'].value_counts().reset_index()
    conteo_area.columns = ["Área", "Cantidad"]

    conteo_practicas = df_filtrado['PRÁCTCAS/GE'].value_counts().reset_index()
    conteo_practicas.columns = ["Tipo", "Cantidad"]

    st.subheader("Número de Alumnos por Área")

    fig_bar = go.Figure()
    x_data = conteo_area["Área"]
    y_data = conteo_area["Cantidad"]

    fig_bar.add_trace(go.Bar(
        x=x_data,
        y=y_data,
        marker=dict(color=y_data, colorscale=[[0, "#ffff00"], [1, "#1f77b4"]], line=dict(color='black', width=1.5)),
        text=y_data,
        textposition='none'
    ))

    for x, y in zip(x_data, y_data):
        fig_bar.add_annotation(
            x=x, y=y, text=f"<b>{y}</b>", showarrow=False, yshift=5,
            font=dict(color="white", size=13), align="center", bgcolor="black", borderpad=4
        )

    fig_bar.update_layout(
        height=500,
        xaxis_title="Área",
        yaxis_title="Número de Alumnos",
        yaxis=dict(range=[0, max(y_data) * 1.2]),
        plot_bgcolor='white'
    )

    st.plotly_chart(fig_bar, use_container_width=True)

    total_alumnos = conteo_area['Cantidad'].sum()

    df['FIN CONV'] = pd.to_datetime(df['FIN CONV'], errors='coerce')
    df['MES 3M'] = pd.to_datetime(df['MES 3M'], errors='coerce')

    df_ge_activos = df[
        (df['PRÁCTCAS/GE'] == 'GE') &
        (df['CONSECUCIÓN GE'] == False) &
        (df['DEVOLUCIÓN GE'] == False) &
        (df['INAPLICACIÓN GE'] == False)
    ].copy()

    df_ge_activos['DIF_MESES'] = (
        (df_ge_activos['MES 3M'].dt.year - df_ge_activos['FIN CONV'].dt.year) * 12 +
        (df_ge_activos['MES 3M'].dt.month - df_ge_activos['FIN CONV'].dt.month)
    )

    hoy = pd.to_datetime("today")

    df_resultado = df_ge_activos[
        (df_ge_activos['DIF_MESES'] == 3) & (df_ge_activos['FIN CONV'] <= hoy)
    ].copy()

    total_ge_indicador = len(df_resultado)

    df_resultado['RIESGO ECONÓMICO'] = (
        df_resultado['RIESGO ECONÓMICO']
        .astype(str)
        .str.replace("€", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .astype(float)
        .fillna(0)
    )

    suma_riesgo_eco = df_resultado['RIESGO ECONÓMICO'].sum()
    suma_riesgo_formateada = f"{suma_riesgo_eco:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="🎯 Total Alumnos", value=total_alumnos)
    with col2:
        st.metric(label="📌 ALUMNO RIESGO TRIM", value=total_ge_indicador)
    with col3:
        st.metric(label="💰 RIESGO ECONOMICO", value=suma_riesgo_formateada)

    st.markdown("---")

    st.subheader("Distribución")
    colpie1, colpie2 = st.columns(2)

    with colpie1:
        fig_pie = px.pie(conteo_practicas, names="Tipo", values="Cantidad")
        fig_pie.update_traces(textposition='inside', textinfo='label+percent+value')
        fig_pie.update_layout(height=500)
        st.plotly_chart(fig_pie, use_container_width=True)

    with colpie2:
        conteo_consultor = df_filtrado['CONSULTOR EIP'].value_counts().reset_index()
        conteo_consultor.columns = ["Consultor", "Cantidad"]
        fig_pie_consultor = px.pie(conteo_consultor, names="Consultor", values="Cantidad")
        fig_pie_consultor.update_traces(textposition='inside', textinfo='label+percent+value')
        fig_pie_consultor.update_layout(height=500)
        st.subheader("Alumnado por Consultor")
        st.plotly_chart(fig_pie_consultor, use_container_width=True)

    st.markdown("---")
    render_mapa_alumnos(df)
