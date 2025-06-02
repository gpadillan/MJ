import streamlit as st
import pandas as pd
from pages.academica.sharepoint_utils import get_access_token, get_site_id, download_excel
from pages.academica.consolidado import show_consolidado
from pages.academica.area_tech import show_area_tech
from pages.academica.gestion_corporativa import show_gestion_corporativa

def deduplicate_headers(headers):
    seen = {}
    result = []
    for h in headers:
        key = h if h else "Unnamed"
        count = seen.get(key, 0)
        new_key = key if count == 0 else f"{key}.{count}"
        result.append(new_key)
        seen[key] = count + 1
    return result

def academica_page():
    st.title("📚 Indicadores Académicos - EIP")

    if st.button("🔄 Actualizar datos"):
        st.session_state["academica_opcion"] = "Consolidado Académico"
        st.rerun()

    config = st.secrets["academica"]
    token = get_access_token(config)
    if not token:
        st.error("❌ Error obteniendo token.")
        return

    site_id = get_site_id(config, token)
    if not site_id:
        st.error("❌ Error obteniendo site_id.")
        return

    file = download_excel(config, token, site_id)
    if not file:
        st.error("❌ No se pudo descargar el Excel.")
        return

    try:
        # Leer todas las hojas como dataframes
        excel_data = {}
        all_sheets = pd.read_excel(file, sheet_name=None, header=None)

        for sheet_name, df in all_sheets.items():
            headers = deduplicate_headers(df.iloc[0].tolist())
            df_cleaned = df[1:].copy()
            df_cleaned.columns = headers
            excel_data[sheet_name] = df_cleaned

        # Inicializar subcategoría si no está
        if "academica_opcion" not in st.session_state:
            st.session_state["academica_opcion"] = "Consolidado Académico"

        opcion = st.radio(
            "Selecciona una subcategoría académica:",
            ("Consolidado Académico", "Área TECH", "Área Gestión Corporativa"),
            key="academica_opcion"
        )

        if opcion == "Consolidado Académico":
            show_consolidado(excel_data)
        elif opcion == "Área TECH":
            show_area_tech(excel_data)
        elif opcion == "Área Gestión Corporativa":
            show_gestion_corporativa(excel_data)

    except Exception as e:
        st.error("❌ Error leyendo el archivo Excel.")
        st.exception(e)
