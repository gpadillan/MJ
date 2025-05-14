import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import io

def render():
    st.header(" Clientes con Estado PENDIENTE")

    if "excel_data" not in st.session_state or st.session_state["excel_data"] is None:
        st.warning("⚠️ No hay archivo cargado. Ve a la sección Gestión de Datos.")
        return

    df = st.session_state["excel_data"].copy()
    df.columns = df.columns.str.strip()
    df['Estado'] = df['Estado'].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip().str.upper()
    df_pendiente = df[df['Estado'] == 'PENDIENTE'].copy()

    if df_pendiente.empty:
        st.info("ℹ️ No hay registros con estado PENDIENTE.")
        return

    año_actual = datetime.today().year
    mes_actual = datetime.today().month
    meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]

    total_clientes_unicos = set()
    resultado_exportacion = {}

    #  PERIODO 2018–2021
    st.markdown("##  Periodo 2018–2021")
    cols_18_21 = [f"Total {a}" for a in range(2018, 2022) if f"Total {a}" in df_pendiente.columns]
    if cols_18_21:
        df1 = df_pendiente[['Cliente'] + cols_18_21].copy()
        df1[cols_18_21] = df1[cols_18_21].apply(pd.to_numeric, errors='coerce').fillna(0)
        df1 = df1.groupby("Cliente", as_index=False)[cols_18_21].sum()
        df1 = df1[df1[cols_18_21].sum(axis=1) > 0]
        total_clientes_unicos.update(df1['Cliente'].unique())
        st.dataframe(df1, use_container_width=True)
        st.markdown(f"**👥 Total clientes con deuda en 2018–2021:** `{df1['Cliente'].nunique()}`")
        resultado_exportacion["2018_2021"] = df1

        resumen1 = df1[cols_18_21].sum().reset_index()
        resumen1.columns = ['Periodo', 'Total Deuda']
        fig1 = px.bar(resumen1, x='Periodo', y='Total Deuda', text_auto='.2s', color='Total Deuda', color_continuous_scale='Blues')
        fig1.update_traces(marker_line_color='black', marker_line_width=0.6)
        st.plotly_chart(fig1, use_container_width=True)

    #  PERIODO 2022–2025
    st.markdown("##  Periodo 2022–2025")
    cols_22_24 = [f"Total {a}" for a in range(2022, 2025) if f"Total {a}" in df_pendiente.columns]
    cols_2025_meses = [f"{mes} 2025" for mes in meses if f"{mes} 2025" in df_pendiente.columns]
    cols_2025_total = ["Total 2025"] if "Total 2025" in df_pendiente.columns else []

    cols_2025_final = []
    key_meses_actual = "filtro_meses_2025"
    default_2025 = [f"{mes} 2025" for mes in meses[:mes_actual] if f"{mes} 2025" in cols_2025_meses]
    if año_actual == 2025:
        st.markdown("###  Selecciona meses de 2025")
        seleccion_meses = st.multiselect(
            "Meses de 2025",
            options=cols_2025_meses,
            default=st.session_state.get(key_meses_actual, default_2025),
            key=key_meses_actual
        )
        cols_2025_final = seleccion_meses
    elif año_actual >= 2026:
        cols_2025_final = cols_2025_total

    cols_22_25 = cols_22_24 + cols_2025_final
    if cols_22_25:
        df2 = df_pendiente[['Cliente'] + cols_22_25].copy()
        df2[cols_22_25] = df2[cols_22_25].apply(pd.to_numeric, errors='coerce').fillna(0)
        df2 = df2.groupby("Cliente", as_index=False)[cols_22_25].sum()
        df2 = df2[df2[cols_22_25].sum(axis=1) > 0]
        total_clientes_unicos.update(df2['Cliente'].unique())
        st.dataframe(df2, use_container_width=True)
        st.markdown(f"**👥 Total clientes con deuda en 2022–2025:** `{df2['Cliente'].nunique()}`")
        resultado_exportacion["2022_2025"] = df2

        resumen2 = df2[cols_22_25].sum().reset_index()
        resumen2.columns = ['Periodo', 'Total Deuda']
        fig2 = px.bar(resumen2, x='Periodo', y='Total Deuda', text_auto='.2s', color='Total Deuda', color_continuous_scale='Greens')
        fig2.update_traces(marker_line_color='black', marker_line_width=0.6)
        st.plotly_chart(fig2, use_container_width=True)

    # 🧮 TOTAL GLOBAL
    st.markdown("---")
    st.markdown(f"### 🧮 **TOTAL GLOBAL de clientes únicos con deuda:** `{len(total_clientes_unicos)}`")

    # ✅ Exportar archivo Excel unificado
    if resultado_exportacion:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            for nombre, data in resultado_exportacion.items():
                data.to_excel(writer, sheet_name=nombre, index=False)

        st.download_button(
            label="📥 Descargar hoja: Clientes con deuda",
            data=buffer.getvalue(),
            file_name="clientes_con_deuda.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.session_state["descarga_pendiente_clientes"] = resultado_exportacion
