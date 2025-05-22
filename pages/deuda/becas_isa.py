import streamlit as st
import pandas as pd
import io

def render():
    st.subheader("Becas ISA – Suma por Año")

    if 'excel_data' not in st.session_state or st.session_state['excel_data'] is None:
        st.warning("⚠️ No hay archivo cargado. Vuelve a la sección Gestión de Cobro.")
        return

    df = st.session_state['excel_data']
    df_beca = df[df['Forma Pago'] == "Becas ISA"]

    if df_beca.empty:
        st.info("No hay registros con 'Beca ISA' en la columna 'Forma Pago'.")
        return

    columnas_totales = [f'Total {anio}' for anio in range(2018, 2030)]
    columnas_disponibles = [col for col in columnas_totales if col in df_beca.columns]

    seleccion = st.multiselect(
        "Selecciona los años que deseas analizar",
        columnas_disponibles,
        default=columnas_disponibles,
        key="filtro_becas_isa_anios"
    )

    if not seleccion:
        st.info("Selecciona al menos un año.")
        return

    # ✅ Convertir columnas seleccionadas a números reales
    df_beca[seleccion] = df_beca[seleccion].apply(pd.to_numeric, errors="coerce")
    suma_totales = df_beca[seleccion].sum(numeric_only=True).reset_index()
    suma_totales.columns = ['Año', 'Suma Total']
    suma_totales['Año'] = suma_totales['Año'].str.replace("Total ", "")

    st.markdown("### Gráfico")
    st.bar_chart(data=suma_totales.set_index("Año"))

    st.markdown("### Tabla")
    st.dataframe(suma_totales, use_container_width=True)

    # Guardar para consolidado
    st.session_state["descarga_becas_isa"] = suma_totales

    st.markdown("---")
    st.subheader("📥 Exportar esta hoja")

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        suma_totales.to_excel(writer, index=False, sheet_name="becas_isa")

    buffer.seek(0)

    st.download_button(
        label="📥 Descargar hoja: Becas ISA",
        data=buffer.getvalue(),
        file_name="becas_isa.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
