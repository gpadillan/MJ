import streamlit as st
import pandas as pd
import io

def render():
    st.subheader(" Pendientes de Cobro – Becas ISA")

    if "excel_data" not in st.session_state or st.session_state["excel_data"] is None:
        st.warning("⚠️ No hay archivo cargado. Ve a la sección Gestión de Cobro.")
        return

    # Siempre trabajar con copia
    df = st.session_state["excel_data"].copy()

    # Normalizar columnas relevantes
    df['Estado'] = df['Estado'].astype(str).str.strip().str.upper()
    df['Forma Pago'] = df['Forma Pago'].astype(str).str.strip().str.upper()

    # Filtrar registros con Estado = PENDIENTE y Forma Pago = BECAS ISA
    df_filtrado = df[
        (df['Estado'] == "PENDIENTE") &
        (df['Forma Pago'] == "BECAS ISA")
    ]

    # Verificar columnas
    columnas_necesarias = ['Cliente', 'Proyecto', 'Curso',"Comercial"]
    if not all(col in df_filtrado.columns for col in columnas_necesarias):
        st.error("❌ El archivo no contiene todas las columnas necesarias: Cliente, Proyecto y Curso.")
        return

    # Tabla a mostrar
    tabla_final = df_filtrado[columnas_necesarias].copy()
    st.dataframe(tabla_final, use_container_width=True)

    # Guardar para consolidado
    st.session_state["descarga_pendiente_cobro_isa"] = tabla_final

    # Exportación
    st.markdown("---")
    st.subheader("📥 Exportar esta hoja")

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        tabla_final.to_excel(writer, sheet_name="pendiente_cobro_isa", index=False)
    
    buffer.seek(0)  # ← IMPORTANTE

    st.download_button(
        label="📥 Descargar hoja: Pendiente Cobro ISA",
        data=buffer.getvalue(),
        file_name="pendiente_cobro_isa.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
