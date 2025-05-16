import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io

def render():
    st.subheader("📊 Pendiente por años y meses del año actual")

    if 'excel_data' not in st.session_state or st.session_state['excel_data'] is None:
        st.warning("⚠️ No hay archivo cargado. Ve a la sección Gestión de Cobro.")
        return

    df = st.session_state['excel_data']

    if "Estado" not in df.columns:
        st.error("❌ Falta la columna 'Estado' en el archivo.")
        return

    df_pendiente = df[df['Estado'].str.strip().str.upper() == "PENDIENTE"]
    df_pendiente.columns = df_pendiente.columns.str.strip().str.replace(r"\s+", " ", regex=True)

    if df_pendiente.empty:
        st.info("ℹ️ No hay registros con 'PENDIENTE' en la columna 'Estado'.")
        return

    año_actual = datetime.today().year

    nombres_meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]

    columnas_totales = [
        col for col in df_pendiente.columns
        if col.startswith("Total ") and col.split(" ")[-1].isdigit() and int(col.split(" ")[-1]) < año_actual
    ]

    columnas_meses_actual = [
        f"{mes} {año_actual}" for mes in nombres_meses if f"{mes} {año_actual}" in df_pendiente.columns
    ]

    columnas_disponibles = columnas_totales + columnas_meses_actual

    if not columnas_disponibles:
        st.warning("⚠️ No se encontraron columnas válidas para mostrar.")
        return

    seleccionadas = st.multiselect(
        f"Selecciona columnas de totales y meses ({año_actual})",
        columnas_disponibles,
        default=columnas_disponibles,
        key="pendientes_columnas_filtro"
    )

    if not seleccionadas:
        st.info("Selecciona al menos una columna.")
        return

    df_numerico = df_pendiente[seleccionadas].apply(pd.to_numeric, errors='coerce').fillna(0)

    # 🔸 Sumar totales por año
    datos_totales = df_numerico[[c for c in seleccionadas if c in columnas_totales]].sum().reset_index()
    datos_totales.columns = ['Periodo', 'Suma Total']
    datos_totales['Periodo'] = datos_totales['Periodo'].str.replace("Total ", "", regex=False)

    # 🔹 Sumar meses del año actual
    datos_meses = df_numerico[[c for c in seleccionadas if c in columnas_meses_actual]].sum().reset_index()
    datos_meses.columns = ['Periodo', 'Suma Total']

    # 📊 Gráfico: Totales
    st.markdown("###  Pendiente por años anteriores)")
    fig_totales = px.bar(
        datos_totales,
        x='Periodo',
        y='Suma Total',
        text_auto='.2s',
        color='Suma Total',
        color_continuous_scale='oranges',
        title="Totales por año (anteriores al actual)"
    )
    fig_totales.update_traces(marker_line_color='black', marker_line_width=0.6)
    fig_totales.update_layout(coloraxis_showscale=False)
    st.plotly_chart(fig_totales, use_container_width=True)

    # 📊 Gráfico: Meses
    st.markdown(f"###  Pendiente por mes ({año_actual})")
    fig_meses = px.bar(
        datos_meses,
        x='Periodo',
        y='Suma Total',
        text_auto='.2s',
        color='Suma Total',
        color_continuous_scale='blues',
        title=f"Meses del año {año_actual}"
    )
    fig_meses.update_traces(marker_line_color='black', marker_line_width=0.6)
    fig_meses.update_layout(coloraxis_showscale=False)
    st.plotly_chart(fig_meses, use_container_width=True)

    #  Unificar totales y meses
    df_suma = pd.concat([datos_totales, datos_meses], ignore_index=True)

    def orden_custom(p):
        partes = p.split()
        meses_dict = {m: i for i, m in enumerate(nombres_meses, 1)}
        if len(partes) == 2 and partes[0] in meses_dict and partes[1].isdigit():
            return (int(partes[1]), meses_dict[partes[0]])
        if p.isdigit():
            return (int(p), 0)
        return (9999, 99)

    df_suma['Orden'] = df_suma['Periodo'].apply(orden_custom)
    df_suma = df_suma.sort_values(by='Orden')

    # 📋 Tabla
    st.markdown("### 📄 Suma total por periodo (años + meses)")
    st.dataframe(df_suma[['Periodo', 'Suma Total']], use_container_width=True)

    # 💾 Guardar para otras vistas
    st.session_state["descarga_año_2025"] = df_suma[['Periodo', 'Suma Total']]

    # 📤 Exportar Excel
    st.markdown("---")
    st.subheader("📥 Exportar esta hoja combinada")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df_suma[['Periodo', 'Suma Total']].to_excel(writer, index=False, sheet_name="pendiente_combinado")
    buffer.seek(0)
    st.download_button(
        label="📥 Descargar hoja: Pendiente por Años y Meses",
        data=buffer.getvalue(),
        file_name="pendiente_combinado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
