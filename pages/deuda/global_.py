import streamlit as st 
import pandas as pd
import plotly.express as px
from datetime import datetime

def render():
    st.subheader("Estado")

    if 'excel_data' not in st.session_state or st.session_state['excel_data'] is None:
        st.warning("⚠️ No hay archivo cargado. Vuelve a la sección Deuda.")
        return

    df = st.session_state['excel_data']

    if 'Estado' not in df.columns:
        st.error("❌ La columna 'Estado' no existe en el archivo.")
        return

    # 🔽 Filtro por Estado
    estados_unicos = sorted(df['Estado'].dropna().unique())
    estados_seleccionados = st.multiselect("Filtrar por Estado", estados_unicos, default=estados_unicos)
    df = df[df['Estado'].isin(estados_seleccionados)]

    # 🔵 Usar año simulado, no el real
    año_actual = st.session_state.get('año_actual', datetime.today().year)

    # 🔵 Columnas disponibles dinámicamente
    columnas_totales = [f'Total {año}' for año in range(2018, año_actual)]

    nombres_meses = [
        'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
    ]
    meses_actuales = [f'{mes} {año_actual}' for mes in nombres_meses]

    # 🔵 Selección múltiple de columnas
    st.markdown(f"### Selección de columnas a mostrar {año_actual}")
    totales_seleccionados = st.multiselect("Selecciona Totales por Año", columnas_totales, default=columnas_totales)
    meses_seleccionados = st.multiselect(f"Selecciona los Meses de {año_actual}", meses_actuales)

    columnas_a_sumar = totales_seleccionados + meses_seleccionados
    columnas_existentes = [col for col in columnas_a_sumar if col in df.columns]

    if not columnas_existentes:
        st.info("Selecciona al menos una columna válida.")
        return

    # Agrupar por Estado
    df_grouped = df.groupby('Estado')[columnas_existentes].sum().reset_index()

    # Agregar fila de Total general
    total_row = pd.DataFrame(df_grouped[columnas_existentes].sum()).T
    total_row.insert(0, 'Estado', 'Total general')

    df_final = pd.concat([df_grouped, total_row], ignore_index=True)

    # Mostrar tabla
    st.markdown("### 📊 Totales agrupados por Estado")
    st.dataframe(df_final, use_container_width=True)

    # Gráfico interactivo por periodo
    st.markdown("### ")
    df_sin_total = df_final[df_final['Estado'] != 'Total general']
    df_plot = df_sin_total.set_index('Estado')[columnas_existentes]

    df_melted = df_plot.reset_index().melt(
        id_vars='Estado', var_name='Periodo', value_name='Valor'
    )

    fig = px.bar(
        df_melted,
        x="Estado",
        y="Valor",
        color="Periodo",
        barmode="group",
        title=f"Totales por Estado y Periodo ({año_actual})",
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)

    # ➕ Gráfico total acumulado por Estado
    st.markdown("### 🧮 Total acumulado por Estado")
    df_grouped['Total'] = df_grouped[columnas_existentes].sum(axis=1)

    fig_total = px.bar(
        df_grouped,
        x='Total',
        y='Estado',
        color='Estado',
        orientation='h',
        title=f"Total acumulado por Estado ({año_actual})",
        text_auto='.2s',
        height=450
    )
    st.plotly_chart(fig_total, use_container_width=True)

    # 🔵 Gráfico Donut
    st.markdown("### Distribución Forma de Pago ")

    if 'Forma Pago' not in df.columns or 'Importe Total Factura' not in df.columns:
        st.warning("⚠️ Faltan columnas necesarias: 'Forma Pago' o 'Importe Total Factura'.")
        return

    df_cobrado = df[df['Estado'] == 'COBRADO']

    if df_cobrado.empty:
        st.info("ℹ️ No hay registros con Estado 'COBRADO'.")
    else:
        df_cobrado['Importe Total Factura'] = (
            pd.to_numeric(df_cobrado['Importe Total Factura'], errors='coerce').fillna(0)
        )
        suma_por_forma_pago = df_cobrado.groupby('Forma Pago')['Importe Total Factura'].sum().reset_index()

        fig_donut = px.pie(
            suma_por_forma_pago,
            names='Forma Pago',
            values='Importe Total Factura',
            hole=0.5,
            title=f"{año_actual}"
        )
        fig_donut.update_traces(
            textposition='inside',
            textinfo='label+percent+value'
        )
        fig_donut.update_layout(height=700)
        st.plotly_chart(fig_donut, use_container_width=True)
