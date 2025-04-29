import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

def render():
    st.subheader("📊 Pendiente por Año")

    if 'excel_data' not in st.session_state or st.session_state['excel_data'] is None:
        st.warning("⚠️ No hay archivo cargado. Vuelve a la sección Deuda.")
        return

    df = st.session_state['excel_data']
    año_actual = st.session_state.get('año_actual', datetime.today().year)

    # 🔍 Filtrar solo registros con Estado == "PENDIENTE"
    df_pendiente = df[df['Estado'] == "PENDIENTE"]

    if df_pendiente.empty:
        st.info("ℹ️ No hay registros con 'PENDIENTE' en la columna 'Estado'.")
        return

    # 📅 Generar lista de meses para el año simulado
    meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    columnas_mes_actual = [
        f"{mes} {año_actual}" for mes in meses
        if f"{mes} {año_actual}" in df_pendiente.columns
    ]

    if not columnas_mes_actual:
        st.warning(f"⚠️ No hay columnas de meses disponibles para {año_actual}.")
        return

    # 🔵 Multiselección solo de meses
    seleccion = st.multiselect(
        f"Selecciona los meses de {año_actual} a visualizar:",
        columnas_mes_actual,
        default=columnas_mes_actual
    )

    if not seleccion:
        st.info("Selecciona al menos un mes.")
        return

    # 🧮 Calcular sumas por mes
    suma_meses = df_pendiente[seleccion].sum().reset_index()
    suma_meses.columns = ['Mes', 'Suma Total']

    st.markdown("### Suma total por mes")
    st.dataframe(suma_meses, use_container_width=True)

    # 📈 Gráfico de barras
    fig = px.bar(
        suma_meses,
        x="Mes",
        y="Suma Total",
        color="Suma Total",
        color_continuous_scale="Reds",
        title=f"Totales de {año_actual} – Estado: PENDIENTE",
        text_auto='.2s'
    )
    fig.update_traces(marker_line_color='black', marker_line_width=0.6)
    st.plotly_chart(fig, use_container_width=True)
