import streamlit as st
import pandas as pd
import os
import plotly.express as px
from datetime import datetime

UPLOAD_FOLDER = "uploaded_admisiones"
LEADS_GENERADOS_FILE = os.path.join(UPLOAD_FOLDER, "leads_generados.xlsx")

def app():
    traducciones_meses = {
        "January": "Enero", "February": "Febrero", "March": "Marzo", "April": "Abril",
        "May": "Mayo", "June": "Junio", "July": "Julio", "August": "Agosto",
        "September": "Septiembre", "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
    }

    if not os.path.exists(LEADS_GENERADOS_FILE):
        st.warning("📭 No se ha subido el archivo de Leads Generados aún.")
        return

    df = pd.read_excel(LEADS_GENERADOS_FILE)
    df.columns = df.columns.str.strip().str.lower()

    if 'creado' not in df.columns:
        st.error("❌ El archivo debe contener la columna 'creado' para el filtro por mes.")
        return

    df["creado"] = pd.to_datetime(df["creado"], dayfirst=True, errors='coerce')
    df["mes_num"] = df["creado"].dt.month
    df["anio"] = df["creado"].dt.year
    df["mes_anio"] = df["creado"].dt.month_name().map(traducciones_meses) + " " + df["anio"].astype(str)

    st.subheader("Filtros")
    meses_disponibles = df[["mes_anio", "mes_num", "anio"]].dropna().drop_duplicates()
    meses_disponibles = meses_disponibles.sort_values(["anio", "mes_num"])
    opciones_meses = ["Todos"] + meses_disponibles["mes_anio"].tolist()
    mes_seleccionado = st.selectbox("Selecciona un Mes:", opciones_meses)

    df_filtrado = df.copy()
    if mes_seleccionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["mes_anio"] == mes_seleccionado]

    if 'programa' not in df.columns or 'propietario' not in df.columns or 'etapa de oportunidad activa' not in df.columns:
        st.error("❌ El archivo debe contener las columnas 'programa', 'propietario' y 'etapa de oportunidad activa'.")
        return

    df_filtrado["programa"] = df_filtrado["programa"].astype(str).str.strip()
    df_filtrado["propietario"] = df_filtrado["propietario"].astype(str).str.strip()
    df_filtrado["etapa de oportunidad activa"] = df_filtrado["etapa de oportunidad activa"].astype(str).str.strip()
    df_filtrado.replace(["nan", "None", ""], "(En Blanco)", inplace=True)

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        programas = ["Todos"] + sorted(df_filtrado["programa"].unique())
        programa_seleccionado = st.selectbox("Selecciona un Programa:", programas)
        if programa_seleccionado != "Todos":
            df_filtrado = df_filtrado[df_filtrado["programa"] == programa_seleccionado]

    with col_f2:
        propietarios = ["Todos"] + sorted(df_filtrado["propietario"].unique())
        propietario_seleccionado = st.selectbox("Selecciona un Propietario:", propietarios)
        if propietario_seleccionado != "Todos":
            df_filtrado = df_filtrado[df_filtrado["propietario"] == propietario_seleccionado]

    # VISUALIZACIÓN SI SE ELIGE "TODOS"
    if mes_seleccionado == "Todos":
        col_intro1, col_intro2 = st.columns(2)

        with col_intro1:
            st.subheader("📆 Total de Leads por Mes")
            leads_por_mes = df.groupby(["mes_anio", "mes_num", "anio"]).size().reset_index(name="Cantidad")
            leads_por_mes = leads_por_mes.sort_values(["anio", "mes_num"])
            leads_por_mes["Mes"] = leads_por_mes["mes_anio"]
            leads_por_mes["Etiqueta"] = leads_por_mes.apply(
                lambda row: f"{row['Mes']} - {row['Cantidad']}", axis=1
            )
            fig_leads_mes = px.pie(leads_por_mes, names="Etiqueta", values="Cantidad", hole=0.4)
            fig_leads_mes.update_layout(showlegend=True, legend_title="Mes")
            st.plotly_chart(fig_leads_mes, use_container_width=True)

        with col_intro2:
            st.subheader("📘Total de leads por Programa")
            conteo_programas_total = df["programa"].value_counts().reset_index()
            conteo_programas_total.columns = ["Programa", "Cantidad"]
            conteo_programas_total = conteo_programas_total.sort_values("Cantidad", ascending=False)
            st.dataframe(conteo_programas_total.style.background_gradient(cmap="Blues"), use_container_width=True)

    st.markdown("---")

    # DASHBOARDS CON FILTROS APLICADOS
    col1, col2 = st.columns(2)

    with col1:
        conteo_programas = df_filtrado["programa"].value_counts().reset_index()
        conteo_programas.columns = ["Programa", "Cantidad"]

        total_leads = conteo_programas["Cantidad"].sum()
        st.subheader(f"📘 Leads por Programa –  TOTAL: {total_leads}")

        # Ya no se inserta fila de total aquí
        st.dataframe(conteo_programas.style.background_gradient(cmap="Blues"), use_container_width=True)

    with col2:
        conteo_propietarios = df_filtrado["propietario"].value_counts().reset_index()
        conteo_propietarios.columns = ["Propietario", "Cantidad"]

        total_propietarios = conteo_propietarios["Cantidad"].sum()
        st.subheader(f"📈 Leads por Propietario –  TOTAL: {total_propietarios}")

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
            height=500,
        )
        fig_propietarios.update_traces(textposition="outside")
        st.plotly_chart(fig_propietarios, use_container_width=True)

    # ORIGEN DEL LEAD
    st.subheader("📥 Origen del Lead")
    if 'origen lead' in df_filtrado.columns:
        conteo_origen = df_filtrado['origen lead'].value_counts().reset_index()
        conteo_origen.columns = ["Origen Lead", "Suma de Leads"]
        st.dataframe(conteo_origen.style.background_gradient(cmap="Reds"), use_container_width=True)
    else:
        st.info("ℹ️ No se encontró la columna 'origen lead' en el archivo.")

    # DETALLE EN BLANCO
    if programa_seleccionado.lower() == "(en blanco)":
        st.markdown("### 🧾 Detalle de Leads con Programa (En Blanco)")
        if all(col in df_filtrado.columns for col in ["propietario", "nombre", "apellidos"]):
            df_blanco = df_filtrado[df_filtrado["programa"].str.lower() == "(en blanco)"]
            st.dataframe(df_blanco[["propietario", "nombre", "apellidos"]], use_container_width=True)
        else:
            st.warning("⚠️ Faltan columnas 'nombre' y/o 'apellidos' para mostrar el detalle.")
