# principal.py
import os
import re
import unicodedata
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

UPLOAD_FOLDER = "uploaded_admisiones"
ARCHIVO_DESARROLLO = os.path.join(UPLOAD_FOLDER, "desarrollo_profesional.xlsx")

NBSP = "\u00A0"

def _norm_spaces(text: str) -> str:
    s = unicodedata.normalize("NFKC", str(text)).replace(NBSP, " ")
    return " ".join(s.strip().split())

def clean_headers(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [
        _norm_spaces(col).upper() if _norm_spaces(col) != "" else f'UNNAMED_{i}'
        for i, col in enumerate(df.columns)
    ]
    if len(df.columns) != len(set(df.columns)):
        st.warning("⚠️ Se encontraron columnas duplicadas. Se eliminarán automáticamente.")
        df = df.loc[:, ~df.columns.duplicated()]
    return df

def es_vacio(valor):
    if pd.isna(valor):
        return True
    v = unicodedata.normalize("NFKC", str(valor)).replace(NBSP, " ").strip().upper()
    return v == ""

def limpiar_riesgo(valor) -> float:
    if isinstance(valor, (int, float)):
        return float(valor)
    if pd.isna(valor):
        return 0.0
    v = re.sub(r"[^\d,\.]", "", str(valor))
    v = v.replace(".", "").replace(",", ".")
    try:
        return float(v)
    except Exception:
        return 0.0

def render(df: pd.DataFrame | None = None):
    st.title("📊 Principal - Área de Empleo")

    # 🔄 Botón para recargar / limpiar caché
    if st.button("🔄 Recargar / limpiar caché"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("Caché limpiada. Datos recargados.")

    if df is None:
        if not os.path.exists(ARCHIVO_DESARROLLO):
            st.warning("⚠️ No se encontró el archivo.")
            return
        try:
            df = pd.read_excel(ARCHIVO_DESARROLLO, sheet_name="GENERAL")
        except Exception:
            df = pd.read_excel(ARCHIVO_DESARROLLO)

    df = clean_headers(df)

    rename_alias = {
        "PRÁCTCAS/GE": "PRÁCTICAS/GE",
        "PRACTICAS/GE": "PRÁCTICAS/GE",
        "CONSULTOR_EIP": "CONSULTOR EIP"
    }
    df = df.rename(columns={k: v for k, v in rename_alias.items() if k in df.columns})

    cols_req = [
        "CONSECUCIÓN GE", "INAPLICACIÓN GE", "DEVOLUCIÓN GE",
        "AREA", "PRÁCTICAS/GE", "CONSULTOR EIP", "RIESGO ECONÓMICO", "FIN CONV",
        "NOMBRE", "APELLIDOS"
    ]
    faltantes = [c for c in cols_req if c not in df.columns]
    if faltantes:
        st.error(f"❌ Faltan columnas: {', '.join(faltantes)}")
        return

    # Activo = las 3 columnas de estado vacías
    df["ES_ACTIVO"] = (
        df["CONSECUCIÓN GE"].map(es_vacio) &
        df["INAPLICACIÓN GE"].map(es_vacio) &
        df["DEVOLUCIÓN GE"].map(es_vacio)
    )

    # Normalizaciones de texto
    for col in ["PRÁCTICAS/GE", "CONSULTOR EIP", "AREA"]:
        df[col] = df[col].where(df[col].notna(), pd.NA).map(
            lambda x: _norm_spaces(x) if pd.notna(x) else x
        ).str.upper()

    # Base: activos con área válida
    df_base = df[df["ES_ACTIVO"]].copy()
    df_base = df_base[
        df_base["AREA"].notna() &
        (~df_base["AREA"].isin(["", "NO ENCONTRADO", "NAN", "<NA>"]))
    ]

    # Filtros UI
    opciones_practicas = sorted(df_base["PRÁCTICAS/GE"].dropna().unique().tolist())
    opciones_consultores = sorted(df_base["CONSULTOR EIP"].dropna().unique().tolist())

    c1, c2 = st.columns(2)
    with c1:
        seleccion_practicas = st.multiselect("Selecciona PRÁCTICAS/GE:", opciones_practicas, default=opciones_practicas)
    with c2:
        seleccion_consultores = st.multiselect("Selecciona CONSULTOR EIP:", opciones_consultores, default=opciones_consultores)

    df_filtrado = df_base[
        df_base["PRÁCTICAS/GE"].isin(seleccion_practicas) &
        df_base["CONSULTOR EIP"].isin(seleccion_consultores)
    ].copy()

    if df_filtrado.empty:
        st.info("No hay datos disponibles para la selección realizada.")
        return

    # Gráfico de barras por área
    conteo_area = df_filtrado["AREA"].value_counts().reset_index()
    conteo_area.columns = ["Área", "Cantidad"]

    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=conteo_area["Área"],
        y=conteo_area["Cantidad"],
        marker=dict(color=conteo_area["Cantidad"], colorscale=[[0, "#ffff00"], [1, "#1f77b4"]], line=dict(color="black", width=1.5)),
    ))
    for x, y in zip(conteo_area["Área"], conteo_area["Cantidad"]):
        fig_bar.add_annotation(
            x=x, y=y, text=f"<b>{y}</b>", showarrow=False, yshift=5,
            font=dict(color="white", size=13), align="center",
            bgcolor="black", borderpad=4
        )
    fig_bar.update_layout(
        height=500, xaxis_title="Área", yaxis_title="Número de Alumnos",
        yaxis=dict(range=[0, max(conteo_area["Cantidad"]) * 1.2]),
        plot_bgcolor="white",
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # KPIs
    total_alumnos = len(df_filtrado)
    hoy = pd.to_datetime("today").normalize()

    df_ge_activos = df_filtrado[df_filtrado["PRÁCTICAS/GE"] == "GE"].copy()
    df_ge_activos["FIN CONV"] = pd.to_datetime(df_ge_activos["FIN CONV"], errors="coerce")
    df_ge_activos["FECHA_RIESGO"] = df_ge_activos["FIN CONV"] + pd.DateOffset(months=3)

    mask_riesgo = (
        df_ge_activos["FECHA_RIESGO"].notna() &
        (df_ge_activos["FECHA_RIESGO"] <= hoy)
    )
    df_riesgo = df_ge_activos.loc[mask_riesgo].copy()
    df_riesgo["RIESGO ECONÓMICO"] = df_riesgo["RIESGO ECONÓMICO"].map(limpiar_riesgo)

    suma_riesgo = df_riesgo["RIESGO ECONÓMICO"].sum()
    suma_riesgo_fmt = f"{suma_riesgo:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
    total_ge_indicador = len(df_riesgo)

    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("🎯 Total Alumnos", total_alumnos)
    with k2:
        st.metric("📌 ALUMNO RIESGO TRIM", total_ge_indicador)
    with k3:
        st.metric("💰 RIESGO ECONOMICO", suma_riesgo_fmt)

    # =================== DISTRIBUCIÓN ===================
    st.markdown("---")
    st.subheader("📊 Distribución")

    colpie1, colpie2 = st.columns(2)

    with colpie1:
        conteo_practicas = df_filtrado["PRÁCTICAS/GE"].value_counts().reset_index()
        conteo_practicas.columns = ["Tipo", "Cantidad"]
        fig_pie = px.pie(conteo_practicas, names="Tipo", values="Cantidad")
        fig_pie.update_traces(textposition="inside", textinfo="label+percent+value")
        fig_pie.update_layout(title="Distribución por Tipo", height=500)
        st.plotly_chart(fig_pie, use_container_width=True)

    with colpie2:
        df_filtrado_consultores = df_filtrado[
            df_filtrado["CONSULTOR EIP"].notna() &
            (df_filtrado["CONSULTOR EIP"].str.upper() != "NO ENCONTRADO")
        ]
        conteo_consultor = df_filtrado_consultores["CONSULTOR EIP"].value_counts().reset_index()
        conteo_consultor.columns = ["Consultor", "Cantidad"]
        fig_pie_consultor = px.pie(conteo_consultor, names="Consultor", values="Cantidad")
        fig_pie_consultor.update_traces(textposition="inside", textinfo="label+percent+value")
        fig_pie_consultor.update_layout(title="Alumnado por Consultor", height=500)
        st.plotly_chart(fig_pie_consultor, use_container_width=True)

    # =============== NUEVO: Tabla detalle por Consultor ===============
    st.markdown("### 👥 Detalle por Consultor")
    consultores_detalle = sorted(df_filtrado["CONSULTOR EIP"].dropna().unique().tolist())
    sel_detalle = st.multiselect(
        "Filtrar tabla por Consultor:",
        options=consultores_detalle,
        default=consultores_detalle
    )

    df_tabla = df_filtrado[df_filtrado["CONSULTOR EIP"].isin(sel_detalle)][
        ["CONSULTOR EIP", "NOMBRE", "APELLIDOS", "AREA", "FIN CONV"]
    ].drop_duplicates().sort_values(["CONSULTOR EIP", "APELLIDOS", "NOMBRE"]).reset_index(drop=True)

    st.dataframe(df_tabla, use_container_width=True)
