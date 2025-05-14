import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io

def render():
    st.subheader("Estado")

    if 'excel_data' not in st.session_state or st.session_state['excel_data'] is None:
        st.warning("⚠️ No hay archivo cargado. Vuelve a la sección Gestión de Cobro.")
        return

    df = st.session_state['excel_data']

    if 'Estado' not in df.columns:
        st.error("❌ La columna 'Estado' no existe en el archivo.")
        return

    año_actual = st.session_state.get('año_actual', datetime.today().year)

    # --- Inicialización de filtros ---
    estados_unicos = sorted(df['Estado'].dropna().unique())
    columnas_totales = [f'Total {a}' for a in range(2018, año_actual)]
    meses_actuales = [f'{mes} {año_actual}' for mes in [
        'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
    ]]
    columnas_disponibles = columnas_totales + meses_actuales

    # --- Filtros persistentes sin conflicto ---
    estados_seleccionados = st.multiselect(
        "Filtrar por Estado",
        estados_unicos,
        default=st.session_state.get("global_estado_filtro", estados_unicos),
        key="global_estado_filtro"
    )

    columnas_seleccionadas = st.multiselect(
        f"Selecciona columnas a mostrar ({año_actual})",
        columnas_disponibles,
        default=st.session_state.get("global_columnas_filtro", columnas_disponibles),
        key="global_columnas_filtro"
    )

    if not estados_seleccionados:
        st.info("Selecciona al menos un Estado.")
        return

    columnas_existentes = [c for c in columnas_seleccionadas if c in df.columns]
    if not columnas_existentes:
        st.info("Selecciona al menos una columna válida.")
        return

    # --- Procesamiento de datos ---
    df_filtrado = df[df['Estado'].isin(estados_seleccionados)].copy()
    df_filtrado[columnas_existentes] = df_filtrado[columnas_existentes].apply(pd.to_numeric, errors='coerce').fillna(0)

    df_grouped = df_filtrado.groupby("Estado")[columnas_existentes].sum().reset_index()
    fila_total = pd.DataFrame(df_grouped[columnas_existentes].sum()).T
    fila_total.insert(0, "Estado", "Total general")
    df_final = pd.concat([df_grouped, fila_total], ignore_index=True)

    # 🔢 Calcular total por fila
    df_final["Total fila"] = df_final[columnas_existentes].sum(axis=1)

    # --- Mostrar tabla principal ---
    st.markdown("### Totales agrupados por Estado")
    st.dataframe(df_final, use_container_width=True)

    # --- Gráfico agrupado por periodo ---
    df_melted = df_grouped.melt(id_vars="Estado", var_name="Periodo", value_name="Total")
    st.markdown("### Totales por Estado y Periodo")
    fig = px.bar(
        df_melted,
        x="Estado",
        y="Total",
        color="Periodo",
        barmode="group",
        text_auto=".2s",
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Gráfico total acumulado ---
    st.markdown("### Total acumulado por Estado")
    df_grouped["Total acumulado"] = df_grouped[columnas_existentes].sum(axis=1)
    fig_total = px.bar(
        df_grouped,
        x="Total acumulado",
        y="Estado",
        color="Estado",
        orientation="h",
        text_auto=".2s",
        height=450
    )
    st.plotly_chart(fig_total, use_container_width=True)

    # --- Donut de Forma de Pago ---
    if "Forma Pago" in df_filtrado.columns:
        df_pago = df_filtrado.copy()
        df_pago["Total Periodo"] = df_pago[columnas_existentes].sum(axis=1)
        resumen_pago = df_pago.groupby("Forma Pago")["Total Periodo"].sum().reset_index()

        st.markdown("### Distribución Forma de Pago")
        fig_donut = px.pie(
            resumen_pago,
            names="Forma Pago",
            values="Total Periodo",
            hole=0.5
        )
        fig_donut.update_traces(textposition="inside", textinfo="label+percent+value")
        fig_donut.update_layout(height=700)
        st.plotly_chart(fig_donut, use_container_width=True)

    # --- Exportación ---
    st.session_state["descarga_global"] = df_final

    st.markdown("---")
    st.subheader("📥 Exportar esta hoja")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df_final.to_excel(writer, index=False, sheet_name="Global")

    st.download_button(
        label="📥 Descargar hoja: Global",
        data=buffer.getvalue(),
        file_name="global_estado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
