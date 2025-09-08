# pagesEIM/deuda/gestion_datos.py

import io
import os
import pandas as pd
import streamlit as st

# Carpeta/archivos de EIM (igual que en pagesEIM/deuda_main.py)
UPLOAD_FOLDER_EIM   = "uploaded_eim"
EXCEL_FILENAME_EIM  = os.path.join(UPLOAD_FOLDER_EIM, "archivo_cargado.xlsx")
TIEMPO_FILENAME_EIM = os.path.join(UPLOAD_FOLDER_EIM, "ultima_subida.txt")


def _cargar_marca_tiempo_eim():
    if os.path.exists(TIEMPO_FILENAME_EIM):
        with open(TIEMPO_FILENAME_EIM, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "Fecha no disponible"


def _safe_write_sheet(writer, base_name: str, payload):
    """
    Escribe DataFrames o dicts de DataFrames con nombres de hoja seguros (<=31 chars).
    """
    def _safe(s: str) -> str:
        bad = '[]:*?/\\'
        for ch in bad:
            s = s.replace(ch, ' ')
        return s[:31]

    if isinstance(payload, pd.DataFrame):
        payload.to_excel(writer, sheet_name=_safe(base_name), index=False)
    elif isinstance(payload, dict):
        # nombre hoja: <base>_<clave>
        for k, df in payload.items():
            sheet = f"{base_name}_{str(k)}"
            payload[k].to_excel(writer, sheet_name=_safe(sheet), index=False)


def render():
    st.header("📁 Gestión de Datos – Gestión de Cobro (EIM)")

    # Asegurar datos en memoria para la vista previa
    if "excel_data_eim" not in st.session_state or st.session_state["excel_data_eim"] is None:
        if os.path.exists(EXCEL_FILENAME_EIM):
            st.session_state["excel_data_eim"] = pd.read_excel(EXCEL_FILENAME_EIM, dtype=str)
        else:
            st.warning("⚠️ No hay archivo de datos cargado (EIM).")
            return

    # Mostrar hora de carga
    upload_time = st.session_state.get("upload_time_eim", _cargar_marca_tiempo_eim())
    st.markdown(f"🕒 **Última actualización:** {upload_time}")

    # Vista previa (primeras filas)
    df = st.session_state["excel_data_eim"]
    st.markdown("### Vista previa del archivo cargado")
    st.dataframe(df.head(100), use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Hojas disponibles:")

    def hoja_estado(clave, nombre):
        return f"✅ {nombre}" if clave in st.session_state else f"❌ {nombre} aún no generado"

    # 🔹 Solo estas dos líneas (como pediste)
    hojas_disponibles = [
        hoja_estado("descarga_global_eim", "Global"),
        hoja_estado("descarga_pendiente_total_eim", "Pendiente Total"),
    ]
    for hoja in hojas_disponibles:
        st.markdown(f"- {hoja}")

    st.markdown("---")
    st.subheader("📥 Descargar Excel Consolidado del Área (EIM)")

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        # Global (si es df o dict de dfs)
        if "descarga_global_eim" in st.session_state:
            _safe_write_sheet(writer, "Global", st.session_state["descarga_global_eim"])

        # Pendiente Total (si es df o dict de dfs)
        if "descarga_pendiente_total_eim" in st.session_state:
            _safe_write_sheet(writer, "pendiente_total", st.session_state["descarga_pendiente_total_eim"])

    buffer.seek(0)
    st.download_button(
        label="📥 Descargar Excel Consolidado",
        data=buffer.getvalue(),
        file_name="gestion_cobro_eim_consolidado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.markdown("---")
    st.subheader("🌐 Descargar informe HTML consolidado (EIM)")

    # Solo unimos los HTML que existan para EIM
    html_claves_eim = {
        "html_global_eim": "Global",
        "html_pendiente_total_eim": "Pendiente Total",
    }
    htmls = {k: st.session_state[k] for k in html_claves_eim if k in st.session_state}

    if not htmls:
        st.info("ℹ️ Aún no hay informes HTML generados desde los módulos (EIM).")
    else:
        html_final = "<html><head><meta charset='utf-8'><title>Informe Consolidado EIM</title></head><body>"
        for clave, contenido in htmls.items():
            html_final += f"<hr><h1>{html_claves_eim[clave]}</h1>"
            html_final += contenido
        html_final += "</body></html>"

        st.download_button(
            label="🌐 Descargar informe HTML Consolidado",
            data=html_final.encode("utf-8"),
            file_name="informe_gestion_cobro_eim_consolidado.html",
            mime="text/html"
        )
