import streamlit as st
import pandas as pd
import os
import plotly.express as px
import unicodedata
from datetime import datetime
from responsive import get_screen_size

UPLOAD_FOLDER = "uploaded_admisiones"
LEADS_GENERADOS_FILE = os.path.join(UPLOAD_FOLDER, "leads_generados.xlsx")

def app():
    width, height = get_screen_size()
    is_mobile = width <= 400

    traducciones_meses = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
        7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }

    if not os.path.exists(LEADS_GENERADOS_FILE):
        st.warning("📭 No se ha subido el archivo de Leads Generados aún.")
        return

    df = pd.read_excel(LEADS_GENERADOS_FILE)
    df.columns = df.columns.str.strip().str.lower()

    if 'creado' not in df.columns:
        st.error("❌ El archivo debe contener la columna 'creado'.")
        return

    df['creado'] = pd.to_datetime(df['creado'], errors='coerce')
    df = df[df['creado'].notna()]

    df["mes_num"] = df["creado"].dt.month
    df["anio"] = df["creado"].dt.year
    df["mes_nombre"] = df["mes_num"].map(traducciones_meses)
    df["mes_anio"] = df["mes_nombre"] + " " + df["anio"].astype(str)

    st.subheader("Filtros")

    meses_disponibles = df[["mes_anio", "mes_num", "anio"]].dropna().drop_duplicates()
    meses_disponibles = meses_disponibles.sort_values(["anio", "mes_num"])
    opciones_meses = ["Todos"] + meses_disponibles["mes_anio"].tolist()
    mes_seleccionado = st.selectbox("Selecciona un Mes:", opciones_meses)

    df_filtrado = df.copy()
    if mes_seleccionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["mes_anio"] == mes_seleccionado]

    if 'programa' not in df.columns or 'propietario' not in df.columns:
        st.error("❌ El archivo debe contener las columnas 'programa' y 'propietario'.")
        return

    df_filtrado["programa"] = df_filtrado["programa"].astype(str).str.strip().replace(["", "nan", "None"], "(En Blanco)")
    df_filtrado["propietario"] = df_filtrado["propietario"].astype(str).str.strip().replace(["", "nan", "None"], "(En Blanco)")

    # === CLASIFICACIÓN POR NOMBRE NORMALIZADO ===
    CATEGORIAS_EXACTAS = {
        "MÁSTER IA": [
            "máster en inteligencia artificial",
            "máster integral en inteligencia artificial",
            "máster ia"
        ],
        "MÁSTER RRHH": [
            "máster recursos humanos rrhh: dirección de personas, desarrollo del talento y gestión laboral",
            "máster en rrhh: dirección de personas, desarrollo de talento y gestión laboral",
            "máster rrhh",
            "master en rrhh, dirección de personas, desarrollo de talento y gestión laboral"
        ],
        "MÁSTER CIBERSEGURIDAD": [
            "máster en dirección de ciberseguridad, hacking ético y seguridad ofensiva",
            "master en direccion de ciberseguridad, hacking etico y seguridad ofensiva",
            "la importancia de la ciberseguridad y privacidad",
        ],
        "CERTIFICACIÓN SAP S/4HANA": [
            "certificado sap s/4hana finance",
            "certificado oficial sap s/4hana finance",
            "certificado oficial sap s/4hana sourcing and procurement",
            "certificado oficial sap s/4hana logística",
            "consultoría sap s4hana finanzas",
            "consultoría sap bw4/hana",
            "consultoría sap s4hana planificación de la producción y fabricación",
            "sap btp: la plataforma para la transformación digital",
            "máster en dirección financiera y consultoría funcional sap s/4hana finance"
        ],
        "MÁSTER DPO": [
            "máster profesional en auditoría de protección de datos, gestión de riesgos y cyber compliance",
            "master en auditoría de protección de datos, gestión de riesgos y cyber compliance",
            "máster en dirección de compliance & protección de datos",
            "máster en auditoría de protección de datos, gestión de riesgos y cyber compliance​"
        ],
        "MÁSTER EERR": [
            "master en gestión eficiente de energías renovables",
            "master profesional en energías renovables, redes inteligentes y movilidad eléctrica",
            "máster en gestión eficiente de las energías renovables",
            "máster en bim y gestión eficiente de la energía (no usar)"
        ],
        "MBA + RRHH": [
            "doble máster oficial en rrhh + mba",
            "doble máster en rrhh + mba",
            "doble máster rrhh + mba",
            "doble máster en dirección financiera + dirección rrhh"
        ],
        "PROGRAMA CALIFORNIA": [
            "programa movilidad california",
            "california state university"
        ]
    }

    def normalizar(texto):
        texto = texto.lower()
        texto = unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode("utf-8")
        return texto.strip()

    def clasificar_programa(nombre):
        nombre_limpio = normalizar(nombre)
        for categoria, nombres in CATEGORIAS_EXACTAS.items():
            if nombre_limpio in [normalizar(n) for n in nombres]:
                return categoria
        return "SIN CLASIFICAR"

    df_filtrado["programa_categoria"] = df_filtrado["programa"].apply(clasificar_programa)

    def ajustar_programa_final(row):
        if row["programa_categoria"] == "SIN CLASIFICAR":
            return row["programa"]
        return row["programa_categoria"]

    df_filtrado["programa_final"] = df_filtrado.apply(ajustar_programa_final, axis=1)

    # === FILTROS ===
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        programas = ["Todos"] + sorted(df_filtrado["programa_final"].unique())
        programa_seleccionado = st.selectbox("Selecciona un Programa:", programas)
        if programa_seleccionado != "Todos":
            df_filtrado = df_filtrado[df_filtrado["programa_final"] == programa_seleccionado]

    with col_f2:
        propietarios = ["Todos"] + sorted(df_filtrado["propietario"].unique())
        propietario_seleccionado = st.selectbox("Selecciona un Propietario:", propietarios)
        if propietario_seleccionado != "Todos":
            df_filtrado = df_filtrado[df_filtrado["propietario"] == propietario_seleccionado]

    # === GRÁFICOS ===
    leads_por_mes = df_filtrado.groupby(["mes_anio", "mes_num", "anio"]).size().reset_index(name="Cantidad")
    leads_por_mes = leads_por_mes.sort_values(["anio", "mes_num"])
    leads_por_mes["Mes"] = leads_por_mes["mes_anio"]
    leads_por_mes["Etiqueta"] = leads_por_mes.apply(lambda row: f"{row['Mes']} - {row['Cantidad']}", axis=1)

    if is_mobile:
        fig_leads = px.bar(leads_por_mes, x="Cantidad", y="Mes", orientation="h", text="Cantidad", height=500)
        fig_leads.update_layout(xaxis_title="Cantidad de Leads", yaxis_title="Mes", margin=dict(l=20, r=20, t=40, b=40))
        fig_leads.update_traces(textposition="outside")
    else:
        fig_leads = px.pie(leads_por_mes, names="Etiqueta", values="Cantidad", hole=0.4)
        fig_leads.update_layout(showlegend=True, legend_title="Mes", margin=dict(l=20, r=20, t=40, b=40))

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📆 Total de Leads por Mes")
        st.plotly_chart(fig_leads, use_container_width=True)

    with col2:
        conteo_programas = df_filtrado["programa_final"].value_counts().reset_index()
        conteo_programas.columns = ["Programa", "Cantidad"]
        total_programas = conteo_programas["Cantidad"].sum()
        st.subheader(f"📘 Total de Leads por Programa – TOTAL: {total_programas}")
        st.dataframe(conteo_programas.style.background_gradient(cmap="Blues"), use_container_width=True)

    # === POR PROPIETARIO ===
    st.subheader("📈 Leads por Propietario")
    conteo_propietarios = df_filtrado["propietario"].value_counts().reset_index()
    conteo_propietarios.columns = ["Propietario", "Cantidad"]
    fig_prop = px.bar(conteo_propietarios, x="Cantidad", y="Propietario", orientation="h", text="Cantidad")
    fig_prop.update_layout(xaxis_title="Número de Leads", yaxis=dict(autorange="reversed"), height=500,
                           margin=dict(l=20, r=20, t=40, b=40))
    fig_prop.update_traces(textposition="outside")
    st.plotly_chart(fig_prop, use_container_width=True)

    # === ORIGEN ===
    st.subheader("📥 Origen del Lead")
    if 'origen lead' in df_filtrado.columns:
        conteo_origen = df_filtrado['origen lead'].astype(str).value_counts().reset_index()
        conteo_origen.columns = ["Origen Lead", "Cantidad"]
        st.dataframe(conteo_origen.style.background_gradient(cmap="Reds"), use_container_width=True)
    else:
        st.info("ℹ️ No se encontró la columna 'origen lead'.")

    # === DETALLE EN BLANCO ===
    if programa_seleccionado.lower() == "(en blanco)":
        st.markdown("### 🧾 Detalle de Leads con Programa (En Blanco)")
        columnas_posibles = [c for c in df_filtrado.columns if c in ["propietario", "nombre", "apellidos"]]
        if len(columnas_posibles) >= 2:
            st.dataframe(df_filtrado[columnas_posibles], use_container_width=True)
        else:
            st.warning("⚠️ Faltan columnas 'nombre' y/o 'apellidos' para mostrar el detalle.")
