import pandas as pd 
import streamlit as st
import plotly.express as px
from datetime import datetime

def render(df):
    st.title("Informe de Cierre de Expedientes")

    df.columns = df.columns.str.strip().str.upper()

    columnas_requeridas = ['CONSECUCIÓN GE', 'DEVOLUCIÓN GE', 'INAPLICACIÓN GE',
                           'MODALIDAD PRÁCTICAS', 'CONSULTOR EIP', 'PRÁCTCAS/GE',
                           'EMPRESA PRÁCT.', 'EMPRESA GE', 'AREA', 'AÑO']
    if not all(col in df.columns for col in columnas_requeridas):
        st.error("Faltan columnas requeridas en el DataFrame.")
        st.write("Columnas encontradas:", df.columns.tolist())
        return

    df['PRÁCTCAS/GE'] = df['PRÁCTCAS/GE'].astype(str).str.strip().str.upper()
    df['EMPRESA PRÁCT.'] = df['EMPRESA PRÁCT.'].astype(str).str.strip().str.upper()
    df['EMPRESA GE'] = df['EMPRESA GE'].astype(str).str.strip().str.upper()
    df['AREA'] = df['AREA'].astype(str).str.strip().str.upper()
    df['AÑO'] = pd.to_numeric(df['AÑO'], errors='coerce')

    df['CONSULTOR EIP'] = df['CONSULTOR EIP'].astype(str).str.strip()
    df['CONSULTOR EIP'] = df['CONSULTOR EIP'].replace('', 'Otros').fillna('Otros')
    df = df[df['CONSULTOR EIP'].str.upper() != 'NO ENCONTRADO']

    df['CONSECUCIÓN_BOOL'] = df['CONSECUCIÓN GE'].astype(str).str.strip().str.upper() == 'TRUE'
    df['DEVOLUCIÓN_BOOL'] = df['DEVOLUCIÓN GE'].astype(str).str.strip().str.upper() == 'TRUE'
    df['INAPLICACIÓN_BOOL'] = df['INAPLICACIÓN GE'].astype(str).str.strip().str.upper() == 'TRUE'

    anios_disponibles = sorted(df['AÑO'].dropna().unique().astype(int))
    opciones_informe = [f"Cierre Expediente Año {a}" for a in anios_disponibles] + ["Cierre Expediente Total"]

    opcion = st.selectbox("Selecciona el tipo de informe:", opciones_informe)

    if "Total" in opcion:
        df_base = df.copy()
    else:
        anio_seleccionado = int(opcion.split()[-1])
        df_base = df[df['AÑO'] == anio_seleccionado].copy()

    df_base['CONSECUCIÓN_BOOL'] = df_base['CONSECUCIÓN GE'].astype(str).str.strip().str.upper() == 'TRUE'
    df_base['INAPLICACIÓN_BOOL'] = df_base['INAPLICACIÓN GE'].astype(str).str.strip().str.upper() == 'TRUE'

    consultores_unicos = sorted(df_base['CONSULTOR EIP'].dropna().unique())
    seleccion_consultores = st.multiselect(
        "Filtrar por Consultor:",
        options=consultores_unicos,
        default=consultores_unicos
    )

    df_filtrado = df_base[df_base['CONSULTOR EIP'].isin(seleccion_consultores)]

    df_filtrado['PRACTICAS_BOOL'] = (
        (df_filtrado['PRÁCTCAS/GE'] == 'GE') &
        (~df_filtrado['EMPRESA PRÁCT.'].isin(['', 'NO ENCONTRADO'])) &
        (df_filtrado['CONSECUCIÓN GE'].astype(str).str.strip().str.upper() == 'FALSE') &
        (df_filtrado['DEVOLUCIÓN GE'].astype(str).str.strip().str.upper() == 'FALSE') &
        (df_filtrado['INAPLICACIÓN GE'].astype(str).str.strip().str.upper() == 'FALSE')
    )

    total_consecucion = df_filtrado['CONSECUCIÓN_BOOL'].sum()
    total_inaplicacion = df_filtrado['INAPLICACIÓN_BOOL'].sum()
    total_practicas_actual = df_filtrado[df_filtrado['PRACTICAS_BOOL']].shape[0]
    total_empresa_ge = df_filtrado['EMPRESA GE'][~df_filtrado['EMPRESA GE'].isin(['', 'NO ENCONTRADO'])].shape[0]
    total_empresa_pract = df_filtrado['EMPRESA PRÁCT.'][~df_filtrado['EMPRESA PRÁCT.'].isin(['', 'NO ENCONTRADO'])].shape[0]

    with st.container():
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.markdown(f"""
            <div style='padding: 6px; background-color: #e3f2fd; border-radius: 8px; font-size: 13px; text-align: center'>
                {'Total CONSECUCIÓN GE' if "Total" in opcion else f'CONSECUCIÓN GE {anio_seleccionado}'}<br><strong style='font-size: 16px'>{total_consecucion}</strong>
            </div>
        """, unsafe_allow_html=True)
        col2.markdown(f"""
            <div style='padding: 6px; background-color: #fce4ec; border-radius: 8px; font-size: 13px; text-align: center'>
                {'Total INAPLICACIÓN GE' if "Total" in opcion else f'INAPLICACIÓN GE {anio_seleccionado}'}<br><strong style='font-size: 16px'>{total_inaplicacion}</strong>
            </div>
        """, unsafe_allow_html=True)
        col3.markdown(f"""
            <div style='padding: 6px; background-color: #e8f5e9; border-radius: 8px; font-size: 13px; text-align: center'>
                Prácticas GE actuales<br><strong style='font-size: 16px'>{total_practicas_actual}</strong>
            </div>
        """, unsafe_allow_html=True)
        col4.markdown(f"""
            <div style='padding: 6px; background-color: #ede7f6; border-radius: 8px; font-size: 13px; text-align: center'>
                Alumnado total en PRÁCTICAS GE<br><strong style='font-size: 16px'>{total_empresa_ge}</strong>
            </div>
        """, unsafe_allow_html=True)
        col5.markdown(f"""
            <div style='padding: 6px; background-color: #f3e5f5; border-radius: 8px; font-size: 13px; text-align: center'>
                Alumnado con EMPRESA PRÁCT.<br><strong style='font-size: 16px'>{total_empresa_pract}</strong>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("### Cierres gestionados por Consultor")

    df_cierre = pd.concat([
        df_filtrado[df_filtrado['CONSECUCIÓN_BOOL']][['CONSULTOR EIP']].assign(CIERRE='CONSECUCIÓN'),
        df_filtrado[df_filtrado['INAPLICACIÓN_BOOL']][['CONSULTOR EIP']].assign(CIERRE='INAPLICACIÓN')
    ])

    resumen_total_cierres = df_cierre.groupby('CONSULTOR EIP').size().reset_index(name='TOTAL_CIERRES')

    fig_pie = px.pie(
        resumen_total_cierres,
        names='CONSULTOR EIP',
        values='TOTAL_CIERRES',
        title=f'Distribución de cierres por Consultor ({opcion})',
        hole=0
    )
    fig_pie.update_traces(textinfo='label+value')
    st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("### Empresas por ÁREA")
    areas_disponibles = ['TODAS'] + sorted(df_filtrado['AREA'].dropna().unique())
    area_seleccionada = st.selectbox("Filtrar empresas por área:", areas_disponibles)
    df_empresas = df_filtrado if area_seleccionada == 'TODAS' else df_filtrado[df_filtrado['AREA'] == area_seleccionada]

    st.markdown("### Resumen por ÁREA")

    df_valid_area = df_empresas[df_empresas['AREA'] != '']
    df_valid_area_pract = df_valid_area.copy()

    resumen_area = pd.DataFrame()
    resumen_area['TOTAL CONSECUCIÓN GE'] = df_valid_area[df_valid_area['CONSECUCIÓN_BOOL']].groupby('AREA').size()
    resumen_area['TOTAL INAPLICACIÓN GE'] = df_valid_area[df_valid_area['INAPLICACIÓN_BOOL']].groupby('AREA').size()
    resumen_area['TOTAL PRÁCTICAS GE'] = df_valid_area_pract[df_valid_area_pract['PRACTICAS_BOOL']].groupby('AREA').size()
    resumen_area = resumen_area.fillna(0).astype(int).sort_values(by='TOTAL CONSECUCIÓN GE', ascending=False)

    # Añadir fila de totales
    total_row = pd.DataFrame(resumen_area.sum()).T
    total_row.index = ['Total']
    resumen_area = pd.concat([resumen_area, total_row])
    resumen_area.index = list(range(1, len(resumen_area))) + ['Total']

    styled_area = resumen_area.style \
        .background_gradient(subset=['TOTAL CONSECUCIÓN GE'], cmap='Greens') \
        .background_gradient(subset=['TOTAL INAPLICACIÓN GE'], cmap='Reds') \
        .background_gradient(subset=['TOTAL PRÁCTICAS GE'], cmap='Blues')

    st.dataframe(styled_area, use_container_width=True)

    col_emp1, col_emp2 = st.columns(2)

    with col_emp1:
        st.markdown("#### Tabla: EMPRESA GE")
        empresa_ge = df_empresas['EMPRESA GE'][~df_empresas['EMPRESA GE'].isin(['', 'NO ENCONTRADO'])]
        empresa_ge = empresa_ge.value_counts().reset_index()
        empresa_ge.columns = ['EMPRESA GE', 'EMPLEOS']
        styled_ge = empresa_ge.style.background_gradient(subset=['EMPLEOS'], cmap='YlOrBr', vmax=20)
        st.dataframe(styled_ge, use_container_width=True)

    with col_emp2:
        st.markdown("#### Tabla: EMPRESA PRÁCT.")
        empresa_pract = df_empresas['EMPRESA PRÁCT.'][~df_empresas['EMPRESA PRÁCT.'].isin(['', 'NO ENCONTRADO'])]
        empresa_pract = empresa_pract.value_counts().reset_index()
        empresa_pract.columns = ['EMPRESA PRÁCT.', 'EMPLEOS']
        styled_pract = empresa_pract.style.background_gradient(subset=['EMPLEOS'], cmap='PuBu', vmax=20)
        st.dataframe(styled_pract, use_container_width=True)
