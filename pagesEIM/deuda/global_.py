# pagesEIM/deuda/global_.py
import io
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.io as pio
import streamlit as st

from utils.eim_normalizer import prepare_eim_df

# Claves de estado para EIM
DATA_KEY      = "excel_data_eim"
SAVE_KEY_XLS  = "descarga_global_eim"
SAVE_KEY_HTML = "html_global_eim"

MESES_ES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

COLORES_FIJOS = {
    "COBRADO": "#1f77b4",
    "DOMICILIACIÓN CONFIRMADA": "#ff7f0e",
    "DOMICILIACIÓN EMITIDA": "#2ca02c",
    "DUDOSO COBRO": "#d62728",
    "INCOBRABLE": "#9467bd",
    "NO COBRADO": "#8c564b",
    "PENDIENTE": "#e377c2",
    "TOTAL GENERAL": "#7f7f7f",
}

# Conjunto de valores inválidos (como texto) a excluir
INVALID_ESTADOS = {
    "", " ", "NAN", "NULL", "NONE", "<NA>", "SIN ESTADO", "NO ENCONTRADO"
}

def _norm_text(s) -> str:
    if pd.isna(s):
        return ""
    t = str(s).replace("\u00A0", " ").strip()
    t = " ".join(t.split())
    return t.upper()

def _get_size():
    try:
        from responsive import get_screen_size
        w, h = get_screen_size()
        return (w or 1200, h or 600)
    except Exception:
        return (1200, 600)

