import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

UPLOAD_FOLDER = "uploaded_admisiones"
ARCHIVO_DESARROLLO = os.path.join(UPLOAD_FOLDER, "desarrollo_profesional.xlsx")

def render(df=None):
    st.title("📊 Principal - Área de Desarrollo Profesional")

    if df is None:
        if not os.path.exists(ARCHIVO_DESARROLLO):
            return
        df = pd.read_excel(ARCHIVO_DESARROLLO)

    df.columns = df.columns.str.strip().str.upper()

    columnas_necesarias = [
        'CONSECUCIÓN GE', 'DEVOLUCIÓN GE', 'INAPLICACIÓN GE',
        'AREA', 'PRÁCTCAS/GE', 'CONSULTOR EIP', 'RIESGO ECONÓMICO',
        'MES 3M', 'FIN CONV'
    ]

    columnas_faltantes = [col for col in columnas_necesarias if col not in df.columns]
    if columnas_faltantes:
        st.error(f"❌ Faltan columnas necesarias: {', '.join(columnas_faltantes)}")
        return

    for col in ['CONSECUCIÓN GE', 'DEVOLUCIÓN GE', 'INAPLICACIÓN GE']:
        df[col] = df[col].map(lambda x: str(x).strip().lower() in ['true', 'verdadero', 'sí', 'si', '1'])

    df['PRÁCTCAS/GE'] = df['PRÁCTCAS/GE'].astype(str).str.strip().str.upper()
    df['CONSULTOR EIP'] = df['CONSULTOR EIP'].astype(str).str.strip().str.upper()

    # Se muestran todos los valores posibles de PRÁCTCAS/GE y CONSULTOR EIP, sin filtrar
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
    fig_bar = px.bar(
        conteo_area,
        x="Área",
        y="Cantidad",
        text_auto=True,
        title=None,
    )
    fig_bar.update_layout(
        xaxis_title="Área",
        yaxis_title="Número de Alumnos",
        height=500
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    total_alumnos = conteo_area['Cantidad'].sum()

    col_indicador = next((c for c in df.columns if "INDICADOR" in c and "3" in c), None)

    if col_indicador:
        df['INDICADOR 3MESES'] = df[col_indicador].astype(str).str.strip().str.upper()
        df['CONSECUCIÓN GE'] = df['CONSECUCIÓN GE'].astype(str).str.strip().str.upper()
        df['DEVOLUCIÓN GE'] = df['DEVOLUCIÓN GE'].astype(str).str.strip().str.upper()
        df['INAPLICACIÓN GE'] = df['INAPLICACIÓN GE'].astype(str).str.strip().str.upper()
        df['PRÁCTCAS/GE'] = df['PRÁCTCAS/GE'].astype(str).str.strip().str.upper()
        df['CONSULTOR EIP'] = df['CONSULTOR EIP'].astype(str).str.strip().str.upper()

        indicadores_validos = [
            '1T', '2T', '3T', '4T', 'YA',
            '1T 2024', '2024 1T', '2024 2T', '2T 2024',
            '3T 2024', '4T 2024', '2024 4T',
            '1T 2025', '2T 2025'
        ]

        filtro_indicador_ge = (
            df['INDICADOR 3MESES'].isin(indicadores_validos) &
            ((df['CONSECUCIÓN GE'] == 'FALSE') | (df['CONSECUCIÓN GE'].isna())) &
            ((df['DEVOLUCIÓN GE'] == 'FALSE') | (df['DEVOLUCIÓN GE'].isna())) &
            ((df['INAPLICACIÓN GE'] == 'FALSE') | (df['INAPLICACIÓN GE'].isna())) &
            (df['PRÁCTCAS/GE'].isin(seleccion_practicas)) &
            (df['CONSULTOR EIP'].isin(seleccion_consultores)) &
            (df['PRÁCTCAS/GE'] == 'GE')
        )

        total_ge_indicador = filtro_indicador_ge.sum()

        df_resultado = df.loc[filtro_indicador_ge, ['RIESGO ECONÓMICO']]
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
    else:
        total_ge_indicador = 0
        suma_riesgo_formateada = "0,00 €"

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
            values="Cantidad",
            title=None,
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
            values="Cantidad",
            title=None,
        )
        fig_pie_consultor.update_traces(textposition='inside', textinfo='label+percent+value')
        fig_pie_consultor.update_layout(height=500)
        st.subheader("Alumnado por Consultor")
        st.plotly_chart(fig_pie_consultor, use_container_width=True)
