import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io

def render():
    st.subheader(" Pendiente por años y meses del año actual")

    if 'excel_data' not in st.session_state or st.session_state['excel_data'] is None:
        st.warning("⚠️ No hay archivo cargado. Vuelve a la sección Deuda.")
        return

    df = st.session_state['excel_data']

    if "Estado" not in df.columns:
        st.error("❌ Falta la columna 'Estado' en el archivo.")
        return

    df_pendiente = df[df['Estado'].str.strip().str.upper() == "PENDIENTE"]

    if df_pendiente.empty:
        st.info("ℹ️ No hay registros con 'PENDIENTE' en la columna 'Estado'.")
        return

    año_actual = st.session_state.get("año_actual", datetime.today().year)
    mes_actual = datetime.today().month

    nombres_meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]

    columnas_totales = [
        col for col in df_pendiente.columns
        if col.startswith("Total ") and col.split()[-1].isdigit() and int(col.split()[-1]) < año_actual
    ]
    columnas_meses = [
        f"{mes} {año_actual}" for mes in nombres_meses[:mes_actual]
        if f"{mes} {año_actual}" in df_pendiente.columns
    ]

    columnas_disponibles = columnas_totales + columnas_meses

    if not columnas_disponibles:
        st.warning("⚠️ No se encontraron columnas válidas para mostrar.")
        return

    filtro_key = "pendientes_columnas_filtro"
    if filtro_key not in st.session_state:
        st.session_state[filtro_key] = columnas_disponibles

    seleccionadas = st.multiselect(
        f"Selecciona columnas de totales y meses ({año_actual})",
        columnas_disponibles,
        default=st.session_state[filtro_key],
        key=filtro_key
    )

    if not seleccionadas:
        st.info("Selecciona al menos una columna.")
        return

    # Procesamiento y visualización
    df_clean = df_pendiente[seleccionadas].apply(pd.to_numeric, errors='coerce').fillna(0)
    df_suma = df_clean.sum().reset_index()
    df_suma.columns = ['Periodo', 'Suma Total']
    df_suma['Periodo'] = df_suma['Periodo'].str.replace("Total ", "")

    st.markdown("### Suma total por periodo")
    st.dataframe(df_suma, use_container_width=True)

    st.markdown("### Gráfico por periodo")
    fig = px.bar(
        df_suma,
        x='Periodo',
        y='Suma Total',
        text_auto='.2s',
        color='Suma Total',
        color_continuous_scale='Reds',
        title=f"Pendiente por Totales y Meses ({año_actual})"
    )
    fig.update_traces(marker_line_color='black', marker_line_width=0.6)
    st.plotly_chart(fig, use_container_width=True)

    # ✅ Guardar para consolidado
    st.session_state["descarga_año_2025"] = df_suma

    # Exportar
    st.markdown("---")
    st.subheader("📥 Exportar esta hoja")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df_suma.to_excel(writer, index=False, sheet_name="pendiente_por_año")

    buffer.seek(0)  # ← IMPORTANTE

    st.download_button(
        label="📥 Descargar hoja: Pendiente por Año",
        data=buffer.getvalue(),
        file_name="pendiente_por_año.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
