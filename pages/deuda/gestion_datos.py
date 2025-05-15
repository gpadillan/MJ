import streamlit as st
import pandas as pd
import io
import os

# Constantes
UPLOAD_FOLDER = "uploaded"
TIEMPO_FILENAME = os.path.join(UPLOAD_FOLDER, "ultima_subida.txt")

def cargar_marca_tiempo():
    if os.path.exists(TIEMPO_FILENAME):
        with open(TIEMPO_FILENAME, "r") as f:
            return f.read().strip()
    return "Fecha no disponible"

def render():
    st.header("📁 Gestión de Datos – Gestión de Cobro")

    # Mostrar la hora de la última carga del archivo
    ultima_actualizacion = cargar_marca_tiempo()
    st.markdown(f"🕒 **Última actualización:** {ultima_actualizacion}")

    if 'excel_data' not in st.session_state or st.session_state['excel_data'] is None:
        st.warning("⚠️ No hay archivo cargado. Ve a la sección principal para subir un archivo.")
        return

    df = st.session_state['excel_data']
    st.markdown("### Vista previa del archivo cargado")
    st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Hojas disponibles:")

    hojas_disponibles = []

    if "descarga_global" in st.session_state:
        hojas_disponibles.append("✅ Global")
    else:
        hojas_disponibles.append("❌ Global aún no generado")

    if "descarga_año_2025" in st.session_state:
        hojas_disponibles.append("✅ Pendiente por Años y Meses Año Actual")
    else:
        hojas_disponibles.append("❌ Pendiente por Años y Meses Año Actual aún no generado")

    if "descarga_pendiente_clientes" in st.session_state:
        hojas_disponibles.append("✅ Pendiente Clientes")
    else:
        hojas_disponibles.append("❌ Pendiente Clientes aún no generado")

    if "descarga_becas_isa" in st.session_state:
        hojas_disponibles.append("✅ Becas ISA - Total Años")
    else:
        hojas_disponibles.append("❌ Becas ISA - Total Años aún no generado")

    if "descarga_becas_isa_mes" in st.session_state:
        hojas_disponibles.append("✅ Becas ISA - Año Actual")
    else:
        hojas_disponibles.append("❌ Becas ISA - Año Actual aún no generado")

    if "descarga_becas_isa_26_27_28" in st.session_state:
        hojas_disponibles.append("✅ Becas ISA Futuro")
    else:
        hojas_disponibles.append("❌ Becas ISA Futuro aún no generado")

    if "descarga_pendiente_cobro_isa" in st.session_state:
        hojas_disponibles.append("✅ Pendiente Cobro ISA")
    else:
        hojas_disponibles.append("❌ Pendiente Cobro ISA aún no generado")

    for hoja in hojas_disponibles:
        st.markdown(f"- {hoja}")

    st.markdown("---")
    st.subheader("📥 Descargar consolidado del área Gestión de Cobro")

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        if "descarga_global" in st.session_state:
            st.session_state["descarga_global"].to_excel(writer, sheet_name="global", index=False)

        if "descarga_año_2025" in st.session_state:
            st.session_state["descarga_año_2025"].to_excel(writer, sheet_name="pendiente_por_año", index=False)

        if "descarga_pendiente_clientes" in st.session_state:
            df_export = st.session_state["descarga_pendiente_clientes"]
            if isinstance(df_export, dict):
                for nombre, hoja in df_export.items():
                    hoja.to_excel(writer, sheet_name=f"pendiente_clientes_{nombre}", index=False)
            else:
                df_export.to_excel(writer, sheet_name="pendiente_clientes", index=False)

        if "descarga_becas_isa" in st.session_state:
            st.session_state["descarga_becas_isa"].to_excel(writer, sheet_name="becas_isa", index=False)

        if "descarga_becas_isa_mes" in st.session_state:
            st.session_state["descarga_becas_isa_mes"].to_excel(writer, sheet_name="becas_isa_mes", index=False)

        if "descarga_becas_isa_26_27_28" in st.session_state:
            st.session_state["descarga_becas_isa_26_27_28"].to_excel(writer, sheet_name="becas_isa_26_27_28", index=False)

        if "descarga_pendiente_cobro_isa" in st.session_state:
            st.session_state["descarga_pendiente_cobro_isa"].to_excel(writer, sheet_name="pendiente_cobro_isa", index=False)

    buffer.seek(0)

    st.download_button(
        label="📥 Descargar Excel Consolidado",
        data=buffer.getvalue(),
        file_name="gestion_cobro_consolidado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
