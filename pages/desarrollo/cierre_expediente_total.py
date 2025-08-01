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
    fecha_referencia = pd.to_datetime("2000-01-01")

    columnas_requeridas = ['CONSECUCIÓN GE', 'DEVOLUCIÓN GE', 'INAPLICACIÓN GE',
                           'MODALIDAD PRÁCTICAS', 'CONSULTOR EIP', 'PRÁCTCAS/GE',
                           'EMPRESA PRÁCT.', 'EMPRESA GE', 'AREA', 'AÑO', 'NOMBRE', 'APELLIDOS', 'FECHA CIERRE']
    if not all(col in df.columns for col in columnas_requeridas):
        st.error("Faltan columnas requeridas en el DataFrame.")
        return

    df = df.copy()
    df['PRÁCTCAS/GE'] = df['PRÁCTCAS/GE'].astype(str).str.strip().str.upper()
    df['EMPRESA PRÁCT.'] = df['EMPRESA PRÁCT.'].astype(str).str.strip().str.upper()
    df['EMPRESA GE'] = df['EMPRESA GE'].astype(str).str.strip().str.upper()
    df['AREA'] = df['AREA'].astype(str).str.strip().str.upper()
    df['AÑO'] = pd.to_numeric(df['AÑO'], errors='coerce')
    df['NOMBRE'] = df['NOMBRE'].astype(str).str.strip().str.upper()
    df['APELLIDOS'] = df['APELLIDOS'].astype(str).str.strip().str.upper()
    df['CONSULTOR EIP'] = df['CONSULTOR EIP'].astype(str).str.strip().replace('', 'Otros').fillna('Otros')
    df = df[df['CONSULTOR EIP'].str.upper() != 'NO ENCONTRADO']

    df['FECHA CIERRE'] = pd.to_datetime(df['FECHA CIERRE'], errors='coerce')
    df['AÑO_CIERRE'] = df['FECHA CIERRE'].dt.year
    df['EN_CURSO_2025_BOOL'] = df['FECHA CIERRE'] == fecha_referencia

    df['CONSECUCIÓN_BOOL'] = df['CONSECUCIÓN GE'].astype(str).str.strip().str.upper() == 'TRUE'
    df['INAPLICACIÓN_BOOL'] = df['INAPLICACIÓN GE'].astype(str).str.strip().str.upper() == 'TRUE'
    df['DEVOLUCIÓN_BOOL'] = df['DEVOLUCIÓN GE'].astype(str).str.strip().str.upper() == 'TRUE'

    anios_disponibles = sorted(df.loc[~df['EN_CURSO_2025_BOOL'], 'AÑO_CIERRE'].dropna().unique().astype(int))
    if 2025 not in anios_disponibles:
        anios_disponibles.append(2025)
    opciones_informe = [f"Cierre Expediente Año {a}" for a in anios_disponibles] + ["Cierre Expediente Total"]
    opcion = st.selectbox("Selecciona el tipo de informe:", opciones_informe)

    if "Total" in opcion:
        df_base = df.copy()
    else:
        anio = int(opcion.split()[-1])
        if anio == 2025:
            df_base = df[(df['AÑO_CIERRE'] == 2025) | (df['EN_CURSO_2025_BOOL'])].copy()
        else:
            df_base = df[df['AÑO_CIERRE'] == anio].copy()

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
    total_empresa_ge = df_filtrado['EMPRESA GE'][~df_filtrado['EMPRESA GE'].isin(['', 'NO ENCONTRADO'])].shape[0]
    total_empresa_pract = df_filtrado['EMPRESA PRÁCT.'][~df_filtrado['EMPRESA PRÁCT.'].isin(['', 'NO ENCONTRADO'])].shape[0]

    with st.container():
        if "Total" in opcion:
            col1, col2, col3 = st.columns(3)
            col1.markdown(render_card("CONSECUCIÓN", total_consecucion, "#e3f2fd"), unsafe_allow_html=True)
            col2.markdown(render_card("INAPLICACIÓN", total_inaplicacion, "#fce4ec"), unsafe_allow_html=True)
            col3.markdown(render_card("Alumnado total en PRÁCTICAS", total_empresa_ge, "#ede7f6"), unsafe_allow_html=True)
        else:
            anio = opcion.split()[-1]
            en_curso_2025 = 0
            if anio == '2025':
                en_curso_2025 = df[
                    (df['EN_CURSO_2025_BOOL']) &
                    (df['CONSULTOR EIP'].isin(seleccion_consultores))
                ].shape[0]
                col1, col2, col3, col4 = st.columns(4)
                col1.markdown(render_card(f"CONSECUCIÓN {anio}", total_consecucion, "#e3f2fd"), unsafe_allow_html=True)
                col2.markdown(render_card(f"INAPLICACIÓN {anio}", total_inaplicacion, "#fce4ec"), unsafe_allow_html=True)
                col3.markdown(render_card(f"Prácticas {anio}", total_empresa_pract, "#f3e5f5"), unsafe_allow_html=True)
                col4.markdown(render_card("Prácticas en curso 2025", en_curso_2025, "#fff3e0"), unsafe_allow_html=True)
            else:
                col1, col2, col3 = st.columns(3)
                col1.markdown(render_card(f"CONSECUCIÓN {anio}", total_consecucion, "#e3f2fd"), unsafe_allow_html=True)
                col2.markdown(render_card(f"INAPLICACIÓN {anio}", total_inaplicacion, "#fce4ec"), unsafe_allow_html=True)
                col3.markdown(render_card(f"Prácticas {anio}", total_empresa_pract, "#f3e5f5"), unsafe_allow_html=True)

    df_validos = df[(df['NOMBRE'] != 'NO ENCONTRADO') & (df['APELLIDOS'] != 'NO ENCONTRADO')]
    total_alumnado_objetivo = df_validos[['NOMBRE', 'APELLIDOS']].drop_duplicates().shape[0]

    st.markdown("## 🎯 OBJETIVOS %")

    insercion_empleo = df_validos[df_validos['CONSECUCIÓN GE'] == 'TRUE']
    porcentaje_empleo = round((insercion_empleo[['NOMBRE', 'APELLIDOS']].drop_duplicates().shape[0] / total_alumnado_objetivo) * 100, 2)

    cond_cierre_dp = (
        (df_validos['CONSECUCIÓN GE'] == 'TRUE') |
        (df_validos['DEVOLUCIÓN GE'] == 'TRUE') |
        (df_validos['INAPLICACIÓN GE'] == 'TRUE')
    )
    porcentaje_cierre_dp = round((df_validos[cond_cierre_dp][['NOMBRE', 'APELLIDOS']].drop_duplicates().shape[0] / total_alumnado_objetivo) * 100, 2)

    practicas_realizadas = df_validos[~df_validos['EMPRESA PRÁCT.'].isin(['', 'NO ENCONTRADO'])]
    porcentaje_practicas = round((practicas_realizadas[['NOMBRE', 'APELLIDOS']].drop_duplicates().shape[0] / total_alumnado_objetivo) * 100, 2)

    conversion_realizada = practicas_realizadas[practicas_realizadas['EMPRESA PRÁCT.'] == practicas_realizadas['EMPRESA GE']]
    if not practicas_realizadas.empty:
        porcentaje_conversion = round((conversion_realizada[['NOMBRE', 'APELLIDOS']].drop_duplicates().shape[0] / practicas_realizadas[['NOMBRE', 'APELLIDOS']].drop_duplicates().shape[0]) * 100, 2)
    else:
        porcentaje_conversion = 0.0

    col_obj1, col_obj2, col_obj3, col_obj4 = st.columns(4)
    col_obj1.markdown(render_card("Inserción laboral Empleo", f"{porcentaje_empleo}%", "#c8e6c9"), unsafe_allow_html=True)
    col_obj2.markdown(render_card("Cierre de expediente Desarrollo Profesional", f"{porcentaje_cierre_dp}%", "#b2dfdb"), unsafe_allow_html=True)
    col_obj3.markdown(render_card("Inserción Laboral Prácticas", f"{porcentaje_practicas}%", "#ffe082"), unsafe_allow_html=True)
    col_obj4.markdown(render_card("Conversión prácticas a empresa", f"{porcentaje_conversion}%", "#f8bbd0"), unsafe_allow_html=True)
