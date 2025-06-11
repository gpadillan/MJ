import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime

def render_card(title, value, color):
    return f"""
        <div style="background-color:{color}; padding:16px; border-radius:12px; text-align:center; box-shadow: 0 4px 8px rgba(0,0,0,0.1)">
            <h4 style="margin-bottom:0.5em">{title}</h4>
            <h2 style="margin:0">{value}</h2>
        </div>
    """

def render(df):
    st.title("Informe de Cierre de Expedientes")

    df.columns = df.columns.str.strip().str.upper()

    columnas_requeridas = ['CONSECUCIÓN GE', 'DEVOLUCIÓN GE', 'INAPLICACIÓN GE',
                           'MODALIDAD PRÁCTICAS', 'CONSULTOR EIP', 'PRÁCTCAS/GE',
                           'EMPRESA PRÁCT.', 'EMPRESA GE', 'AREA', 'AÑO', 'NOMBRE']
    if not all(col in df.columns for col in columnas_requeridas):
        st.error("Faltan columnas requeridas en el DataFrame.")
        st.write("Columnas encontradas:", df.columns.tolist())
        return

    df['PRÁCTCAS/GE'] = df['PRÁCTCAS/GE'].astype(str).str.strip().str.upper()
    df['EMPRESA PRÁCT.'] = df['EMPRESA PRÁCT.'].astype(str).str.strip().str.upper()
    df['EMPRESA GE'] = df['EMPRESA GE'].astype(str).str.strip().str.upper()
    df['AREA'] = df['AREA'].astype(str).str.strip().str.upper()
    df['AÑO'] = pd.to_numeric(df['AÑO'], errors='coerce')
    df['NOMBRE'] = df['NOMBRE'].astype(str).str.strip()
    df['CONSULTOR EIP'] = df['CONSULTOR EIP'].astype(str).str.strip().replace('', 'Otros').fillna('Otros')
    df = df[df['CONSULTOR EIP'].str.upper() != 'NO ENCONTRADO']

    df['CONSECUCIÓN_BOOL'] = df['CONSECUCIÓN GE'].astype(str).str.strip().str.upper() == 'TRUE'
    df['DEVOLUCIÓN_BOOL'] = df['DEVOLUCIÓN GE'].astype(str).str.strip().str.upper() == 'TRUE'
    df['INAPLICACIÓN_BOOL'] = df['INAPLICACIÓN GE'].astype(str).str.strip().str.upper() == 'TRUE'

    anios_disponibles = sorted(df['AÑO'].dropna().unique().astype(int))
    opciones_informe = [f"Cierre Expediente Año {a}" for a in anios_disponibles] + ["Cierre Expediente Total"]
    opcion = st.selectbox("Selecciona el tipo de informe:", opciones_informe)

    df_base = df.copy() if "Total" in opcion else df[df['AÑO'] == int(opcion.split()[-1])].copy()
    consultores_unicos = sorted(df_base['CONSULTOR EIP'].dropna().unique())
    seleccion_consultores = st.multiselect("Filtrar por Consultor:", options=consultores_unicos, default=consultores_unicos)
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
    total_practicas_actual = df_filtrado['PRACTICAS_BOOL'].sum()
    total_empresa_ge = df_filtrado['EMPRESA GE'][~df_filtrado['EMPRESA GE'].isin(['', 'NO ENCONTRADO'])].shape[0]
    total_empresa_pract = df_filtrado['EMPRESA PRÁCT.'][~df_filtrado['EMPRESA PRÁCT.'].isin(['', 'NO ENCONTRADO'])].shape[0]

    with st.container():
        if "Total" in opcion:
            col1, col2, col3, col4 = st.columns(4)
            col1.markdown(render_card("CONSECUCIÓN", total_consecucion, "#e3f2fd"), unsafe_allow_html=True)
            col2.markdown(render_card("INAPLICACIÓN", total_inaplicacion, "#fce4ec"), unsafe_allow_html=True)
            col3.markdown(render_card("Alumnado total en PRÁCTICAS", total_empresa_ge, "#ede7f6"), unsafe_allow_html=True)
            col4.markdown(render_card("Prácticas actuales", total_practicas_actual, "#e8f5e9"), unsafe_allow_html=True)
        else:
            col1, col2, col3 = st.columns(3)
            anio = opcion.split()[-1]
            col1.markdown(render_card(f"CONSECUCIÓN {anio}", total_consecucion, "#e3f2fd"), unsafe_allow_html=True)
            col2.markdown(render_card(f"INAPLICACIÓN {anio}", total_inaplicacion, "#fce4ec"), unsafe_allow_html=True)
            col3.markdown(render_card("Alumnado PRÁCTICAS", total_empresa_pract, "#f3e5f5"), unsafe_allow_html=True)

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
    resumen_area['TOTAL CONSECUCIÓN'] = df_valid_area[df_valid_area['CONSECUCIÓN_BOOL']].groupby('AREA').size()
    resumen_area['TOTAL INAPLICACIÓN'] = df_valid_area[df_valid_area['INAPLICACIÓN_BOOL']].groupby('AREA').size()
    if "Total" in opcion:
        resumen_area['TOTAL PRÁCTICAS'] = df_valid_area_pract[df_valid_area_pract['PRACTICAS_BOOL']].groupby('AREA').size()

    resumen_area = resumen_area.fillna(0).astype(int).sort_values(by='TOTAL CONSECUCIÓN', ascending=False)
    total_row = pd.DataFrame(resumen_area.sum()).T
    total_row.index = ['Total']
    resumen_area = pd.concat([resumen_area, total_row])
    resumen_area.index = list(range(1, len(resumen_area))) + ['Total']

    styled_area = resumen_area.style \
        .background_gradient(subset=['TOTAL CONSECUCIÓN'], cmap='Greens') \
        .background_gradient(subset=['TOTAL INAPLICACIÓN'], cmap='Reds')
    if 'TOTAL PRÁCTICAS' in resumen_area.columns:
        styled_area = styled_area.background_gradient(subset=['TOTAL PRÁCTICAS'], cmap='Blues')
    st.dataframe(styled_area, use_container_width=True)

    col_emp1, col_emp2 = st.columns(2)
    with col_emp1:
        st.markdown("#### Tabla: EMPRESA GE")
        empresa_ge = df_empresas['EMPRESA GE'][~df_empresas['EMPRESA GE'].isin(['', 'NO ENCONTRADO'])].value_counts().reset_index()
        empresa_ge.columns = ['EMPRESA GE', 'EMPLEOS']
        st.dataframe(empresa_ge.style.background_gradient(subset=['EMPLEOS'], cmap='YlOrBr'), use_container_width=True)
    with col_emp2:
        st.markdown("#### Tabla: EMPRESA PRÁCT.")
        empresa_pract = df_empresas['EMPRESA PRÁCT.'][~df_empresas['EMPRESA PRÁCT.'].isin(['', 'NO ENCONTRADO'])].value_counts().reset_index()
        empresa_pract.columns = ['EMPRESA PRÁCT.', 'EMPLEOS']
        st.dataframe(empresa_pract.style.background_gradient(subset=['EMPLEOS'], cmap='PuBu'), use_container_width=True)

    # 🎯 OBJETIVOS %
    total_alumnado = total_consecucion + total_inaplicacion + total_practicas_actual

    st.markdown(f"""
        <h2 style='margin: 0 0 1rem 0;'>🎯 OBJETIVOS % — <span style="font-weight: normal; font-size: 1.2rem;">Total Alumnado: {total_alumnado}</span></h2>
    """, unsafe_allow_html=True)

    df_validos = df[df['NOMBRE'].str.upper() != 'NO ENCONTRADO']
    insercion_empleo = df_validos[df_validos['CONSECUCIÓN GE'] == 'TRUE']
    porcentaje_empleo = round((insercion_empleo['NOMBRE'].nunique() / total_alumnado) * 100, 2)

    cond_cierre_dp = (
        (df_validos['CONSECUCIÓN GE'] == 'TRUE') |
        (df_validos['DEVOLUCIÓN GE'] == 'TRUE') |
        (df_validos['INAPLICACIÓN GE'] == 'TRUE')
    )
    porcentaje_cierre_dp = round((df_validos[cond_cierre_dp]['NOMBRE'].nunique() / total_alumnado) * 100, 2)

    cond_practicas = ~df_validos['EMPRESA PRÁCT.'].isin(['', 'NO ENCONTRADO'])
    porcentaje_practicas = round((df_validos[cond_practicas]['NOMBRE'].nunique() / total_alumnado) * 100, 2)

    cond_conversion = (
        (df_validos['EMPRESA PRÁCT.'] == df_validos['EMPRESA GE']) &
        (~df_validos['EMPRESA PRÁCT.'].isin(['', 'NO ENCONTRADO']))
    )
    porcentaje_conversion = round((df_validos[cond_conversion]['NOMBRE'].nunique() / total_alumnado) * 100, 2)

    col_obj1, col_obj2, col_obj3, col_obj4 = st.columns(4)
    col_obj1.markdown(render_card("Inserción laboral Empleo", f"{porcentaje_empleo}%", "#c8e6c9"), unsafe_allow_html=True)
    col_obj2.markdown(render_card("Cierre de expediente Desarrollo Profesional", f"{porcentaje_cierre_dp}%", "#b2dfdb"), unsafe_allow_html=True)
    col_obj3.markdown(render_card("Inserción Laboral Prácticas", f"{porcentaje_practicas}%", "#ffe082"), unsafe_allow_html=True)
    col_obj4.markdown(render_card("Conversión prácticas a empresa", f"{porcentaje_conversion}%", "#f8bbd0"), unsafe_allow_html=True)
