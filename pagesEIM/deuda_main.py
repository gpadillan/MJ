# pagesEIM/deuda_main.py
import os
import io
import pandas as pd
import pytz
from datetime import datetime
import streamlit as st

# ✅ importa los módulos reales, NO desde __init__.py
from pagesEIM.deuda import gestion_datos_eim, global_eim, pendiente_eim
from pagesEIM.deuda import estado_restante_eim   # ⬅️ nuevo import

# --- rutas de almacenamiento compartidas por EIM ---
UPLOAD_FOLDER_EIM   = "uploaded_eim"
EXCEL_FILENAME_EIM  = os.path.join(UPLOAD_FOLDER_EIM, "archivo_cargado.xlsx")
TIEMPO_FILENAME_EIM = os.path.join(UPLOAD_FOLDER_EIM, "ultima_subida.txt")


def _guardar_excel_eim(df: pd.DataFrame):
    os.makedirs(UPLOAD_FOLDER_EIM, exist_ok=True)
    df.to_excel(EXCEL_FILENAME_EIM, index=False)


def _guardar_marca_tiempo_eim():
    os.makedirs(UPLOAD_FOLDER_EIM, exist_ok=True)
    zona = pytz.timezone("Europe/Madrid")
    hora_local = datetime.now(zona).strftime("%d/%m/%Y %H:%M:%S")
    with open(TIEMPO_FILENAME_EIM, "w", encoding="utf-8") as f:
        f.write(hora_local)
    return hora_local


def _cargar_excel_guardado_eim():
    if os.path.exists(EXCEL_FILENAME_EIM):
        return pd.read_excel(EXCEL_FILENAME_EIM, dtype=str)
    return None


def _cargar_marca_tiempo_eim():
    if os.path.exists(TIEMPO_FILENAME_EIM):
        with open(TIEMPO_FILENAME_EIM, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "Fecha no disponible"


def deuda_eim_page():
    """Página principal: Gestión de Cobro · EIM"""
    # estado inicial
    if "excel_data_eim" not in st.session_state:
        st.session_state["excel_data_eim"] = None
    if "excel_filename_eim" not in st.session_state:
        st.session_state["excel_filename_eim"] = None
    if "upload_time_eim" not in st.session_state:
        st.session_state["upload_time_eim"] = None

    # intenta cargar desde disco si no hay nada en sesión
    if st.session_state["excel_data_eim"] is None:
        df_guardado = _cargar_excel_guardado_eim()
        if df_guardado is not None:
            st.session_state["excel_data_eim"] = df_guardado
            st.session_state["excel_filename_eim"] = "archivo_cargado.xlsx"
            st.session_state["upload_time_eim"] = _cargar_marca_tiempo_eim()

    col_t, col_time = st.columns([0.8, 0.2])
    with col_t:
        st.header("📂 Gestión de Cobro · EIM")
    with col_time:
        st.markdown(
            f"<div style='margin-top:25px;color:gray'>🕒 Última actualización: "
            f"{st.session_state.get('upload_time_eim', 'Fecha no disponible')}</div>",
            unsafe_allow_html=True
        )

    # subida solo admins
    if st.session_state.get("role") == "admin":
        archivo = st.file_uploader("📤 Sube un Excel (EIM)", type=["xlsx", "xls"], key="uploader_eim")
        if archivo:
            try:
                xls = pd.ExcelFile(archivo, engine="openpyxl")
                df  = pd.read_excel(xls, sheet_name=xls.sheet_names[0], dtype=str)
                hora = _guardar_marca_tiempo_eim()

                # guarda en sesión + disco para todos
                st.session_state["excel_data_eim"]     = df
                st.session_state["excel_filename_eim"] = archivo.name
                st.session_state["upload_time_eim"]    = hora
                _guardar_excel_eim(df)

                st.success(f"✅ Archivo cargado y guardado: {archivo.name}")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al procesar el archivo: {e}")
    else:
        # si no hay nada y tampoco hay archivo en disco
        if st.session_state["excel_data_eim"] is None and not os.path.exists(EXCEL_FILENAME_EIM):
            st.info("⚠️ El administrador aún no ha subido el archivo.")
            return

    if st.session_state["excel_data_eim"] is not None:
        st.success(f"📎 Archivo cargado: {st.session_state['excel_filename_eim']}")

    # selector subpáginas (añadimos "Estado restante")
    subcategorias = ["Gestión de Datos", "Global", "Pendiente Total", "Estado restante"]
    if "subcategoria_deuda_eim" not in st.session_state:
        st.session_state["subcategoria_deuda_eim"] = subcategorias[0]

    c1, c2 = st.columns([0.85, 0.15])
    with c1:
        seccion = st.selectbox(
            "Selecciona una subcategoría:",
            subcategorias,
            index=subcategorias.index(st.session_state["subcategoria_deuda_eim"]),
            key="subcategoria_deuda_eim"
        )
    with c2:
        if st.session_state.get("role") == "admin":
            if st.button("🗑️", help="Eliminar archivo y reiniciar EIM", key="trash_reset_eim"):
                st.session_state["excel_data_eim"] = None
                st.session_state["excel_filename_eim"] = None
                st.session_state["upload_time_eim"] = None
                if os.path.exists(EXCEL_FILENAME_EIM):
                    os.remove(EXCEL_FILENAME_EIM)
                if os.path.exists(TIEMPO_FILENAME_EIM):
                    os.remove(TIEMPO_FILENAME_EIM)
                st.rerun()

    # router de subpáginas
    if seccion == "Gestión de Datos":
        gestion_datos_eim.render()
    elif seccion == "Global":
        global_eim.render()
    elif seccion == "Pendiente Total":
        pendiente_eim.render()
    elif seccion == "Estado restante":
        estado_restante_eim.render()   # ⬅️ nuevo router


# Alias para routers antiguos
def deuda_page():
    return deuda_eim_page()
