import streamlit as st
import pandas as pd
import plotly.express as px
import re

def normalizar_booleano(valor):
    if pd.isna(valor):
        return False
    return str(valor).strip().lower() in ["true", "1", "1.0", "sí", "si", "verdadero"]

def limpiar_riesgo(valor) -> float:
    if isinstance(valor, (int, float)):
        return float(valor)
    if pd.isna(valor):
        return 0.0
    v = re.sub(r"[^\d,\.]", "", str(valor))
    v = v.replace(".", "").replace(",", ".")
    try:
        return float(v)
    except Exception:
        return 0.0

def convertir_fecha_excel(valor):
    try:
        if pd.isna(valor):
            return pd.NaT
        if isinstance(valor, (int, float)):
            return pd.to_datetime("1899-12-30") + pd.to_timedelta(int(valor), unit="D")
        return pd.to_datetime(valor, errors='coerce')
    except:
        return pd.NaT

def render(df):
    st.title("💰 Riesgo Económico")

    # 🔄 Botón para recargar / limpiar caché
    if st.button("🔄 Recargar / limpiar caché"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("Caché limpiada. Datos recargados.")

    df.columns = df.columns.str.strip().str.upper()
    df = df.rename(columns={
        'PRÁCTCAS/GE': 'PRÁCTICAS/GE',
        'PRACTICAS/GE': 'PRÁCTICAS/GE'
    })

    columnas_requeridas = [
        'NOMBRE', 'APELLIDOS', 'PRÁCTICAS/GE', 'CONSULTOR EIP',
        'CONSECUCIÓN GE', 'DEVOLUCIÓN GE', 'INAPLICACIÓN GE',
        'FIN CONV', 'RIESGO ECONÓMICO', 'EJECUCIÓN GARANTÍA', 'AREA', 'FECHA CIERRE'
    ]
    for col in columnas_requeridas:
        if col not in df.columns:
            st.error(f"❌ Falta la columna: {col}")
            return

    # Procesamiento de fechas
    df['FIN CONV'] = pd.to_datetime(df['FIN CONV'], errors='coerce')
    df['EJECUCIÓN GARANTÍA'] = pd.to_datetime(df['EJECUCIÓN GARANTÍA'], errors='coerce')
    df['FECHA CIERRE'] = df['FECHA CIERRE'].apply(convertir_fecha_excel)
    hoy = pd.to_datetime("today")
    df['FECHA_RIESGO'] = df['FIN CONV'] + pd.DateOffset(months=3)

    # Filtrado de alumnos en riesgo
    df_filtrado = df[
        ((df['CONSECUCIÓN GE'].astype(str).str.lower().str.strip().isin(['false', 'nan', ''])) |
         df['CONSECUCIÓN GE'].isna()) &
        ((df['DEVOLUCIÓN GE'].astype(str).str.lower().str.strip().isin(['false', 'nan', ''])) |
         df['DEVOLUCIÓN GE'].isna()) &
        ((df['INAPLICACIÓN GE'].astype(str).str.lower().str.strip().isin(['false', 'nan', ''])) |
         df['INAPLICACIÓN GE'].isna()) &
        (df['PRÁCTICAS/GE'].str.strip().str.upper() == 'GE') &
        df['FIN CONV'].notna() &
        (df['FECHA_RIESGO'] <= hoy)
    ].copy()

    total_alumnos = len(df_filtrado)

    df_filtrado['RIESGO ECONÓMICO'] = df_filtrado['RIESGO ECONÓMICO'].map(limpiar_riesgo)
    suma_riesgo = df_filtrado['RIESGO ECONÓMICO'].sum()
    suma_riesgo_str = f"{suma_riesgo:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"

    total_ejecucion_pasada = df_filtrado[
        df_filtrado['EJECUCIÓN GARANTÍA'].notna() & (df_filtrado['EJECUCIÓN GARANTÍA'] < hoy)
    ].shape[0]

    # 🔴 DEVOLUCIÓN GE
    df['DEVOLUCIÓN GE'] = df['DEVOLUCIÓN GE'].apply(normalizar_booleano)
    df_devolucion = df[df['DEVOLUCIÓN GE'] == True].copy()
    df_devolucion['RIESGO ECONÓMICO'] = df_devolucion['RIESGO ECONÓMICO'].map(limpiar_riesgo)

    total_devoluciones = df_devolucion.shape[0]
    total_riesgo_devolucion = df_devolucion['RIESGO ECONÓMICO'].sum()
    riesgo_devolucion_str = f"{total_riesgo_devolucion:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"

    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📌 ALUMNO RIESGO TRIM", total_alumnos)
    col2.metric("💰 RIESGO ECONÓMICO", suma_riesgo_str)
    col3.metric("⏳ VENCIDA GE", total_ejecucion_pasada)
    col4.markdown(
        f"""
        <div style='text-align:center; padding-top: 12px'>
            <div style='font-size:1.1em;'>🔴 DEVOLUCIÓN GE</div>
            <div style='font-size:1.9em'>{total_devoluciones} <span style='font-size:0.75em; color:gray;'>({riesgo_devolucion_str})</span></div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    # Distribución
    if "CONSULTOR EIP" in df_filtrado.columns:
        conteo_consultores = df_filtrado["CONSULTOR EIP"].value_counts().reset_index()
        conteo_consultores.columns = ["CONSULTOR", "ALUMNOS EN RIESGO"]

        st.subheader("🔄 Distribución de Alumnado en RIESGO por Consultor")
        fig = px.pie(
            conteo_consultores,
            names="CONSULTOR",
            values="ALUMNOS EN RIESGO",
            hole=0.5
        )
        fig.update_traces(textinfo='label+value')
        st.plotly_chart(fig, use_container_width=True)

        # Detalle alumnos en riesgo
        st.markdown("### 📋 Detalle de alumnos en riesgo")
        columnas_tabla = ['NOMBRE', 'APELLIDOS', 'CONSULTOR EIP', 'AREA', 'RIESGO ECONÓMICO', 'FECHA CIERRE']
        df_resultado_vista = df_filtrado[columnas_tabla].copy()
        df_resultado_vista['RIESGO ECONÓMICO'] = df_resultado_vista['RIESGO ECONÓMICO'].apply(
            lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
        )
        st.dataframe(df_resultado_vista, use_container_width=True)

        # Detalle devoluciones
        st.markdown("### 🔴 Detalle de alumnos con DEVOLUCIÓN GE")
        columnas_devolucion = ['NOMBRE', 'APELLIDOS', 'AREA', 'RIESGO ECONÓMICO', 'FECHA CIERRE']
        df_devolucion_vista = df_devolucion[columnas_devolucion].copy()
        df_devolucion_vista['RIESGO ECONÓMICO'] = df_devolucion_vista['RIESGO ECONÓMICO'].apply(
            lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
        )
        st.dataframe(df_devolucion_vista, use_container_width=True)

    else:
        st.warning("⚠️ La columna 'CONSULTOR EIP' no está disponible en los datos.")
