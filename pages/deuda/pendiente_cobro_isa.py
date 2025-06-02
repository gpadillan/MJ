import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import plotly.io as pio
import io

def render():
    st.header(" Pendientes de Cobro – Becas ISA")

    if "excel_data" not in st.session_state or st.session_state["excel_data"] is None:
        st.warning("⚠️ No hay archivo cargado. Ve a la sección Gestión de Cobro.")
        return

    df = st.session_state["excel_data"].copy()
    df.columns = df.columns.str.strip()
    df['Estado'] = df['Estado'].astype(str).str.strip().str.upper()
    df['Forma Pago'] = df['Forma Pago'].astype(str).str.strip().str.upper()

    df_pendiente = df[(df['Estado'] == "PENDIENTE") & (df['Forma Pago'] == "BECAS ISA")].copy()
    if df_pendiente.empty:
        st.info("ℹ️ No hay registros con estado PENDIENTE y forma de pago BECAS ISA.")
        return

    año_actual = datetime.today().year
    mes_actual = datetime.today().month
    meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]

    total_clientes_unicos = set()
    tabla_global = pd.DataFrame()

    # PERIODO 2022–2025
    cols_22_24 = [f"Total {a}" for a in range(2022, 2025) if f"Total {a}" in df_pendiente.columns]
    cols_2025_meses = [f"{mes} 2025" for mes in meses if f"{mes} 2025" in df_pendiente.columns]
    cols_2025_total = ["Total 2025"] if "Total 2025" in df_pendiente.columns else []

    cols_2025_final = []
    key_meses_actual = "filtro_meses_becas_2025"
    default_2025 = [f"{mes} 2025" for mes in meses[:mes_actual] if f"{mes} 2025" in df_pendiente.columns]
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
        st.markdown("##  Periodo 2022–2025")
        df2 = df_pendiente[['Cliente'] + cols_22_25].copy()
        df2[cols_22_25] = df2[cols_22_25].apply(pd.to_numeric, errors='coerce').fillna(0)
        df2 = df2.groupby("Cliente", as_index=False)[cols_22_25].sum()
        df2 = df2[df2[cols_22_25].sum(axis=1) > 0]

        if not df2.empty:
            ultima_columna = cols_22_25[-1]
            index_ultima = df2.columns.get_loc(ultima_columna)
            columnas_a_sumar = df2.columns[1:index_ultima + 1]
            df2["Total Cliente"] = df2[columnas_a_sumar].sum(axis=1)

            deuda_total_22_25 = df2["Total Cliente"].sum()
            total_clientes_unicos.update(df2['Cliente'].unique())
            st.dataframe(df2, use_container_width=True)
            st.markdown(f"**👥 Total clientes con deuda en 2022–2025:** `{df2['Cliente'].nunique()}` – 💰 Total deuda: `{deuda_total_22_25:,.2f} €`")

            resumen2 = df2[columnas_a_sumar].sum().reset_index()
            resumen2.columns = ['Periodo', 'Total Deuda']
            clientes_por_periodo = df2[columnas_a_sumar].gt(0).sum().reset_index()
            clientes_por_periodo.columns = ['Periodo', 'Nº Clientes']
            resumen2 = resumen2.merge(clientes_por_periodo, on='Periodo')

            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=resumen2["Periodo"],
                y=resumen2["Total Deuda"],
                marker_color='rgb(34,163,192)',
                text=[
                    f"€ {deuda:,.2f}<br>👥 {clientes}"
                    for deuda, clientes in zip(resumen2["Total Deuda"], resumen2["Nº Clientes"])
                ],
                textposition='outside',
                textfont=dict(color='black'),
                hovertemplate='%{text}<extra></extra>',
            ))
            fig2.update_traces(marker_line_color='black', marker_line_width=1.2)
            fig2.update_layout(
                title="Total Deuda y Número de Clientes por Periodo",
                yaxis_title="Total Deuda (€)",
                xaxis_title="Periodo",
                plot_bgcolor='white'
            )
            st.plotly_chart(fig2, use_container_width=True)

            df_base = df_pendiente[['Cliente', 'Proyecto', 'Curso', 'Comercial', 'Fecha Inicio', 'Fecha Factura']].copy()
            df_base = df_base.dropna(subset=["Fecha Factura"])
            df_base['Fecha Inicio'] = pd.to_datetime(df_base['Fecha Inicio'], errors='coerce')
            tabla_22_25 = pd.merge(df2[['Cliente', 'Total Cliente']], df_base, on='Cliente', how='left')
            tabla_22_25 = tabla_22_25.groupby('Cliente', as_index=False).agg({
                'Proyecto': 'first',
                'Curso': 'first',
                'Comercial': 'first',
                'Fecha Inicio': 'min',
                'Total Cliente': 'sum'
            })
            tabla_22_25["Fecha Inicio"] = tabla_22_25["Fecha Inicio"].dt.strftime('%Y-%m-%d')
            tabla_global = pd.concat([tabla_global, tabla_22_25], ignore_index=True)

    if not tabla_global.empty:
        st.markdown("---")
        st.markdown(f"### **TOTAL de clientes pendiente Becas ISA:** `{tabla_global['Cliente'].nunique()}`")
        st.markdown("### Detalle total de pendiente por cliente")
        st.dataframe(tabla_global, use_container_width=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            tabla_global.to_excel(writer, sheet_name="detalle_deuda", index=False)
        buffer.seek(0)

        st.download_button(
            label="📥 Descargar hoja: Becas ISA Pendiente",
            data=buffer.getvalue(),
            file_name="becas_isa_pendientes.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.session_state["descarga_pendiente_cobro_isa"] = tabla_global

        # ✅ HTML actualizado
        grafico_html = pio.to_html(fig2, include_plotlyjs='cdn', full_html=False) if 'fig2' in locals() else ""

        html_content = f"""
        <html>
            <head><meta charset='utf-8'><title>Detalle Pendiente Becas ISA</title></head>
            <body>
                <h1>Pendientes de Cobro – Becas ISA</h1>
                <p>Total clientes únicos: <strong>{tabla_global['Cliente'].nunique()}</strong></p>
                <h2>Gráfico Total Deuda y Nº de Clientes por Periodo</h2>
                {grafico_html}
                <hr>
                <h2>Tabla Detalle</h2>
                {tabla_global.to_html(index=False)}
            </body>
        </html>
        """
        
        st.download_button(
            label="🌐 Descargar vista HTML",
            data=html_content.encode("utf-8"),
            file_name="becas_isa_pendientes.html",
            mime="text/html"
        )

        # Guardar HTML para el consolidado general
        st.session_state["html_pendiente_cobro_isa"] = html_content


        # Guardar HTML en disco para consolidado
        import os
        os.makedirs("uploaded", exist_ok=True)
        with open("uploaded/reporte_pendiente_cobro_isa.html", "w", encoding="utf-8") as f:
            f.write(html_content)
