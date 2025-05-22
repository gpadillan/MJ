import streamlit as st
import pandas as pd
import os

# Rutas
UPLOAD_FOLDER = "uploaded"
EXCEL_FILENAME = "archivo_cargado.xlsx"
TIEMPO_FILENAME = os.path.join(UPLOAD_FOLDER, "ultima_subida.txt")

# Cargar desde disco (solo si no hay nada en memoria)
def cargar_excel_guardado():
    ruta = os.path.join(UPLOAD_FOLDER, EXCEL_FILENAME)
    if os.path.exists(ruta):
        return pd.read_excel(ruta)
    return None

def cargar_marca_tiempo():
    if os.path.exists(TIEMPO_FILENAME):
        with open(TIEMPO_FILENAME, "r") as f:
            return f.read().strip()
    return None

# Importar subpáginas
from pages.deuda import (
    gestion_datos,
    global_,
    año_2025,
    becas_isa,
    becas_isa_mes,
    becas_isa_26_27_28,
    pendiente_clientes,
    pendiente_cobro_isa
)

def deuda_page():
    # Inicializar claves en session_state si no existen
    st.session_state.setdefault('excel_data', None)
    st.session_state.setdefault('excel_filename', None)
    st.session_state.setdefault('upload_time', None)

    # Cargar desde disco solo si no hay datos en memoria ni archivo subido
    if (
        st.session_state['excel_data'] is None
        and st.session_state.get("uploaded_excel_bytes") is None
    ):
        df_guardado = cargar_excel_guardado()
        if df_guardado is not None:
            st.session_state['excel_data'] = df_guardado
            st.session_state['excel_filename'] = EXCEL_FILENAME
            st.session_state['upload_time'] = cargar_marca_tiempo()

    # Cabecera de la sección
    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        st.header("📂 Sección: Gestión de Cobro")
    with col2:
        upload_time = st.session_state.get("upload_time", "Fecha no disponible")
        st.markdown(
            f"<div style='margin-top: 25px; font-size: 14px; color: gray;'>🕒 Última actualización: {upload_time}</div>",
            unsafe_allow_html=True
        )

    # Si el usuario no es admin y no hay archivo cargado
    if st.session_state['role'] != "admin" and st.session_state['excel_data'] is None:
        st.warning("⚠️ El administrador aún no ha subido el archivo.")
        return

    # Mostrar nombre del archivo si ya está cargado
    if st.session_state['excel_data'] is not None:
        st.success(f"📎 Archivo cargado: {st.session_state.get('excel_filename', 'No disponible')}")

    # Selector de subcategorías
    subcategorias = [
        "Gestión de Datos",
        "Global",
        "Pendiente por años y meses año actual",
        "Becas ISA - Total Años",
        "Becas ISA - Año actual",
        "Becas ISA Futuro",
        "Pendiente Clientes",
        "Pendiente Cobro ISA"
    ]

    st.session_state.setdefault("subcategoria_deuda", subcategorias[0])

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
                st.session_state['uploaded_excel_bytes'] = None
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
    elif seccion == "Pendiente por años y meses año actual":
        año_2025.render()
    elif seccion == "Becas ISA - Total Años":
        becas_isa.render()
    elif seccion == "Becas ISA - Año actual":
        becas_isa_mes.render()
    elif seccion == "Becas ISA Futuro":
        becas_isa_26_27_28.render()
    elif seccion == "Pendiente Clientes":
        pendiente_clientes.render()
    elif seccion == "Pendiente Cobro ISA":
        pendiente_cobro_isa.render()
