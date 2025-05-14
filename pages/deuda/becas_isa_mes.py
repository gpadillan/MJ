import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io

def render():
    st.subheader("Becas ISA – Mes - Año actual")

    if 'excel_data' not in st.session_state or st.session_state['excel_data'] is None:
        st.warning("⚠️ No hay archivo cargado. Vuelve a la sección Deuda.")
        return

    df = st.session_state['excel_data']

    año_actual = st.session_state.get('año_actual') or datetime.today().year

    df_beca = df[df['Forma Pago'] == "Becas ISA"]

    if df_beca.empty:
        st.info("No hay registros con 'Becas ISA' en la columna 'Forma Pago'.")
        return

    meses = [
        f"{mes} {año_actual}" for mes in [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
    ]
    meses_disponibles = [mes for mes in meses if mes in df_beca.columns]

    if not meses_disponibles:
        st.info(f"ℹ️ No hay meses disponibles en el archivo para {año_actual}.")
        return

    key_filtro = "filtro_becas_isa_mes"
    if key_filtro not in st.session_state:
        st.session_state[key_filtro] = meses_disponibles

    meses_seleccionados = st.multiselect(
        f"Selecciona los meses de {año_actual}",
        meses_disponibles,
        default=st.session_state[key_filtro]
    )
    st.session_state[key_filtro] = meses_seleccionados

    if not meses_seleccionados:
        st.info("Selecciona al menos un mes.")
        return

    suma_mensual = df_beca[meses_seleccionados].sum().reset_index()
    suma_mensual.columns = ['Mes', 'Suma Total']

    st.markdown("### Suma mensual de Becas ISA")
    st.dataframe(suma_mensual, use_container_width=True)

    fig = px.pie(
        suma_mensual,
        names="Mes",
        values="Suma Total",
        title=f"Distribución mensual – Becas ISA {año_actual}"
    )
    fig.update_traces(textinfo='percent+label')
    st.plotly_chart(fig, use_container_width=True)

    # Guardar para exportación consolidada
    st.session_state["descarga_becas_isa_mes"] = suma_mensual

    st.markdown("---")
    st.subheader("📥 Exportar esta hoja")

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        suma_mensual.to_excel(writer, index=False, sheet_name="becas_isa_mes")

    st.download_button(
        label="📥 Descargar hoja: Becas ISA Mes",
        data=buffer.getvalue(),
        file_name="becas_mes_Año_actual.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
