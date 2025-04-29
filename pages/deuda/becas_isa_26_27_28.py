import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

def render():
    st.subheader("🎓 Becas ISA Futuro – Suma por Año")

    if 'excel_data' not in st.session_state or st.session_state['excel_data'] is None:
        st.warning("⚠️ No hay archivo cargado. Vuelve a la sección Deuda.")
        return

    df = st.session_state['excel_data']

    # Filtrar registros de Becas ISA
    df_beca = df[df['Forma Pago'] == "Becas ISA"]

    if df_beca.empty:
        st.info("ℹ️ No hay registros con 'Becas ISA' en la columna 'Forma Pago'.")
        return

    año_actual = datetime.today().year

    # 🔍 Buscar columnas tipo 'Total XXXX'
    columnas_total = [col for col in df_beca.columns if col.startswith('Total ')]

    columnas_futuras = []
    for col in columnas_total:
        partes = col.split()
        if len(partes) == 2 and partes[1].isdigit():
            año_col = int(partes[1])
            if año_col > año_actual:
                columnas_futuras.append(col)

    if not columnas_futuras:
        st.warning(f"⚠️ No hay columnas de años futuros disponibles después de {año_actual}.")
        return

    seleccion = st.multiselect(
        f"Selecciona los años futuros a visualizar después de {año_actual}:",
        columnas_futuras,
        default=columnas_futuras
    )

    if not seleccion:
        st.info("Selecciona al menos un año para visualizar.")
        return

    # Calcular sumas por año seleccionado
    suma_totales = df_beca[seleccion].sum().reset_index()
    suma_totales.columns = ['Año', 'Suma Total']
    suma_totales['Año'] = suma_totales['Año'].str.replace("Total ", "")

    st.markdown("### 📊 Suma total por año")
    st.dataframe(suma_totales, use_container_width=True)

    # Gráfico de evolución
    st.markdown("### 📈 Evolución anual")
    fig = px.line(
        suma_totales,
        x="Año",
        y="Suma Total",
        markers=True,
        title=" Becas ISA Futuro"
    )
    st.plotly_chart(fig, use_container_width=True)
