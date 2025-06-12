import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio
import io
from datetime import datetime
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

    if width >= 768:
        fig1 = px.bar(
            df_melted[df_melted["Estado"] != "TOTAL GENERAL"],
            x="Estado",
            y="Total",
            color="Periodo",
            barmode="group",
            text_auto=".2s",
            height=height,
            width=width,
            template="plotly_white"
        )
        st.plotly_chart(fig1)
    else:
        st.markdown("#### Vista móvil")
        for periodo in columnas_existentes:
            st.markdown(f"**{periodo}**")
            df_periodo = df_melted[df_melted["Periodo"] == periodo]
            for _, row in df_periodo.iterrows():
                st.markdown(f"""
                    <div style="background:#ddd;padding:10px;margin-bottom:10px;border-radius:8px;">
                        <b>{row['Estado']}</b>: {row['Total']:.2f}
                    </div>
                """, unsafe_allow_html=True)

    st.markdown("### Total acumulado por Estado")

    df_grouped["Total acumulado"] = df_grouped[columnas_existentes].sum(axis=1)

    if width >= 768:
        fig2 = px.bar(
            df_grouped,
            x="Total acumulado",
            y="Estado",
            orientation="h",
            color="Estado",
            text_auto=".2s",
            height=height,
            width=width,
            template="plotly_white"
        )
        st.plotly_chart(fig2)
    else:
        st.markdown("#### Vista móvil: distribución acumulada")
        df_cobrado = df_grouped[df_grouped['Estado'] == 'COBRADO']
        df_otros = df_grouped[df_grouped['Estado'] != 'COBRADO']

        fig_cobrado = px.pie(df_cobrado, names="Estado", values="Total acumulado", title="COBRADO")
        fig_otros = px.pie(df_otros, names="Estado", values="Total acumulado", title="Otros Estados")

        st.plotly_chart(fig_cobrado)
        st.plotly_chart(fig_otros)

    if "Forma Pago" in df_filtrado.columns:
        df_pago = df_filtrado.copy()
        df_pago["Total Periodo"] = df_pago[columnas_existentes].sum(axis=1)
        resumen_pago = df_pago.groupby("Forma Pago")["Total Periodo"].sum().reset_index()

        st.markdown("### Distribución Forma de Pago")
        fig3 = px.pie(
            resumen_pago,
            names="Forma Pago",
            values="Total Periodo",
            hole=0.4,
            template="plotly_white"
        )
        st.plotly_chart(fig3)

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

    st.markdown("### 💾 Exportar informe visual")
    html_buffer = io.StringIO()
    html_buffer.write("<html><body>")
    html_buffer.write(df_final.to_html(index=False))

    if width >= 768:
        html_buffer.write(pio.to_html(fig1, include_plotlyjs='cdn', full_html=False))
        html_buffer.write(pio.to_html(fig2, include_plotlyjs='cdn', full_html=False))
    else:
        html_buffer.write(pio.to_html(fig_cobrado, include_plotlyjs='cdn', full_html=False))
        html_buffer.write(pio.to_html(fig_otros, include_plotlyjs='cdn', full_html=False))

    if "fig3" in locals():
        html_buffer.write(pio.to_html(fig3, include_plotlyjs='cdn', full_html=False))

    html_buffer.write("</body></html>")
    st.download_button("📄 Descargar informe HTML", html_buffer.getvalue(), "reporte_estado.html", "text/html")

    os.makedirs("uploaded", exist_ok=True)
    with open("uploaded/reporte_estado.html", "w", encoding="utf-8") as f:
        f.write(html_buffer.getvalue())

    st.session_state["html_global"] = html_buffer.getvalue()
