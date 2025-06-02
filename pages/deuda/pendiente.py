import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio
from datetime import datetime
import io

resultado_exportacion = {}

def vista_clientes_pendientes():
    st.header("📄 Clientes con Estado PENDIENTE")

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
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

    total_clientes_unicos = set()

    st.markdown("## 🕰️ Periodo 2018–2021")
    cols_18_21 = [f"Total {a}" for a in range(2018, 2022) if f"Total {a}" in df_pendiente.columns]
    if cols_18_21:
        df1 = df_pendiente[['Cliente'] + cols_18_21].copy()
        df1[cols_18_21] = df1[cols_18_21].apply(pd.to_numeric, errors='coerce').fillna(0)
        df1 = df1.groupby("Cliente", as_index=False)[cols_18_21].sum()
        df1 = df1[df1[cols_18_21].sum(axis=1) > 0]
        total_clientes_unicos.update(df1['Cliente'].unique())
        st.dataframe(df1, use_container_width=True)

        total_deuda_18_21 = df1[cols_18_21].sum().sum()
        st.markdown(f"**👥 Total clientes con deuda en 2018–2021:** `{df1['Cliente'].nunique()}` – 🏅 Total deuda: `{total_deuda_18_21:,.2f} €`")
        resultado_exportacion["2018_2021"] = df1

        resumen1 = df1[cols_18_21].sum().reset_index()
        resumen1.columns = ['Periodo', 'Total Deuda']
        global fig1
        fig1 = px.bar(resumen1, x='Periodo', y='Total Deuda', text_auto='.2s', color='Total Deuda', color_continuous_scale='Blues')
        fig1.update_traces(marker_line_color='black', marker_line_width=0.6)
        st.plotly_chart(fig1, use_container_width=True)

    st.markdown("## 📅 Periodo 2022–2025")
    cols_22_24 = [f"Total {a}" for a in range(2022, 2025) if f"Total {a}" in df_pendiente.columns]
    cols_2025_meses = [f"{mes} 2025" for mes in meses if f"{mes} 2025" in df_pendiente.columns]
    key_meses_actual = "filtro_meses_2025"
    default_2025 = cols_22_24 + [m for m in cols_2025_meses if meses.index(m.split()[0]) < mes_actual]

    if año_actual == 2025:
        st.markdown("### 📌 Selecciona columnas del periodo 2022–2025")
        columnas_disponibles = cols_22_24 + cols_2025_meses
        seleccion_usuario = st.multiselect("Columnas disponibles:", columnas_disponibles,
                                           default=st.session_state.get(key_meses_actual, default_2025),
                                           key=key_meses_actual)
        cols_22_25 = seleccion_usuario
    else:
        cols_22_25 = cols_22_24

    if cols_22_25:
        df2 = df_pendiente[['Cliente'] + cols_22_25].copy()
        df2[cols_22_25] = df2[cols_22_25].apply(pd.to_numeric, errors='coerce').fillna(0)
        df2 = df2.groupby("Cliente", as_index=False)[cols_22_25].sum()
        df2 = df2[df2[cols_22_25].sum(axis=1) > 0]
        total_clientes_unicos.update(df2['Cliente'].unique())
        st.dataframe(df2, use_container_width=True)

        total_deuda_22_25 = df2[cols_22_25].sum().sum()
        st.markdown(f"**👥 Total clientes con deuda en 2022–2025:** `{df2['Cliente'].nunique()}` – 🏅 Total deuda: `{total_deuda_22_25:,.2f} €`")
        resultado_exportacion["2022_2025"] = df2

        resumen2 = df2[cols_22_25].sum().reset_index()
        resumen2.columns = ['Periodo', 'Total Deuda']
        global fig2
        fig2 = px.bar(resumen2, x='Periodo', y='Total Deuda', text_auto='.2s', color='Total Deuda', color_continuous_scale='Greens')
        fig2.update_traces(marker_line_color='black', marker_line_width=0.6)
        st.plotly_chart(fig2, use_container_width=True)

    total_global = 0
    if "2018_2021" in resultado_exportacion:
        total_global += resultado_exportacion["2018_2021"].iloc[:, 1:].sum().sum()
    if "2022_2025" in resultado_exportacion:
        total_global += resultado_exportacion["2022_2025"].iloc[:, 1:].sum().sum()
    st.markdown(f"### 🧮 TOTAL GLOBAL de clientes únicos con deuda: `{len(total_clientes_unicos)}` – 🏅 Total deuda: `{total_global:,.2f} €`")

    columnas_info = ['Cliente', 'Proyecto', 'Curso', 'Comercial']
    columnas_sumatorias = cols_18_21 + cols_22_25 if 'cols_22_25' in locals() else []
    if columnas_sumatorias:
        global df_detalle
        df_detalle = df_pendiente[df_pendiente['Cliente'].isin(total_clientes_unicos)][columnas_info + columnas_sumatorias].copy()
        df_detalle[columnas_sumatorias] = df_detalle[columnas_sumatorias].apply(pd.to_numeric, errors='coerce').fillna(0)
        df_detalle['Total deuda'] = df_detalle[columnas_sumatorias].sum(axis=1)
        df_detalle = df_detalle.groupby(['Cliente'], as_index=False).agg({
            'Proyecto': lambda x: ', '.join(sorted(set(x))),
            'Curso': lambda x: ', '.join(sorted(set(x))),
            'Comercial': lambda x: ', '.join(sorted(set(x))),
            'Total deuda': 'sum'
        }).sort_values(by='Total deuda', ascending=False)
        st.markdown("### 📋 Detalle de deuda por cliente")
        st.dataframe(df_detalle, use_container_width=True)
        resultado_exportacion["ResumenClientes"] = df_detalle

    st.markdown("---")

