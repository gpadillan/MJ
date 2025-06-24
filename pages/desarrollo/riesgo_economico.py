import streamlit as st
import pandas as pd
import plotly.express as px

def render(df):
    st.title("💰 Riesgo Económico")

    # 🧼 Limpieza reforzada de nombres de columnas
    df.columns = df.columns.map(
        lambda x: str(x).strip()
        .upper()
        .replace("Á", "A")
        .replace("É", "E")
        .replace("Í", "I")
        .replace("Ó", "O")
        .replace("Ú", "U")
    )

    # 🧪 Mostrar columnas disponibles para depuración
    st.write("📋 Columnas actuales en el DataFrame:", df.columns.tolist())

    columnas_requeridas = [
        'NOMBRE', 'APELLIDOS', 'PRACTCAS/GE', 'CONSULTOR EIP',
        'CONSECUCION GE', 'DEVOLUCION GE', 'INAPLICACION GE',
        'FIN CONV', 'MES 3M', 'RIESGO ECONOMICO', 'EJECUCION GARANTIA', 'AREA'
    ]

    for col in columnas_requeridas:
        if col not in df.columns:
            st.error(f"❌ Falta la columna: {col}")
            return

    df_filtrado = df[
        ((df['CONSECUCION GE'].astype(str).str.lower().str.strip().isin(['false', 'nan', ''])) |
         (df['CONSECUCION GE'].isna())) &
        ((df['DEVOLUCION GE'].astype(str).str.lower().str.strip().isin(['false', 'nan', ''])) |
         (df['DEVOLUCION GE'].isna())) &
        ((df['INAPLICACION GE'].astype(str).str.lower().str.strip().isin(['false', 'nan', ''])) |
         (df['INAPLICACION GE'].isna())) &
        (df['PRACTCAS/GE'].str.strip().str.upper() == 'GE')
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

    df_resultado['RIESGO ECONOMICO'] = (
        df_resultado['RIESGO ECONOMICO']
        .astype(str)
        .str.replace("€", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .astype(float)
        .fillna(0)
    )
    suma_riesgo = df_resultado['RIESGO ECONOMICO'].sum()
    suma_riesgo_str = f"{suma_riesgo:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"

    df_resultado['EJECUCION GARANTIA'] = pd.to_datetime(df_resultado['EJECUCION GARANTIA'], errors='coerce')
    total_ejecucion_pasada = df_resultado[
        (df_resultado['EJECUCION GARANTIA'].notna()) &
        (df_resultado['EJECUCION GARANTIA'] < hoy)
    ].shape[0]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="📌 ALUMNO RIESGO TRIM", value=total_alumnos)
    with col2:
        st.metric(label="💰 RIESGO ECONÓMICO", value=suma_riesgo_str)
    with col3:
        st.metric(label="⏳ VENCIDA GE", value=total_ejecucion_pasada)

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
        columnas_tabla = ['NOMBRE', 'APELLIDOS', 'CONSULTOR EIP', 'AREA', 'RIESGO ECONOMICO']
        df_resultado_vista = df_resultado[columnas_tabla].copy()

        df_resultado_vista['RIESGO ECONOMICO'] = df_resultado_vista['RIESGO ECONOMICO'].apply(
            lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
        )

        st.dataframe(df_resultado_vista, use_container_width=True)
    else:
        st.warning("⚠️ La columna 'CONSULTOR EIP' no está disponible en los datos.")
