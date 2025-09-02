# pagesEIM/gestion_datos.py
import io
import os
from datetime import datetime

import pandas as pd
import streamlit as st

# ===== Claves de sesión específicas de EIM =====
DATA_KEY            = "excel_data_eim"            # DF cargado para EIM (en memoria)
BYTES_KEY           = "excel_eim_bytes"           # bytes del archivo subido
FILENAME_KEY        = "excel_eim_filename"        # nombre del archivo
UPLOAD_TIME_KEY     = "excel_eim_upload_time"     # timestamp legible

# Fichero "publicado para todos"
PUBLISHED_DIR       = "uploaded"
PUBLISHED_FILE      = os.path.join(PUBLISHED_DIR, "archivo_cargado_eim.xlsx")

# Estas las rellenan las subpáginas Global/Pendiente (EIM)
GLOBAL_XLS_ALIASES  = ["descarga_global_eim", "descarga_global"]
GLOBAL_HTML_ALIASES = ["html_global_eim", "html_global"]
PEND_XLS_ALIASES    = ["descarga_pendiente_total_eim", "descarga_pendiente_total"]
PEND_HTML_ALIASES   = ["html_pendiente_total_eim", "html_pendiente_total"]

def _is_admin() -> bool:
    # El rol viene de tu login. "admin" puede subir/borrar/publicar.
    return st.session_state.get("role", "").lower() == "admin"

def _fmt_dt(dt: datetime | None) -> str:
    if not dt:
        return "Fecha no disponible"
    try:
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(dt)

def _read_uploaded_file(file) -> pd.DataFrame:
    """
    Lee XLSX/XLS/CSV en un DataFrame (primera hoja si hay varias).
    Devuelve texto en mayúsculas/str para evitar problemas en vistas.
    """
    name = file.name.lower()
    content = file.read()
    if name.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(content), dtype=str)
    else:
        try:
            df = pd.read_excel(io.BytesIO(content), sheet_name=0, dtype=str)
        except Exception:
            df = pd.read_excel(io.BytesIO(content), dtype=str)
    return df, content

def _first_in_state(aliases: list[str]):
    for k in aliases:
        if k in st.session_state and st.session_state[k] is not None:
            return k, st.session_state[k]
    return None, None

def _set_canonical_from_aliases(aliases: list[str]):
    if not aliases:
        return None, None
    found_k, val = _first_in_state(aliases)
    if found_k is None:
        return None, None
    canonical = aliases[0]
    st.session_state[canonical] = val
    return canonical, val

