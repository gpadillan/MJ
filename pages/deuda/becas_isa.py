import streamlit as st
import pandas as pd

def render():
    st.subheader("Becas ISA – Suma por Año")

    if 'excel_data' not in st.session_state or st.session_state['excel_data'] is None:
        st.warning("⚠️ No hay archivo cargado. Vuelve a la sección Deuda.")
        return

    df = st.session_state['excel_data']

    # 🔍 Filtrar solo registros con "Beca ISA"
    df_beca = df[df['Forma Pago'] == "Becas ISA"]

    if df_beca.empty:
        st.info("No hay registros con 'Beca ISA' en la columna 'Forma Pago'.")
        return

    # 🧮 Columnas disponibles desde 2018 a 2029
    columnas_totales = [f'Total {anio}' for anio in range(2018, 2030)]
    columnas_disponibles = [col for col in columnas_totales if col in df_beca.columns]

    # Selección de años
    seleccion = st.multiselect("Selecciona los años que deseas analizar", columnas_disponibles)

    if not seleccion:
        st.info("Selecciona al menos un año.")
        return

    # Calcular suma total por año seleccionado
    suma_totales = df_beca[seleccion].sum().reset_index()
    suma_totales.columns = ['Año', 'Suma Total']
    suma_totales['Año'] = suma_totales['Año'].str.replace("Total ", "")  # Limpiar texto

    st.markdown("### 📊 Suma por año (solo Beca ISA)")
    st.dataframe(suma_totales, use_container_width=True)

    st.markdown("### 📈 Gráfico")
    st.bar_chart(data=suma_totales.set_index("Año"))
