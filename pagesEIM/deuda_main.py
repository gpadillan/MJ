# pagesEIM/deuda_main.py
import os
import io
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytz
import streamlit as st

# ====== Rutas compartidas (puedes sobreescribir con secrets) ======
UPLOAD_FOLDER = st.secrets.get("shared_upload_path", "uploaded")
EIM_EXCEL_FILENAME = "archivo_cargado_eim.xlsx"
EIM_TIME_FILENAME  = "ultima_subida_eim.txt"

def _ruta_excel() -> str:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    return os.path.join(UPLOAD_FOLDER, EIM_EXCEL_FILENAME)

def _ruta_tiempo() -> str:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    return os.path.join(UPLOAD_FOLDER, EIM_TIME_FILENAME)

# ====== Persistencia ======
def guardar_excel_eim(df: pd.DataFrame):
    df.to_excel(_ruta_excel(), index=False)

def guardar_marca_tiempo_eim() -> str:
    zona = pytz.timezone("Europe/Madrid")
    hora_local = datetime.now(zona).strftime("%d/%m/%Y %H:%M:%S")
    with open(_ruta_tiempo(), "w", encoding="utf-8") as f:
        f.write(hora_local)
    return hora_local

def cargar_excel_guardado_eim() -> pd.DataFrame | None:
    path = _ruta_excel()
    if os.path.exists(path):
        try:
            return pd.read_excel(path, dtype=str)
        except Exception:
            return None
    return None

def cargar_marca_tiempo_eim() -> str:
    path = _ruta_tiempo()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "Fecha no disponible"

# ====== Comprobación de submódulos ======
def _comprobar_submodulos():
    base = Path(__file__).parent / "deuda"
    esperados = [
        "__init__.py",
        "gestion_datos.py",
        "global_.py",
        "pendiente.py",
    ]
    faltan = [n for n in esperados if not (base / n).exists()]
    if faltan:
        st.error("Faltan archivos en `pagesEIM/deuda/`:")
        for n in faltan:
            st.markdown(f"- ❌ `{n}`")
        st.stop()

# ====== Página principal de Gestión de Cobro (EIM) ======
def deuda_page():
    # Estado de sesión (EIM)
    st.session_state.setdefault('excel_data_eim', None)
    st.session_state.setdefault('excel_filename_eim', None)
    st.session_state.setdefault('upload_time_eim', None)

    # Cabecera
    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        st.header("📂 Gestión de Cobro (EIM)")
    with col2:
        st.markdown(
            f"<div style='margin-top: 25px; font-size: 14px; color: gray;'>"
            f"🕒 Última actualización: {st.session_state.get('upload_time_eim','Fecha no disponible')}</div>",
            unsafe_allow_html=True
        )

    # Cargar desde disco si no hay datos en sesión
    if st.session_state['excel_data_eim'] is None:
        df_guardado = cargar_excel_guardado_eim()
        if df_guardado is not None:
            st.session_state['excel_data_eim'] = df_guardado
            st.session_state['excel_filename_eim'] = EIM_EXCEL_FILENAME
            st.session_state['upload_time_eim'] = cargar_marca_tiempo_eim()

    # Subida de archivo solo para administradores
    if st.session_state.get('role', 'viewer') == "admin":
        archivo = st.file_uploader("📤 Sube un archivo Excel (EIM)", type=["xlsx", "xls"], key="eim_uploader")
        if archivo:
            try:
                xls = pd.ExcelFile(archivo, engine="openpyxl")
                df = pd.read_excel(xls, sheet_name=xls.sheet_names[0], dtype=str)

                # Guardar en disco compartido + marca de tiempo
                guardar_excel_eim(df)
                hora_local = guardar_marca_tiempo_eim()

                # Guardar en sesión
                st.session_state['excel_data_eim'] = df
                st.session_state['excel_filename_eim'] = archivo.name
                st.session_state['upload_time_eim'] = hora_local

                st.success(f"✅ Archivo EIM cargado y guardado: {archivo.name}")
                st.rerun()
            except Exception as e:
                st.error("❌ Error al procesar el archivo EIM.")
                st.exception(e)
                return
    else:
        # Usuarios no-admin: asegurar lectura del fichero compartido
        if st.session_state['excel_data_eim'] is None:
            df_guardado = cargar_excel_guardado_eim()
            if df_guardado is not None:
                st.session_state['excel_data_eim'] = df_guardado
                st.session_state['excel_filename_eim'] = EIM_EXCEL_FILENAME
                st.session_state['upload_time_eim'] = cargar_marca_tiempo_eim()
            else:
                st.warning("⚠️ El administrador aún no ha subido el archivo de EIM.")
                return

    # Mostrar nombre del archivo
    if st.session_state['excel_data_eim'] is not None:
        st.success(f"📎 Archivo cargado (EIM): {st.session_state['excel_filename_eim']}")

    # Diagnóstico de submódulos
    _comprobar_submodulos()

    # Imports perezosos (solo lo que necesitas: gestión_datos, global_, pendiente)
    try:
        from pagesEIM.deuda import gestion_datos as eim_gestion_datos
        from pagesEIM.deuda import global_       as eim_global
        from pagesEIM.deuda import pendiente     as eim_pendiente
    except Exception as e:
        st.error("❌ No se pudieron cargar los submódulos de `pagesEIM.deuda` (gestion_datos/global_/pendiente).")
        st.info("Revisa nombres (minúsculas/mayúsculas) y que exista `__init__.py`.")
        st.exception(e)
        return

    # Navegación (solo estas tres)
    subcategorias = [
        "Gestión de Datos",
        "Global",
        "Pendiente Total",
    ]
    st.session_state.setdefault("subcategoria_deuda_eim", subcategorias[0])

    seccion = st.selectbox(
        "Selecciona una subcategoría:",
        subcategorias,
        index=subcategorias.index(st.session_state["subcategoria_deuda_eim"]),
        key="subcategoria_deuda_eim"
    )

    if seccion == "Gestión de Datos":
        eim_gestion_datos.render()
    elif seccion == "Global":
        eim_global.render()
    elif seccion == "Pendiente Total":
        eim_pendiente.render()
