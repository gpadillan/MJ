import streamlit as st
import pandas as pd
from pages.academica.sharepoint_utils import get_access_token, get_site_id, download_excel
from pages.academica.consolidado import show_consolidado
from pages.academica.area_tech import show_area_tech
from pages.academica.gestion_corporativa import show_gestion_corporativa

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
        # Lectura robusta del Excel
        excel_data_raw = pd.read_excel(file, sheet_name=None, header=None)

        excel_data = {}
        for sheet_name, df in excel_data_raw.items():
            headers = df.iloc[0].tolist()
            headers = [f"col_{i}" if h == "" else str(h) for i, h in enumerate(headers)]
            headers = pd.io.parsers.ParserBase({'names': headers})._maybe_dedup_names(headers)

            cleaned_df = df[1:]
            cleaned_df.columns = headers
            excel_data[sheet_name] = cleaned_df

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
