import streamlit as st
import pandas as pd
import plotly.express as px
import os
import unicodedata
from datetime import datetime
from responsive import get_screen_size

# =========================
# RUTAS / CONSTANTES
# =========================
UPLOAD_FOLDER = "uploaded_admisiones"
VENTAS_FILE = os.path.join(UPLOAD_FOLDER, "ventas.xlsx")
PREVENTAS_FILE = os.path.join(UPLOAD_FOLDER, "preventas.xlsx")
ANIO_ACTUAL = 2025

# =========================
# NORMALIZACIÓN DE NOMBRES
# =========================
def _strip_accents_lower(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s

# Mapa de categorías -> lista de palabras clave (todas evaluadas sobre el texto normalizado y sin acentos)
CATEGORIAS_KEYWORDS = {
    "MÁSTER CIBERSEGURIDAD": [
        "ciber", "ciberseguridad", "hacking", "etico", "etico y seguridad", "seguridad ofensiva",
        "seguridad informatica", "ethical hacking", "ofensiva"
    ],
    "MÁSTER RRHH": [
        "rrhh", "recursos humanos", "gestion laboral", "human resources"
    ],
    "MÁSTER EERR": [
        "eerr", "energias", "energia", "energias renovables", "renovables", "energetica"
    ],
    "MÁSTER DPO": [
        "dpo", "delegado de proteccion de datos", "proteccion de datos", "privacidad", "rgpd", "gdpr"
    ],
    "MÁSTER IA": [
        "ia", "inteligencia artificial", "machine learning", "aprendizaje automatico"
    ],
    "CERTIFICACIÓN SAP S/4HANA": [
        "sap", "s/4hana", "certificacion sap", "certificacion s/4hana", "sap s4hana", "sap s 4 hana"
    ],
    "MBA + RRHH": [
        "mba rrhh", "mba + rrhh", "mba y rrhh", "mba recursos humanos"
    ],
    "PROGRAMA CALIFORNIA": [
        "california", "programa california"
    ],
}

def unificar_nombre(valor_original: str) -> str:
    """
    Devuelve la categoría unificada según palabras clave.
    Si no coincide con ninguna, devuelve el valor original sin tocar.
    """
    if not isinstance(valor_original, str) or not valor_original.strip():
        return valor_original
    base = _strip_accents_lower(valor_original)

    # Orden de chequeo: si hay riesgo de solaparse, puedes priorizar categorías moviéndolas arriba/abajo
    for categoria, keywords in CATEGORIAS_KEYWORDS.items():
        for kw in keywords:
            if kw in base:
                return categoria

    # Si no hay match, devolvemos el texto original tal cual
    return valor_original

# =========================
# APP
# =========================
def app():
    try:
        width, height = get_screen_size()
        if not width or not height:
            raise Exception("No screen size")
    except Exception:
        width, height = 1000, 600  # fallback para escritorio

    traducciones_meses = {
        "January": "Enero", "February": "Febrero", "March": "Marzo", "April": "Abril",
        "May": "Mayo", "June": "Junio", "July": "Julio", "August": "Agosto",
        "September": "Septiembre", "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
    }
    orden_meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
                   "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

    if not os.path.exists(VENTAS_FILE):
        st.warning("⚠️ No se ha encontrado el archivo 'ventas.xlsx'.")
        return

    # ======= CARGA DE DATOS =======
    df_ventas = pd.read_excel(VENTAS_FILE)

    # Convertir nombres de columnas a minúsculas (sin acentos) para evitar problemas
    cols_map = {c: _strip_accents_lower(c) for c in df_ventas.columns}
    df_ventas.rename(columns=cols_map, inplace=True)

    # Asegurar columnas clave mínimas
    if "nombre" not in df_ventas.columns or "propietario" not in df_ventas.columns:
        st.warning("❌ El archivo de ventas debe tener columnas 'nombre' y 'propietario'.")
        return

    # Importe a numérico si existe
    if "importe" in df_ventas.columns:
        df_ventas["importe"] = pd.to_numeric(df_ventas["importe"], errors="coerce").fillna(0)

    # Fecha cierre -> año y mes
    if "fecha de cierre" in df_ventas.columns:
        df_ventas["fecha de cierre"] = pd.to_datetime(df_ventas["fecha de cierre"], errors="coerce")
        df_ventas = df_ventas[df_ventas["fecha de cierre"].dt.year == ANIO_ACTUAL]
        if df_ventas.empty:
            st.warning(f"❌ No hay datos de ventas para el año seleccionado ({ANIO_ACTUAL}).")
            return
        df_ventas["mes"] = df_ventas["fecha de cierre"].dt.month_name().map(traducciones_meses)
        df_ventas["mes_num"] = df_ventas["fecha de cierre"].dt.month
    else:
        st.warning("❌ El archivo de ventas no contiene la columna 'fecha de cierre'.")
        return

    # ======= UNIFICACIÓN DE NOMBRES =======
    # Nueva columna 'nombre_unificado' según las reglas
    df_ventas["nombre_unificado"] = df_ventas["nombre"].apply(unificar_nombre)

    # ======= PREVENTAS (opcional) =======
    if os.path.exists(PREVENTAS_FILE):
        df_preventas = pd.read_excel(PREVENTAS_FILE)
        # normalizar columnas preventas
        df_preventas.rename(columns={c: _strip_accents_lower(c) for c in df_preventas.columns}, inplace=True)
        columnas_importe = [col for col in df_preventas.columns if "importe" in col]
        total_preventas_importe = df_preventas[columnas_importe].sum(numeric_only=True).sum() if columnas_importe else 0
        total_preventas_count = df_preventas.shape[0]
    else:
        total_preventas_importe = 0
        total_preventas_count = 0

    # Copia para totales/año
    df_ventas_original = df_ventas.copy()

    # ======= UI =======
    st.subheader("📊 Ventas y Preventas")

    meses_disponibles = (
        df_ventas[["mes", "mes_num"]]
        .dropna()
        .drop_duplicates()
        .sort_values(["mes_num"], ascending=False)
    )
    opciones_meses = ["Todos"] + meses_disponibles["mes"].tolist()
    mes_seleccionado = st.selectbox("Selecciona un Mes:", opciones_meses)

    if mes_seleccionado != "Todos":
        df_ventas = df_ventas[df_ventas["mes"] == mes_seleccionado]

    st.markdown(f"### {mes_seleccionado}")

    # ======= AGRUPACIONES (usando el nombre unificado) =======
    resumen = df_ventas.groupby(["nombre_unificado", "propietario"]).size().reset_index(name="Total Matrículas")
    totales_propietario = resumen.groupby("propietario")["Total Matrículas"].sum().reset_index()
    totales_propietario["propietario_display"] = totales_propietario.apply(
        lambda row: f"{row['propietario']} ({row['Total Matrículas']})", axis=1
    )
    resumen = resumen.merge(
        totales_propietario[["propietario", "propietario_display"]],
        on="propietario",
        how="left"
    )

    orden_propietarios = (
        totales_propietario.sort_values(by="Total Matrículas", ascending=False)["propietario_display"].tolist()
    )
    orden_masters = (
        resumen.groupby("nombre_unificado")["Total Matrículas"].sum().sort_values(ascending=False).index.tolist()
    )

    color_palette = px.colors.qualitative.Plotly + px.colors.qualitative.D3 + px.colors.qualitative.Alphabet
    propietarios_unicos = resumen["propietario_display"].dropna().unique()
    color_map = {prop: color_palette[i % len(color_palette)] for i, prop in enumerate(sorted(propietarios_unicos))}

    # ======= GRÁFICOS =======
    if mes_seleccionado == "Todos":
        df_bar = df_ventas.groupby(["mes", "propietario"], dropna=False).size().reset_index(name="Total Matrículas")
        df_bar = df_bar.merge(totales_propietario[["propietario", "propietario_display"]], on="propietario", how="left")
        totales_mes_grafico = df_bar.groupby("mes")["Total Matrículas"].sum().to_dict()
        df_bar["mes_etiqueta"] = df_bar["mes"].apply(lambda m: f"{m} ({totales_mes_grafico.get(m, 0)})" if pd.notna(m) else m)
        orden_mes_etiqueta = [f"{m} ({totales_mes_grafico[m]})" for m in orden_meses if m in totales_mes_grafico]

        fig = px.bar(
            df_bar,
            x="mes_etiqueta",
            y="Total Matrículas",
            color="propietario_display",
            color_discrete_map=color_map,
            barmode="group",
            text="Total Matrículas",
            title="Distribución Mensual de Matrículas por Propietario",
            width=width,
            height=height
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            xaxis_title="Mes",
            yaxis_title="Total Matrículas",
            margin=dict(l=20, r=20, t=40, b=140),
            xaxis=dict(categoryorder="array", categoryarray=orden_mes_etiqueta),
            legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig)
    else:
        fig = px.scatter(
            resumen,
            x="nombre_unificado",
            y="propietario_display",
            size="Total Matrículas",
            color="propietario_display",
            color_discrete_map=color_map,
            text="Total Matrículas",
            size_max=60,
            width=width,
            height=height
        )
        fig.update_traces(
            textposition="middle center",
            textfont_size=12,
            textfont_color="white",
            marker=dict(line=dict(color="black", width=1.2))
        )
        fig.update_layout(
            xaxis_title="Máster / Programa (Unificado)",
            yaxis_title="Propietario",
            legend=dict(orientation="v", yanchor="top", y=0.98, xanchor="left", x=1.02),
            margin=dict(l=20, r=20, t=40, b=80)
        )
        fig.update_yaxes(categoryorder="array", categoryarray=orden_propietarios[::-1])
        fig.update_xaxes(categoryorder="array", categoryarray=orden_masters)
        st.plotly_chart(fig)

    # ======= TARJETAS DE TOTALES =======
    total_importe = df_ventas["importe"].sum() if "importe" in df_ventas.columns else 0
    total_oportunidades = df_ventas_original.shape[0]
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
            <div style='padding: 1rem; background-color: #f1f3f6; border-left: 5px solid #1f77b4; border-radius: 8px;'>
                <h4 style='margin: 0;'> Importe Total ({mes_seleccionado})</h4>
                <p style='font-size: 1.5rem; font-weight: bold; margin: 0;'>{total_importe:,.2f} €</p>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        cantidad_matriculas = df_ventas.shape[0] if mes_seleccionado != "Todos" else total_oportunidades
        titulo_matriculas = f"Matrículas ({mes_seleccionado})" if mes_seleccionado != "Todos" else f"Matrículas ({ANIO_ACTUAL})"
        st.markdown(f"""
            <div style='padding: 1rem; background-color: #f1f3f6; border-left: 5px solid #1f77b4; border-radius: 8px;'>
                <h4 style='margin: 0;'> {titulo_matriculas}</h4>
                <p style='font-size: 1.5rem; font-weight: bold; margin: 0;'>{cantidad_matriculas}</p>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
            <div style='padding: 1rem; background-color: #f1f3f6; border-left: 5px solid #1f77b4; border-radius: 8px;'>
                <h4 style='margin: 0;'>Preventas</h4>
                <p style='font-size: 1.5rem; font-weight: bold; margin: 0;'>{total_preventas_importe:,.2f} € ({total_preventas_count})</p>
            </div>
        """, unsafe_allow_html=True)

    # ======= TOTALES POR MÁSTER (UNIFICADO) =======
    st.markdown(f"### Totales por Máster — {mes_seleccionado}")
    agrupado = (
        df_ventas.groupby("nombre_unificado")
        .size()
        .reset_index(name="Total Matrículas")
        .sort_values("Total Matrículas", ascending=False)
    )
    for i in range(0, len(agrupado), 3):
        cols = st.columns(3)
        for j in range(3):
            if i + j < len(agrupado):
                row = agrupado.iloc[i + j]
                cols[j].markdown(f"""
                    <div style='padding: 1rem; background-color: #f1f3f6; border-left: 5px solid #2ca02c; border-radius: 8px;'>
                        <h5 style='margin: 0;'>{row['nombre_unificado']}</h5>
                        <p style='font-size: 1.3rem; font-weight: bold; margin: 0;'>{row['Total Matrículas']}</p>
                    </div>
                """, unsafe_allow_html=True)

    # ======= IMPORTE POR PROPIETARIO =======
    if "importe" in df_ventas.columns:
        st.markdown(f"### Importe Total por Propietario ({mes_seleccionado})")
        importe_por_propietario = df_ventas.groupby("propietario")["importe"].sum().reset_index()
        importe_por_propietario = importe_por_propietario.merge(
            df_ventas.groupby("propietario").size().reset_index(name="Total Matrículas"),
            on="propietario", how="left"
        )
        importe_por_propietario["propietario_display"] = importe_por_propietario.apply(
            lambda row: f"{row['propietario']} ({row['Total Matrículas']})", axis=1
        )
        importe_por_propietario = importe_por_propietario.sort_values("importe", ascending=False)

        # Color por propietario (si no existe en el mapa, usa uno por defecto)
        color_fallback = "#1f77b4"
        for i in range(0, len(importe_por_propietario), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(importe_por_propietario):
                    row = importe_por_propietario.iloc[i + j]
                    color = color_map.get(row["propietario_display"], color_fallback)
                    text_color = "#ffffff"
                    cols[j].markdown(f"""
                        <div style='padding: 0.6rem; background-color: {color}; border-radius: 6px;
                                    box-shadow: 1px 1px 5px rgba(0,0,0,0.1); margin-bottom: 0.5rem;'>
                            <h5 style='margin: 0; color: {text_color}; font-size: 1rem;'>{row['propietario_display']}</h5>
                            <p style='font-size: 1.2rem; font-weight: bold; margin: 0; color: {text_color};'>{row['importe']:,.2f} €</p>
                        </div>
                    """, unsafe_allow_html=True)

# Para ejecución directa en Streamlit (si usas "streamlit run este_archivo.py")
if __name__ == "__main__":
    app()
