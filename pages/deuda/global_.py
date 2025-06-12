﻿import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io
import plotly.io as pio
from responsive import get_screen_size
import os

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

    estados_unicos = sorted(df['Estado'].dropna().unique())
    columnas_totales = [f'Total {a}' for a in range(2018, año_actual)]
    meses_actuales = [f'{mes} {año_actual}' for mes in [
        'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
    ]]
    columnas_disponibles = columnas_totales + meses_actuales

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

    df_filtrado = df[df['Estado'].isin(estados_seleccionados)].copy()
    df_filtrado[columnas_existentes] = df_filtrado[columnas_existentes].apply(pd.to_numeric, errors='coerce').fillna(0)

    df_grouped = df_filtrado.groupby("Estado")[columnas_existentes].sum().reset_index()
    fila_total = pd.DataFrame(df_grouped[columnas_existentes].sum()).T
    fila_total.insert(0, "Estado", "TOTAL GENERAL")
    df_final = pd.concat([df_grouped, fila_total], ignore_index=True)
    df_final["Total fila"] = df_final[columnas_existentes].sum(axis=1)

    st.markdown("### Totales agrupados por Estado")
    st.dataframe(df_final, use_container_width=True)

    width, height = get_screen_size()

    df_melted = df_final.drop(columns=["Total fila"]).melt(
        id_vars="Estado", var_name="Periodo", value_name="Total"
    )

    st.markdown("### Totales por Estado y Periodo")

    colores_fijos = {
        "COBRADO": "#1f77b4",
        "DOMICILIACIÓN CONFIRMADA": "#ff7f0e",
        "DOMICILIACIÓN EMITIDA": "#2ca02c",
        "DUDOSO COBRO": "#d62728",
        "INCOBRABLE": "#9467bd",
        "NO COBRADO": "#8c564b",
        "PENDIENTE": "#e377c2",
        "TOTAL GENERAL": "#7f7f7f"
    }

    if width >= 768:
        df_plot = df_melted[df_melted["Estado"] != "TOTAL GENERAL"]
        fig1 = px.bar(
            df_plot,
            x="Estado",
            y="Total",
            color="Periodo",
            barmode="group",
            text_auto=".2s",
            height=height,
            width=width,
            template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Plotly
        )
        st.plotly_chart(fig1)
    else:
        st.markdown("#### Totales por Estado y Periodo (vista móvil)")

        for periodo in columnas_existentes:
            st.markdown(f"**{periodo}**")
            df_periodo = df_melted[df_melted["Periodo"] == periodo]

            for _, row in df_periodo.iterrows():
                estado = row["Estado"]
                total = row["Total"]
                color = colores_fijos.get(estado.strip().upper(), "#cccccc")

                st.markdown(f"""
                    <div style="background-color:{color}; padding:10px; border-radius:8px; margin-bottom:10px; color:white;">
                        <strong>{estado}</strong><br>
                        Total: <span style="font-size:1.2em;">{total:.2f}</span>
                    </div>
                """, unsafe_allow_html=True)

    st.markdown("### Total acumulado por Estado")
    df_grouped["Total acumulado"] = df_grouped[columnas_existentes].sum(axis=1)

    if width >= 768:
        fig2 = px.bar(
            df_grouped,
            x="Total acumulado",
            y="Estado",
            color="Estado",
            orientation="h",
            text_auto=".2s",
            height=height,
            width=width,
            template="plotly_white",
            color_discrete_map=colores_fijos
        )
        st.plotly_chart(fig2)
    else:
        estados_otros = [
            "DOMICILIACIÓN CONFIRMADA", "DOMICILIACIÓN EMITIDA",
            "DUDOSO COBRO", "INCOBRABLE", "NO COBRADO", "PENDIENTE"
        ]

        df_cobrado = df_grouped[df_grouped['Estado'] == 'COBRADO']
        df_otros = df_grouped[df_grouped['Estado'].isin(estados_otros)]

        if not df_cobrado.empty:
            st.markdown("#### Gráfico: COBRADO")
            fig_cobrado = px.pie(
                df_cobrado,
                names="Estado",
                values="Total acumulado",
                hole=0.5,
                template="plotly_white",
                color_discrete_map=colores_fijos
            )
            fig_cobrado.update_traces(textposition="inside", textinfo="label+percent+value")
            fig_cobrado.update_layout(height=int(height * 0.6), width=width)
            st.plotly_chart(fig_cobrado)

        if not df_otros.empty:
            st.markdown("#### Gráfico: Otros Estados")
            fig_otros = px.pie(
                df_otros,
                names="Estado",
                values="Total acumulado",
                hole=0.5,
                template="plotly_white",
                color_discrete_map=colores_fijos
            )
            fig_otros.update_traces(textposition="inside", textinfo="label+percent+value")
            fig_otros.update_layout(height=int(height * 0.6), width=width)
            st.plotly_chart(fig_otros)

    fig3 = None
    if "Forma Pago" in df_filtrado.columns:
        df_pago = df_filtrado.copy()
        df_pago["Total Periodo"] = df_pago[columnas_existentes].sum(axis=1)
        resumen_pago = df_pago.groupby("Forma Pago")["Total Periodo"].sum().reset_index()

        st.markdown("### Distribución Forma de Pago")
        fig3 = px.pie(
            resumen_pago,
            names="Forma Pago",
            values="Total Periodo",
            hole=0.5,
            template="plotly_white"
        )
        fig3.update_traces(textposition="inside", textinfo="label+percent+value")
        fig3.update_layout(height=height, width=width)
        st.plotly_chart(fig3)

    st.session_state["descarga_global"] = df_final
    st.markdown("---")
    st.subheader("📥 Exportar esta hoja")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df_final.to_excel(writer, index=False, sheet_name="Global")
    buffer.seek(0)
    st.download_button(
        label="📥 Descargar hoja: Global",
        data=buffer.getvalue(),
        file_name="global_estado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
