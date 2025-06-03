import streamlit as st 
import pandas as pd
import os
import plotly.express as px
from datetime import datetime

UPLOAD_FOLDER = "uploaded_admisiones"
EXCEL_FILE = os.path.join(UPLOAD_FOLDER, "matricula_programas_25.xlsx")

def app():
    traducciones_meses = {
        "January": "Enero", "February": "Febrero", "March": "Marzo", "April": "Abril",
        "May": "Mayo", "June": "Junio", "July": "Julio", "August": "Agosto",
        "September": "Septiembre", "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
    }
    now = datetime.now()
    mes_actual = traducciones_meses[now.strftime("%B")] + " " + now.strftime("%Y")

    st.markdown(f"<h1>📊 Matrículas por Programa y Propietario - {mes_actual}</h1>", unsafe_allow_html=True)

    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name="Contactos")
    except Exception as e:
        st.error(f"No se pudo cargar el archivo: {e}")
        return

    if "Programa" not in df.columns or "propietario" not in df.columns:
        st.error("Faltan columnas requeridas: 'Programa' o 'propietario'")
        return

    df["Programa"] = df["Programa"].astype(str).str.strip()
    df["propietario"] = df["propietario"].astype(str).str.strip()
    df = df.replace("nan", pd.NA).dropna(subset=["Programa", "propietario"])

    st.subheader("Selecciona un programa")
    programas_unicos = sorted(df["Programa"].unique())
    programa_seleccionado = st.selectbox("Programa", ["Todos"] + programas_unicos)

    df_filtrado = df if programa_seleccionado == "Todos" else df[df["Programa"] == programa_seleccionado]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Matrículas por programa")
        conteo_programa = df["Programa"].value_counts().reset_index()
        conteo_programa.columns = ["programa", "cantidad"]
        fig1 = px.bar(
            conteo_programa,
            x="programa",
            y="cantidad",
            color="programa",
            text="cantidad"
        )
        fig1.update_layout(
            xaxis_title=None,
            yaxis_title="Cantidad",
            showlegend=True,
            xaxis=dict(showticklabels=False)
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.subheader("Propietarios")

        propietarios = ["Todos"] + sorted(df_filtrado["propietario"].unique())
        propietario_seleccionado = st.selectbox("Selecciona un propietario", propietarios)

        if propietario_seleccionado != "Todos":
            df_filtrado = df_filtrado[df_filtrado["propietario"] == propietario_seleccionado]

        if propietario_seleccionado == "Todos":
            st.metric(label="Total alumnos V2", value=df_filtrado.shape[0])
        else:
            tabla_programas = (
                df_filtrado.groupby("Programa")
                .size()
                .reset_index(name="Cantidad")
                .sort_values("Cantidad", ascending=False)
            )
            if not tabla_programas.empty:
                st.dataframe(tabla_programas, use_container_width=True)
            else:
                st.info("Este propietario no tiene registros para el filtro actual.")

        if propietario_seleccionado == "Todos":
            conteo_prop = df_filtrado["propietario"].value_counts().reset_index()
            conteo_prop.columns = ["propietario", "cantidad"]

            fig2 = px.funnel(
                conteo_prop,
                y="propietario",
                x="cantidad",
                text="cantidad",
                color_discrete_sequence=["#1f77b4"]
            )
            fig2.update_layout(
                xaxis_title="Cantidad",
                yaxis_title=None,
                showlegend=False
            )
            fig2.update_traces(
                texttemplate="%{x}",
                textfont_size=16,
                textposition="inside"
            )
            st.plotly_chart(fig2, use_container_width=True)

    if "PVP" in df_filtrado.columns and not df_filtrado.empty:
        df_filtrado["PVP"] = pd.to_numeric(df_filtrado["PVP"], errors="coerce").fillna(0)
        promedio_pvp = df_filtrado["PVP"].sum() / df_filtrado.shape[0]
        st.metric(label="Promedio de PVP", value=f"{promedio_pvp:,.0f} €")
    else:
        st.metric(label="Promedio de PVP", value="0 €")

    st.markdown("---")
    st.subheader("📊 Análisis")

    col3, col4, col5 = st.columns([1, 1, 1])

    with col3:
        st.subheader("Forma de Pago")

        if "Forma de Pago" in df_filtrado.columns:
            df_filtrado["Forma de Pago"] = (
                df_filtrado["Forma de Pago"]
                .astype(str)
                .str.strip()
                .replace(["nan", "None", ""], "(En Blanco)")
                .fillna("(En Blanco)")
            )

            conteo_pago = df_filtrado["Forma de Pago"].value_counts().reset_index()
            conteo_pago.columns = ["forma_pago", "cantidad"]

            formas_pago = conteo_pago["forma_pago"].tolist()
            color_palette = px.colors.qualitative.Bold
            color_map = {fp: color_palette[i % len(color_palette)] for i, fp in enumerate(formas_pago)}

            fig3 = px.pie(
                conteo_pago,
                names="forma_pago",
                values="cantidad",
                hole=0.4,
                color="forma_pago",
                color_discrete_map=color_map
            )
            fig3.update_layout(
                showlegend=True,
                legend_title="Forma de pago"
            )
            st.plotly_chart(fig3, use_container_width=True)

            st.markdown("### 🧾 Detalle: Pagos 'En Blanco'")
            pagos_en_blanco = df_filtrado[df_filtrado["Forma de Pago"] == "(En Blanco)"]
            if not pagos_en_blanco.empty:
                st.dataframe(
                    pagos_en_blanco[["propietario", "Programa", "Forma de Pago"]].reset_index(drop=True),
                    use_container_width=True
                )
            else:
                st.info("No hay registros con forma de pago '(En Blanco)' para este filtro.")
        else:
            st.info("La columna 'Forma de Pago' no está disponible en el archivo.")

    with col4:
        st.subheader("Suma de PVP por Forma de Pago")

        if "Forma de Pago" in df_filtrado.columns and "PVP" in df_filtrado.columns:
            suma_pvp = df_filtrado.groupby("Forma de Pago")["PVP"].sum().reset_index()
            suma_pvp = suma_pvp.sort_values("PVP", ascending=True)

            fig4 = px.funnel(
                suma_pvp,
                y="Forma de Pago",
                x="PVP",
                color="Forma de Pago",
                color_discrete_map=color_map
            )
            fig4.update_layout(
                width=650,
                xaxis_title="Suma de PVP (€)",
                yaxis=dict(showticklabels=False),
                showlegend=False
            )
            fig4.update_traces(
                texttemplate="%{x:,.0f} €",
                textfont_size=16,
                textposition="inside"
            )
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("No hay datos suficientes para mostrar el embudo de PVP por forma de pago.")

    with col5:
        st.subheader("Total por Origen")

        if "origen" in df_filtrado.columns:
            df_filtrado["origen"] = (
                df_filtrado["origen"]
                .astype(str)
                .str.strip()
                .replace(["nan", "None", ""], "(En Blanco)")
                .fillna("(En Blanco)")
            )

            conteo_origen = df_filtrado["origen"].value_counts().reset_index()
            conteo_origen.columns = ["Origen", "Cantidad"]

            total = conteo_origen["Cantidad"].sum()
            total_row = pd.DataFrame([{"Origen": "TOTAL", "Cantidad": total}])
            tabla_origen = pd.concat([conteo_origen, total_row], ignore_index=True)

            st.dataframe(tabla_origen, use_container_width=True)
        else:
            st.info("La columna 'origen' no está disponible en el archivo.")