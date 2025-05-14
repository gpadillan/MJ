import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io

def render():
    st.subheader("🎓 Becas ISA Futuro – Suma por Año")

    if 'excel_data' not in st.session_state or st.session_state['excel_data'] is None:
        st.warning("⚠️ No hay archivo cargado. Vuelve a la sección Gestión de Cobro.")
        return

    df = st.session_state['excel_data']
    df_beca = df[df['Forma Pago'] == "Becas ISA"]

    if df_beca.empty:
        st.info("ℹ️ No hay registros con 'Becas ISA' en la columna 'Forma Pago'.")
        return

    año_actual = datetime.today().year

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

    # ⚠️ No se asigna a session_state después del widget
    seleccion = st.multiselect(
        f"Selecciona los años futuros a visualizar después de {año_actual}:",
        options=columnas_futuras,
        default=st.session_state.get("filtro_becas_isa_futuro", columnas_futuras),
        key="filtro_becas_isa_futuro"
    )

    if not seleccion:
        st.info("Selecciona al menos un año para visualizar.")
        return

    suma_totales = df_beca[seleccion].sum().reset_index()
    suma_totales.columns = ['Año', 'Suma Total']
    suma_totales['Año'] = suma_totales['Año'].str.replace("Total ", "")

    st.markdown("### Suma total por año")
    st.dataframe(suma_totales, use_container_width=True)

    fig = px.line(
        suma_totales,
        x="Año",
        y="Suma Total",
        markers=True,
        title="Becas ISA Futuro"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.session_state["descarga_becas_isa_26_27_28"] = suma_totales

    st.markdown("---")
    st.subheader("📥 Exportar esta hoja")

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        suma_totales.to_excel(writer, index=False, sheet_name="becas_isa_26_27_28")

    st.download_button(
        label="📥 Descargar hoja: Becas ISA 26/27/28",
        data=buffer.getvalue(),
        file_name="becas_Futuro.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
