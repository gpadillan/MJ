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
    año_actual = 2025
    width, height = get_screen_size()
    is_mobile = width <= 400

    traducciones_meses = {
        "January": "Enero", "February": "Febrero", "March": "Marzo", "April": "Abril",
        "May": "Mayo", "June": "Junio", "July": "Julio", "August": "Agosto",
        "September": "Septiembre", "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
    }

    orden_meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
                   "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

    if not os.path.exists(VENTAS_FILE):
        st.warning("⚠️ No se ha encontrado el archivo 'ventas.xlsx'.")
        return

    df_ventas = pd.read_excel(VENTAS_FILE)

    if os.path.exists(PREVENTAS_FILE):
        df_preventas = pd.read_excel(PREVENTAS_FILE)
        columnas_importe = [col for col in df_preventas.columns if "importe" in col.lower()]
        total_preventas_importe = df_preventas[columnas_importe].sum(numeric_only=True).sum() if columnas_importe else 0
        total_preventas_count = df_preventas.shape[0]
    else:
        df_preventas = pd.DataFrame()
        total_preventas_importe = 0
        total_preventas_count = 0

    if 'fecha de cierre' in df_ventas.columns:
        df_ventas['fecha de cierre'] = pd.to_datetime(
            df_ventas['fecha de cierre'],
            format="%Y-%m-%d",
            errors='coerce'
        )

        fechas_validas = df_ventas['fecha de cierre'].notna().sum()
        st.write(f"🔎 Fechas válidas encontradas: {fechas_validas}")

        df_ventas = df_ventas[df_ventas['fecha de cierre'].dt.year == año_actual]

        if df_ventas.empty:
            st.warning("❌ No hay datos de ventas para el año seleccionado (2025).")
            return

        df_ventas['mes'] = df_ventas['fecha de cierre'].dt.month_name().map(traducciones_meses)
        df_ventas['mes_num'] = df_ventas['fecha de cierre'].dt.month
    else:
        st.warning("❌ El archivo de ventas no contiene la columna 'fecha de cierre'.")
        return

    df_ventas_original = df_ventas.copy()

    st.subheader("📊 Ventas y Preventas")

    meses_disponibles = df_ventas[['mes', 'mes_num']].dropna().drop_duplicates()
    meses_disponibles = meses_disponibles.sort_values(['mes_num'], ascending=False)
    opciones_meses = ["Todos"] + meses_disponibles['mes'].tolist()
    mes_seleccionado = st.selectbox("Selecciona un Mes:", opciones_meses)

    if mes_seleccionado != "Todos":
        df_ventas = df_ventas[df_ventas['mes'] == mes_seleccionado]

    st.markdown(f"### 📊 Ventas y Preventas - {mes_seleccionado}")

    if 'nombre' in df_ventas.columns and 'propietario' in df_ventas.columns:
        if mes_seleccionado == "Todos":
            st.markdown("#### 🎯 Matrículas por Mes y Propietario")

            df_bar = df_ventas.groupby(['mes', 'propietario'], dropna=False).size().reset_index(name='Total Matrículas')

            totales_prop = df_bar.groupby('propietario')['Total Matrículas'].sum().reset_index()
            totales_prop['propietario_display'] = totales_prop.apply(
                lambda row: f"{row['propietario']} ({row['Total Matrículas']})", axis=1
            )

            df_bar = df_bar.merge(totales_prop[['propietario', 'propietario_display']], on='propietario', how='left')

            meses_presentes = df_bar['mes'].dropna().unique().tolist()
            orden_mes_filtrado = [m for m in orden_meses if m in meses_presentes]

            if is_mobile:
                fig = px.bar(
                    df_bar,
                    x='Total Matrículas',
                    y='propietario_display',
                    color='mes',
                    orientation='h',
                    text='Total Matrículas',
                    title='Matrículas por Propietario (Vista Móvil)',
                    width=width,
                    height=height + 500
                )
                fig.update_layout(
                    margin=dict(l=20, r=20, t=40, b=100),
                    yaxis_title='Propietario',
                    xaxis_title='Total Matrículas',
                    legend_title='Mes',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.35,
                        xanchor="center",
                        x=0.5
                    )
                )
                fig.update_traces(textposition='outside', textfont_size=14)
            else:
                fig = px.bar(
                    df_bar,
                    x='mes',
                    y='Total Matrículas',
                    color='propietario_display',
                    barmode='group',
                    text='Total Matrículas',
                    title='Distribución Mensual de Matrículas por Propietario',
                    width=width,
                    height=height
                )
                fig.update_traces(textposition='outside')
                fig.update_layout(
                    xaxis_title="Mes",
                    yaxis_title="Total Matrículas",
                    margin=dict(l=20, r=20, t=40, b=140),
                    xaxis=dict(categoryorder='array', categoryarray=orden_mes_filtrado),
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
            st.markdown("#### Distribución de Matrículas por Programa y Propietario")

            resumen = df_ventas.groupby(['nombre', 'propietario']).size().reset_index(name='Total Matrículas')
            totales_propietario = resumen.groupby('propietario')['Total Matrículas'].sum().reset_index()
            totales_propietario['propietario_display'] = totales_propietario.apply(
                lambda row: f"{row['propietario']} ({row['Total Matrículas']})", axis=1
            )
            resumen = resumen.merge(totales_propietario[['propietario', 'propietario_display']], on='propietario', how='left')

            orden_propietarios = totales_propietario.sort_values(by='Total Matrículas', ascending=False)['propietario_display'].tolist()
            orden_masters = resumen.groupby('nombre')['Total Matrículas'].sum().sort_values(ascending=False).index.tolist()

            if is_mobile:
                fig = px.bar(
                    resumen,
                    x='Total Matrículas',
                    y='nombre',
                    color='propietario_display',
                    orientation='h',
                    text='Total Matrículas',
                    width=width,
                    height=height + 400,
                    title='Matrículas por Programa (Vista Móvil)'
                )
                fig.update_layout(
                    margin=dict(l=20, r=20, t=40, b=120),
                    yaxis_title='Programa',
                    xaxis_title='Total Matrículas',
                    legend_title='Propietario',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.35,
                        xanchor="center",
                        x=0.5
                    )
                )
                fig.update_traces(textposition='outside', textfont_size=13)
            else:
                fig = px.scatter(
                    resumen,
                    x='nombre',
                    y='propietario_display',
                    size='Total Matrículas',
                    color='propietario_display',
                    text='Total Matrículas',
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
                    xaxis_title='Máster',
                    yaxis_title='Propietario',
                    legend_title='Propietario (Total)',
                    margin=dict(l=20, r=20, t=40, b=80),
                    legend=dict(
                        orientation="v",
                        yanchor="top",
                        y=0.98,
                        xanchor="left",
                        x=1.02,
                        bgcolor='rgba(255,255,255,0.95)',
                        bordercolor='lightgray',
                        borderwidth=1
                    )
                )
                fig.update_yaxes(categoryorder='array', categoryarray=orden_propietarios[::-1])
                fig.update_xaxes(categoryorder='array', categoryarray=orden_masters)

            st.plotly_chart(fig)

        total_importe = df_ventas['importe'].sum() if 'importe' in df_ventas.columns else 0
        total_oportunidades = df_ventas_original.shape[0]

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
