import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

def render():
    st.subheader("📋 Pendiente de Clientes por Rango de Años")

    if 'excel_data' not in st.session_state or st.session_state['excel_data'] is None:
        st.warning("⚠️ No hay archivo cargado. Vuelve a la sección Deuda.")
        return

    df = st.session_state['excel_data']
    df_pendiente = df[df['Estado'] == "PENDIENTE"]

    if df_pendiente.empty:
        st.info("ℹ️ No hay registros con 'PENDIENTE' en la columna 'Estado'.")
        return

    año_actual = st.session_state.get('año_actual', datetime.today().year)

    rangos = {
        "2018-2021": (2018, 2021),
        "2022-2025": (2022, 2025),
        "2026-2029": (2026, 2029),
        "2030-2033": (2030, 2033),
    }

    meses_lista = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]

    algun_rango_mostrado = False

    for nombre_rango, (inicio, fin) in rangos.items():
        if inicio > año_actual:
            continue

        columnas_rango = []

        columnas_totales = [
            f"Total {a}" for a in range(inicio, min(fin + 1, año_actual))
            if f"Total {a}" in df_pendiente.columns
        ]
        columnas_rango.extend(columnas_totales)

        columnas_meses_actual = []
        if inicio <= año_actual <= fin:
            columnas_meses_actual = [
                f"{mes} {año_actual}" for mes in meses_lista
                if f"{mes} {año_actual}" in df_pendiente.columns
            ]

        columnas_existentes = columnas_rango.copy()

        if columnas_meses_actual:
            st.markdown(f"### 🗓️ Selección de meses para {nombre_rango}")
            meses_seleccionados = st.multiselect(
                f"Selecciona meses de {año_actual} en {nombre_rango}:",
                columnas_meses_actual,
                default=columnas_meses_actual,
                key=f"meses_{nombre_rango}"
            )
            columnas_existentes += meses_seleccionados

        if not columnas_existentes:
            continue

        if 'Cliente' not in df_pendiente.columns:
            st.warning("⚠️ No se encontró la columna 'Cliente' en el archivo.")
            return

        df_clientes = df_pendiente[['Cliente'] + columnas_existentes].copy()

        for col in columnas_existentes:
            df_clientes[col] = pd.to_numeric(df_clientes[col], errors='coerce').fillna(0)

        df_filtrado = df_clientes[df_clientes[columnas_existentes].gt(0).any(axis=1)]

        if df_filtrado.empty:
            continue

        algun_rango_mostrado = True

        # ✅ Agrupar correctamente por cliente
        df_agrupado = df_filtrado.groupby('Cliente', as_index=False).sum()

        st.markdown(f"## 🔹 Rango {nombre_rango}")

        st.markdown("### 📄 Clientes con deuda")
        st.dataframe(df_agrupado, use_container_width=True)

        num_clientes = df_agrupado['Cliente'].nunique()  # ✅ Solo cuenta únicos
        st.markdown(f"**🧾 Total de clientes con deuda:** `{num_clientes}`")

        st.markdown("### 📈 Total de deuda por periodo seleccionado")
        resumen = df_agrupado[columnas_existentes].sum().reset_index()
        resumen.columns = ['Periodo', 'Total Deuda']

        fig = px.bar(
            resumen,
            x='Periodo',
            y='Total Deuda',
            color='Total Deuda',
            color_continuous_scale="Reds",
            title=f"Deuda total ({nombre_rango})",
            text_auto='.2s'
        )
        fig.update_traces(marker_line_color='black', marker_line_width=0.6)
        st.plotly_chart(fig, use_container_width=True)

    if not algun_rango_mostrado:
        st.warning("⚠️ No hay datos disponibles para el año simulado.")