def render():
    st.header("Sección: Gestión de Cobro (EIM)")

    # ===== Estado actual de datos cargados =====
    last_name = st.session_state.get(FILENAME_KEY, None)
    last_time = st.session_state.get(UPLOAD_TIME_KEY, None)

    if last_name:
        st.info(f"Hay datos EIM cargados: **{last_name}** · {_fmt_dt(last_time)}")
    else:
        st.warning("No hay datos EIM cargados todavía.")

    # ===== Botones admin =====
    col_a, col_b, col_c = st.columns([1, 1, 3])

    with col_a:
        if st.button("🧹 Limpiar datos cargados (EIM)", disabled=not _is_admin()):
            for k in [DATA_KEY, BYTES_KEY, FILENAME_KEY, UPLOAD_TIME_KEY]:
                if k in st.session_state:
                    del st.session_state[k]
            for k in GLOBAL_XLS_ALIASES + GLOBAL_HTML_ALIASES + PEND_XLS_ALIASES + PEND_HTML_ALIASES:
                if k in st.session_state:
                    del st.session_state[k]
            st.success("Datos EIM eliminados de memoria.")
            st.rerun()

    with col_b:
        if st.button("📢 Publicar para todos", disabled=not (_is_admin() and (BYTES_KEY in st.session_state))):
            try:
                os.makedirs(PUBLISHED_DIR, exist_ok=True)
                raw = st.session_state.get(BYTES_KEY)
                if raw is None:
                    st.warning("No hay archivo en memoria para publicar. Sube un archivo primero.")
                else:
                    with open(PUBLISHED_FILE, "wb") as f:
                        f.write(raw)
                    st.success(f"Publicado en **{PUBLISHED_FILE}**. Ahora cualquier usuario puede verlo.")
            except Exception as e:
                st.error(f"No se pudo publicar el archivo: {e}")

    # ===== Uploader (sólo admin) =====
    st.markdown("### Subir archivo de deuda para **EIM**")
    if not _is_admin():
        st.info("🔒 Solo los usuarios con rol **admin** pueden subir, limpiar o publicar el archivo.")
    uploaded = st.file_uploader(
        "Sube tu archivo (Excel o CSV) para EIM",
        type=["xlsx", "xls", "csv"],
        key="uploader_eim",
        disabled=not _is_admin(),
    )

    if uploaded is not None and _is_admin():
        try:
            df, raw = _read_uploaded_file(uploaded)
            st.session_state[DATA_KEY]        = df
            st.session_state[BYTES_KEY]       = raw
            st.session_state[FILENAME_KEY]    = uploaded.name
            st.session_state[UPLOAD_TIME_KEY] = datetime.now()
            st.success(f"Archivo **{uploaded.name}** cargado correctamente para EIM.")
        except Exception as e:
            st.error(f"No se pudo leer el archivo: {e}")

    # ===== Vista previa si hay datos cargados =====
    if DATA_KEY in st.session_state and st.session_state[DATA_KEY] is not None:
        st.markdown("---")
        st.subheader("Vista previa del archivo cargado")
        st.caption(f"Última actualización: {_fmt_dt(st.session_state.get(UPLOAD_TIME_KEY, None))}")
        st.dataframe(st.session_state[DATA_KEY].head(100), use_container_width=True)
    else:
        st.stop()

    st.markdown("---")
    st.subheader("📄 Hojas disponibles:")

    _set_canonical_from_aliases(GLOBAL_XLS_ALIASES)
    _set_canonical_from_aliases(GLOBAL_HTML_ALIASES)
    _set_canonical_from_aliases(PEND_XLS_ALIASES)
    _set_canonical_from_aliases(PEND_HTML_ALIASES)

    disponibles = []
    if _first_in_state(GLOBAL_XLS_ALIASES)[0]:
        disponibles.append("✅ Global")
    if _first_in_state(PEND_XLS_ALIASES)[0]:
        disponibles.append("✅ Pendiente")

    if not disponibles:
        st.info("Aún no hay hojas generadas por las subpáginas **Global** o **Pendiente**.")
    else:
        for linea in disponibles:
            st.markdown(f"- {linea}")

    # ===== Exportar Excel consolidado =====
    st.markdown("---")
    st.subheader("📥 Descargar Excel Consolidado del Área (EIM)")

    has_global = _first_in_state(GLOBAL_XLS_ALIASES)[0] is not None
    has_pend   = _first_in_state(PEND_XLS_ALIASES)[0] is not None
    has_any_sheet = has_global or has_pend

    if not has_any_sheet:
        st.info("Aún no hay hojas generadas por las subpáginas **Global** o **Pendiente**.")
    else:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            # Global
            _, df_glob = _first_in_state(GLOBAL_XLS_ALIASES)
            if df_glob is not None:
                if isinstance(df_glob, dict):
                    for name, df_sheet in df_glob.items():
                        df_sheet.to_excel(writer, index=False, sheet_name=f"Global_{name[:20]}")
                else:
                    df_glob.to_excel(writer, index=False, sheet_name="Global")

            # Pendiente
            _, pend = _first_in_state(PEND_XLS_ALIASES)
            if pend is not None:
                if isinstance(pend, dict):
                    for name, df_sheet in pend.items():
                        df_sheet.to_excel(writer, index=False, sheet_name=f"Pend_{name[:23]}")
                else:
                    pend.to_excel(writer, index=False, sheet_name="Pendiente")

        buffer.seek(0)
        st.download_button(
            label="📥 Descargar Excel Consolidado (EIM)",
            data=buffer.getvalue(),
            file_name="gestion_cobro_eim_consolidado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # ===== Exportar HTML consolidado =====
    st.markdown("---")
    st.subheader("🌐 Descargar informe HTML consolidado (EIM)")

    html_parts = []
    _, g_html = _first_in_state(GLOBAL_HTML_ALIASES)
    _, p_html = _first_in_state(PEND_HTML_ALIASES)
    if g_html:
        html_parts.append(("<h1>Global (EIM)</h1>", g_html))
    if p_html:
        html_parts.append(("<h1>Pendiente (EIM)</h1>", p_html))

    if not html_parts:
        st.info("Aún no hay informes HTML generados desde las subpáginas Global/Pendiente.")
    else:
        html_final = "<html><head><meta charset='utf-8'><title>Informe Consolidado EIM</title></head><body>"
        for title_html, content in html_parts:
            html_final += "<hr>" + title_html + content
        html_final += "</body></html>"

        st.download_button(
            label="🌐 Descargar informe HTML Consolidado (EIM)",
            data=html_final.encode("utf-8"),
            file_name="informe_gestion_cobro_eim.html",
            mime="text/html",
        )
