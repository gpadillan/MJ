import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from plotly.io import to_html

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

    cols_22_25 = st.multiselect(
        "📌 Selecciona columnas del periodo 2022–2025:",
        cols_22_24 + cols_2025_meses,
        default=st.session_state.get(key_meses_actual, default_2025),
        key=key_meses_actual
    )

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

    num_clientes_total = len(total_clientes_unicos)
    deuda_total_acumulada = 0
    if 'df1' in locals():
        deuda_total_acumulada += total_deuda_18_21
    if 'df2' in locals():
        deuda_total_acumulada += total_deuda_22_25

    st.markdown(f"**👥 Total clientes con deuda en 2018–2025:** `{num_clientes_total}` – 🏅 Total deuda: `{deuda_total_acumulada:,.2f} €`")

    st.session_state["total_clientes_unicos"] = num_clientes_total
    st.session_state["total_deuda_acumulada"] = deuda_total_acumulada

    columnas_info = ['Cliente', 'Proyecto', 'Curso', 'Comercial', 'Forma Pago']
    columnas_sumatorias = cols_18_21 + cols_22_25
    if columnas_sumatorias:
        df_detalle = df_pendiente[df_pendiente['Cliente'].isin(total_clientes_unicos)][columnas_info + columnas_sumatorias].copy()
        df_detalle[columnas_sumatorias] = df_detalle[columnas_sumatorias].apply(pd.to_numeric, errors='coerce').fillna(0)
        df_detalle['Total deuda'] = df_detalle[columnas_sumatorias].sum(axis=1)

        df_detalle = df_detalle.groupby(['Cliente'], as_index=False).agg({
            'Proyecto': lambda x: ', '.join(sorted(set(x))),
            'Curso': lambda x: ', '.join(sorted(set(x))),
            'Comercial': lambda x: ', '.join(sorted(set(x))),
            'Forma Pago': lambda x: ', '.join(sorted(set(str(i) for i in x if pd.notna(i)))),
            'Total deuda': 'sum'
        }).sort_values(by='Total deuda', ascending=False)

        st.markdown("### 📋 Detalle de deuda por cliente")

        gb = GridOptionsBuilder.from_dataframe(df_detalle)
        gb.configure_default_column(filter=True, sortable=True, resizable=True)
        gb.configure_grid_options(domLayout='normal', suppressRowClickSelection=True)
        grid_response = AgGrid(
            df_detalle,
            gridOptions=gb.build(),
            update_mode=GridUpdateMode.MODEL_CHANGED,
            fit_columns_on_grid_load=True,
            allow_unsafe_jscode=True,
            height=600,
            use_container_width=True
        )

        df_filtrado = grid_response["data"]
        resultado_exportacion["ResumenClientes"] = df_filtrado
        st.session_state["detalle_filtrado"] = df_filtrado

    st.markdown("---")

def vista_año_2025():
    año_actual = datetime.today().year
    st.subheader("📊 Pendiente TOTAL")

    if 'excel_data' not in st.session_state or st.session_state['excel_data'] is None:
        st.warning("⚠️ No hay archivo cargado.")
        return

    df = st.session_state["excel_data"].copy()
    df_pendiente = df[df["Estado"].str.strip().str.upper() == "PENDIENTE"]

    columnas_totales = [
        col for col in df_pendiente.columns
        if col.startswith("Total ") and col.split()[-1].isdigit() and int(col.split()[-1]) <= año_actual
    ]

    df_numerico = df_pendiente[columnas_totales].apply(pd.to_numeric, errors='coerce').fillna(0)
    datos = df_numerico.sum().reset_index()
    datos.columns = ['Periodo', 'Suma Total']

    total_deuda_barras = datos['Suma Total'].sum()
    st.session_state["total_deuda_barras"] = total_deuda_barras

    global fig_totales
    fig_totales = px.bar(
        datos,
        x='Periodo',
        y='Suma Total',
        text_auto='.2s',
        color='Suma Total',
        color_continuous_scale='Blues'
    )
    st.plotly_chart(fig_totales, use_container_width=True)

    df_total = datos.copy()
    df_total.loc[len(df_total)] = ['TOTAL GENERAL', total_deuda_barras]
    st.dataframe(df_total, use_container_width=True)
    resultado_exportacion["Totales_Años_Meses"] = df_total

def render():
    vista_clientes_pendientes()
    vista_año_2025()

    total_global = st.session_state.get("total_deuda_barras", 0)
    texto_total_global = f"TOTAL desde gráfico anual: 🏅 {total_global:,.2f} €"
    st.markdown(f"### 🧮 {texto_total_global}")

    # ✅ Guardar para consolidación en gestion_datos.py
    st.session_state["descarga_año_2025"] = resultado_exportacion

    if resultado_exportacion:
        buffer_excel = io.BytesIO()
        with pd.ExcelWriter(buffer_excel, engine="xlsxwriter") as writer:
            for sheet_name, df_export in resultado_exportacion.items():
                df_export.to_excel(writer, index=False, sheet_name=sheet_name[:31])
        buffer_excel.seek(0)

        st.download_button(
            label="📥 Descargar Excel consolidado",
            data=buffer_excel.getvalue(),
            file_name="exportacion_completa.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    html_buffer = io.StringIO()
    html_buffer.write("<html><head><meta charset='utf-8'><title>Exportación</title></head><body>")

    html_buffer.write("<h1>Resumen 2018–2021</h1>")
    if "2018_2021" in resultado_exportacion:
        html_buffer.write(resultado_exportacion["2018_2021"].to_html(index=False))
        html_buffer.write(to_html(fig1, include_plotlyjs='cdn', full_html=False))

    html_buffer.write("<h1>Resumen 2022–2025</h1>")
    if "2022_2025" in resultado_exportacion:
        html_buffer.write(resultado_exportacion["2022_2025"].to_html(index=False))
        html_buffer.write(to_html(fig2, include_plotlyjs='cdn', full_html=False))

    html_buffer.write("<h2>Totales combinados</h2>")
    html_buffer.write(f"<p><strong>👥 Total clientes con deuda en 2018–2025:</strong> {st.session_state.get('total_clientes_unicos', 0)} – 🏅 Total deuda: {st.session_state.get('total_deuda_acumulada', 0):,.2f} €</p>")

    if "ResumenClientes" in resultado_exportacion:
        html_buffer.write("<h1>Detalle de deuda por cliente</h1>")
        html_buffer.write(resultado_exportacion["ResumenClientes"].to_html(index=False))

    html_buffer.write("<h2>Totales por año (deuda anual)</h2>")
    if "Totales_Años_Meses" in resultado_exportacion:
        html_buffer.write(resultado_exportacion["Totales_Años_Meses"].to_html(index=False))
        html_buffer.write(to_html(fig_totales, include_plotlyjs='cdn', full_html=False))

    html_buffer.write(f"<h2>{texto_total_global}</h2>")
    html_buffer.write("</body></html>")

    st.download_button(
        label="📄 Descargar HTML filtrado",
        data=html_buffer.getvalue(),
        file_name="detalle_filtrado.html",
        mime="text/html"
    )
