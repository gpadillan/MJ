import streamlit as st
import pandas as pd
import plotly.express as px

def render(df):
    st.title("💰 Riesgo Económico")

    df.columns = df.columns.str.strip().str.upper()

    columnas_requeridas = [
        'NOMBRE', 'APELLIDOS', 'PRÁCTCAS/GE', 'CONSULTOR EIP',
        'CONSECUCIÓN GE', 'DEVOLUCIÓN GE', 'INAPLICACIÓN GE',
        'FIN CONV', 'MES 3M', 'RIESGO ECONÓMICO', 'EJECUCIÓN GARANTÍA', 'AREA'
    ]
    for col in columnas_requeridas:
        if col not in df.columns:
            st.error(f"❌ Falta la columna: {col}")
            return

    df_filtrado = df[
        ((df['CONSECUCIÓN GE'].astype(str).str.lower().str.strip().isin(['false', 'nan', ''])) |
         (df['CONSECUCIÓN GE'].isna())) &
        ((df['DEVOLUCIÓN GE'].astype(str).str.lower().str.strip().isin(['false', 'nan', ''])) |
         (df['DEVOLUCIÓN GE'].isna())) &
        ((df['INAPLICACIÓN GE'].astype(str).str.lower().str.strip().isin(['false', 'nan', ''])) |
         (df['INAPLICACIÓN GE'].isna())) &
        (df['PRÁCTCAS/GE'].str.strip().str.upper() == 'GE')
    ].copy()

    df_filtrado['FIN CONV'] = pd.to_datetime(df_filtrado['FIN CONV'], errors='coerce')
    df_filtrado['MES 3M'] = pd.to_datetime(df_filtrado['MES 3M'], errors='coerce')

    df_filtrado['DIF_MESES'] = (
        (df_filtrado['MES 3M'].dt.year - df_filtrado['FIN CONV'].dt.year) * 12 +
        (df_filtrado['MES 3M'].dt.month - df_filtrado['FIN CONV'].dt.month)
    )

    hoy = pd.to_datetime("today")

    df_resultado = df_filtrado[
        (df_filtrado['DIF_MESES'] == 3) &
        (df_filtrado['FIN CONV'] <= hoy)
    ].copy()

    total_alumnos = len(df_resultado)

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
    suma_riesgo = df_resultado['RIESGO ECONÓMICO'].sum()
    suma_riesgo_str = f"{suma_riesgo:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"

    df_resultado['EJECUCIÓN GARANTÍA'] = pd.to_datetime(df_resultado['EJECUCIÓN GARANTÍA'], errors='coerce')
    total_ejecucion_pasada = df_resultado[
        (df_resultado['EJECUCIÓN GARANTÍA'].notna()) &
        (df_resultado['EJECUCIÓN GARANTÍA'] < hoy)
    ].shape[0]

    devolucion_true_count = df['DEVOLUCIÓN GE'].astype(str).str.lower().str.strip() == 'true'
    num_devoluciones_true = devolucion_true_count.sum()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="📌 ALUMNO RIESGO TRIM", value=total_alumnos)
    with col2:
        st.metric(label="💰 RIESGO ECONÓMICO", value=suma_riesgo_str)
    with col3:
        st.metric(label="⏳ VENCIDA GE", value=total_ejecucion_pasada)
    with col4:
        st.metric(label="🔴 DEVOLUCIÓN GE", value=num_devoluciones_true)

    st.markdown("---")

    if "CONSULTOR EIP" in df_resultado.columns:
        conteo_consultores = df_resultado["CONSULTOR EIP"].value_counts().reset_index()
        conteo_consultores.columns = ["CONSULTOR", "ALUMNOS EN RIESGO"]

        st.subheader("🔄 Distribución por Consultor")
        fig = px.pie(
            conteo_consultores,
            names="CONSULTOR",
            values="ALUMNOS EN RIESGO",
            hole=0.5,
            title="Distribución de Alumnado en Riesgo por Consultor"
        )
        fig.update_traces(textinfo='label+value')
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 📋 Detalle de alumnos en riesgo")
        columnas_tabla = ['NOMBRE', 'APELLIDOS', 'CONSULTOR EIP', 'AREA', 'RIESGO ECONÓMICO']
        df_resultado_vista = df_resultado[columnas_tabla].copy()

        df_resultado_vista['RIESGO ECONÓMICO'] = df_resultado_vista['RIESGO ECONÓMICO'].apply(
            lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
        )

        st.dataframe(df_resultado_vista, use_container_width=True)
    else:
        st.warning("⚠️ La columna 'CONSULTOR EIP' no está disponible en los datos.")