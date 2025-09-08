import os
import io
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.io as pio
import streamlit as st

from responsive import get_screen_size


# ===================== HELPERS =====================

MESES_ES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

COLORES_FIJOS = {
    "COBRADO": "#1f77b4",
    "DOMICILIACIÓN CONFIRMADA": "#ff7f0e",
    "DOMICILIACIÓN EMITIDA": "#2ca02c",
    "DUDOSO COBRO": "#d62728",
    "INCOBRABLE": "#9467bd",
    "NO COBRADO": "#8c564b",
    "PENDIENTE": "#e377c2",
    "TOTAL GENERAL": "#7f7f7f"
}

def num_es(v: float, dec: int = 2) -> str:
    try:
        f = float(v)
    except Exception:
        f = 0.0
    s = f"{f:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

def num_es_sin_dec(v: float) -> str:
    try:
        f = float(v)
    except Exception:
        f = 0.0
    s = f"{f:,.0f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

def y_range_con_padding(series):
    vals = pd.to_numeric(series, errors="coerce").fillna(0)
    vmin = float(vals.min() if len(vals) else 0)
    vmax = float(vals.max() if len(vals) else 0)
    if vmin >= 0:
        return [0, (vmax * 1.25) if vmax != 0 else 1]
    if vmax <= 0:
        return [(vmin * 1.25) if vmin != 0 else -1, 0]
    span = vmax - vmin
    pad = span * 0.15
    return [vmin - pad, vmax + pad]


# ===================== PÁGINA =====================

