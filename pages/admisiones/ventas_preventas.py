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
        if mes_seleccionado == "Todos":
            df_bar = df_ventas.groupby(['mes', 'propietario'], dropna=False).size().reset_index(name='Total Matrículas')
            totales_prop = df_bar.groupby('propietario')['Total Matrículas'].sum().reset_index()
            totales_prop['propietario_display'] = totales_prop.apply(lambda row: f"{row['propietario']} ({row['Total Matrículas']})", axis=1)
            df_bar = df_bar.merge(totales_prop[['propietario', 'propietario_display']], on='propietario', how='left')

            totales_mes_grafico = df_bar.groupby('mes')['Total Matrículas'].sum().to_dict()
            df_bar['mes_etiqueta'] = df_bar['mes'].apply(lambda m: f"{m} ({totales_mes_grafico[m]})" if pd.notna(m) else m)
            orden_mes_etiqueta = [f"{m} ({totales_mes_grafico[m]})" for m in orden_meses if m in totales_mes_grafico]

            propietarios_unicos = df_bar['propietario_display'].unique()
            color_palette = px.colors.qualitative.Alphabet + px.colors.qualitative.Dark24 + px.colors.qualitative.Vivid
            while len(color_palette) < len(propietarios_unicos):
                color_palette += color_palette
            color_map = dict(zip(sorted(propietarios_unicos), color_palette))

            if is_mobile:
                fig = px.bar(
                    df_bar,
                    x='Total Matrículas',
                    y='propietario_display',
                    color='mes_etiqueta',
                    orientation='h',
                    text='Total Matrículas',
                    width=width,
                    height=height + 500
                )
                fig.update_layout(
                    margin=dict(l=20, r=20, t=40, b=100),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5)
                )
            else:
                fig = px.bar(
                    df_bar,
                    x='mes_etiqueta',
                    y='Total Matrículas',
                    color='propietario_display',
                    color_discrete_map=color_map,
                    barmode='group',
                    text='Total Matrículas',
                    width=width,
                    height=height
                )
                fig.update_layout(
                    xaxis=dict(categoryorder='array', categoryarray=orden_mes_etiqueta),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5)
                )
            st.plotly_chart(fig)

        else:
            resumen = df_ventas.groupby(['nombre', 'propietario']).size().reset_index(name='Total Matrículas')
            totales_propietario = resumen.groupby('propietario')['Total Matrículas'].sum().reset_index()
            totales_propietario['propietario_display'] = totales_propietario.apply(
                lambda row: f"{row['propietario']} ({row['Total Matrículas']})", axis=1)
            resumen = resumen.merge(totales_propietario[['propietario', 'propietario_display']], on='propietario', how='left')

            orden_propietarios = totales_propietario.sort_values(by='Total Matrículas', ascending=False)['propietario_display'].tolist()
            orden_masters = resumen.groupby('nombre')['Total Matrículas'].sum().sort_values(ascending=False).index.tolist()

            propietarios_unicos = resumen['propietario_display'].unique()
            color_palette = px.colors.qualitative.Prism + px.colors.qualitative.Safe
            while len(color_palette) < len(propietarios_unicos):
                color_palette += color_palette
            color_map = dict(zip(sorted(propietarios_unicos), color_palette))

            if is_mobile:
                fig = px.bar(
                    resumen,
                    x='Total Matrículas',
                    y='nombre',
                    color='propietario_display',
                    orientation='h',
                    text='Total Matrículas',
                    width=width,
                    height=height + 400
                )
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
                fig.update_traces(marker=dict(line=dict(color='black', width=1.2)))
                fig.update_layout(
                    xaxis=dict(categoryorder='array', categoryarray=orden_masters),
                    yaxis=dict(categoryorder='array', categoryarray=orden_propietarios[::-1])
                )
            st.plotly_chart(fig)

        total_importe = df_ventas['importe'].sum() if 'importe' in df_ventas.columns else 0
        total_oportunidades = df_ventas_original.shape[0]

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(f"Importe Total ({mes_seleccionado})", f"{total_importe:,.2f} €")
        with col2:
            st.metric(f"Matrículas ({mes_seleccionado})", df_ventas.shape[0])
        with col3:
            st.metric("Preventas", f"{total_preventas_importe:,.2f} € ({total_preventas_count})")

        st.markdown(f"### Totales por Máster ({mes_seleccionado})")
        agrupado = df_ventas.groupby('nombre').size().reset_index(name='Total Matrículas').sort_values('Total Matrículas', ascending=False)
        for i in range(0, len(agrupado), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(agrupado):
                    row = agrupado.iloc[i + j]
                    cols[j].metric(label=row['nombre'], value=row['Total Matrículas'])
    else:
        st.warning("❌ El archivo de ventas debe tener columnas 'nombre' y 'propietario'.")
