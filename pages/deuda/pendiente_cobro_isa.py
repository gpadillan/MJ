import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
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

            # Añadir a tabla_global
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

    # PERIODO 2026–2029
    if año_actual >= 2026:
        cols_meses_actual = [f"{mes} {año_actual}" for mes in meses if f"{mes} {año_actual}" in df_pendiente.columns]
        if cols_meses_actual:
            st.markdown(f"##  Periodo {año_actual}–{año_actual + 3}")
            seleccion_meses = st.multiselect(
                f"Selecciona meses de {año_actual}",
                options=cols_meses_actual,
                default=cols_meses_actual
            )
            if seleccion_meses:
                df_meses = df_pendiente[['Cliente'] + seleccion_meses].copy()
                df_meses[seleccion_meses] = df_meses[seleccion_meses].apply(pd.to_numeric, errors='coerce').fillna(0)
                df_meses = df_meses.groupby("Cliente", as_index=False)[seleccion_meses].sum()
                df_meses = df_meses[df_meses[seleccion_meses].sum(axis=1) > 0]

                if not df_meses.empty:
                    df_meses["Total Cliente"] = df_meses[seleccion_meses].sum(axis=1)
                    total_clientes_unicos.update(df_meses['Cliente'].unique())
                    st.dataframe(df_meses, use_container_width=True)
                    st.markdown(f"**👥 Total clientes con deuda en {año_actual}:** `{df_meses['Cliente'].nunique()}` – 💰 Total deuda: `{df_meses['Total Cliente'].sum():,.2f} €`")

                    resumen_meses = df_meses[seleccion_meses].sum().reset_index()
                    resumen_meses.columns = ['Periodo', 'Total Deuda']
                    resumen_meses['Nº Clientes'] = df_meses[seleccion_meses].gt(0).sum().values

                    fig_meses = go.Figure()
                    fig_meses.add_trace(go.Bar(
                        x=resumen_meses["Periodo"],
                        y=resumen_meses["Total Deuda"],
                        marker_color='lightgreen',
                        text=[
                            f"€ {deuda:,.2f}<br>👥 {clientes}"
                            for deuda, clientes in zip(resumen_meses["Total Deuda"], resumen_meses["Nº Clientes"])
                        ],
                        textposition='outside',
                        textfont=dict(color='black'),
                        hovertemplate='%{text}<extra></extra>',
                    ))
                    fig_meses.update_traces(marker_line_color='black', marker_line_width=1.2)
                    fig_meses.update_layout(
                        title=f"Total Deuda y Nº Clientes por Mes ({año_actual})",
                        yaxis_title="Total Deuda (€)",
                        xaxis_title="Mes",
                        plot_bgcolor='white'
                    )
                    st.plotly_chart(fig_meses, use_container_width=True)

                    # Añadir a tabla_global
                    df_base_2026 = df_pendiente[['Cliente', 'Proyecto', 'Curso', 'Comercial', 'Fecha Inicio', 'Fecha Factura']].copy()
                    df_base_2026 = df_base_2026.dropna(subset=["Fecha Factura"])
                    df_base_2026['Fecha Inicio'] = pd.to_datetime(df_base_2026['Fecha Inicio'], errors='coerce')
                    tabla_2026 = pd.merge(df_meses[['Cliente', 'Total Cliente']], df_base_2026, on='Cliente', how='left')
                    tabla_2026 = tabla_2026.groupby('Cliente', as_index=False).agg({
                        'Proyecto': 'first',
                        'Curso': 'first',
                        'Comercial': 'first',
                        'Fecha Inicio': 'min',
                        'Total Cliente': 'sum'
                    })
                    tabla_2026["Fecha Inicio"] = tabla_2026["Fecha Inicio"].dt.strftime('%Y-%m-%d')
                    tabla_global = pd.concat([tabla_global, tabla_2026], ignore_index=True)

    # TOTAL GLOBAL FINAL
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
