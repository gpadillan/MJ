import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io

# Rutas
UPLOAD_FOLDER = "uploaded"
EXCEL_FILENAME = "archivo_cargado.xlsx"
TIEMPO_FILENAME = os.path.join(UPLOAD_FOLDER, "ultima_subida.txt")

# Guardar Excel en disco
def guardar_excel(df):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    ruta = os.path.join(UPLOAD_FOLDER, EXCEL_FILENAME)
    df.to_excel(ruta, index=False)

# Guardar la fecha de carga
def guardar_marca_tiempo(fecha_str):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    with open(TIEMPO_FILENAME, "w") as f:
        f.write(fecha_str)

# Cargar Excel si existe
def cargar_excel_guardado():
    ruta = os.path.join(UPLOAD_FOLDER, EXCEL_FILENAME)
    if os.path.exists(ruta):
        return pd.read_excel(ruta, dtype=str)
    return None

# Cargar fecha/hora si existe
def cargar_marca_tiempo():
    if os.path.exists(TIEMPO_FILENAME):
        with open(TIEMPO_FILENAME, "r") as f:
            return f.read().strip()
    return None

# Importar subpáginas actualizadas
from pages.deuda import (
    gestion_datos,
    global_,
    pendiente,
    becas_unificado,
    pendiente_cobro_isa
)

def deuda_page():
    if 'excel_data' not in st.session_state:
        st.session_state['excel_data'] = None
    if 'excel_filename' not in st.session_state:
        st.session_state['excel_filename'] = None
    if 'upload_time' not in st.session_state:
        st.session_state['upload_time'] = None

    # Cargar desde disco si no hay datos en sesión
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

    # Subida de archivo solo para administradores
    if st.session_state['role'] == "admin":
        archivo = st.file_uploader("📤 Sube un archivo Excel", type=["xlsx", "xls"])
        if archivo:
            try:
                xls = pd.ExcelFile(archivo)
                df = pd.read_excel(xls, sheet_name=xls.sheet_names[0], dtype=str)
                upload_time_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

                # Guardar en sesión
                st.session_state['excel_data'] = df
                st.session_state['excel_filename'] = archivo.name
                st.session_state['upload_time'] = upload_time_str

                # Guardar en disco
                guardar_excel(df)
                guardar_marca_tiempo(upload_time_str)

                st.success(f"✅ Archivo cargado y guardado: {archivo.name}")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al procesar el archivo: {e}")
    else:
        # Para no admin, intenta cargar desde disco si session_state no tiene nada
        if (
            "excel_data" not in st.session_state
            or st.session_state['excel_data'] is None
        ):
            ruta_excel = os.path.join(UPLOAD_FOLDER, EXCEL_FILENAME)
            if os.path.exists(ruta_excel):
                with open(ruta_excel, "rb") as f:
                    content = f.read()
                    st.session_state["uploaded_excel_bytes"] = content
                    st.session_state["excel_data"] = pd.read_excel(io.BytesIO(content), dtype=str)
            else:
                st.warning("⚠️ El administrador aún no ha subido el archivo.")
                return

    # Mostrar nombre del archivo cargado
    if st.session_state['excel_data'] is not None:
        st.success(f"📎 Archivo cargado: {st.session_state['excel_filename']}")

    # Subcategorías de navegación
    subcategorias = [
        "Gestión de Datos",
        "Global",
        "Pendiente Total",
        "Becas ISA - Consolidado",
        "Pendiente Cobro ISA"
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
        if st.session_state['role'] == "admin":
            if st.button("🗑️", key="trash_reset", help="Eliminar archivo y reiniciar"):
                st.session_state['excel_data'] = None
                st.session_state['excel_filename'] = None
                st.session_state['upload_time'] = None
                if os.path.exists(os.path.join(UPLOAD_FOLDER, EXCEL_FILENAME)):
                    os.remove(os.path.join(UPLOAD_FOLDER, EXCEL_FILENAME))
                if os.path.exists(TIEMPO_FILENAME):
                    os.remove(TIEMPO_FILENAME)
                st.rerun()

    # Navegación por subcategorías
    if seccion == "Gestión de Datos":
        gestion_datos.render()
    elif seccion == "Global":
        global_.render()
    elif seccion == "Pendiente Total":
        pendiente.render()
    elif seccion == "Becas ISA - Consolidado":
        becas_unificado.render()
    elif seccion == "Pendiente Cobro ISA":
        pendiente_cobro_isa.render()
