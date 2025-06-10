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
            st.markdown("#### 📊 Oportunidades Totales por Propietario")

            df_agg = df_ventas.groupby('propietario').size().reset_index(name='Total Oportunidades')
            df_agg = df_agg.sort_values(by='Total Oportunidades', ascending=False)
            df_agg['propietario_display'] = df_agg.apply(
                lambda row: f"{row['propietario']} ({row['Total Oportunidades']})", axis=1
            )

            if is_mobile:
                fig = px.pie(
                    df_agg,
                    names='propietario_display',
                    values='Total Oportunidades',
                    title="Distribución Total de Oportunidades",
                )
                fig.update_traces(
                    textinfo='label',  # Solo nombre, sin %
                    textposition='inside',
                    pull=[0.02] * len(df_agg)
                )
                fig.update_layout(
                    height=500,
                    margin=dict(t=40, b=80),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.4,
                        xanchor="center",
                        x=0.5,
                        bgcolor="rgba(255,255,255,0.95)",
                        bordercolor="lightgray",
                        borderwidth=1,
                        font=dict(size=12)
                    )
                )
                st.plotly_chart(fig)

            else:
                df_bar = df_ventas.groupby(['mes_anio', 'propietario']).size().reset_index(name='Total Oportunidades')
                totales_prop = df_bar.groupby('propietario')['Total Oportunidades'].sum().reset_index()
                totales_prop['propietario_display'] = totales_prop.apply(
                    lambda row: f"{row['propietario']} ({row['Total Oportunidades']})", axis=1
                )
                df_bar = df_bar.merge(totales_prop[['propietario', 'propietario_display']], on='propietario', how='left')
                df_bar = df_bar.sort_values(by='mes_anio')

                fig = px.bar(
                    df_bar,
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
                fig.update_layout(
                    xaxis_title="Mes",
                    yaxis_title="Total Oportunidades",
                    margin=dict(l=20, r=20, t=40, b=140),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.5,
                        xanchor="center",
                        x=0.5,
                        bgcolor="rgba(255,255,255,0.95)",
                        bordercolor="lightgray",
                        borderwidth=1
                    )
                )
                st.plotly_chart(fig)

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
                    x='nombre',
                    y='propietario_display',
                    size='Total Oportunidades',
                    color='propietario_display',
                    text='Total Oportunidades',
                    size_max=25,
                    width=width,
                    height=1100
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
                xaxis_title='Máster' if not is_mobile else 'Máster',
                yaxis_title='Propietario' if not is_mobile else 'Propietario',
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
                fig.update_xaxes(categoryorder='array', categoryarray=orden_masters)
                fig.update_yaxes(categoryorder='array', categoryarray=orden_propietarios[::-1])

            st.plotly_chart(fig)

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