def render():
    st.subheader("Estado")

    # datos base
    if 'excel_data' not in st.session_state or st.session_state['excel_data'] is None:
        st.warning("⚠️ No hay archivo cargado. Vuelve a la sección Gestión de Cobro.")
        return

    df = st.session_state['excel_data'].copy()
    if 'Estado' not in df.columns:
        st.error("❌ La columna 'Estado' no existe en el archivo.")
        return

    anio_actual = st.session_state.get('año_actual', datetime.today().year)

    # ===== filtros =====
    estados_unicos = sorted(df['Estado'].dropna().unique())
    columnas_totales = [f'Total {a}' for a in range(2018, anio_actual)]
    meses_actuales = [f'{m} {anio_actual}' for m in MESES_ES]
    columnas_disponibles = columnas_totales + meses_actuales

    estados_seleccionados = st.multiselect(
        "Filtrar por Estado",
        estados_unicos,
        default=st.session_state.get("global_estado_filtro", estados_unicos),
        key="global_estado_filtro"
    )
    columnas_seleccionadas = st.multiselect(
        f"Selecciona columnas a mostrar ({anio_actual})",
        columnas_disponibles,
        default=st.session_state.get("global_columnas_filtro", columnas_disponibles),
        key="global_columnas_filtro"
    )

    if not estados_seleccionados:
        st.info("Selecciona al menos un Estado.")
        return

    columnas_existentes = [c for c in columnas_seleccionadas if c in df.columns]
    if not columnas_existentes:
        st.info("Selecciona al menos una columna válida.")
        return

    df[columnas_existentes] = df[columnas_existentes].apply(pd.to_numeric, errors='coerce').fillna(0)
    df_filtrado = df[df['Estado'].isin(estados_seleccionados)].copy()
    df_grouped = df_filtrado.groupby("Estado")[columnas_existentes].sum().reset_index()

    # ===== 1) Total acumulado por Estado =====
    width, height = get_screen_size()
    df_grouped["Total acumulado"] = df_grouped[columnas_existentes].sum(axis=1)

    fig_total = px.bar(
        df_grouped.sort_values("Total acumulado", ascending=True),
        x="Total acumulado", y="Estado",
        color="Estado",
        color_discrete_map=COLORES_FIJOS,
        orientation="h",
        template="plotly_white",
        text=df_grouped.sort_values("Total acumulado", ascending=True)["Total acumulado"].apply(
            lambda v: f"€ {num_es_sin_dec(v)}"
        )
    )
    fig_total.update_traces(textposition="outside", textfont=dict(size=12), cliponaxis=False)
    fig_total.update_layout(
        title="Total acumulado por Estado",
        height=max(360, 48*len(df_grouped)+140),
        showlegend=False,
        margin=dict(t=60, b=40, l=70, r=30)
    )
    st.plotly_chart(fig_total, use_container_width=True)

    # ===== 2) Por Estado: Históricos | Año actual por meses =====
    st.markdown("### Totales por Estado y Periodo")

    cols_hist_sorted = sorted(
        [c for c in columnas_existentes if c.startswith("Total ")],
        key=lambda c: int(c.split()[1])
    )
    mes_order = [f"{m} {anio_actual}" for m in MESES_ES if f"{m} {anio_actual}" in columnas_existentes]

    for estado in estados_seleccionados:
        row = df_grouped[df_grouped["Estado"] == estado]
        if row.empty:
            continue

        color_estado = COLORES_FIJOS.get(estado.strip().upper(), "#3b82f6")
        c1, c2 = st.columns(2)

        if cols_hist_sorted:
            serie_hist = row[cols_hist_sorted].iloc[0]
            df_hist = pd.DataFrame({"Periodo": cols_hist_sorted, "Total": serie_hist.values})
            total_hist = float(df_hist["Total"].sum())

            fig_hist = px.bar(
                df_hist, x="Periodo", y="Total",
                color_discrete_sequence=[color_estado],
                template="plotly_white",
                text=df_hist["Total"].apply(lambda v: f"€ {num_es_sin_dec(v)}")
            )
            fig_hist.update_traces(marker=dict(opacity=0.45, line=dict(color=color_estado, width=1.2)))
            fig_hist.update_yaxes(range=y_range_con_padding(df_hist["Total"]))
            fig_hist.update_layout(
                title=f"{estado} — Históricos (Total: € {num_es(total_hist)})",
                height=520,
                margin=dict(t=90, b=90, l=70, r=40),
                yaxis_zeroline=True, yaxis_zerolinewidth=2, yaxis_zerolinecolor="#888",
                showlegend=False
            )
            fig_hist.update_traces(textposition="outside", textfont=dict(size=14), cliponaxis=False)
            c1.plotly_chart(fig_hist, use_container_width=True)
        else:
            c1.info("Sin columnas históricas seleccionadas.")

        if mes_order:
            serie_mes = row[mes_order].iloc[0]
            df_mes = pd.DataFrame({"Periodo": mes_order, "Total": serie_mes.values})
            total_mes = float(df_mes["Total"].sum())

            fig_mes = px.bar(
                df_mes, x="Periodo", y="Total",
                color_discrete_sequence=[color_estado],
                template="plotly_white",
                text=df_mes["Total"].apply(lambda v: f"€ {num_es_sin_dec(v)}")
            )
            fig_mes.update_yaxes(range=y_range_con_padding(df_mes["Total"]))
            fig_mes.update_layout(
                title=f"{estado} — {anio_actual} por meses (Total: € {num_es(total_mes)})",
                height=520,
                margin=dict(t=90, b=90, l=70, r=40),
                yaxis_zeroline=True, yaxis_zerolinewidth=2, yaxis_zerolinecolor="#888",
                showlegend=False
            )
            fig_mes.update_traces(textposition="outside", textfont=dict(size=14), cliponaxis=False)
            c2.plotly_chart(fig_mes, use_container_width=True)
        else:
            c2.info(f"Sin meses de {anio_actual} seleccionados.")

    # ===== 3) Distribución Forma de Pago (filtrada por Estado + columnas) =====
    if "Forma Pago" in df.columns:
        df_pago = df[df["Estado"].isin(estados_seleccionados)].copy()
        df_pago["Total Periodo"] = df_pago[columnas_existentes].sum(axis=1)

        resumen_pago = (
            df_pago.groupby("Forma Pago", dropna=False)["Total Periodo"]
                   .sum()
                   .reset_index()
        )
        resumen_pago = resumen_pago[resumen_pago["Total Periodo"] != 0]

        st.markdown("### Distribución Forma de Pago (filtrada)")
        if resumen_pago.empty:
            st.info("No hay importes para los filtros actuales.")
        else:
            fig_pago = px.pie(
                resumen_pago,
                names="Forma Pago",
                values="Total Periodo",
                template="plotly_white"
            )
            fig_pago.update_traces(textposition="inside", textinfo="label+percent+value")
            fig_pago.update_layout(
                height=540,
                margin=dict(t=60, b=40, l=10, r=10),
                legend_title_text="Forma de pago",
                legend=dict(orientation="v")
            )
            st.plotly_chart(fig_pago, use_container_width=True)
    else:
        st.info("No existe la columna 'Forma Pago' en el archivo.")

    # ===== 4) Exportaciones =====
    df_final = df_grouped.copy()
    df_final["Total fila"] = df_final[columnas_existentes].sum(axis=1)

    # >>>>>>>>>> CLAVE PARA EL TICK VERDE EN "Hojas disponibles"
    st.session_state["descarga_global"] = df_final  # <<<<<<<< AQUÍ ESTABA EL FALTANTE
    # >>>>>>>>>>

    st.markdown("---")
    st.subheader("📥 Exportar esta hoja")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df_final.to_excel(writer, index=False, sheet_name="Global")
    buffer.seek(0)
    st.download_button(
        label="📥 Descargar hoja: Global",
        data=buffer.getvalue(),
        file_name="global_estado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Informe HTML
    st.markdown("### 💾 Exportar informe visual")
    html_buffer = io.StringIO()
    html_buffer.write("<html><head><meta charset='utf-8'><title>Informe de Estado</title></head><body>")
    html_buffer.write("<h1>Totales por Estado</h1>")
    html_buffer.write(df_final.to_html(index=False))

    html_buffer.write("<h2>Total acumulado por Estado</h2>")
    html_buffer.write(pio.to_html(fig_total, include_plotlyjs='cdn', full_html=False))

    html_buffer.write("<h2>Gráficos por Estado</h2>")
    for estado in estados_seleccionados:
        row = df_grouped[df_grouped["Estado"] == estado]
        if row.empty:
            continue
        color_estado = COLORES_FIJOS.get(estado.strip().upper(), "#3b82f6")

        if cols_hist_sorted:
            serie_hist = row[cols_hist_sorted].iloc[0]
            df_hist = pd.DataFrame({"Periodo": cols_hist_sorted, "Total": serie_hist.values})
            total_hist = float(df_hist["Total"].sum())
            fig_hist = px.bar(
                df_hist, x="Periodo", y="Total",
                color_discrete_sequence=[color_estado],
                template="plotly_white",
                text=df_hist["Total"].apply(lambda v: f"€ {num_es_sin_dec(v)}")
            )
            fig_hist.update_traces(marker=dict(opacity=0.45, line=dict(color=color_estado, width=1.2)))
            fig_hist.update_yaxes(range=y_range_con_padding(df_hist["Total"]))
            fig_hist.update_traces(textposition="outside", textfont=dict(size=14), cliponaxis=False)
            fig_hist.update_layout(
                title=f"{estado} — Históricos (Total: € {num_es(total_hist)})",
                height=520,
                margin=dict(t=90, b=90, l=70, r=40),
                yaxis_zeroline=True, yaxis_zerolinewidth=2, yaxis_zerolinecolor="#888",
                showlegend=False
            )
            html_buffer.write(pio.to_html(fig_hist, include_plotlyjs='cdn', full_html=False))

        if mes_order:
            serie_mes = row[mes_order].iloc[0]
            df_mes = pd.DataFrame({"Periodo": mes_order, "Total": serie_mes.values})
            total_mes = float(df_mes["Total"].sum())
            fig_mes = px.bar(
                df_mes, x="Periodo", y="Total",
                color_discrete_sequence=[color_estado],
                template="plotly_white",
                text=df_mes["Total"].apply(lambda v: f"€ {num_es_sin_dec(v)}")
            )
            fig_mes.update_yaxes(range=y_range_con_padding(df_mes["Total"]))
            fig_mes.update_traces(textposition="outside", textfont=dict(size=14), cliponaxis=False)
            fig_mes.update_layout(
                title=f"{estado} — {anio_actual} por meses (Total: € {num_es(total_mes)})",
                height=520,
                margin=dict(t=90, b=90, l=70, r=40),
                yaxis_zeroline=True, yaxis_zerolinewidth=2, yaxis_zerolinecolor="#888",
                showlegend=False
            )
            html_buffer.write(pio.to_html(fig_mes, include_plotlyjs='cdn', full_html=False))

    # Pie (filtrado) en HTML
    if "Forma Pago" in df.columns:
        df_pago = df[df["Estado"].isin(estados_seleccionados)].copy()
        df_pago["Total Periodo"] = df_pago[columnas_existentes].sum(axis=1)
        resumen_pago = (
            df_pago.groupby("Forma Pago", dropna=False)["Total Periodo"].sum().reset_index()
        )
        resumen_pago = resumen_pago[resumen_pago["Total Periodo"] != 0]
        if not resumen_pago.empty:
            fig_pago = px.pie(
                resumen_pago,
                names="Forma Pago",
                values="Total Periodo",
                template="plotly_white"
            )
            fig_pago.update_traces(textposition="inside", textinfo="label+percent+value")
            fig_pago.update_layout(height=540)
            html_buffer.write("<h2>Distribución Forma de Pago (filtrada)</h2>")
            html_buffer.write(pio.to_html(fig_pago, include_plotlyjs='cdn', full_html=False))

    html_buffer.write("</body></html>")

    st.download_button(
        label="📄 Descargar informe HTML",
        data=html_buffer.getvalue(),
        file_name="reporte_estado.html",
        mime="text/html"
    )

    os.makedirs("uploaded", exist_ok=True)
    with open("uploaded/reporte_estado.html", "w", encoding="utf-8") as f:
        f.write(html_buffer.getvalue())

    # Ya lo guardabas, lo dejo aquí igualmente:
    st.session_state["html_global"] = html_buffer.getvalue()
