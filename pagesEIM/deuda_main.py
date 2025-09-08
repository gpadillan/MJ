# pagesEIM/deuda_main.py

import os
import io
import pytz
import pandas as pd
import streamlit as st
from datetime import datetime

# =========================
# Rutas/constantes EIM
# =========================
UPLOAD_FOLDER_EIM   = "uploaded_eim"
EXCEL_FILENAME_EIM  = "archivo_cargado.xlsx"
TIEMPO_FILENAME_EIM = os.path.join(UPLOAD_FOLDER_EIM, "ultima_subida.txt")


# =========================
# Helpers de persistencia
# =========================
def _guardar_excel_eim(df: pd.DataFrame):
    os.makedirs(UPLOAD_FOLDER_EIM, exist_ok=True)
    ruta = os.path.join(UPLOAD_FOLDER_EIM, EXCEL_FILENAME_EIM)
    df.to_excel(ruta, index=False)

def _guardar_marca_tiempo_eim() -> str:
    os.makedirs(UPLOAD_FOLDER_EIM, exist_ok=True)
    zona = pytz.timezone("Europe/Madrid")
    hora_local = datetime.now(zona).strftime("%d/%m/%Y %H:%M:%S")
    with open(TIEMPO_FILENAME_EIM, "w", encoding="utf-8") as f:
        f.write(hora_local)
    return hora_local

def _cargar_excel_guardado_eim():
    ruta = os.path.join(UPLOAD_FOLDER_EIM, EXCEL_FILENAME_EIM)
    if os.path.exists(ruta):
        return pd.read_excel(ruta, dtype=str)
    return None

def _cargar_marca_tiempo_eim() -> str:
    if os.path.exists(TIEMPO_FILENAME_EIM):
        with open(TIEMPO_FILENAME_EIM, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "Fecha no disponible"


# =========================
# Subpáginas (tus módulos EIM)
# =========================
# Usamos los que ya tienes: gestion_datos, global_, pendiente
from pagesEIM.deuda import (
    gestion_datos as gestion_datos_eim,
    global_       as global_eim,
    pendiente     as pendiente_eim,
)


def deuda_page():
    # Estados de sesión EIM
    if "excel_data_eim" not in st.session_state:
        st.session_state["excel_data_eim"] = None
    if "excel_filename_eim" not in st.session_state:
        st.session_state["excel_filename_eim"] = None
    if "upload_time_eim" not in st.session_state:
        st.session_state["upload_time_eim"] = None

    # Si no hay datos en sesión, intenta cargar del disco
    if st.session_state["excel_data_eim"] is None:
        df_guardado = _cargar_excel_guardado_eim()
        if df_guardado is not None:
            st.session_state["excel_data_eim"]   = df_guardado
            st.session_state["excel_filename_eim"] = EXCEL_FILENAME_EIM
            st.session_state["upload_time_eim"]  = _cargar_marca_tiempo_eim()

    # Cabecera + última actualización
    col1, col2 = st.columns([0.8, 0.2], gap="large")
    with col1:
        st.header("📂 Sección: Gestión de Cobro (EIM)")
    with col2:
        upload_time = st.session_state.get("upload_time_eim", "Fecha no disponible")
        st.markdown(
            f"<div style='margin-top: 25px; font-size: 14px; color: gray;'>"
            f"🕒 Última actualización: {upload_time}"
            f"</div>",
            unsafe_allow_html=True
        )

    # Subida de archivo solo para administradores (igual que en EIP)
    # Asegúrate de setear st.session_state['role'] = "admin" para ver el uploader.
    if st.session_state.get("role") == "admin":
        archivo = st.file_uploader("📤 Sube un archivo Excel (EIM)", type=["xlsx", "xls"], key="uploader_eim")
        if archivo:
            try:
                xls = pd.ExcelFile(archivo, engine="openpyxl")
                df  = pd.read_excel(xls, sheet_name=xls.sheet_names[0], dtype=str)
                hora_local = _guardar_marca_tiempo_eim()

                # Guarda en sesión
                st.session_state["excel_data_eim"]    = df
                st.session_state["excel_filename_eim"] = archivo.name
                st.session_state["upload_time_eim"]   = hora_local

                # Persiste en disco
                _guardar_excel_eim(df)

                st.success(f"✅ Archivo cargado y guardado (EIM): {archivo.name}")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al procesar el archivo EIM: {e}")
    else:
        # Si no es admin, intenta cargar desde el disco si aún no hay datos
        if st.session_state["excel_data_eim"] is None:
            ruta_excel = os.path.join(UPLOAD_FOLDER_EIM, EXCEL_FILENAME_EIM)
            if os.path.exists(ruta_excel):
                with open(ruta_excel, "rb") as f:
                    content = f.read()
                    st.session_state["uploaded_excel_bytes_eim"] = content
                    st.session_state["excel_data_eim"] = pd.read_excel(io.BytesIO(content), dtype=str)
                    st.session_state["upload_time_eim"] = _cargar_marca_tiempo_eim()
            else:
                st.warning("⚠️ El administrador aún no ha subido el archivo (EIM).")
                return

    # Mostrar nombre del archivo cargado
    if st.session_state["excel_data_eim"] is not None:
        st.success(f"📎 Archivo cargado (EIM): {st.session_state['excel_filename_eim']}")

    # Navegación por subcategorías (igual que tu EIM, pero con look&feel de EIP)
    subcategorias = ["Gestión de Datos", "Global", "Pendiente"]

    if "subcategoria_deuda_eim" not in st.session_state:
        st.session_state["subcategoria_deuda_eim"] = subcategorias[0]

    col1, col2 = st.columns([0.85, 0.15])
    with col1:
        seccion = st.selectbox(
            "Selecciona una subcategoría:",
            subcategorias,
            index=subcategorias.index(st.session_state["subcategoria_deuda_eim"]),
            key="subcategoria_deuda_eim"
        )
    with col2:
        if st.session_state.get("role") == "admin":
            if st.button("🗑️", key="trash_reset_eim", help="Eliminar archivo y reiniciar (EIM)"):
                st.session_state["excel_data_eim"]    = None
                st.session_state["excel_filename_eim"] = None
                st.session_state["upload_time_eim"]   = None
                if os.path.exists(os.path.join(UPLOAD_FOLDER_EIM, EXCEL_FILENAME_EIM)):
                    os.remove(os.path.join(UPLOAD_FOLDER_EIM, EXCEL_FILENAME_EIM))
                if os.path.exists(TIEMPO_FILENAME_EIM):
                    os.remove(TIEMPO_FILENAME_EIM)
                st.rerun()

    # Render de subpáginas EIM (llaman a tus módulos)
    if seccion == "Gestión de Datos":
        # Este módulo debería leer st.session_state["excel_data_eim"]
        gestion_datos_eim.render()
    elif seccion == "Global":
        global_eim.render()
    elif seccion == "Pendiente":
        pendiente_eim.render()
