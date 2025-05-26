import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

UPLOAD_FOLDER = "uploaded_admisiones"
VENTAS_FILE = os.path.join(UPLOAD_FOLDER, "ventas.xlsx")
PREVENTAS_FILE = os.path.join(UPLOAD_FOLDER, "preventas.xlsx")

def app():
    año_actual = datetime.today().year

    traducciones_meses = {
        "January": "Enero", "February": "Febrero", "March": "Marzo", "April": "Abril",
        "May": "Mayo", "June": "Junio", "July": "Julio", "August": "Agosto",
        "September": "Septiembre", "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
    }

    if not os.path.exists(VENTAS_FILE) or not os.path.exists(PREVENTAS_FILE):
        st.warning("⚠️ No se han encontrado los archivos 'ventas.xlsx' y/o 'preventas.xlsx'. Sube los archivos desde 'Gestión de Datos'.")
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
            df_agg = df_agg.sort_values(by='mes_anio')

            fig = px.bar(
                df_agg,
                x='mes_anio',
                y='Total Oportunidades',
                color='propietario',
                barmode='group',
                text='Total Oportunidades',
                title='Distribución Mensual de Oportunidades por Propietario'
            )
            fig.update_layout(xaxis_title="Mes", yaxis_title="Total Oportunidades", height=500)
            fig.update_traces(textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

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

            fig = px.scatter(
                resumen,
                x='nombre',
                y='propietario_display',
                size='Total Oportunidades',
                color='propietario_display',
                text='Total Oportunidades',
                size_max=60,
                height=600
            )

            fig.update_traces(
                textposition='middle center',
                textfont_size=16,
                textfont_color='white',
                textfont_family='Arial Black',
                marker=dict(line=dict(color='black', width=1.5))
            )

            fig.update_layout(
                xaxis_title='Máster',
                yaxis_title='Propietario',
                legend_title='Propietario (Total)'
            )
            fig.update_yaxes(categoryorder='array', categoryarray=orden_propietarios[::-1])
            fig.update_xaxes(categoryorder='array', categoryarray=orden_masters)

            st.plotly_chart(fig, use_container_width=True)

        total_importe = df_ventas['importe'].sum() if 'importe' in df_ventas.columns else 0
        total_oportunidades = len(df_ventas)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"""
                <div style='padding: 1rem; background-color: #f1f3f6; border-left: 5px solid #1f77b4;
                            border-radius: 8px;'>
                    <h4 style='margin: 0;'> Importe Total ({mes_seleccionado})</h4>
                    <p style='font-size: 1.5rem; font-weight: bold; margin: 0;'>{total_importe:,.2f} €</p>
                </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
                <div style='padding: 1rem; background-color: #f1f3f6; border-left: 5px solid #1f77b4;
                            border-radius: 8px;'>
                    <h4 style='margin: 0;'>Matrículas ({año_actual})</h4>
                    <p style='font-size: 1.5rem; font-weight: bold; margin: 0;'>{total_oportunidades}</p>
                </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
                <div style='padding: 1rem; background-color: #f1f3f6; border-left: 5px solid #1f77b4;
                            border-radius: 8px;'>
                    <h4 style='margin: 0;'>Preventas</h4>
                    <p style='font-size: 1.5rem; font-weight: bold; margin: 0;'>{total_preventas_importe:,.2f} € ({total_preventas_count})</p>
                </div>
            """, unsafe_allow_html=True)

    else:
        st.warning("❌ El archivo de ventas debe tener columnas 'nombre' y 'propietario'.")
