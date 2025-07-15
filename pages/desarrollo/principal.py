import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import os
from datetime import datetime

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

def render(df=None):
    st.title("📊 Principal - Área de Desarrollo Profesional")

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
        textposition='none'  # No texto automático, lo haremos manual
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
        fig_pie = px.pie(
            conteo_practicas,
            names="Tipo",
            values="Cantidad"
        )
        fig_pie.update_traces(textposition='inside', textinfo='label+percent+value')
        fig_pie.update_layout(height=500)
        st.plotly_chart(fig_pie, use_container_width=True)

    with colpie2:
        conteo_consultor = df_filtrado['CONSULTOR EIP'].value_counts().reset_index()
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