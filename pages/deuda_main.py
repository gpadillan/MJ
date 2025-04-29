import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Carpeta de subida
UPLOAD_FOLDER = "uploaded"
EXCEL_FILENAME = "archivo_cargado.xlsx"
TIEMPO_FILENAME = os.path.join(UPLOAD_FOLDER, "ultima_subida.txt")

# Función para guardar el Excel
def guardar_excel(df):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    ruta = os.path.join(UPLOAD_FOLDER, EXCEL_FILENAME)
    df.to_excel(ruta, index=False)

# Función para guardar la fecha/hora de subida
def guardar_marca_tiempo(fecha_str):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    with open(TIEMPO_FILENAME, "w") as f:
        f.write(fecha_str)

# Función para cargar el Excel desde disco
def cargar_excel_guardado():
    ruta = os.path.join(UPLOAD_FOLDER, EXCEL_FILENAME)
    if os.path.exists(ruta):
        return pd.read_excel(ruta)
    return None

# Función para cargar la fecha/hora desde disco
def cargar_marca_tiempo():
    if os.path.exists(TIEMPO_FILENAME):
        with open(TIEMPO_FILENAME, "r") as f:
            return f.read().strip()
    return None

# Importar submódulos
from pages.deuda import (
    gestion_datos,
    global_,
    año_2025,
    becas_isa,
    becas_isa_mes,
    becas_isa_26_27_28,
    pendiente_clientes
)

def deuda_page():
    # Inicializar estado si falta
    if 'excel_data' not in st.session_state:
        st.session_state['excel_data'] = None
    if 'excel_filename' not in st.session_state:
        st.session_state['excel_filename'] = None
    if 'upload_time' not in st.session_state:
        st.session_state['upload_time'] = None

    # Cargar desde disco si es necesario
    if st.session_state['excel_data'] is None or st.session_state['upload_time'] is None:
        df_guardado = cargar_excel_guardado()
        if df_guardado is not None:
            st.session_state['excel_data'] = df_guardado
            st.session_state['excel_filename'] = EXCEL_FILENAME
            st.session_state['upload_time'] = cargar_marca_tiempo() or "Fecha no disponible"

    # Mostrar encabezado
    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        st.header("📂 Sección: Deuda")
    with col2:
        if st.session_state.get("upload_time"):
            st.markdown(
                f"<div style='margin-top: 25px; font-size: 14px; color: gray;'>🕒 {st.session_state['upload_time']}<br><small>Última actualización por administrador</small></div>",
                unsafe_allow_html=True
            )

    # Si no hay Excel aún, mostrar opciones
    if st.session_state['excel_data'] is None:
        if st.session_state['role'] == "admin":
            archivo = st.file_uploader("📤 Sube un archivo Excel", type=["xlsx", "xls"])
            if archivo:
                try:
                    xls = pd.ExcelFile(archivo)
                    df = pd.read_excel(xls, sheet_name=xls.sheet_names[0])
                    st.session_state['excel_data'] = df
                    st.session_state['excel_filename'] = archivo.name
                    st.session_state['upload_time'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    guardar_excel(df)
                    guardar_marca_tiempo(st.session_state['upload_time'])
                    st.success(f"✅ Archivo cargado y guardado: {archivo.name}")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al procesar el archivo: {e}")
        else:
            st.warning("⚠️ El administrador aún no ha subido el archivo.")
        return

    # Mostrar confirmación
    st.success(f"📎 Archivo cargado: {st.session_state['excel_filename']}")

    # Subcategorías y papelera para admin
    col1, col2 = st.columns([0.85, 0.15])
    with col1:
        seccion = st.selectbox("Selecciona una subcategoría:", [
            "Gestión de Datos",
            "Global",
            "Pendiente por Año",
            "Becas ISA - Año",
            "Becas ISA-mes",
            "Becas ISA Futuro",
            "Pendiente Clientes"
        ])
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

    # Enrutamiento
    if seccion == "Gestión de Datos":
        gestion_datos.render()
    elif seccion == "Global":
        global_.render()
    elif seccion == "Pendiente por Año":
        año_2025.render()
    elif seccion == "Becas ISA - Año":
        becas_isa.render()
    elif seccion == "Becas ISA-mes":
        becas_isa_mes.render()
    elif seccion == "Becas ISA Futuro":
        becas_isa_26_27_28.render()
    elif seccion == "Pendiente Clientes":
        pendiente_clientes.render()
