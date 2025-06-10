import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
from responsive import get_screen_size

UPLOAD_FOLDER = "uploaded_admisiones"
VENTAS_FILE = os.path.join(UPLOAD_FOLDER, "ventas.xlsx")
PREVENTAS_FILE = os.path.join(UPLOAD_FOLDER, "preventas.xlsx")

def app():
    año_actual = datetime.today().year
    width, height = get_screen_size()
    is_mobile = width <= 400

    traducciones_meses = {
        "January": "Enero", "February": "Febrero", "March": "Marzo", "April": "Abril",
        "May": "Mayo", "June": "Junio", "July": "Julio", "August": "Agosto",
        "September": "Septiembre", "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
    }

    if not os.path.exists(VENTAS_FILE) or not os.path.exists(PREVENTAS_FILE):
        st.warning("⚠️ No se han encontrado los archivos 'ventas.xlsx' y/o 'preventas.xlsx'.")
        return

    df_ventas = pd.read_excel(VENTAS_FILE)
    df_preventas = pd.read_excel(PREVENTAS_FILE)

    columnas_importe = [col for col in df_preventas.columns if "importe" in col.lower()]
    total_preventas_importe = df_preventas[columnas_importe].sum(numeric_only=True).sum() if columnas_importe else 0
    total_preventas_count = df_preventas.shape[0]

    if 'fecha de cierre' in df_ventas.columns:
        df_ventas['fecha de cierre'] = pd.to_datetime(df_ventas['fecha de cierre'], dayfirst=True, errors='coerce')
        df_ventas['mes_num'] = df_ventas['fecha de cierre'].dt.month
        df_ventas['anio'] = df_ventas['fecha de cierre'].dt.year
        df_ventas['mes_anio'] = df_ventas['fecha de cierre'].dt.month_name().map(traducciones_meses) + " " + df_ventas['anio'].astype(str)

        st.subheader("📊 Ventas y Preventas")
        meses_disponibles = df_ventas[['mes_anio', 'mes_num', 'anio']].dropna().drop_duplicates()
        meses_disponibles = meses_disponibles.sort_values(['anio', 'mes_num'], ascending=[False, False])
        opciones_meses = ["Todos"] + meses_disponibles['mes_anio'].tolist()
        mes_seleccionado = st.selectbox("Selecciona un Mes:", opciones_meses)

        if mes_seleccionado != "Todos":
            df_ventas = df_ventas[df_ventas['mes_anio'] == mes_seleccionado]
    else:
        st.warning("❌ El archivo de ventas no contiene la columna 'fecha de cierre'.")
        return

    st.markdown(f"### 📊 Ventas y Preventas - {mes_seleccionado}")

    if 'nombre' in df_ventas.columns and 'propietario' in df_ventas.columns:
        if mes_seleccionado == "Todos":
            st.markdown("#### 📊 Oportunidades por Mes y Propietario")

            df_agg = df_ventas.groupby(['mes_anio', 'propietario']).size().reset_index(name='Total Oportunidades')

            # Totales por propietario
            totales_por_propietario = df_agg.groupby('propietario')['Total Oportunidades'].sum().reset_index()
            totales_por_propietario['propietario_display'] = totales_por_propietario.apply(
                lambda row: f"{row['propietario']} ({row['Total Oportunidades']})", axis=1
            )
            df_agg = df_agg.merge(totales_por_propietario[['propietario', 'propietario_display']], on='propietario', how='left')

            # Crear gráfico sin leyenda
            fig = px.bar(
                df_agg,
                x='mes_anio',
                y='Total Oportunidades',
                color='propietario_display',
                barmode='group',
                text='Total Oportunidades',
                title='Distribución Mensual de Oportunidades por Propietario',
                width=width,
                height=height
            )
            fig.update_traces(textposition='outside')
            fig.update_layout(showlegend=False)

            st.plotly_chart(fig)

            # Crear leyenda personalizada debajo del gráfico
            color_map = {trace.name: trace.marker.color for trace in fig.data}
            legend_html = "<div style='display: flex; flex-wrap: wrap; gap: 0.5rem; padding: 1rem; background-color: #f9f9f9; border-radius: 8px;'>"

            for propietario, color in color_map.items():
                legend_html += f"""
                <div style='display: flex; align-items: center; margin-right: 12px;'>
                    <div style='width: 15px; height: 15px; background-color: {color}; margin-right: 6px; border: 1px solid #ccc;'></div>
                    <span style='font-size: 0.9rem;'>{propietario}</span>
                </div>
                """

            legend_html += "</div>"
            st.markdown(legend_html, unsafe_allow_html=True)

        else:
            st.markdown("#### Distribución de Oportunidades y Propietario")

            resumen = df_ventas.groupby(['nombre', 'propietario']).size().reset_index(name='Total Oportunidades')
            totales_propietario = resumen.groupby('propietario')['Total Oportunidades'].sum().reset_index()
            totales_propietario['propietario_display'] = totales_propietario.apply(
                lambda row: f"{row['propietario']} ({row['Total Oportunidades']})", axis=1
            )
            resumen = resumen.merge(totales_propietario[['propietario', 'propietario_display']], on='propietario', how='left')
            orden_propietarios = totales_propietario.sort_values(by='Total Oportunidades', ascending=False)['propietario_display'].tolist()
            orden_masters = resumen.groupby('nombre')['Total Oportunidades'].sum().sort_values(ascending=False).index.tolist()

            if is_mobile:
                fig = px.scatter(
                    resumen,
                    x='propietario_display',
                    y='nombre',
                    size='Total Oportunidades',
                    color='propietario_display',
                    text='Total Oportunidades',
                    size_max=40,
                    width=width,
                    height=900
                )
            else:
                fig = px.scatter(
                    resumen,
                    x='nombre',
                    y='propietario_display',
                    size='Total Oportunidades',
                    color='propietario_display',
                    text='Total Oportunidades',
                    size_max=60,
                    width=width,
                    height=height
                )

            fig.update_traces(
                textposition='middle center',
                textfont_size=12,
                textfont_color='white',
                marker=dict(line=dict(color='black', width=1.2))
            )

            fig.update_layout(
                xaxis_title='Máster' if not is_mobile else 'Propietario',
                yaxis_title='Propietario' if not is_mobile else 'Máster',
                legend_title='Propietario (Total)',
                margin=dict(l=20, r=20, t=40, b=100 if is_mobile else 40),
                legend=dict(
                    orientation="h" if is_mobile else "v",
                    yanchor="bottom" if is_mobile else "top",
                    y=-0.35 if is_mobile else 0.98,
                    xanchor="center" if is_mobile else "left",
                    x=0.5 if is_mobile else 1.02,
                    bgcolor='rgba(255,255,255,0.95)',
                    bordercolor='lightgray',
                    borderwidth=1
                )
            )

            if not is_mobile:
                fig.update_yaxes(categoryorder='array', categoryarray=orden_propietarios[::-1])
                fig.update_xaxes(categoryorder='array', categoryarray=orden_masters)
            else:
                fig.update_xaxes(categoryorder='array', categoryarray=orden_propietarios)
                fig.update_yaxes(categoryorder='array', categoryarray=orden_masters[::-1])

            st.plotly_chart(fig)

        total_importe = df_ventas['importe'].sum() if 'importe' in df_ventas.columns else 0
        total_oportunidades = len(df_ventas)

        col1, col2, col3 = st.columns(3)

        def mostrar_metricas(col, titulo, valor):
            col.markdown(f"""
                <div style='padding: 1rem; background-color: #f1f3f6; border-left: 5px solid #1f77b4;
                            border-radius: 8px;'>
                    <h4 style='margin: 0;'>{titulo}</h4>
                    <p style='font-size: 1.5rem; font-weight: bold; margin: 0;'>{valor}</p>
                </div>
            """, unsafe_allow_html=True)

        mostrar_metricas(col1, f"Importe Total ({mes_seleccionado})", f"{total_importe:,.2f} €")
        mostrar_metricas(col2, f"Matrículas ({año_actual})", total_oportunidades)
        mostrar_metricas(col3, "Preventas", f"{total_preventas_importe:,.2f} € ({total_preventas_count})")

    else:
        st.warning("❌ El archivo de ventas debe tener columnas 'nombre' y 'propietario'.")
