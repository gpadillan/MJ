import streamlit as st
import pandas as pd
from datetime import datetime
from pages.admisiones import gestion_datos, ventas_preventas

def app():
    fecha_actual = datetime.now().strftime("%d/%m/%Y")

    st.markdown(f"<h1>📋 Sección: Admisiones <small style='font-size:18px;'>&nbsp;&nbsp;Fecha: {fecha_actual}</small></h1>", unsafe_allow_html=True)

    if 'df_ventas' in st.session_state and st.session_state['df_ventas'] is not None:
        st.success(f"✅ Archivo cargado: archivo_ventas.xlsx")
    
    if 'df_preventas' in st.session_state and st.session_state['df_preventas'] is not None:
        st.success(f"✅ Archivo cargado: archivo_preventas.xlsx")

    st.markdown("Selecciona una subcategoría:")
    subcategoria = st.selectbox(
        "Selecciona una subcategoría:",
        ["Gestión de Datos", "Ventas y Preventas", "Situación Actual", "Leads Generados"],
        label_visibility="collapsed"
    )

    if subcategoria == "Gestión de Datos":
        gestion_datos.app()

    elif subcategoria == "Ventas y Preventas":
        ventas_preventas.app()

    elif subcategoria == "Situación Actual":
        try:
            from pages.admisiones import situacion_2025
            situacion_2025.app()
        except ImportError:
            st.warning("El módulo situacion_2025 no está disponible aún.")
            st.info("Esta sección está en desarrollo.")

    elif subcategoria == "Leads Generados":
        try:
            from pages.admisiones import leads_generados
            leads_generados.app()
        except ImportError:
            st.warning("El módulo leads_generados no está disponible aún.")
            st.info("Esta sección está en desarrollo.")

if __name__ == "__main__":
    app()