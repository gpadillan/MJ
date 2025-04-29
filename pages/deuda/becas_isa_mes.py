import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

def render():
    st.subheader(" Becas ISA – Mes")

    if 'excel_data' not in st.session_state or st.session_state['excel_data'] is None:
        st.warning("⚠️ No hay archivo cargado. Vuelve a la sección Deuda.")
        return

    df = st.session_state['excel_data']

    # ✅ Usar año simulado si existe, o año actual del sistema
    año_actual = st.session_state.get('año_actual') or datetime.today().year

    df_beca = df[df['Forma Pago'] == "Becas ISA"]

    if df_beca.empty:
        st.info("No hay registros con 'Becas ISA' en la columna 'Forma Pago'.")
        return

    # 📅 Generar dinámicamente los meses del año actual
    meses = [
        f"Enero {año_actual}", f"Febrero {año_actual}", f"Marzo {año_actual}", f"Abril {año_actual}",
        f"Mayo {año_actual}", f"Junio {año_actual}", f"Julio {año_actual}", f"Agosto {año_actual}",
        f"Septiembre {año_actual}", f"Octubre {año_actual}", f"Noviembre {año_actual}", f"Diciembre {año_actual}"
    ]
    meses_disponibles = [mes for mes in meses if mes in df_beca.columns]

    if not meses_disponibles:
        st.info(f"ℹ️ No hay meses disponibles en el archivo para {año_actual}.")
        return

    # 🔵 Selector de meses
    meses_seleccionados = st.multiselect(
        f"Selecciona los meses de {año_actual}",
        meses_disponibles,
        default=meses_disponibles
    )

    if not meses_seleccionados:
        st.info("Selecciona al menos un mes.")
        return

    # 🧮 Sumar valores por mes
    suma_mensual = df_beca[meses_seleccionados].sum().reset_index()
    suma_mensual.columns = ['Mes', 'Suma Total']

    st.markdown("### 📊 Suma mensual de Becas ISA")
    st.dataframe(suma_mensual, use_container_width=True)

    # 📈 Gráfico de pastel
    st.markdown("### ")
    fig = px.pie(
        suma_mensual,
        names="Mes",
        values="Suma Total",
        title=f"Distribución mensual – Becas ISA {año_actual}"
    )
    fig.update_traces(textinfo='percent+label')
    st.plotly_chart(fig, use_container_width=True)
