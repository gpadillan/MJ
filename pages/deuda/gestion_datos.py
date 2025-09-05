import streamlit as st
import pandas as pd
import io
import os

UPLOAD_FOLDER = "uploaded"
TIEMPO_FILENAME = os.path.join(UPLOAD_FOLDER, "ultima_subida.txt")
EXCEL_FILENAME = os.path.join(UPLOAD_FOLDER, "archivo_cargado.xlsx")


def cargar_marca_tiempo():
    if os.path.exists(TIEMPO_FILENAME):
        with open(TIEMPO_FILENAME, "r") as f:
            return f.read().strip()
    return "Fecha no disponible"


def render():
    st.header("📁 Gestión de Datos – Gestión de Cobro")

    # Asegurar que los datos están en memoria
    if "excel_data" not in st.session_state or st.session_state["excel_data"] is None:
        if os.path.exists(EXCEL_FILENAME):
            with open(EXCEL_FILENAME, "rb") as f:
                content = f.read()
                st.session_state["uploaded_excel_bytes"] = content
                st.session_state["excel_data"] = pd.read_excel(io.BytesIO(content), dtype=str)
        else:
            st.warning("⚠️ No hay archivo de datos cargado.")
            return

    # Mostrar hora de carga
    upload_time = st.session_state.get("upload_time", cargar_marca_tiempo())
    st.markdown(f"🕒 **Última actualización:** {upload_time}")

    # Mostrar preview (solo primeras filas por rendimiento)
    df = st.session_state["excel_data"]
    st.markdown("### Vista previa del archivo cargado")
    st.dataframe(df.head(100), use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Hojas disponibles:")

    def hoja_estado(clave, nombre):
        return f"✅ {nombre}" if clave in st.session_state else f"❌ {nombre} aún no generado"

    hojas_disponibles = [
        hoja_estado("descarga_global", "Global"),
        hoja_estado("descarga_pendiente_total", "Pendiente Total"),
        hoja_estado("descarga_becas_isa", "Becas ISA – Consolidado"),
        hoja_estado("descarga_pendiente_cobro_isa", "Pendiente Cobro ISA"),
    ]

    for hoja in hojas_disponibles:
        st.markdown(f"- {hoja}")

    st.markdown("---")
    st.subheader("📥 Descargar Excel Consolidado del Área")

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        if "descarga_global" in st.session_state:
            st.session_state["descarga_global"].to_excel(writer, sheet_name="Global", index=False)

        if "descarga_pendiente_total" in st.session_state:
            pendiente_total = st.session_state["descarga_pendiente_total"]
            if isinstance(pendiente_total, dict):
                for nombre, hoja in pendiente_total.items():
                    hoja.to_excel(writer, sheet_name=f"pendiente_{nombre[:22]}", index=False)
            else:
                pendiente_total.to_excel(writer, sheet_name="pendiente_total", index=False)

        if "descarga_becas_isa" in st.session_state:
            becas = st.session_state["descarga_becas_isa"]
            if isinstance(becas, dict):
                for nombre, hoja in becas.items():
                    hoja.to_excel(writer, sheet_name=f"becas_isa_{nombre[:22]}", index=False)
            else:
                becas.to_excel(writer, sheet_name="becas_isa", index=False)

        if "descarga_pendiente_cobro_isa" in st.session_state:
            st.session_state["descarga_pendiente_cobro_isa"].to_excel(
                writer, sheet_name="pendiente_cobro_isa", index=False
            )

    buffer.seek(0)
    st.download_button(
        label="📥 Descargar Excel Consolidado",
        data=buffer.getvalue(),
        file_name="gestion_cobro_consolidado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.markdown("---")
    st.subheader("🌐 Descargar informe HTML consolidado")

    html_claves = {
        "html_global": "Global",
        "html_pendiente_total": "Pendiente Total",
        "html_becas_isa": "Becas ISA – Consolidado",
        "html_pendiente_cobro_isa": "Pendiente Cobro ISA",
    }

    htmls = {k: st.session_state[k] for k in html_claves if k in st.session_state}

    if not htmls:
        st.info("ℹ️ Aún no hay informes HTML generados desde los módulos.")
    else:
        html_final = "<html><head><meta charset='utf-8'><title>Informe Consolidado</title></head><body>"
        for clave, contenido in htmls.items():
            html_final += f"<hr><h1>{html_claves[clave]}</h1>"
            html_final += contenido
        html_final += "</body></html>"

        st.download_button(
            label="🌐 Descargar informe HTML Consolidado",
            data=html_final.encode("utf-8"),
            file_name="informe_gestion_cobro_consolidado.html",
            mime="text/html"
        )
