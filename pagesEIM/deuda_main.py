# pagesEIM/deuda_main.py
import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
import io

# === Rutas compartidas (pon aquí una RUTA DE RED si cada usuario ejecuta su app local) ===
UPLOAD_FOLDER = st.secrets.get("shared_upload_path", "uploaded")  # p.ej. "\\\\SRV\\MainjobsData\\uploaded"
EIM_EXCEL_FILENAME = "archivo_cargado_eim.xlsx"
EIM_TIME_FILENAME  = "ultima_subida_eim.txt"

def _ruta_excel():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    return os.path.join(UPLOAD_FOLDER, EIM_EXCEL_FILENAME)

def _ruta_tiempo():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    return os.path.join(UPLOAD_FOLDER, EIM_TIME_FILENAME)

# Guardar Excel en disco (EIM)
def guardar_excel_eim(df: pd.DataFrame):
    df.to_excel(_ruta_excel(), index=False)

# Guardar marca de tiempo (hora Madrid)
def guardar_marca_tiempo_eim() -> str:
    zona = pytz.timezone("Europe/Madrid")
    hora_local = datetime.now(zona).strftime("%d/%m/%Y %H:%M:%S")
    with open(_ruta_tiempo(), "w", encoding="utf-8") as f:
        f.write(hora_local)
    return hora_local

# Cargar Excel si existe (EIM)
def cargar_excel_guardado_eim() -> pd.DataFrame | None:
    path = _ruta_excel()
    if os.path.exists(path):
        try:
            return pd.read_excel(path, dtype=str)
        except Exception:
            return None
    return None

# Cargar marca de tiempo
def cargar_marca_tiempo_eim() -> str:
    path = _ruta_tiempo()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "Fecha no disponible"

# =================== SUBPÁGINAS ===================
from pagesEIM.deuda import gestion_datos, global_, pendiente, becas_unificado, pendiente_cobro_isa

def deuda_page():
    # Estado de sesión
    st.session_state.setdefault('excel_data_eim', None)
    st.session_state.setdefault('excel_filename_eim', None)
    st.session_state.setdefault('upload_time_eim', None)

    # Si no hay datos en sesión, intenta cargar del disco compartido
    if st.session_state['excel_data_eim'] is None:
        df_guardado = cargar_excel_guardado_eim()
        if df_guardado is not None:
            st.session_state['excel_data_eim'] = df_guardado
            st.session_state['excel_filename_eim'] = EIM_EXCEL_FILENAME
            st.session_state['upload_time_eim'] = cargar_marca_tiempo_eim()

    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        st.header("📂 Sección: Gestión de Cobro (EIM)")
    with col2:
        st.markdown(
            f"<div style='margin-top: 25px; font-size: 14px; color: gray;'>🕒 Última actualización: {st.session_state.get('upload_time_eim','Fecha no disponible')}</div>",
            unsafe_allow_html=True
        )

    # Subida solo admin
    if st.session_state.get('role', 'viewer') == "admin":
        archivo = st.file_uploader("📤 Sube un archivo Excel (EIM)", type=["xlsx", "xls"], key="eim_uploader")
        if archivo:
            try:
                xls = pd.ExcelFile(archivo, engine="openpyxl")
                df = pd.read_excel(xls, sheet_name=xls.sheet_names[0], dtype=str)

                # Guarda en disco compartido + marca de tiempo
                guardar_excel_eim(df)
                hora_local = guardar_marca_tiempo_eim()

                # Guarda en sesión
                st.session_state['excel_data_eim'] = df
                st.session_state['excel_filename_eim'] = archivo.name
                st.session_state['upload_time_eim'] = hora_local

                st.success(f"✅ Archivo EIM cargado y guardado: {archivo.name}")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al procesar el archivo: {e}")
    else:
        # Vista no admin: garantiza lectura del fichero compartido
        if st.session_state['excel_data_eim'] is None:
            df_guardado = cargar_excel_guardado_eim()
            if df_guardado is not None:
                st.session_state['excel_data_eim'] = df_guardado
                st.session_state['excel_filename_eim'] = EIM_EXCEL_FILENAME
                st.session_state['upload_time_eim'] = cargar_marca_tiempo_eim()
            else:
                st.warning("⚠️ El administrador aún no ha subido el archivo de EIM.")
                return

    # Aviso nombre de archivo
    if st.session_state['excel_data_eim'] is not None:
        st.success(f"📎 Archivo cargado (EIM): {st.session_state['excel_filename_eim']}")

    # Navegación (igual que antes)
    subcategorias = [
        "Gestión de Datos",
        "Global",
        "Pendiente Total",
        "Becas ISA - Consolidado",
        "Pendiente Cobro ISA",
    ]
    st.session_state.setdefault("subcategoria_deuda_eim", subcategorias[0])

    seccion = st.selectbox(
        "Selecciona una subcategoría:",
        subcategorias,
        index=subcategorias.index(st.session_state["subcategoria_deuda_eim"]),
        key="subcategoria_deuda_eim"
    )

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
