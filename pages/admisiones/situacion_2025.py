import streamlit as st
import pandas as pd
import os
import plotly.express as px
from datetime import datetime
from responsive import get_screen_size

UPLOAD_FOLDER = "uploaded_admisiones"
EXCEL_FILE = os.path.join(UPLOAD_FOLDER, "matricula_programas_25.xlsx")

# ----------------- Helpers -----------------
def _to_year(series_like):
    dt = pd.to_datetime(series_like, errors="coerce", dayfirst=True)
    return dt.dt.year

def _fill_blank(s: pd.Series, blank_label="(En Blanco)"):
    out = s.astype(str).str.strip()
    out = out.replace(["", "nan", "NaN", "NONE", "None"], blank_label)
    return out.fillna(blank_label)

def _is_blank_series(s: pd.Series):
    """Detecta si el valor está en 'blanco' (sin tocar a '(En Blanco)')"""
    s2 = s.astype(str).str.strip()
    return s2.isin(["", "nan", "NaN", "NONE", "None"])

# ----------------- APP -----------------
def app():
    width, height = get_screen_size()
    is_mobile = width <= 400

    traducciones_meses = {
        "January": "Enero", "February": "Febrero", "March": "Marzo", "April": "Abril",
        "May": "Mayo", "June": "Junio", "July": "Julio", "August": "Agosto",
        "September": "Septiembre", "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
    }
    now = datetime.now()
    mes_actual = traducciones_meses[now.strftime("%B")] + " " + now.strftime("%Y")

    st.markdown(f"<h1>Matrículas por Programa y Propietario - {mes_actual}</h1>", unsafe_allow_html=True)

    # Carga
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name="Contactos")
    except Exception as e:
        st.error(f"No se pudo cargar el archivo: {e}")
        return

    if "Programa" not in df.columns or "propietario" not in df.columns:
        st.error("Faltan columnas requeridas: 'Programa' o 'propietario'")
        return

    # Normalización sin perder filas
    df["Programa"] = _fill_blank(df["Programa"])
    df["propietario"] = _fill_blank(df["propietario"])

    # Clasificación de programas
    programa_mapping = {
        "Certificado oficial SAP S/4HANA Finance": "CERTIFICACIÓN SAP S/4HANA",
        "Consultoría SAP S4HANA Ventas": "CERTIFICACIÓN SAP S/4HANA",
        "Master en Auditoría de Protección de Datos, Gestión de Riesgos y Cyber Compliance": "MÁSTER DPO",
        "Máster Profesional en Auditoría de Protección de Datos, Gestión de Riesgos y Cyber Compliance": "MÁSTER DPO",
        "Máster en Dirección de Compliance & Protección de Datos": "MÁSTER DPO",
        "Master en Dirección de Ciberseguridad, Hacking Ético y Seguridad Ofensiva": "MÁSTER CIBERSEGURIDAD",
        "Máster en Dirección de Ciberseguridad, Hacking Ético y Seguridad Ofensiva": "MÁSTER CIBERSEGURIDAD",
        "Master en Gestión Eficiente de Energías Renovables": "MÁSTER EERR",
        "Máster en Gestión Eficiente de las Energías Renovables": "MÁSTER EERR",
        "Programa Movilidad California": "PROGRAMA CALIFORNIA",
        "Máster en RRHH: Dirección de Personas, Desarrollo de Talento y Gestión Laboral": "MÁSTER RRHH",
        "Master en RRHH, dirección de personas, desarrollo de talento y gestión laboral": "MÁSTER RRHH",
        "Máster en Inteligencia Artificial": "MÁSTER IA"
    }
    df["programa_categoria"] = df["Programa"].map(programa_mapping).fillna(df["Programa"])

    # Selector de Año (sin "Todos")
    col_ultimo = "último contacto" if "último contacto" in df.columns else ("Último contacto" if "Último contacto" in df.columns else None)
    if not col_ultimo:
        st.error("No se encontró la columna 'último contacto' / 'Último contacto'.")
        return

    df["_anio"] = _to_year(df[col_ultimo])
    df = df[df["_anio"].notna()].copy()
    anios_disponibles = sorted(df["_anio"].unique().tolist(), reverse=True)
    if not anios_disponibles:
        st.info("No hay años disponibles en la columna de último contacto.")
        return

    st.subheader("")
    anio_sel = st.selectbox("Año", [str(int(a)) for a in anios_disponibles], index=0)
    df = df[df["_anio"] == int(anio_sel)]
    titulo_anio = anio_sel

    # Filtro por programa
    st.subheader("Selecciona un programa")
    programas_unicos = sorted(df["programa_categoria"].unique())
    programa_seleccionado = st.selectbox("Programa", ["Todos"] + programas_unicos)
    df_filtrado = df if programa_seleccionado == "Todos" else df[df["programa_categoria"] == programa_seleccionado]

    # UI
    col1, col2 = st.columns(2)

    with col1:
        st.subheader(f"Total matrículas — {titulo_anio}")
        conteo_programa = df_filtrado["programa_categoria"].value_counts().reset_index()
        conteo_programa.columns = ["programa", "cantidad"]

        if conteo_programa.empty:
            st.info("No hay datos para los filtros seleccionados.")
        else:
            colores = px.colors.qualitative.Plotly
            color_map = {row["programa"]: colores[i % len(colores)] for i, row in conteo_programa.iterrows()}
            fig1 = px.bar(
                conteo_programa, x="programa", y="cantidad",
                color="programa", text="cantidad",
                color_discrete_map=color_map
            )
            fig1.update_layout(
                xaxis_title=None, yaxis_title="Cantidad",
                showlegend=not is_mobile, xaxis=dict(showticklabels=False)
            )
            st.plotly_chart(fig1, use_container_width=True)

            if is_mobile:
                st.markdown("---")
                st.markdown("<h4 style='font-size: 1rem;'>Detalle de programas</h4>", unsafe_allow_html=True)
                for _, row in conteo_programa.iterrows():
                    color = color_map[row["programa"]]
                    st.markdown(
                        f"<div style='font-size: 12px; margin-bottom: 4px;'>"
                        f"<span style='display: inline-block; width: 10px; height: 10px; background-color: {color}; margin-right: 6px; border-radius: 2px;'></span>"
                        f"{row['programa']}</div>",
                        unsafe_allow_html=True
                    )

    with col2:
        st.subheader("Propietarios")
        propietarios = ["Todos"] + sorted(df_filtrado["propietario"].unique())
        propietario_seleccionado = st.selectbox("Selecciona un propietario", propietarios)

        df_final = df_filtrado if propietario_seleccionado == "Todos" else df_filtrado[df_filtrado["propietario"] == propietario_seleccionado]

        # Métrica principal: label dinámico según año seleccionado
        current_year = datetime.now().year
        label_kpi = "Matrícula en curso" if int(anio_sel) == current_year else f"Matrícula {anio_sel}"
        st.metric(label=label_kpi, value=df_final.shape[0])

        if propietario_seleccionado == "Todos":
            conteo_prop = df_final["propietario"].value_counts().reset_index()
            conteo_prop.columns = ["propietario", "cantidad"]
            if not conteo_prop.empty:
                fig2 = px.funnel(conteo_prop, y="propietario", x="cantidad", text="cantidad", color_discrete_sequence=["#1f77b4"])
                fig2.update_layout(xaxis_title="Cantidad", yaxis_title=None, showlegend=False)
                fig2.update_traces(texttemplate="%{x}", textfont_size=16, textposition="inside")
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No hay propietarios para los filtros aplicados.")
        else:
            tabla_programas = (
                df_final.groupby("programa_categoria").size().reset_index(name="Cantidad")
                .sort_values("Cantidad", ascending=False)
            )
            if not tabla_programas.empty:
                st.dataframe(tabla_programas, use_container_width=True)
            else:
                st.info("Este propietario no tiene registros para el filtro actual.")

    # --- Promedio de PVP (suma / nº filas) ---
    st.markdown("---")
    if "PVP" in df_final.columns and not df_final.empty:
        df_final = df_final.copy()
        df_final["PVP"] = pd.to_numeric(df_final["PVP"], errors="coerce").fillna(0)
        promedio_pvp = df_final["PVP"].sum() / df_final.shape[0]
        st.metric(label="Promedio de PVP", value=f"{promedio_pvp:,.0f} €")
    else:
        st.metric(label="Promedio de PVP", value="0 €")

    # ===== Análisis =====
    st.subheader("📊 Análisis")
    col3, col4 = st.columns([1, 1])

    with col3:
        st.subheader("Forma de Pago")
        if "Forma de Pago" in df_final.columns and not df_final.empty:
            tmp = df_final.copy()
            # Para el gráfico: visualizamos con "(En Blanco)"
            forma_pago_str = tmp["Forma de Pago"].astype(str).str.strip()
            tmp["Forma de Pago (vist)"] = forma_pago_str.replace(["", "nan", "NaN", "NONE", "None"], "(En Blanco)")
            conteo_pago = tmp["Forma de Pago (vist)"].value_counts().reset_index()
            conteo_pago.columns = ["forma_pago", "cantidad"]

            if not conteo_pago.empty:
                formas_pago = conteo_pago["forma_pago"].tolist()
                color_palette = px.colors.qualitative.Bold
                color_map_fp = {fp: color_palette[i % len(color_palette)] for i, fp in enumerate(formas_pago)}
                fig3 = px.pie(conteo_pago, names="forma_pago", values="cantidad", hole=0.4, color="forma_pago", color_discrete_map=color_map_fp)
                fig3.update_layout(showlegend=True, legend_title="Forma de pago")
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("No hay datos de 'Forma de Pago' para los filtros seleccionados.")
        else:
            st.info("La columna 'Forma de Pago' no está disponible en el archivo.")

    with col4:
        st.subheader("Suma de PVP por Forma de Pago")
        if "Forma de Pago" in df_final.columns and "PVP" in df_final.columns and not df_final.empty:
            tmp = df_final.copy()
            tmp["Forma de Pago"] = tmp["Forma de Pago"].astype(str).str.strip().replace(
                ["", "nan", "NaN", "NONE", "None"], "(En Blanco)"
            )
            tmp["PVP"] = pd.to_numeric(tmp["PVP"], errors="coerce").fillna(0)
            suma_pvp = tmp.groupby("Forma de Pago")["PVP"].sum().reset_index().sort_values("PVP", ascending=True)

            fig4 = px.funnel(suma_pvp, y="Forma de Pago", x="PVP", color="Forma de Pago")
            fig4.update_layout(width=650, xaxis_title="Suma de PVP (€)", yaxis=dict(showticklabels=False), showlegend=False)
            fig4.update_traces(texttemplate="%{x:,.0f} €", textfont_size=16, textposition="inside")
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("No hay datos suficientes para mostrar el embudo de PVP por forma de pago.")

    # ======= TABLA A PANTALLA COMPLETA (sin 'Motivo' y PVP en blanco como texto) =======
    st.markdown("---")
    st.subheader("Registros con PVP o Forma de Pago en blanco")

    if "PVP" in df_final.columns and "Forma de Pago" in df_final.columns and not df_final.empty:
        tmp = df_final.copy()

        # Flags de blanco (sin reemplazar por '(En Blanco)' aún)
        fp_blank_flag = _is_blank_series(tmp["Forma de Pago"])
        pvp_blank_flag = _is_blank_series(tmp["PVP"])

        # PVP numérico para los que NO están en blanco (para formatear)
        tmp["PVP_NUM"] = pd.to_numeric(tmp["PVP"], errors="coerce")

        # Filtrar registros donde falta FP o PVP
        faltantes = tmp[fp_blank_flag | pvp_blank_flag].copy()
        if not faltantes.empty:
            # Forma de pago visible
            faltantes["Forma de Pago"] = faltantes["Forma de Pago"].astype(str).str.strip().replace(
                ["", "nan", "NaN", "NONE", "None"], "(En Blanco)"
            )
            # PVP visible: si estaba blanco -> "(En Blanco)", si no -> formato €
            def _pvp_display(row):
                val_raw = str(row["PVP"]).strip()
                if val_raw in ["", "nan", "NaN", "NONE", "None"]:
                    return "(En Blanco)"
                val = pd.to_numeric(row["PVP_NUM"], errors="coerce")
                if pd.isna(val):
                    return "(En Blanco)"
                return f"{val:,.0f} €".replace(",", ".")
            faltantes["PVP"] = faltantes.apply(_pvp_display, axis=1)

            st.dataframe(
                faltantes[["propietario", "Programa", "programa_categoria", "Forma de Pago", "PVP"]]
                .reset_index(drop=True),
                use_container_width=True
            )
        else:
            st.info("No hay registros con PVP o Forma de Pago en blanco para este filtro.")
    else:
        st.info("No hay datos suficientes para mostrar el detalle de faltantes.")