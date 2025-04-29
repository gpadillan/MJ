import streamlit as st
import pandas as pd

def render():
    st.subheader("📑 Vista completa de Excel")

    if 'excel_data' not in st.session_state or st.session_state['excel_data'] is None:
        st.warning("⚠️ No hay archivo cargado. Por favor, ve a la sección Deuda y sube un archivo.")
        return

    df = st.session_state['excel_data']

    # Vista previa del archivo Excel completo
    st.dataframe(df, use_container_width=True)
