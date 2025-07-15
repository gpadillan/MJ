import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
from datetime import datetime

# ✅ FUNCIÓN PARA CARGAR GOOGLE SHEET CON CACHÉ Y LIMPIEZA DE ENCABEZADOS
@st.cache_data
def cargar_google_sheet():
    try:
        creds = st.secrets["google_service_account"]
        credentials = service_account.Credentials.from_service_account_info(
            creds,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        client = gspread.authorize(credentials)
        sheet = client.open_by_key("1CPhL56knpvaYZznGF-YgIuHWWCWPtWGpkSgbf88GJFQ")
        worksheet = sheet.get_worksheet(0)

        # ✅ Obtener todos los valores y limpiar encabezados
        values = worksheet.get_all_values()
        headers = [col.strip() for col in values[0]]
        df = pd.DataFrame(values[1:], columns=headers)

        # ✅ Detectar y eliminar columnas duplicadas
        duplicadas = df.columns[df.columns.duplicated()]
        if not duplicadas.empty:
            st.warning(f"⚠️ Columnas duplicadas detectadas y eliminadas: {duplicadas.tolist()}")
            df = df.loc[:, ~df.columns.duplicated()]

        return df

    except Exception as e:
        st.error(f"❌ Error al cargar los datos: {e}")
        return None

# ✅ FUNCIÓN PRINCIPAL DE LA PÁGINA
def desarrollo_page():
    fecha_actual = datetime.today().strftime("%d/%m/%Y")

    if st.button("🔄 Recargar datos desde Google Sheets"):
        st.cache_data.clear()
        st.rerun()

    st.markdown(
        f"<h1>🚀 Área Desarrollo Profesional <span style='font-size:18px; color: gray;'>🗓️ {fecha_actual}</span></h1>",
        unsafe_allow_html=True
    )

    df = cargar_google_sheet()

    if df is None or df.empty:
        st.warning("⚠️ No se pudieron cargar los datos del documento.")
        return

    st.success("✅ Datos cargados correctamente desde Google Sheets.")

    subcategorias = [
        "Principal",
        "Riesgo económico",
        "Cierre expediente total"
    ]

    seleccion = st.selectbox("Selecciona una subcategoría:", subcategorias)

    if seleccion == "Principal":
        from pages.desarrollo import principal
        principal.render(df)
    elif seleccion == "Riesgo económico":
        from pages.desarrollo import riesgo_economico
        riesgo_economico.render(df)
    elif seleccion == "Cierre expediente total":
        from pages.desarrollo import cierre_expediente_total
        cierre_expediente_total.render(df)
