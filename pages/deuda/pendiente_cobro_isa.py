import streamlit as st
import pandas as pd
import plotly.express as px
import io

def render():
    st.subheader("📊 Pendientes de Cobro – Becas ISA")

    if "excel_data" not in st.session_state or st.session_state["excel_data"] is None:
        st.warning("⚠️ No hay archivo cargado. Ve a la sección Gestión de Cobro.")
        return

    df = st.session_state["excel_data"].copy()

    df['Estado'] = df['Estado'].astype(str).str.strip().str.upper()
    df['Forma Pago'] = df['Forma Pago'].astype(str).str.strip().str.upper()

    df_filtrado = df[
        (df['Estado'] == "PENDIENTE") & (df['Forma Pago'] == "BECAS ISA")
    ]

    columnas_mostrar = ['Cliente', 'Proyecto', 'Curso', 'Comercial']
    columnas_fechas = ['Fecha Inicio', 'Fecha Factura', 'Importe Total Factura']

    for col in columnas_fechas:
        if col not in df_filtrado.columns:
            st.error(f"❌ Falta la columna '{col}' en el archivo.")
            return

    df_filtrado['Fecha Inicio'] = pd.to_datetime(df_filtrado['Fecha Inicio'], errors='coerce')
    df_filtrado = df_filtrado.dropna(subset=['Fecha Inicio'])

    meses_es = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }

    df_filtrado['Mes'] = df_filtrado['Fecha Inicio'].dt.month
    df_filtrado['Año'] = df_filtrado['Fecha Inicio'].dt.year
    df_filtrado['Mes Año'] = df_filtrado['Mes'].map(meses_es) + " " + df_filtrado['Año'].astype(str)
    df_filtrado['Orden'] = df_filtrado['Año'] * 100 + df_filtrado['Mes']

    resumen = df_filtrado.groupby(['Mes Año', 'Orden']).agg(
        Importe_Total=('Importe Total Factura', 'sum'),
        Numero_Clientes=('Cliente', 'nunique')
    ).reset_index().sort_values('Orden')

    fig = px.bar(
        resumen,
        x='Mes Año',
        y='Importe_Total',
        text='Numero_Clientes',
        color='Importe_Total',
        color_continuous_scale=px.colors.sequential.GnBu,
        title="Importe total por Fecha de Inicio (Clientes por barra)"
    )
    fig.update_traces(marker_line_color='black', marker_line_width=0.6, textposition='outside')
    fig.update_layout(coloraxis_showscale=False, yaxis_title="Importe Total (€)")
    st.plotly_chart(fig, use_container_width=True)

    tabla_final = (
        df_filtrado
        .groupby('Cliente', as_index=False)
        .agg({
            'Proyecto': 'first',
            'Curso': 'first',
            'Comercial': 'first',
            'Fecha Inicio': 'min',
            'Fecha Factura': 'max',
            'Importe Total Factura': 'sum'
        })
        .sort_values(by='Fecha Inicio')
    )

    st.dataframe(tabla_final, use_container_width=True)

    st.session_state["descarga_pendiente_cobro_isa"] = tabla_final

    st.markdown("---")
    st.subheader("📥 Exportar esta hoja")

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        tabla_final.to_excel(writer, sheet_name="pendiente_cobro_isa", index=False)

    st.download_button(
        label="📥 Descargar hoja: Pendiente Cobro ISA",
        data=buffer.getvalue(),
        file_name="pendiente_cobro_isa.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