def vista_año_2025():
    st.subheader("📊 Pendiente por años y meses del año actual")

    if 'excel_data' not in st.session_state or st.session_state['excel_data'] is None:
        st.warning("⚠️ No hay archivo cargado.")
        return

    df = st.session_state["excel_data"].copy()
    df_pendiente = df[df["Estado"].str.strip().str.upper() == "PENDIENTE"]
    año_actual = datetime.today().year
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    columnas_totales = [col for col in df_pendiente.columns if col.startswith("Total ") and col.split()[-1].isdigit() and int(col.split()[-1]) < año_actual]
    columnas_meses = [f"{m} {año_actual}" for m in meses if f"{m} {año_actual}" in df_pendiente.columns]
    seleccionadas = st.multiselect("Selecciona columnas para visualizar:", columnas_totales + columnas_meses, default=columnas_totales + columnas_meses)
    if not seleccionadas:
        return

    df_numerico = df_pendiente[seleccionadas].apply(pd.to_numeric, errors='coerce').fillna(0)
    datos = df_numerico.sum().reset_index()
    datos.columns = ['Periodo', 'Suma Total']
    global fig_totales
    fig_totales = px.bar(datos, x='Periodo', y='Suma Total', text_auto='.2s', color='Suma Total', color_continuous_scale='Blues')
    st.plotly_chart(fig_totales, use_container_width=True)

    df_total = datos.copy()
    df_total.loc[len(df_total)] = ['TOTAL GENERAL', df_total['Suma Total'].sum()]
    st.dataframe(df_total, use_container_width=True)
    resultado_exportacion["Totales_Años_Meses"] = df_total

def render():
    vista_clientes_pendientes()
    vista_año_2025()

    total_global = 0
    if "2018_2021" in resultado_exportacion:
        total_global += resultado_exportacion["2018_2021"].iloc[:, 1:].sum().sum()
    if "2022_2025" in resultado_exportacion:
        total_global += resultado_exportacion["2022_2025"].iloc[:, 1:].sum().sum()

    texto_total_global = f"TOTAL GLOBAL de clientes únicos con deuda: {len(set(df_detalle['Cliente']))} – 🏅 Total deuda: {total_global:,.2f} €"
    st.markdown(f"### 🧮 {texto_total_global}")

    if resultado_exportacion:
        buffer_excel = io.BytesIO()
        with pd.ExcelWriter(buffer_excel, engine="xlsxwriter") as writer:
            for sheet_name, df_export in resultado_exportacion.items():
                df_export.to_excel(writer, index=False, sheet_name=sheet_name[:31])
        buffer_excel.seek(0)

        st.markdown("---")
        st.subheader("📥 Exportar todos los datos")
        st.download_button(
            label="📥 Descargar Excel consolidado",
            data=buffer_excel.getvalue(),
            file_name="exportacion_completa.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Guardar en session_state como dict de DataFrames
        st.session_state["descarga_año_2025"] = resultado_exportacion.copy()

    # HTML
    html_buffer = io.StringIO()
    html_buffer.write("<html><head><title>Informe Visual</title></head><body>")
    if 'df_detalle' in globals():
        html_buffer.write("<h1>Detalle de clientes</h1>")
        html_buffer.write(df_detalle.to_html(index=False))
    if 'fig1' in globals():
        html_buffer.write("<h2>Gráfico deuda 2018–2021</h2>")
        html_buffer.write(pio.to_html(fig1, include_plotlyjs='cdn', full_html=False))
    if 'fig2' in globals():
        html_buffer.write("<h2>Gráfico deuda 2022–2025</h2>")
        html_buffer.write(pio.to_html(fig2, include_plotlyjs='cdn', full_html=False))
    if 'fig_totales' in globals():
        html_buffer.write("<h2>Totales por años anteriores</h2>")
        html_buffer.write(pio.to_html(fig_totales, include_plotlyjs='cdn', full_html=False))
    html_buffer.write("<h2>Resumen general</h2>")
    html_buffer.write(f"<p><strong>{texto_total_global}</strong></p>")
    html_buffer.write("</body></html>")

    st.download_button(
        label="📄 Descargar informe HTML",
        data=html_buffer.getvalue(),
        file_name="reporte_visual.html",
        mime="text/html"
    )

# Guardar el HTML en disco para consolidado
    import os
    os.makedirs("uploaded", exist_ok=True)
    with open("uploaded/reporte_visual.html", "w", encoding="utf-8") as f:
        f.write(html_buffer.getvalue())

    # También guardar en session_state para consolidado ZIP
    st.session_state["html_año_2025"] = html_buffer.getvalue()