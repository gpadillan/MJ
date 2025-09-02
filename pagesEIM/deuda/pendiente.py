# pagesEIM/deuda/pendiente.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from plotly.io import to_html

from utils.eim_normalizer import prepare_eim_df, coerce_numeric, months_for_year, totals_until_year

resultado_exportacion = {}
DATA_KEY = "excel_data_eim"

def vista_clientes_pendientes():
    st.header("📄 Clientes con Estado PENDIENTE")

    if DATA_KEY not in st.session_state or st.session_state[DATA_KEY] is None:
        st.warning("⚠️ No hay archivo cargado. Ve a la sección Gestión de Datos (EIM).")
        return

    df = prepare_eim_df(st.session_state[DATA_KEY])

    df_pendiente = df[df['Estado'] == 'PENDIENTE'].copy()
    if df_pendiente.empty:
        st.info("ℹ️ No hay registros con estado PENDIENTE.")
        return

    año_actual = datetime.today().year
    mes_actual = datetime.today().month
    meses = months_for_year(año_actual)

    total_clientes_unicos = set()

    st.markdown("## 🕰️ Periodo 2018–2021")
    cols_18_21 = [c for c in totals_until_year(2021, 2018) if c in df_pendiente.columns]
    if cols_18_21:
        df1 = df_pendiente[['Cliente'] + cols_18_21].copy()
        df1 = coerce_numeric(df1, cols_18_21)
        df1 = df1.groupby("Cliente", as_index=False)[cols_18_21].sum()
        df1 = df1[df1[cols_18_21].sum(axis=1) > 0]
        total_clientes_unicos.update(df1['Cliente'].unique())
        st.dataframe(df1, use_container_width=True)

        total_deuda_18_21 = df1[cols_18_21].sum().sum()
        st.markdown(f"**👥 Total clientes con deuda 2018–2021:** {df1['Cliente'].nunique()} – 🏅 Total deuda: {total_deuda_18_21:,.2f} €")
        resultado_exportacion["2018_2021"] = df1

        resumen1 = pd.DataFrame({
            'Periodo': cols_18_21,
            'Total_Deuda': [df1[col].sum() for col in cols_18_21],
            'Num_Clientes': [(df1.groupby('Cliente')[col].sum() > 0).sum() for col in cols_18_21]
        })
        resumen1['Texto'] = resumen1.apply(lambda r: f"{r['Total_Deuda']:,.2f} €<br>👥 {r['Num_Clientes']}", axis=1)

        global fig1
        fig1 = px.bar(resumen1, x='Periodo', y='Total_Deuda', text='Texto',
                      color='Total_Deuda', color_continuous_scale='Blues')
        fig1.update_traces(marker_line_color='black', marker_line_width=0.6, textposition='inside', hovertemplate=None)
        fig1.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
        st.plotly_chart(fig1, use_container_width=True)

    st.markdown("## 📅 Periodo 2022–{} + meses {}".format(año_actual-1, año_actual))
    cols_22_prev = [c for c in totals_until_year(año_actual - 1, 2022) if c in df_pendiente.columns]
    cols_year_months = [c for c in months_for_year(año_actual) if c in df_pendiente.columns]

    # Por defecto: hasta el mes actual (no incluye meses futuros)
    default_months = [m for i, m in enumerate(cols_year_months, start=1) if i <= mes_actual]

    cols_22_aa = st.multiselect(
        "📌 Selecciona columnas del periodo:",
        cols_22_prev + cols_year_months,
        default=cols_22_prev + default_months,
        key="eim_pendiente_cols"
    )

    if cols_22_aa:
        df2 = df_pendiente[['Cliente'] + cols_22_aa].copy()
        df2 = coerce_numeric(df2, cols_22_aa)
        df2 = df2.groupby("Cliente", as_index=False)[cols_22_aa].sum()
        df2 = df2[df2[cols_22_aa].sum(axis=1) > 0]
        total_clientes_unicos.update(df2['Cliente'].unique())
        st.dataframe(df2, use_container_width=True)

        total_deuda_22_aa = df2[cols_22_aa].sum().sum()
        st.markdown(f"**👥 Total clientes con deuda 2022–{año_actual}:** {df2['Cliente'].nunique()} – 🏅 Total deuda: {total_deuda_22_aa:,.2f} €")
        resultado_exportacion["2022_actual"] = df2

        resumen2 = pd.DataFrame({
            'Periodo': cols_22_aa,
            'Total_Deuda': [df2[col].sum() for col in cols_22_aa],
            'Num_Clientes': [(df2.groupby('Cliente')[col].sum() > 0).sum() for col in cols_22_aa]
        })
        resumen2['Texto'] = resumen2.apply(lambda r: f"{r['Total_Deuda']:,.2f} €<br>👥 {r['Num_Clientes']}", axis=1)

        global fig2
        fig2 = px.bar(resumen2, x='Periodo', y='Total_Deuda', text='Texto',
                      color='Total_Deuda', color_continuous_scale='Greens')
        fig2.update_traces(marker_line_color='black', marker_line_width=0.6, textposition='inside', hovertemplate=None)
        fig2.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
        st.plotly_chart(fig2, use_container_width=True)

    num_clientes_total = len(total_clientes_unicos)
    deuda_total_acumulada = 0
    if 'df1' in locals():
        deuda_total_acumulada += total_deuda_18_21
    if 'df2' in locals():
        deuda_total_acumulada += total_deuda_22_aa

    st.markdown(f"**👥 Total clientes con deuda (2018–{año_actual}):** {num_clientes_total} – 🏅 Total deuda: {deuda_total_acumulada:,.2f} €")
    st.session_state["total_clientes_unicos"] = num_clientes_total
    st.session_state["total_deuda_acumulada"] = deuda_total_acumulada

    # Detalle por cliente (agregación simple)
    columnas_info = [c for c in ['Cliente', 'Proyecto', 'Curso', 'Comercial', 'Forma Pago'] if c in df_pendiente.columns]
    columnas_sumatorias = (cols_18_21 if 'cols_18_21' in locals() else []) + (cols_22_aa if 'cols_22_aa' in locals() else [])
    if columnas_sumatorias and columnas_info:
        df_detalle = df_pendiente[df_pendiente['Cliente'].isin(total_clientes_unicos)][columnas_info + columnas_sumatorias].copy()
        df_detalle = coerce_numeric(df_detalle, columnas_sumatorias)
        df_detalle['Total deuda'] = df_detalle[columnas_sumatorias].sum(axis=1)

        agg = {'Total deuda': 'sum'}
        for c in columnas_info:
            if c != 'Cliente':
                agg[c] = lambda x: ', '.join(sorted(set(str(v) for v in x if pd.notna(v))))
        df_detalle = df_detalle.groupby(['Cliente'], as_index=False).agg(agg).sort_values(by='Total deuda', ascending=False)

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