def render():
    st.subheader("Estado")

    # ===== Carga =====
    if DATA_KEY not in st.session_state or st.session_state[DATA_KEY] is None:
        st.warning("⚠️ No hay archivo cargado. Vuelve a la pestaña **Gestión de datos** (EIM).")
        return

    try:
        df = prepare_eim_df(st.session_state[DATA_KEY])
    except Exception as e:
        st.error(f"❌ No se pudo normalizar el archivo: {e}")
        return

    if "Estado" not in df.columns:
        st.error("❌ La columna **Estado** no existe tras la normalización.")
        return

    # ===== Filtro robusto de estados inválidos =====
    estado_norm = df["Estado"].apply(_norm_text)
    df = df[~estado_norm.isin(INVALID_ESTADOS)].copy()
    df["Estado"] = estado_norm[~estado_norm.isin(INVALID_ESTADOS)]

    if df.empty:
        st.info("No hay registros con un estado válido para mostrar.")
        return

    # ===== Periodo =====
    anio_actual = datetime.today().year
    columnas_totales = [f"Total {a}" for a in range(2018, anio_actual) if f"Total {a}" in df.columns]
    columnas_mes_actual = [f"{m} {anio_actual}" for m in MESES_ES if f"{m} {anio_actual}" in df.columns]
    columnas_disponibles = columnas_totales + columnas_mes_actual

    if not columnas_disponibles:
        st.info("No hay columnas de totales por año o meses del año actual en el archivo.")
        return

    # ===== Filtros =====
    estados_unicos = sorted(df["Estado"].dropna().unique())
    estados_sel = st.multiselect(
        "Filtrar por Estado",
        options=estados_unicos,
        default=estados_unicos,
        key="eim_global_estado_filtro",
    )

    cols_sel = st.multiselect(
        f"Selecciona columnas a mostrar ({anio_actual})",
        options=columnas_disponibles,
        default=columnas_disponibles,
        key="eim_global_columnas_filtro",
    )

    if not estados_sel:
        st.info("Selecciona al menos un estado.")
        return
    if not cols_sel:
        st.info("Selecciona al menos una columna válida.")
        return

    # ===== Agregación =====
    df_f = df[df["Estado"].isin(estados_sel)].copy()
    df_f[cols_sel] = df_f[cols_sel].apply(pd.to_numeric, errors="coerce").fillna(0)

    df_group = df_f.groupby("Estado", dropna=True)[cols_sel].sum().reset_index()

    fila_total = pd.DataFrame(df_group[cols_sel].sum()).T
    fila_total.insert(0, "Estado", "TOTAL GENERAL")
    df_final = pd.concat([df_group, fila_total], ignore_index=True)
    df_final["Total fila"] = df_final[cols_sel].sum(axis=1)

    st.markdown("### Totales agrupados por Estado")
    st.dataframe(df_final, use_container_width=True)

    # ===== Gráficos =====
    width, height = _get_size()

    df_melt = df_final.drop(columns=["Total fila"]).melt(
        id_vars="Estado", var_name="Periodo", value_name="Total"
    )

    st.markdown("### Totales por Estado y Periodo")
    for estado in [e for e in estados_sel if e != "TOTAL GENERAL"]:
        df_e = df_melt[df_melt["Estado"] == estado]
        if df_e.empty:
            continue
        color = COLORES_FIJOS.get(estado.strip().upper(), "#cccccc")
        fig = px.bar(
            df_e,
            x="Periodo",
            y="Total",
            color_discrete_sequence=[color],
            text_auto=".2s",
            title=f"Gráfico: {estado}",
            template="plotly_white",
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Total acumulado por Estado")
    df_group["Total acumulado"] = df_group[cols_sel].sum(axis=1)
    fig2 = px.bar(
        df_group[df_group["Estado"].isin(estados_sel)],
        x="Total acumulado",
        y="Estado",
        color="Estado",
        color_discrete_map=COLORES_FIJOS,
        orientation="h",
        text_auto=".2s",
        height=height,
        width=width,
        template="plotly_white",
    )
    st.plotly_chart(fig2, use_container_width=True)

    fig3 = None
    if "Forma Pago" in df_f.columns:
        df_pago = df_f.copy()
        df_pago["Total Periodo"] = df_pago[cols_sel].sum(axis=1)
        resumen_pago = df_pago.groupby("Forma Pago")["Total Periodo"].sum().reset_index()

        st.markdown("### Distribución Forma de Pago")
        fig3 = px.pie(
            resumen_pago,
            names="Forma Pago",
            values="Total Periodo",
            hole=0.5,
            template="plotly_white",
        )
        fig3.update_traces(textposition="inside", textinfo="label+percent+value")
        st.plotly_chart(fig3, use_container_width=True)

    # ===== Exportaciones =====
    st.session_state[SAVE_KEY_XLS] = df_final

    st.markdown("---")
    st.subheader("📥 Exportar esta hoja")

    buf_xls = io.BytesIO()
    with pd.ExcelWriter(buf_xls, engine="xlsxwriter") as writer:
        df_final.to_excel(writer, index=False, sheet_name="Global")
    buf_xls.seek(0)
    st.download_button(
        label="📥 Descargar hoja: Global (EIM)",
        data=buf_xls.getvalue(),
        file_name="global_estado_eim.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.markdown("### 💾 Exportar informe visual (HTML)")
    html_buf = io.StringIO()
    html_buf.write("<html><head><meta charset='utf-8'><title>Informe de Estado (EIM)</title></head><body>")
    html_buf.write("<h1>Totales por Estado</h1>")
    html_buf.write(df_final.to_html(index=False))

    html_buf.write("<h2>Gráficos por Estado y Periodo</h2>")
    for estado in [e for e in estados_sel if e != "TOTAL GENERAL"]:
        df_e = df_melt[df_melt["Estado"] == estado]
        if df_e.empty:
            continue
        color = COLORES_FIJOS.get(estado.strip().upper(), "#cccccc")
        fig_e = px.bar(
            df_e,
            x="Periodo",
            y="Total",
            color_discrete_sequence=[color],
            text_auto=".2s",
            title=f"Gráfico: {estado}",
            template="plotly_white",
        )
        html_buf.write(pio.to_html(fig_e, include_plotlyjs="cdn", full_html=False))

    html_buf.write("<h2>Gráfico Total Acumulado</h2>")
    html_buf.write(pio.to_html(fig2, include_plotlyjs="cdn", full_html=False))

    if fig3:
        html_buf.write("<h2>Distribución Forma de Pago</h2>")
        html_buf.write(pio.to_html(fig3, include_plotlyjs="cdn", full_html=False))

    html_buf.write("</body></html>")
    html_str = html_buf.getvalue()

    st.download_button(
        label="🌐 Descargar informe HTML (EIM)",
        data=html_str.encode("utf-8"),
        file_name="reporte_estado_eim.html",
        mime="text/html",
    )

    st.session_state[SAVE_KEY_HTML] = html_str
