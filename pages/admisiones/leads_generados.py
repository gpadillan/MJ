import streamlit as st
import pandas as pd
import os
import plotly.express as px
from datetime import datetime

UPLOAD_FOLDER = "uploaded_admisiones"
LEADS_GENERADOS_FILE = os.path.join(UPLOAD_FOLDER, "leads_generados.xlsx")

def app():
    # 🔵 Obtener el mes actual en español
    traducciones_meses = {
        "January": "Enero", "February": "Febrero", "March": "Marzo", "April": "Abril",
        "May": "Mayo", "June": "Junio", "July": "Julio", "August": "Agosto",
        "September": "Septiembre", "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
    }
    now = datetime.now()
    mes_actual = traducciones_meses[now.strftime("%B")] + " " + now.strftime("%Y")

    # 🔵 Mostrar el título con el mes actual
    st.markdown(f"<h1>📊 Leads Generados - {mes_actual}</h1>", unsafe_allow_html=True)

    if not os.path.exists(LEADS_GENERADOS_FILE):
        st.warning("📭 No se ha subido el archivo de Leads Generados aún.")
        return

    df = pd.read_excel(LEADS_GENERADOS_FILE)

    # Normalizar columnas
    df.columns = df.columns.str.strip().str.lower()

    if 'programa' not in df.columns or 'propietario' not in df.columns or 'etapa de oportunidad activa' not in df.columns:
        st.error("❌ El archivo debe contener las columnas 'programa', 'propietario' y 'etapa de oportunidad activa'.")
        return

    df["programa"] = df["programa"].astype(str).str.strip()
    df["propietario"] = df["propietario"].astype(str).str.strip()
    df["etapa de oportunidad activa"] = df["etapa de oportunidad activa"].astype(str).str.strip()
    df.replace(["nan", "None", ""], "(En Blanco)", inplace=True)

    # --- FILTRO POR PROGRAMA ---
    st.subheader("Filtro de Programa")
    programas = ["Todos"] + sorted(df["programa"].unique())
    programa_seleccionado = st.selectbox("Selecciona un Programa:", programas)

    df_filtrado = df.copy()
    if programa_seleccionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["programa"] == programa_seleccionado]

    # --- FILTRO POR PROPIETARIO ---
    st.subheader("Filtro de Propietario")
    propietarios = ["Todos"] + sorted(df_filtrado["propietario"].unique())
    propietario_seleccionado = st.selectbox("Selecciona un Propietario:", propietarios)

    if propietario_seleccionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["propietario"] == propietario_seleccionado]

    st.markdown("---")

    # --- DASHBOARDS PRINCIPALES FILTRADOS ---
    st.subheader("Leads por Programa y Etapa")

    col1, col2 = st.columns([2, 1])

    with col1:
        conteo_programas = df_filtrado["programa"].value_counts().reset_index()
        conteo_programas.columns = ["Programa", "Cantidad"]
        st.dataframe(conteo_programas, use_container_width=True)

    with col2:
        total_leads = df_filtrado.shape[0]
        st.metric(label="🎯 Total Leads Registrados", value=total_leads)

        if "etapa de oportunidad activa" in df_filtrado.columns:
            df_filtrado["etapa de oportunidad activa"] = df_filtrado["etapa de oportunidad activa"].astype(str).str.strip().str.lower()
            leads_oportunidad = df_filtrado[df_filtrado["etapa de oportunidad activa"].str.contains("oportunidad", na=False)].shape[0]
            st.metric(label="📈 Leads en Oportunidad", value=leads_oportunidad)
        else:
            st.warning("⚠️ No se encontró la columna 'etapa de oportunidad activa' en el archivo.")

        st.markdown("---")

        # 👉 Preparar donut ordenado
        conteo_etapa = df_filtrado["etapa de oportunidad activa"].value_counts().reset_index()
        conteo_etapa.columns = ["Etapa", "Cantidad"]

        orden_etapas = [
            "(en blanco)", "nuevo", "contactado", "en negociación",
            "propuesta enviada", "oportunidad", "cerrado ganado", "cerrado perdido"
        ]

        conteo_etapa["Etapa"] = conteo_etapa["Etapa"].str.lower()
        conteo_etapa["Orden"] = conteo_etapa["Etapa"].apply(lambda x: orden_etapas.index(x) if x in orden_etapas else len(orden_etapas))
        conteo_etapa = conteo_etapa.sort_values("Orden")

        fig_etapa = px.pie(
            conteo_etapa,
            names="Etapa",
            values="Cantidad",
            hole=0.4
        )
        fig_etapa.update_layout(
            showlegend=True,
            legend_title="Etapa",
        )
        st.plotly_chart(fig_etapa, use_container_width=True)

    st.markdown("---")

    # --- Mostrar Leads en (En Blanco) --- (pero SOLO si no son TODOS)
    if not (programa_seleccionado == "Todos" and propietario_seleccionado == "Todos"):
        st.subheader("⚠️ Datos En Blanco detectados:")

        hay_programa_blanco = df_filtrado["programa"].str.lower().eq("(en blanco)").any()
        hay_etapa_blanco = df_filtrado["etapa de oportunidad activa"].str.lower().eq("(en blanco)").any()

        if hay_programa_blanco:
            st.markdown("#### Leads con **Programa (En Blanco)**")
            df_blanco_programa = df_filtrado[df_filtrado["programa"].str.lower() == "(en blanco)"]
            if 'id' in df_blanco_programa.columns:
                st.dataframe(
                    df_blanco_programa[["propietario", "id"]],
                    use_container_width=True
                )
            else:
                st.warning("No se encontró la columna 'ID' en el archivo.")

        if hay_etapa_blanco:
            st.markdown("#### Leads con **Etapa de Oportunidad (En Blanco)**")
            df_blanco_etapa = df_filtrado[df_filtrado["etapa de oportunidad activa"].str.lower() == "(en blanco)"]
            if 'id' in df_blanco_etapa.columns:
                st.dataframe(
                    df_blanco_etapa[["propietario", "id"]],
                    use_container_width=True
                )
            else:
                st.warning("No se encontró la columna 'ID' en el archivo.")

        if not hay_programa_blanco and not hay_etapa_blanco:
            st.success("✅ No hay registros en blanco en los filtros aplicados.")

    # --- GRÁFICO DE PROPIETARIOS ---
    st.subheader("Número de Leads por Propietario")

    conteo_propietarios = df_filtrado["propietario"].value_counts().reset_index()
    conteo_propietarios.columns = ["Propietario", "Cantidad"]

    fig_propietarios = px.bar(
        conteo_propietarios,
        x="Cantidad",
        y="Propietario",
        orientation="h",
        text="Cantidad",
    )
    fig_propietarios.update_layout(
        xaxis_title="Número de Leads",
        yaxis_title="Propietario",
        yaxis=dict(autorange="reversed"),
        height=600,
    )
    fig_propietarios.update_traces(textposition="outside")

    st.plotly_chart(fig_propietarios, use_container_width=True)
