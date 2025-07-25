# Guardado como: principal.py
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import os
from datetime import datetime
import msal
import requests
import re

UPLOAD_FOLDER = "uploaded_admisiones"
ARCHIVO_DESARROLLO = os.path.join(UPLOAD_FOLDER, "desarrollo_profesional.xlsx")


def clean_headers(df):
    df.columns = [
        str(col).strip().upper() if str(col).strip() != '' else f'UNNAMED_{i}'
        for i, col in enumerate(df.columns)
    ]
    if len(df.columns) != len(set(df.columns)):
        st.warning("⚠️ Se encontraron columnas duplicadas. Se eliminarán automáticamente.")
        df = df.loc[:, ~df.columns.duplicated()]
    return df


def parse_bool(value):
    return str(value).strip().lower() in ['true', 'verdadero', 'sí', 'si', '1']


def limpiar_riesgo(valor):
    if pd.isna(valor):
        return 0.0
    valor = re.sub(r"[^\d,\.]", "", str(valor))
    valor = valor.replace(".", "").replace(",", ".")
    try:
        return float(valor)
    except:
        return 0.0


@st.cache_data(ttl=600)
def listar_estructura_convenios():
    try:
        config = st.secrets["empleo"]

        app = msal.ConfidentialClientApplication(
            config["client_id"],
            authority=f"https://login.microsoftonline.com/{config['tenant_id']}",
            client_credential=config["client_secret"]
        )

        token_result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        if "access_token" not in token_result:
            st.error("❌ No se pudo obtener token de acceso.")
            return None

        token = token_result["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        site_url = f"https://graph.microsoft.com/v1.0/sites/{config['domain']}:/sites/{config['site_name']}"
        site_resp = requests.get(site_url, headers=headers)
        site_resp.raise_for_status()
        site_id = site_resp.json()["id"]

        # ✅ Ruta final correcta
        base_path = "/Shared Documents/EMPLEO/_PRÁCTICAS/Convenios firmados"
        root_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:{base_path}"
        carpeta_resp = requests.get(root_url, headers=headers)
        carpeta_resp.raise_for_status()
        carpeta_id = carpeta_resp.json()["id"]

        hijos_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{carpeta_id}/children"
        hijos_resp = requests.get(hijos_url, headers=headers)
        hijos_resp.raise_for_status()

        resultado = []
        nivel_1_folders = [item for item in hijos_resp.json().get("value", []) if "folder" in item]

        for folder1 in nivel_1_folders:
            nombre1 = folder1["name"]
            id1 = folder1["id"]

            try:
                sub_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{id1}/children"
                sub_resp = requests.get(sub_url, headers=headers)
                sub_resp.raise_for_status()

                sub_folders = [item for item in sub_resp.json().get("value", []) if "folder" in item]
                if not sub_folders:
                    resultado.append({"Carpeta Nivel 1": nombre1, "Subcarpeta Nivel 2": "—"})
                else:
                    for sub in sub_folders:
                        resultado.append({"Carpeta Nivel 1": nombre1, "Subcarpeta Nivel 2": sub["name"]})

            except requests.exceptions.RequestException as e:
                resultado.append({"Carpeta Nivel 1": nombre1, "Subcarpeta Nivel 2": "⚠️ Error de acceso"})
                st.warning(f"⚠️ No se pudo acceder a subcarpetas de: {nombre1} — {str(e)}")

        return pd.DataFrame(resultado)

    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error de red o autenticación: {e}")
        return None
    except Exception as e:
        st.error(f"❌ Error inesperado al consultar SharePoint: {e}")
        return None


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
        df[col] = df[col].map(parse_bool)

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
    x_data = conteo_area["Área"]
    y_data = conteo_area["Cantidad"]

    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=x_data,
        y=y_data,
        marker=dict(
            color=y_data,
            colorscale=[[0, "#ffff00"], [1, "#1f77b4"]],
            line=dict(color='black', width=1.5)
        ),
        text=y_data,
        textposition='none'
    ))

    for x, y in zip(x_data, y_data):
        fig_bar.add_annotation(
            x=x,
            y=y,
            text=f"<b>{y}</b>",
            showarrow=False,
            yshift=5,
            font=dict(color="white", size=13),
            align="center",
            bgcolor="black",
            borderpad=4
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
        (df_ge_activos['DIF_MESES'] == 3) & 
        (df_ge_activos['FIN CONV'] <= hoy)
    ].copy()

    total_ge_indicador = len(df_resultado)

    df_resultado['RIESGO ECONÓMICO'] = df_resultado['RIESGO ECONÓMICO'].map(limpiar_riesgo)
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
        conteo_practicas = df_filtrado['PRÁCTCAS/GE'].value_counts().reset_index()
        conteo_practicas.columns = ["Tipo", "Cantidad"]
        fig_pie = px.pie(
            conteo_practicas,
            names="Tipo",
            values="Cantidad"
        )
        fig_pie.update_traces(textposition='inside', textinfo='label+percent+value')
        fig_pie.update_layout(height=500)
        st.plotly_chart(fig_pie, use_container_width=True)

    with colpie2:
        df_filtrado_consultores = df_filtrado[
            df_filtrado['CONSULTOR EIP'].str.upper() != 'NO ENCONTRADO'
        ]
        conteo_consultor = df_filtrado_consultores['CONSULTOR EIP'].value_counts().reset_index()
        conteo_consultor.columns = ["Consultor", "Cantidad"]
        fig_pie_consultor = px.pie(
            conteo_consultor,
            names="Consultor",
            values="Cantidad"
        )
        fig_pie_consultor.update_traces(textposition='inside', textinfo='label+percent+value')
        fig_pie_consultor.update_layout(height=500)
        st.subheader("Alumnado por Consultor")
        st.plotly_chart(fig_pie_consultor, use_container_width=True)

    st.markdown("---")
    st.subheader("📁 Estructura de carpetas: Convenios firmados (SharePoint)")
    df_estructura = listar_estructura_convenios()
    if df_estructura is not None:
        st.dataframe(df_estructura)
    else:
        st.info("No se pudo obtener la estructura de carpetas.")
