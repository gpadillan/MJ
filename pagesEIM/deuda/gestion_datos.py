# pagesEIM/gestion_datos.py
import io
import os
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st

# ====== Claves de sesión específicas de EIM ======
DATA_KEY            = "excel_data_eim"            # DF cargado (en memoria, por sesión)
BYTES_KEY           = "excel_eim_bytes"           # bytes del archivo subido (sesión)
FILENAME_KEY        = "excel_eim_filename"        # nombre del archivo subido (sesión)
UPLOAD_TIME_KEY     = "excel_eim_upload_time"     # timestamp de subida (sesión)

# Rutas de persistencia (compartidas por todos los usuarios)
BASE_DIR = Path(__file__).resolve().parent.parent  # carpeta raíz de la app (ajusta si fuese necesario)
PERSIST_DIR = (BASE_DIR / "uploaded")
PERSIST_DIR.mkdir(exist_ok=True, parents=True)
PERSIST_XLSX = PERSIST_DIR / "archivo_cargado_eim.xlsx"  # archivo público único

# Estas las rellenan las subpáginas Global/Pendiente (EIM)
# Aceptamos alias para no romper si otra página usa nombres sin "_eim"
GLOBAL_XLS_ALIASES  = ["descarga_global_eim", "descarga_global"]
GLOBAL_HTML_ALIASES = ["html_global_eim", "html_global"]
PEND_XLS_ALIASES    = ["descarga_pendiente_total_eim", "descarga_pendiente_total"]
PEND_HTML_ALIASES   = ["html_pendiente_total_eim", "html_pendiente_total"]


# ===================== Helpers =====================

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

def _read_uploaded_file(file) -> tuple[pd.DataFrame, bytes]:
    """
    Lee XLSX/XLS/CSV en un DataFrame (primera hoja si hay varias).
    Devuelve (df, bytes_crudos_del_archivo_subido).
    """
    raw = file.read()
    name = file.name.lower()
    bio = io.BytesIO(raw)

    if name.endswith(".csv"):
        df = pd.read_csv(bio, dtype=str)
    else:
        # Excel: intenta leer primera hoja
        try:
            df = pd.read_excel(bio, sheet_name=0, dtype=str)
        except Exception:
            df = pd.read_excel(bio, dtype=str)
    return df, raw

def _first_in_state(aliases: list[str]):
    """
    Devuelve (key_encontrada, valor) para la primera clave existente en session_state
    dentro de la lista de alias. Si no existe ninguna, (None, None).
    """
    for k in aliases:
        if k in st.session_state and st.session_state[k] is not None:
            return k, st.session_state[k]
    return None, None

def _set_canonical_from_aliases(aliases: list[str]):
    """
    Si hay valor en cualquier alias, lo copia al primer alias de la lista
    (clave canónica) para unificar. Devuelve (key_canonica, valor) o (None, None).
    """
    if not aliases:
        return None, None
    found_k, val = _first_in_state(aliases)
    if found_k is None:
        return None, None
    canonical = aliases[0]
    st.session_state[canonical] = val
    return canonical, val

