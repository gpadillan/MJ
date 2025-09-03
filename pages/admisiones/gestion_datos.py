import streamlit as st
import os
import pandas as pd
from datetime import datetime
import pytz

# Carpetas y archivos
UPLOAD_FOLDER = "uploaded_admisiones"
VENTAS_FILE = os.path.join(UPLOAD_FOLDER, "ventas.xlsx")
PREVENTAS_FILE = os.path.join(UPLOAD_FOLDER, "preventas.xlsx")
PVFE_FILE = os.path.join(UPLOAD_FOLDER, "pv_fe.xlsx")          # <<--- NUEVO
SITUACION_FILE = os.path.join(UPLOAD_FOLDER, "matricula_programas_25.xlsx")
LEADS_GENERADOS_FILE = os.path.join(UPLOAD_FOLDER, "leads_generados.xlsx")
METADATA_FILE = os.path.join(UPLOAD_FOLDER, "metadata.txt")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

def app():
    st.header("📁 Gestión de Datos: Admisiones")
    upload_time = cargar_metadata()
    st.markdown(f"🕒 **Última actualización:** `{upload_time}`")

    if st.session_state.get("role") == "admin":
        st.markdown("### 📤 Subir archivos Excel")

        # Ahora 3 columnas: Ventas, Preventas, PV-FE
        col1, col2, col3 = st.columns(3)

        with col1:
            archivo_ventas = st.file_uploader("Ventas", type=["xlsx"], key="ventas")
            if archivo_ventas:
                guardar_archivo(archivo_ventas, VENTAS_FILE)
                st.success("✅ Archivo de ventas subido correctamente.")
                st.rerun()

        with col2:
            archivo_preventas = st.file_uploader("Preventas", type=["xlsx"], key="preventas")
            if archivo_preventas:
                guardar_archivo(archivo_preventas, PREVENTAS_FILE)
                st.success("✅ Archivo de preventas subido correctamente.")
                st.rerun()

        with col3:
            archivo_pvfe = st.file_uploader("PV-FE", type=["xlsx"], key="pv_fe")
            if archivo_pvfe:
                guardar_archivo(archivo_pvfe, PVFE_FILE)
                st.success("✅ Archivo PV-FE subido correctamente.")
                st.rerun()

        st.markdown("### ➕ Subida archivo para Situación 2025")
        archivo_situacion = st.file_uploader("Situación 2025 (matricula_programas_25.xlsx)", type=["xlsx"], key="situacion")
        if archivo_situacion:
            guardar_archivo(archivo_situacion, SITUACION_FILE)
            st.success("✅ Archivo de situación 2025 subido correctamente.")
            st.rerun()

        st.markdown("### ➕ Subir archivo de Leads Generados")
        archivo_leads = st.file_uploader("Leads Generados (leads_generados.xlsx)", type=["xlsx"], key="leads_generados")
        if archivo_leads:
            guardar_archivo(archivo_leads, LEADS_GENERADOS_FILE)
            st.success("✅ Archivo de leads generados subido correctamente.")
            st.rerun()

    st.markdown("### 📄 Archivos actuales")

    # Vista previa en 3 columnas para mantener simetría con la subida
    col1, col2, col3 = st.columns(3)

    with col1:
        if os.path.exists(VENTAS_FILE):
            st.markdown("**Ventas.xlsx**")
            st.dataframe(pd.read_excel(VENTAS_FILE), use_container_width=True)
            if st.session_state.get("role") == "admin":
                if st.button("🗑️ Eliminar Ventas", key="del_ventas"):
                    eliminar_archivo(VENTAS_FILE)
                    st.rerun()
        else:
            st.info("📭 No hay archivo de ventas")

    with col2:
        if os.path.exists(PREVENTAS_FILE):
            st.markdown("**Preventas.xlsx**")
            st.dataframe(pd.read_excel(PREVENTAS_FILE), use_container_width=True)
            if st.session_state.get("role") == "admin":
                if st.button("🗑️ Eliminar Preventas", key="del_preventas"):
                    eliminar_archivo(PREVENTAS_FILE)
                    st.rerun()
        else:
            st.info("📭 No hay archivo de preventas")

    with col3:
        if os.path.exists(PVFE_FILE):
            st.markdown("**PV-FE.xlsx**")
            st.dataframe(pd.read_excel(PVFE_FILE), use_container_width=True)
            if st.session_state.get("role") == "admin":
                if st.button("🗑️ Eliminar PV-FE", key="del_pvfe"):
                    eliminar_archivo(PVFE_FILE)
                    st.rerun()
        else:
            st.info("📭 No hay archivo PV-FE")

    st.markdown("---")
    st.markdown("### 🗂️ Archivo de Situación 2025")
    if os.path.exists(SITUACION_FILE):
        st.dataframe(pd.read_excel(SITUACION_FILE), use_container_width=True)
        if st.session_state.get("role") == "admin":
            if st.button("🗑️ Eliminar Situación 2025", key="del_situacion"):
                eliminar_archivo(SITUACION_FILE)
                st.rerun()
    else:
        st.info("📭 No hay archivo de situación 2025")

    st.markdown("### 🗂️ Archivo de Leads Generados")
    if os.path.exists(LEADS_GENERADOS_FILE):
        st.dataframe(pd.read_excel(LEADS_GENERADOS_FILE), use_container_width=True)
        if st.session_state.get("role") == "admin":
            if st.button("🗑️ Eliminar Leads Generados", key="del_leads_generados"):
                eliminar_archivo(LEADS_GENERADOS_FILE)
                st.rerun()
    else:
        st.info("📭 No hay archivo de leads generados")
