# pagesEIM/admisiones/main_admisiones.py
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import datetime

# Importa las subpáginas de Admisiones (EIM)
from pagesEIM.admisiones import gestion_datos, ventas_preventas

def app():
    fecha_actual = datetime.now().strftime("%d/%m/%Y")

    st.markdown(
        f"<h1>📋 Sección: Admisiones · EIM "
        f"<small style='font-size:18px;'>&nbsp;&nbsp;Fecha: {fecha_actual}</small></h1>",
        unsafe_allow_html=True
    )

    # ✅ Solo mostramos si existen los DataFrames, sin errores si faltan
    df_ventas_eim = st.session_state.get("df_ventas_eim")
    df_preventas_eim = st.session_state.get("df_preventas_eim")
    df_pvfe_eim = st.session_state.get("df_pvfe_eim")

    if df_ventas_eim is not None:
        st.success("✅ Archivo cargado: ventas_eim.xlsx")
    if df_preventas_eim is not None:
        st.success("✅ Archivo cargado: preventas_eim.xlsx")
    if df_pvfe_eim is not None:
        st.success("✅ Archivo cargado: pv_fe_eim.xlsx")

    # Selección de subcategoría
    st.markdown("Selecciona una subcategoría:")
    subcategoria = st.selectbox(
        "Selecciona una subcategoría:",
        ["Gestión de Datos", "Ventas y Preventas"],
        label_visibility="collapsed"
    )

    # Enrutamiento según selección
    if subcategoria == "Gestión de Datos":
        gestion_datos.app()

    elif subcategoria == "Ventas y Preventas":
        ventas_preventas.app()

if __name__ == "__main__":
    app()
