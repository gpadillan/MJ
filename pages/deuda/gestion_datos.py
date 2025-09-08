import streamlit as st
import pandas as pd
import io
import os
from datetime import datetime

UPLOAD_FOLDER = "uploaded"
TIEMPO_FILENAME = os.path.join(UPLOAD_FOLDER, "ultima_subida.txt")
EXCEL_FILENAME = os.path.join(UPLOAD_FOLDER, "archivo_cargado.xlsx")

MESES_ES = [
    "Enero","Febrero","Marzo","Abril","Mayo","Junio",
    "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"
]

def cargar_marca_tiempo():
    if os.path.exists(TIEMPO_FILENAME):
        with open(TIEMPO_FILENAME, "r") as f:
            return f.read().strip()
    return "Fecha no disponible"

# ===============================
# Hidratador: crea descarga_global si falta
# ===============================
def _ensure_descarga_global():
    """Intenta generar st.session_state['descarga_global'] a partir de excel_data."""
    if "descarga_global" in st.session_state:
        return  # ya está
    if "excel_data" not in st.session_state or st.session_state["excel_data"] is None:
        return

    df = st.session_state["excel_data"].copy()
    if "Estado" not in df.columns:
        return

    anio_actual = st.session_state.get("año_actual", datetime.today().year)

    # Columnas candidatas (históricas + meses del año actual)
    cols_hist = [f"Total {a}" for a in range(2018, anio_actual)]
    cols_mes  = [f"{m} {anio_actual}" for m in MESES_ES]
    columnas_existentes = [c for c in cols_hist + cols_mes if c in df.columns]
    if not columnas_existentes:
        return

    # Numéricos + agrupación por Estado
    df[columnas_existentes] = df[columnas_existentes].apply(pd.to_numeric, errors="coerce").fillna(0)
    df_group = df.groupby("Estado")[columnas_existentes].sum().reset_index()
    df_group["Total fila"] = df_group[columnas_existentes].sum(axis=1)

    # Clave usada para el ✅ en Gestión de Datos
    st.session_state["descarga_global"] = df_group

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

    # Intentar reconstruir 'descarga_global' si aún no existe
    _ensure_descarga_global()

    # Mostrar hora de carga
    upload_time = st.session_state.get("upload_time", cargar_marca_tiempo())
    st.markdown(f"🕒 **Última actualización:** {upload_time}")

    # Preview (solo primeras filas por rendimiento)
    df = st.session_state["excel_data"]
    st.markdown("### Vista previa del archivo cargado")
    st.dataframe(df.head(100), use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Hojas disponibles:")

    def _has_any(*keys):
        """Devuelve True si existe cualquiera de las claves en session_state."""
        return any(k in st.session_state for k in keys)

    def hoja_estado(keys, nombre):
        # Marca ✅ si hay DataFrame o HTML de esa hoja
        return f"✅ {nombre}" if _has_any(*keys) else f"❌ {nombre} aún no generado"

    hojas_disponibles = [
        hoja_estado(("descarga_global", "html_global"), "Global"),
        hoja_estado(("descarga_pendiente_total", "html_pendiente_total"), "Pendiente Total"),
        hoja_estado(("descarga_becas_isa", "html_becas_isa"), "Becas ISA – Consolidado"),
        hoja_estado(("descarga_pendiente_cobro_isa", "html_pendiente_cobro_isa"), "Pendiente Cobro ISA"),
    ]

    for hoja in hojas_disponibles:
        st.markdown(f"- {hoja}")

    # (Opcional) Debug rápido
    # with st.expander("🔧 Ver claves de session_state (debug)", expanded=False):
    #     st.write(sorted(st.session_state.keys()))

    st.markdown("---")
    st.subheader("📥 Descargar Excel Consolidado del Área")

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        # Global: si tenemos DataFrame lo metemos; si sólo hay HTML, el hidratador ya habrá intentado crear DF
        if "descarga_global" in st.session_state:
            st.session_state["descarga_global"].to_excel(writer, sheet_name="Global", index=False)

        if "descarga_pendiente_total" in st.session_state:
            pendiente_total = st.session_state["descarga_pendiente_total"]
            if isinstance(pendiente_total, dict):
                for nombre, hoja in pendiente_total.items():
                    if isinstance(hoja, pd.DataFrame):
                        hoja.to_excel(writer, sheet_name=f"pendiente_{nombre[:22]}", index=False)
            elif isinstance(pendiente_total, pd.DataFrame):
                pendiente_total.to_excel(writer, sheet_name="pendiente_total", index=False)

        if "descarga_becas_isa" in st.session_state:
            becas = st.session_state["descarga_becas_isa"]
            if isinstance(becas, dict):
                for nombre, hoja in becas.items():
                    if isinstance(hoja, pd.DataFrame):
                        hoja.to_excel(writer, sheet_name=f"becas_isa_{nombre[:22]}", index=False)
            elif isinstance(becas, pd.DataFrame):
                becas.to_excel(writer, sheet_name="becas_isa", index=False)

        if "descarga_pendiente_cobro_isa" in st.session_state:
            d = st.session_state["descarga_pendiente_cobro_isa"]
            if isinstance(d, pd.DataFrame):
                d.to_excel(writer, sheet_name="pendiente_cobro_isa", index=False)

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
