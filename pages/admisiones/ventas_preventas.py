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
        df_ventas['fecha de cierre'] = pd.to_datetime(df_ventas['fecha de cierre'], format="%Y-%m-%d", errors='coerce')
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

    meses_disponibles = df_ventas[['mes', 'mes_num']].dropna().drop_duplicates().sort_values(['mes_num'], ascending=False)
    opciones_meses = ["Todos"] + meses_disponibles['mes'].tolist()
    mes_seleccionado = st.selectbox("Selecciona un Mes:", opciones_meses)

    if mes_seleccionado != "Todos":
        df_ventas = df_ventas[df_ventas['mes'] == mes_seleccionado]

    st.markdown(f"### {mes_seleccionado}")

    if 'nombre' in df_ventas.columns and 'propietario' in df_ventas.columns:
        resumen = df_ventas.groupby(['nombre', 'propietario']).size().reset_index(name='Total Matrículas')
        totales_propietario = resumen.groupby('propietario')['Total Matrículas'].sum().reset_index()
        totales_propietario['propietario_display'] = totales_propietario.apply(
            lambda row: f"{row['propietario']} ({row['Total Matrículas']})", axis=1)
        resumen = resumen.merge(totales_propietario[['propietario', 'propietario_display']], on='propietario', how='left')

        orden_propietarios = totales_propietario.sort_values(by='Total Matrículas', ascending=False)['propietario_display'].tolist()
        orden_masters = resumen.groupby('nombre')['Total Matrículas'].sum().sort_values(ascending=False).index.tolist()

        color_palette = px.colors.qualitative.Plotly + px.colors.qualitative.D3 + px.colors.qualitative.Alphabet
        propietarios_unicos = resumen['propietario_display'].unique()
        color_map = {prop: color_palette[i % len(color_palette)] for i, prop in enumerate(sorted(propietarios_unicos))}

        if mes_seleccionado == "Todos":
            df_bar = df_ventas.groupby(['mes', 'propietario'], dropna=False).size().reset_index(name='Total Matrículas')
            df_bar = df_bar.merge(totales_propietario[['propietario', 'propietario_display']], on='propietario', how='left')
            totales_mes_grafico = df_bar.groupby('mes')['Total Matrículas'].sum().to_dict()
            df_bar['mes_etiqueta'] = df_bar['mes'].apply(lambda m: f"{m} ({totales_mes_grafico[m]})" if pd.notna(m) else m)
            orden_mes_etiqueta = [f"{m} ({totales_mes_grafico[m]})" for m in orden_meses if m in totales_mes_grafico]

            fig = px.bar(
                df_bar,
                x='mes_etiqueta',
                y='Total Matrículas',
                color='propietario_display',
                color_discrete_map=color_map,
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
                xaxis=dict(categoryorder='array', categoryarray=orden_mes_etiqueta),
                legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig)
        else:
            fig = px.scatter(
                resumen,
                x='nombre',
                y='propietario_display',
                size='Total Matrículas',
                color='propietario_display',
                color_discrete_map=color_map,
                text='Total Matrículas',
                size_max=60,
                width=width,
                height=height
            )
            fig.update_traces(textposition='middle center', textfont_size=12, textfont_color='white',
                              marker=dict(line=dict(color='black', width=1.2)))
            fig.update_layout(
                xaxis_title='Máster',
                yaxis_title='Propietario',
                legend=dict(orientation="v", yanchor="top", y=0.98, xanchor="left", x=1.02),
                margin=dict(l=20, r=20, t=40, b=80)
            )
            fig.update_yaxes(categoryorder='array', categoryarray=orden_propietarios[::-1])
            fig.update_xaxes(categoryorder='array', categoryarray=orden_masters)
            st.plotly_chart(fig)

        total_importe = df_ventas['importe'].sum() if 'importe' in df_ventas.columns else 0
        total_oportunidades = df_ventas_original.shape[0]
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"""
                <div style='padding: 1rem; background-color: #f1f3f6; border-left: 5px solid #1f77b4; border-radius: 8px;'>
                    <h4 style='margin: 0;'> Importe Total ({mes_seleccionado})</h4>
                    <p style='font-size: 1.5rem; font-weight: bold; margin: 0;'>{total_importe:,.2f} €</p>
                </div>
            """, unsafe_allow_html=True)

        with col2:
            cantidad_matriculas = df_ventas.shape[0] if mes_seleccionado != "Todos" else total_oportunidades
            titulo_matriculas = f"Matrículas ({mes_seleccionado})" if mes_seleccionado != "Todos" else f"Matrículas ({año_actual})"
            st.markdown(f"""
                <div style='padding: 1rem; background-color: #f1f3f6; border-left: 5px solid #1f77b4; border-radius: 8px;'>
                    <h4 style='margin: 0;'> {titulo_matriculas}</h4>
                    <p style='font-size: 1.5rem; font-weight: bold; margin: 0;'>{cantidad_matriculas}</p>
                </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
                <div style='padding: 1rem; background-color: #f1f3f6; border-left: 5px solid #1f77b4; border-radius: 8px;'>
                    <h4 style='margin: 0;'>Preventas</h4>
                    <p style='font-size: 1.5rem; font-weight: bold; margin: 0;'>{total_preventas_importe:,.2f} € ({total_preventas_count})</p>
                </div>
            """, unsafe_allow_html=True)

        st.markdown(f"### Totales por Máster ({mes_seleccionado})")
        agrupado = df_ventas.groupby('nombre').size().reset_index(name='Total Matrículas').sort_values('Total Matrículas', ascending=False)
        for i in range(0, len(agrupado), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(agrupado):
                    row = agrupado.iloc[i + j]
                    cols[j].markdown(f"""
                        <div style='padding: 1rem; background-color: #f1f3f6; border-left: 5px solid #2ca02c; border-radius: 8px;'>
                            <h5 style='margin: 0;'>{row['nombre']}</h5>
                            <p style='font-size: 1.3rem; font-weight: bold; margin: 0;'>{row['Total Matrículas']}</p>
                        </div>
                    """, unsafe_allow_html=True)

        # Importe total por propietario (en todos los casos)
        if 'importe' in df_ventas.columns:
            st.markdown(f"### Importe Total por Propietario ({mes_seleccionado})")

            importe_por_propietario = df_ventas.groupby('propietario')['importe'].sum().reset_index()
            importe_por_propietario = importe_por_propietario.merge(
                df_ventas.groupby('propietario').size().reset_index(name='Total Matrículas'),
                on='propietario',
                how='left'
            )
            importe_por_propietario['propietario_display'] = importe_por_propietario.apply(
                lambda row: f"{row['propietario']} ({row['Total Matrículas']})", axis=1
            )
            importe_por_propietario = importe_por_propietario.sort_values('importe', ascending=False)

            for i in range(0, len(importe_por_propietario), 3):
                cols = st.columns(3)
                for j in range(3):
                    if i + j < len(importe_por_propietario):
                        row = importe_por_propietario.iloc[i + j]
                        color = color_map.get(row['propietario_display'], "#1f77b4")
                        cols[j].markdown(f"""
                            <div style='padding: 1rem; background-color: #f1f3f6;
                                        border-left: 5px solid {color}; border-radius: 8px;'>
                                <h5 style='margin: 0;'>{row['propietario_display']}</h5>
                                <p style='font-size: 1.3rem; font-weight: bold; margin: 0;'>{row['importe']:,.2f} €</p>
                            </div>
                        """, unsafe_allow_html=True)

    else:
        st.warning("❌ El archivo de ventas debe tener columnas 'nombre' y 'propietario'.")