def _persist_save_df_as_xlsx(df: pd.DataFrame):
    """
    Publica para todos: guarda el DF en PERSIST_XLSX.
    (Se estandariza a XLSX para lectura consistente.)
    """
    with pd.ExcelWriter(PERSIST_XLSX, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Datos")
    # Permisos (no siempre aplica en Windows, no pasa nada si falla)
    try:
        os.chmod(PERSIST_XLSX, 0o644)
    except Exception:
        pass

def _persist_load_df() -> pd.DataFrame | None:
    """
    Carga el archivo público si existe, si no devuelve None.
    """
    if PERSIST_XLSX.exists():
        try:
            return pd.read_excel(PERSIST_XLSX, dtype=str)
        except Exception:
            return None
    return None

def _persist_mtime_str() -> str:
    if PERSIST_XLSX.exists():
        ts = datetime.fromtimestamp(PERSIST_XLSX.stat().st_mtime)
        return _fmt_dt(ts)
    return "—"


# ===================== Pantalla =====================

def render():
    st.header("")

    # ===== Si no hay nada en sesión, intenta cargar el archivo PÚBLICO para todos =====
    if DATA_KEY not in st.session_state or st.session_state[DATA_KEY] is None:
        df_publico = _persist_load_df()
        if df_publico is not None:
            st.session_state[DATA_KEY] = df_publico
            st.session_state[FILENAME_KEY] = PERSIST_XLSX.name
            # Guardamos el mtime como "última publicación"
            try:
                st.session_state[UPLOAD_TIME_KEY] = datetime.fromtimestamp(PERSIST_XLSX.stat().st_mtime)
            except Exception:
                st.session_state[UPLOAD_TIME_KEY] = None

    # ===== Estado actual =====
    last_name = st.session_state.get(FILENAME_KEY, None) or (PERSIST_XLSX.name if PERSIST_XLSX.exists() else None)
    last_time = st.session_state.get(UPLOAD_TIME_KEY, None)

    if PERSIST_XLSX.exists():
        st.info(f"📢 Archivo público activo: **{PERSIST_XLSX.name}** · Publicado: **{_persist_mtime_str()}**")
    elif last_name:
        st.info(f"Datos en tu sesión: **{last_name}** · {_fmt_dt(last_time)}")
    else:
        st.warning("No hay datos EIM cargados todavía (ni públicos ni en tu sesión).")

    # ===== Acciones admin =====
    col_a, col_b, col_c = st.columns([1, 1, 3])
    with col_a:
        if st.button("🧹 Limpiar memoria (tu sesión)", disabled=not _is_admin()):
            for k in [DATA_KEY, BYTES_KEY, FILENAME_KEY, UPLOAD_TIME_KEY]:
                if k in st.session_state:
                    del st.session_state[k]
            # También limpiar salidas de Global/Pendiente EIM (todos los alias)
            for k in GLOBAL_XLS_ALIASES + GLOBAL_HTML_ALIASES + PEND_XLS_ALIASES + PEND_HTML_ALIASES:
                if k in st.session_state:
                    del st.session_state[k]
            st.success("Memoria de tu sesión limpiada.")
            st.rerun()

    with col_b:
        if st.button("🗑️ Borrar archivo público", disabled=not (_is_admin() and PERSIST_XLSX.exists())):
            try:
                PERSIST_XLSX.unlink(missing_ok=True)
                st.success("Archivo público eliminado. Los usuarios dejarán de verlo.")
            except Exception as e:
                st.error(f"No se pudo borrar el archivo público: {e}")
            st.rerun()

    # ===== Uploader (solo admin) =====
    st.markdown("### Subir archivo de deuda para **EIM**")
    if not _is_admin():
        st.info("🔒 Solo los usuarios con rol **admin** pueden subir/publicar o borrar el archivo. "
                "Puedes visualizar los datos públicos y descargar reportes.")
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
            st.success(f"Archivo **{uploaded.name}** cargado en tu sesión.")
        except Exception as e:
            st.error(f"No se pudo leer el archivo: {e}")

        # Botón para PUBLICAR a todos (guardar a disco compartido como XLSX)
        if st.button("📢 Publicar para todos (guardar en servidor)", type="primary"):
            try:
                _persist_save_df_as_xlsx(st.session_state[DATA_KEY])
                st.cache_data.clear()
                st.cache_resource.clear()
                st.success(f"¡Publicado! Todos verán **{PERSIST_XLSX.name}** · {_persist_mtime_str()}")
            except Exception as e:
                st.error(f"No se pudo publicar el archivo: {e}")
            st.rerun()

    # ===== Vista previa =====
    if DATA_KEY in st.session_state and st.session_state[DATA_KEY] is not None:
        st.markdown("---")
        st.subheader("Vista previa de datos activos")
        fuente = "PÚBLICO" if PERSIST_XLSX.exists() and st.session_state.get(FILENAME_KEY) == PERSIST_XLSX.name else "TU SESIÓN"
        st.caption(f"Fuente: {fuente} · Última actualización: "
                   f"{_persist_mtime_str() if fuente=='PÚBLICO' else _fmt_dt(st.session_state.get(UPLOAD_TIME_KEY, None))}")
        st.dataframe(st.session_state[DATA_KEY].head(100), use_container_width=True)
    else:
        st.stop()

    # ===== Hojas disponibles generadas por subpáginas =====
    st.markdown("---")
    st.subheader("📄 Hojas disponibles:")

    # Unifica (migración silenciosa) a claves canónicas
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
