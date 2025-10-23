# pages/deuda_main.py
import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
import io

# Evita SettingWithCopyWarning globalmente
pd.options.mode.copy_on_write = True

# Rutas
UPLOAD_FOLDER = "uploaded"
EXCEL_FILENAME = "archivo_cargado.xlsx"
TIEMPO_FILENAME = os.path.join(UPLOAD_FOLDER, "ultima_subida.txt")

def guardar_excel(df):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    ruta = os.path.join(UPLOAD_FOLDER, EXCEL_FILENAME)
    df.to_excel(ruta, index=False)

def guardar_marca_tiempo():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    zona = pytz.timezone("Europe/Madrid")
    hora_local = datetime.now(zona).strftime("%d/%m/%Y %H:%M:%S")
    with open(TIEMPO_FILENAME, "w") as f:
        f.write(hora_local)
    return hora_local

def cargar_excel_guardado():
    ruta = os.path.join(UPLOAD_FOLDER, EXCEL_FILENAME)
    if os.path.exists(ruta):
        return pd.read_excel(ruta, dtype=str)
    return None

def cargar_marca_tiempo():
    if os.path.exists(TIEMPO_FILENAME):
        with open(TIEMPO_FILENAME, "r") as f:
            return f.read().strip()
    return "Fecha no disponible"

# ===================== IMPORTS DE SUBMÓDULOS (evitar símbolos del paquete) =====================
# Asegúrate de que pages/deuda/__init__.py esté vacío.
from pages.deuda import gestion_datos
from pages.deuda import global_              # módulo con .render()
from pages.deuda import pendiente            # módulo con .render()
from pages.deuda import becas_unificado      # módulo con .render()
from pages.deuda import pendiente_cobro_isa  # módulo con .render()
from pages.deuda import estado_restante      # ✅ NUEVO: Estados restantes (con .render())

# ==============================================================================================

def deuda_page():
    if 'excel_data' not in st.session_state:
        st.session_state['excel_data'] = None
    if 'excel_filename' not in st.session_state:
        st.session_state['excel_filename'] = None
    if 'upload_time' not in st.session_state:
        st.session_state['upload_time'] = None

    if st.session_state['excel_data'] is None:
        df_guardado = cargar_excel_guardado()
        if df_guardado is not None:
            st.session_state['excel_data'] = df_guardado
            st.session_state['excel_filename'] = EXCEL_FILENAME
            st.session_state['upload_time'] = cargar_marca_tiempo()

    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        st.header("📂 Sección: Gestión de Cobro")
    with col2:
        upload_time = st.session_state.get("upload_time", "Fecha no disponible")
        st.markdown(
            f"<div style='margin-top: 25px; font-size: 14px; color: gray;'>🕒 Última actualización: {upload_time}</div>",
            unsafe_allow_html=True
        )

    if st.session_state.get('role') == "admin":
        archivo = st.file_uploader("📤 Sube un archivo Excel", type=["xlsx", "xls"])
        if archivo:
            try:
                xls = pd.ExcelFile(archivo, engine="openpyxl")
                df = pd.read_excel(xls, sheet_name=xls.sheet_names[0], dtype=str)
                hora_local = guardar_marca_tiempo()

                st.session_state['excel_data'] = df
                st.session_state['excel_filename'] = archivo.name
                st.session_state['upload_time'] = hora_local

                guardar_excel(df)

                st.success(f"✅ Archivo cargado y guardado: {archivo.name}")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al procesar el archivo: {e}")
    else:
        if st.session_state.get("excel_data") is None:
            ruta_excel = os.path.join(UPLOAD_FOLDER, EXCEL_FILENAME)
            if os.path.exists(ruta_excel):
                with open(ruta_excel, "rb") as f:
                    content = f.read()
                    st.session_state["uploaded_excel_bytes"] = content
                    st.session_state["excel_data"] = pd.read_excel(io.BytesIO(content), dtype=str)
                    st.session_state["upload_time"] = cargar_marca_tiempo()
            else:
                st.warning("⚠️ El administrador aún no ha subido el archivo.")
                return

    if st.session_state['excel_data'] is not None:
        st.success(f"📎 Archivo cargado: {st.session_state['excel_filename']}")

    subcategorias = [
        "Gestión de Datos",
        "Global",
        "Pendiente Total",
        "Estado restante",           # ✅ NUEVO en el menú
        "Becas ISA - Consolidado",
        "Pendiente Cobro ISA",
    ]

    if "subcategoria_deuda" not in st.session_state:
        st.session_state["subcategoria_deuda"] = subcategorias[0]

    col1, col2 = st.columns([0.85, 0.15])
    with col1:
        seccion = st.selectbox(
            "Selecciona una subcategoría:",
            subcategorias,
            index=subcategorias.index(st.session_state["subcategoria_deuda"]),
            key="subcategoria_deuda"
        )
    with col2:
        if st.session_state.get('role') == "admin":
            if st.button("🗑️", key="trash_reset", help="Eliminar archivo y reiniciar"):
                st.session_state['excel_data'] = None
                st.session_state['excel_filename'] = None
                st.session_state['upload_time'] = None
                if os.path.exists(os.path.join(UPLOAD_FOLDER, EXCEL_FILENAME)):
                    os.remove(os.path.join(UPLOAD_FOLDER, EXCEL_FILENAME))
                if os.path.exists(TIEMPO_FILENAME):
                    os.remove(TIEMPO_FILENAME)
                st.rerun()

    if seccion == "Gestión de Datos":
        gestion_datos.render()
    elif seccion == "Global":
        global_.render()
    elif seccion == "Pendiente Total":
        pendiente.render()
    elif seccion == "Estado restante":          # ✅ Router a la nueva vista
        estado_restante.render()
    elif seccion == "Becas ISA - Consolidado":
        becas_unificado.render()
    elif seccion == "Pendiente Cobro ISA":
        pendiente_cobro_isa.render()
