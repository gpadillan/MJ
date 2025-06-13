import streamlit as st
import pandas as pd
import os
from datetime import datetime
from pages.academica.sharepoint_utils import get_access_token, get_site_id, download_excel
from google.oauth2 import service_account
import gspread

# === UTILS ===
def format_euro(value):
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# === CACHES ===
@st.cache_data(show_spinner=False)
def load_admisiones(ventas_path, preventas_path):
    df_ventas, df_preventas = None, None
    if os.path.exists(ventas_path):
        df_ventas = pd.read_excel(ventas_path)
    if os.path.exists(preventas_path):
        df_preventas = pd.read_excel(preventas_path)
    return df_ventas, df_preventas

@st.cache_data(show_spinner=False)
def load_gestion_data(file_path):
    if os.path.exists(file_path):
        return pd.read_excel(file_path)
    return pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_google_sheet(sheet_key):
    creds = st.secrets["google_service_account"]
    credentials = service_account.Credentials.from_service_account_info(
        creds, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    client = gspread.authorize(credentials)
    worksheet = client.open_by_key(sheet_key).get_worksheet(0)
    df = pd.DataFrame(worksheet.get_all_records())
    df.columns = df.columns.str.strip().str.upper()
    return df

@st.cache_data(show_spinner=False)
def load_academica_data():
    config = st.secrets["academica"]
    token = get_access_token(config)
    site_id = get_site_id(config, token)
    file = download_excel(config, token, site_id)
    return pd.read_excel(file, sheet_name=None)

# === COMPONENTS ===
def render_info_card(title, value1, value2, color="#e3f2fd"):
    return f"""<div style='padding: 8px; background-color: {color}; border-radius: 8px;
        font-size: 13px; text-align: center; border: 1px solid #ccc;
        box-shadow: 1px 1px 5px rgba(0,0,0,0.1);'>
        <strong>{title}</strong><br>
        👥 Matrículas: <strong>{value1}</strong><br>
        💶 Importe: <strong>{value2} €</strong></div>"""

def render_import_card(title, value, color="#ede7f6"):
    return f"""<div style='padding: 8px; background-color: {color}; border-radius: 8px;
        font-size: 13px; text-align: center; border: 1px solid #ccc;
        box-shadow: 1px 1px 5px rgba(0,0,0,0.1);'>
        <strong>{title}</strong><br><strong>{value}</strong></div>"""

# === MAIN PAGE ===
def principal_page():
    st.title("📊 Panel Principal")

    if st.button("🔄 Recargar datos manualmente"):
        st.cache_data.clear()

    VENTAS_FILE = "uploaded_admisiones/ventas.xlsx"
    PREVENTAS_FILE = "uploaded_admisiones/preventas.xlsx"
    GESTION_FILE = "uploaded/archivo_cargado.xlsx"
    SHEET_KEY = "1CPhL56knpvaYZznGF-YgIuHWWCWPtWGpkSgbf88GJFQ"

    df_ventas, df_preventas = load_admisiones(VENTAS_FILE, PREVENTAS_FILE)
    df_gestion = load_gestion_data(GESTION_FILE)
    df_dev = load_google_sheet(SHEET_KEY)
    df_academica_dict = load_academica_data()
    df_academica = df_academica_dict.get("CONSOLIDADO ACADÉMICO", pd.DataFrame())

    mes_actual = datetime.now().month
    anio_actual = datetime.now().year
    nombres_meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    traduccion_meses = {i+1: nombre for i, nombre in enumerate(nombres_meses)}

    # === ADMISIONES ===
    total_matriculas = 0
    matriculas_por_mes = {}
    importes_por_mes = {}
    if df_ventas is not None and not df_ventas.empty:
        df_ventas['fecha de cierre'] = pd.to_datetime(df_ventas['fecha de cierre'], dayfirst=True, errors='coerce')
        df_ventas = df_ventas.dropna(subset=['fecha de cierre'])
        df_ventas = df_ventas[df_ventas['fecha de cierre'].dt.year == anio_actual]
        df_ventas['mes'] = df_ventas['fecha de cierre'].dt.month
        total_matriculas = len(df_ventas)
        for m in range(1, mes_actual + 1):
            df_mes = df_ventas[df_ventas['mes'] == m]
            matriculas_por_mes[m] = len(df_mes)
            importes_por_mes[m] = df_mes.get('importe', pd.Series(0)).sum()

    total_preventas = len(df_preventas) if df_preventas is not None else 0
    total_preventas_importe = 0
    if df_preventas is not None and not df_preventas.empty:
        columnas_importe = [col for col in df_preventas.columns if "importe" in col.lower()]
        if columnas_importe:
            total_preventas_importe = df_preventas[columnas_importe].sum(numeric_only=True).sum()

    st.markdown("## 📥 Admisiones")
    st.markdown(f"### 📅 Matrículas por Mes ({anio_actual})")
    meses = [
        (traduccion_meses[m], matriculas_por_mes.get(m, 0), f"{importes_por_mes.get(m, 0):,.2f}".replace(",", "."))
        for m in range(1, mes_actual + 1)
    ]
    for i in range(0, len(meses), 4):
        cols = st.columns(4)
        for j, (mes, matriculas, importe) in enumerate(meses[i:i+4]):
            cols[j].markdown(render_info_card(mes, matriculas, importe), unsafe_allow_html=True)

    st.markdown("### Total General")
    col1, col2 = st.columns(2)
    col1.markdown(render_info_card("Matrículas Totales", total_matriculas, f"{sum(importes_por_mes.values()):,.2f}".replace(",", "."), "#c8e6c9"), unsafe_allow_html=True)
    col2.markdown(render_info_card("Preventas", total_preventas, f"{total_preventas_importe:,.2f}".replace(",", "."), "#ffe0b2"), unsafe_allow_html=True)

    # === GESTIÓN COBRO HASTA MES ACTUAL ===
    if not df_gestion.empty and "Estado" in df_gestion.columns:
        df_gestion.columns = df_gestion.columns.str.strip()
        df_gestion["Estado"] = df_gestion["Estado"].astype(str).str.strip().str.upper()

        columnas_mes_actual = [f"{mes} {anio_actual}" for mes in nombres_meses[:mes_actual]]
        columnas_validas = [col for col in columnas_mes_actual if col in df_gestion.columns]

        df_gestion[columnas_validas] = df_gestion[columnas_validas].apply(pd.to_numeric, errors='coerce').fillna(0)
        df_filtrado = df_gestion[df_gestion["Estado"] != "TOTAL"].copy()
        df_filtrado["Total Acumulado"] = df_filtrado[columnas_validas].sum(axis=1)

        if not df_filtrado.empty:
            st.markdown("---")
            st.markdown("## 💼 Gestión de Cobro")
            st.markdown(f"### Totales por Estado hasta {nombres_meses[mes_actual - 1].upper()} {anio_actual}")

            estado_items = df_filtrado[["Estado", "Total Acumulado"]].values.tolist()
            for i in range(0, len(estado_items), 4):
                cols = st.columns(4)
                for j, (estado, total) in enumerate(estado_items[i:i+4]):
                    valor_formateado = format_euro(round(total, 2))
                    cols[j].markdown(render_import_card(f"{estado.title()}", valor_formateado), unsafe_allow_html=True)

    # === ACADÉMICA ===
    if not df_academica.empty:
        st.markdown("---")
        st.markdown("## 🎓 Indicadores Académicos")
        try:
            indicadores = [
                ("🧑‍🎓 Alumnos/as", int(df_academica.iloc[1, 1])),
                ("🎯 Éxito académico", f"{df_academica.iloc[2, 2]:.2%}".replace(".", ",")),
                ("🚫 Absentismo", f"{df_academica.iloc[3, 2]:.2%}".replace(".", ",")),
                ("⚠️ Riesgo", f"{df_academica.iloc[4, 2]:.2%}".replace(".", ",")),
                ("📅 Cumpl. Fechas Docente", f"{df_academica.iloc[5, 2]:.0%}".replace(".", ",")),
                ("📅 Cumpl. Fechas Alumnado", f"{df_academica.iloc[6, 2]:.0%}".replace(".", ",")),
                ("📄 Cierre Exp. Académico", f"{df_academica.iloc[7, 2]:.2%}".replace(".", ",")),
                ("😃 Satisfacción Alumnado", f"{df_academica.iloc[8, 2]:.2%}".replace(".", ",")),
                ("⭐ Reseñas", f"{df_academica.iloc[9, 2]:.2%}".replace(".", ",")),
                ("📢 Recomendación Docente", int(df_academica.iloc[10, 2])),
                ("📣 Reclamaciones", int(df_academica.iloc[11, 2]))
            ]
            for i in range(0, len(indicadores), 4):
                cols = st.columns(4)
                for j, (titulo, valor) in enumerate(indicadores[i:i+4]):
                    cols[j].markdown(render_import_card(titulo, valor, "#f0f4c3"), unsafe_allow_html=True)

            st.markdown("### 🏅 Certificaciones")
            total_cert = int(df_academica.iloc[13, 2])
            st.markdown(render_import_card("🎖️ Total Certificaciones", total_cert, "#dcedc8"), unsafe_allow_html=True)
        except Exception as e:
            st.warning("⚠️ Error al procesar los indicadores académicos.")
            st.exception(e)
