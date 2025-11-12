# pagesEIM/gestion_datos.py
# -*- coding: utf-8 -*-
import streamlit as st
import os
import pandas as pd
from datetime import datetime
import pytz

# =========================
# 📂 Carpetas y archivos (EIM)
# =========================
UPLOAD_FOLDER = "uploaded_eim"                             # <- carpeta propia EIM

VENTAS_FILE = os.path.join(UPLOAD_FOLDER, "ventas_eim.xlsx")
PREVENTAS_FILE = os.path.join(UPLOAD_FOLDER, "preventas_eim.xlsx")
PVFE_FILE = os.path.join(UPLOAD_FOLDER, "pv_fe_eim.xlsx")
SITUACION_FILE = os.path.join(UPLOAD_FOLDER, "situacion_eim_2025.xlsx")
LEADS_GENERADOS_FILE = os.path.join(UPLOAD_FOLDER, "leads_generados_eim.xlsx")
METADATA_FILE = os.path.join(UPLOAD_FOLDER, "metadata_eim.txt")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================
# 💾 Utilidades de guardado
# =========================
def guardar_archivo(archivo, ruta):
    with open(ruta, "wb") as f:
        f.write(archivo.read())
    guardar_metadata()

def guardar_metadata():
    zona = pytz.timezone("Europe/Madrid")
    hora_local = datetime.now(zona).strftime("%d/%m/%Y %H:%M:%S")
    with open(METADATA_FILE, "w") as f:
        f.write(hora_local)

def cargar_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, "r") as f:
            return f.read()
    return "No disponible"

def eliminar_archivo(ruta):
    if os.path.exists(ruta):
        os.remove(ruta)

# =========================
# 🚀 Página
# =========================
def app():
    st.header("📁 Gestión de Datos: EIM")
    upload_time = cargar_metadata()
    st.markdown(f"🕒 **Última actualización:** `{upload_time}`")

    # Solo admin puede subir/borrar
    if st.session_state.get("role") == "admin":
        st.markdown("### 📤 Subir archivos Excel")

        # Tres columnas: Ventas, Preventas, PV-FE
        col1, col2, col3 = st.columns(3)

        with col1:
            archivo_ventas = st.file_uploader("Ventas (EIM)", type=["xlsx"], key="ventas_eim")
            if archivo_ventas:
                guardar_archivo(archivo_ventas, VENTAS_FILE)
                st.success("✅ Archivo de ventas (EIM) subido correctamente.")
                st.rerun()

        with col2:
            archivo_preventas = st.file_uploader("Preventas (EIM)", type=["xlsx"], key="preventas_eim")
            if archivo_preventas:
                guardar_archivo(archivo_preventas, PREVENTAS_FILE)
                st.success("✅ Archivo de preventas (EIM) subido correctamente.")
                st.rerun()

        with col3:
            archivo_pvfe = st.file_uploader("PV-FE (EIM)", type=["xlsx"], key="pv_fe_eim")
            if archivo_pvfe:
                guardar_archivo(archivo_pvfe, PVFE_FILE)
                st.success("✅ Archivo PV-FE (EIM) subido correctamente.")
                st.rerun()

        st.markdown("### ➕ Subida archivo para Situación 2025 (EIM)")
        archivo_situacion = st.file_uploader("Situación 2025 (EIM)", type=["xlsx"], key="situacion_eim")
        if archivo_situacion:
            guardar_archivo(archivo_situacion, SITUACION_FILE)
            st.success("✅ Archivo de situación 2025 (EIM) subido correctamente.")
            st.rerun()

        st.markdown("### ➕ Subir archivo de Leads Generados (EIM)")
        archivo_leads = st.file_uploader("Leads Generados (EIM)", type=["xlsx"], key="leads_generados_eim")
        if archivo_leads:
            guardar_archivo(archivo_leads, LEADS_GENERADOS_FILE)
            st.success("✅ Archivo de leads generados (EIM) subido correctamente.")
            st.rerun()

    # =========================
    # 👀 Archivos actuales
    # =========================
    st.markdown("### 📄 Archivos actuales")
    col1, col2, col3 = st.columns(3)

    # Ventas
    with col1:
        if os.path.exists(VENTAS_FILE):
            st.markdown("**ventas_eim.xlsx**")
            st.dataframe(pd.read_excel(VENTAS_FILE), use_container_width=True)
            if st.session_state.get("role") == "admin":
                if st.button("🗑️ Eliminar Ventas (EIM)", key="del_ventas_eim"):
                    eliminar_archivo(VENTAS_FILE)
                    st.rerun()
        else:
            st.info("📭 No hay archivo de ventas (EIM)")

    # Preventas
    with col2:
        if os.path.exists(PREVENTAS_FILE):
            st.markdown("**preventas_eim.xlsx**")
            st.dataframe(pd.read_excel(PREVENTAS_FILE), use_container_width=True)
            if st.session_state.get("role") == "admin":
                if st.button("🗑️ Eliminar Preventas (EIM)", key="del_preventas_eim"):
                    eliminar_archivo(PREVENTAS_FILE)
                    st.rerun()
        else:
            st.info("📭 No hay archivo de preventas (EIM)")

    # PV-FE
    with col3:
        if os.path.exists(PVFE_FILE):
            st.markdown("**pv_fe_eim.xlsx**")
            st.dataframe(pd.read_excel(PVFE_FILE), use_container_width=True)
            if st.session_state.get("role") == "admin":
                if st.button("🗑️ Eliminar PV-FE (EIM)", key="del_pvfe_eim"):
                    eliminar_archivo(PVFE_FILE)
                    st.rerun()
        else:
            st.info("📭 No hay archivo PV-FE (EIM)")

    st.markdown("---")

    # Situación 2025
    st.markdown("### 🗂️ Archivo de Situación 2025 (EIM)")
    if os.path.exists(SITUACION_FILE):
        st.dataframe(pd.read_excel(SITUACION_FILE), use_container_width=True)
        if st.session_state.get("role") == "admin":
            if st.button("🗑️ Eliminar Situación 2025 (EIM)", key="del_situacion_eim"):
                eliminar_archivo(SITUACION_FILE)
                st.rerun()
    else:
        st.info("📭 No hay archivo de situación 2025 (EIM)")

    # Leads Generados
    st.markdown("### 🗂️ Archivo de Leads Generados (EIM)")
    if os.path.exists(LEADS_GENERADOS_FILE):
        st.dataframe(pd.read_excel(LEADS_GENERADOS_FILE), use_container_width=True)
        if st.session_state.get("role") == "admin":
            if st.button("🗑️ Eliminar Leads Generados (EIM)", key="del_leads_generados_eim"):
                eliminar_archivo(LEADS_GENERADOS_FILE)
                st.rerun()
    else:
        st.info("📭 No hay archivo de leads generados (EIM)")
