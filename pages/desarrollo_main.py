import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

@st.cache_data
def cargar_google_sheet():
    SERVICE_ACCOUNT_FILE = "credenciales.json"
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly"
    ]

    try:
        credentials = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES
        )
        client = gspread.authorize(credentials)
        sheet = client.open_by_key("1CPhL56knpvaYZznGF-YgIuHWWCWPtWGpkSgbf88GJFQ")
        worksheet = sheet.get_worksheet(0)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"❌ Error al cargar los datos: {e}")
        return None

def desarrollo_page():
    st.title("🚀 Área Desarrollo Profesional")

    df = cargar_google_sheet()

    if df is None or df.empty:
        st.warning("⚠️ No se pudieron cargar los datos del documento.")
        return

    st.success("✅ Datos cargados correctamente desde Google Sheets.")

    subcategorias = [
        "Principal",
        "Total alumnado consultor",
        "Riesgo económico",
        "Alumnado riesgo consultor",
        "Cierre expediente 2025",
        "Cierre expediente total",
        "Inserciones / empresa",
        "Objetivos %"
    ]

    seleccion = st.selectbox("Selecciona una subcategoría:", subcategorias)

    if seleccion == "Principal":
        from pages.desarrollo import principal
        principal.render(df)

    elif seleccion == "Total alumnado consultor":
        from pages.desarrollo import total_alumnado_consultor
        total_alumnado_consultor.render(df)

    elif seleccion == "Riesgo económico":
        from pages.desarrollo import riesgo_economico
        riesgo_economico.render(df)

    elif seleccion == "Alumnado riesgo consultor":
        from pages.desarrollo import alumnado_riesgo_consultor
        alumnado_riesgo_consultor.render(df)

    elif seleccion == "Cierre expediente 2025":
        from pages.desarrollo import cierre_expediente_2025
        cierre_expediente_2025.render(df)

    elif seleccion == "Cierre expediente total":
        from pages.desarrollo import cierre_expediente_total
        cierre_expediente_total.render(df)

    elif seleccion == "Inserciones / empresa":
        from pages.desarrollo import inserciones_empresa
        inserciones_empresa.render(df)

    elif seleccion == "Objetivos %":
        from pages.desarrollo import objetivos_porcentaje
        objetivos_porcentaje.render(df)