def vista_totales_anuales():
    año_actual = datetime.today().year

    if DATA_KEY not in st.session_state or st.session_state[DATA_KEY] is None:
        return
    df = prepare_eim_df(st.session_state[DATA_KEY])
    df_pend = df[df["Estado"] == "PENDIENTE"]

    columnas_totales = [c for c in df_pend.columns if c.startswith("Total ") and c.split()[-1].isdigit() and int(c.split()[-1]) <= año_actual]
    if not columnas_totales:
        return

    df_pend = coerce_numeric(df_pend, columnas_totales)
    resumen_total = pd.DataFrame({
        'Periodo': columnas_totales,
        'Suma_Total': [df_pend[col].sum() for col in columnas_totales],
        'Num_Clientes': [(df_pend.groupby("Cliente")[col].sum() > 0).sum() for col in columnas_totales]
    })
    resumen_total['Texto'] = resumen_total.apply(lambda r: f"{r['Suma_Total']:,.2f} €<br>👥 {r['Num_Clientes']}", axis=1)

    total_deuda_barras = resumen_total['Suma_Total'].sum()
    st.session_state["total_deuda_barras"] = total_deuda_barras

    global fig_totales
    fig_totales = px.bar(resumen_total, x='Periodo', y='Suma_Total', text='Texto',
                         color='Suma_Total', color_continuous_scale='Blues')
    fig_totales.update_traces(textposition='inside', hovertemplate=None)
    fig_totales.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
    st.plotly_chart(fig_totales, use_container_width=True)

    df_total = resumen_total.drop(columns='Texto').copy()
    df_total.loc[len(df_total)] = ['TOTAL GENERAL', total_deuda_barras, '']
    st.dataframe(df_total, use_container_width=True)
    resultado_exportacion["Totales_Años_Meses"] = df_total

def render():
    vista_clientes_pendientes()
    vista_totales_anuales()

    total_global = st.session_state.get("total_deuda_barras", 0)
    st.markdown(f"### 🧮 TOTAL desde gráfico anual: 🏅 {total_global:,.2f} €")

    if resultado_exportacion:
        st.session_state["descarga_pendiente_total"] = resultado_exportacion

        buffer_excel = io.BytesIO()
        with pd.ExcelWriter(buffer_excel, engine="xlsxwriter") as writer:
            for sheet_name, df_export in resultado_exportacion.items():
                df_export.to_excel(writer, index=False, sheet_name=sheet_name[:31])
        buffer_excel.seek(0)

        st.download_button(
            label="📥 Descargar Excel consolidado",
            data=buffer_excel.getvalue(),
            file_name="exportacion_pendiente_eim.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # HTML consolidado
        html_buffer = io.StringIO()
        html_buffer.write("<html><head><meta charset='utf-8'><title>Exportación PENDIENTE (EIM)</title></head><body>")

        if "2018_2021" in resultado_exportacion:
            html_buffer.write("<h1>Resumen 2018–2021</h1>")
            html_buffer.write(resultado_exportacion["2018_2021"].to_html(index=False))
            html_buffer.write(to_html(fig1, include_plotlyjs='cdn', full_html=False))

        if "2022_actual" in resultado_exportacion:
            html_buffer.write("<h1>Resumen 2022–Actual</h1>")
            html_buffer.write(resultado_exportacion["2022_actual"].to_html(index=False))
            html_buffer.write(to_html(fig2, include_plotlyjs='cdn', full_html=False))

        if "Totales_Años_Meses" in resultado_exportacion:
            html_buffer.write("<h2>Totales por año (deuda anual)</h2>")
            html_buffer.write(resultado_exportacion["Totales_Años_Meses"].to_html(index=False))
            html_buffer.write(to_html(fig_totales, include_plotlyjs='cdn', full_html=False))

        html_buffer.write(f"<h2>TOTAL anual: {total_global:,.2f} €</h2>")
        html_buffer.write("</body></html>")

        st.session_state["html_pendiente_total"] = html_buffer.getvalue()

        st.download_button(
            label="🌐 Descargar reporte HTML completo",
            data=st.session_state["html_pendiente_total"],
            file_name="reporte_pendiente_eim.html",
            mime="text/html"
        )
