# pagesEIM/deuda/global_eim.py
import os
import io
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go
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


def hex_to_rgb(hex_color: str):
    hex_color = str(hex_color).lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return r, g, b


def rgb_to_hex(rgb_tuple):
    return '#{:02x}{:02x}{:02x}'.format(
        max(0, min(255, int(rgb_tuple[0]))),
        max(0, min(255, int(rgb_tuple[1]))),
        max(0, min(255, int(rgb_tuple[2])))
    )


def lighten_color(hex_color: str, factor: float = 0.6):
    """
    Devuelve una versión más clara del color mezclando con blanco.
    factor: 0 -> color original, 1 -> blanco. Valores típicos 0.35-0.75.
    """
    r, g, b = hex_to_rgb(hex_color)
    r_new = r + (255 - r) * factor
    g_new = g + (255 - g) * factor
    b_new = b + (255 - b) * factor
    return rgb_to_hex((r_new, g_new, b_new))


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
    st.subheader("Estado (EIM)")

    # cargamos df específico EIM o fallback genérico
    df = st.session_state.get("excel_data_eim", None)
    if df is None:
        df = st.session_state.get("excel_data", None)

    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        st.warning("⚠️ No hay archivo cargado. Vuelve a la sección Gestión de Datos (EIM).")
        return

    df = df.copy()
    if "Estado" not in df.columns:
        st.error("❌ La columna 'Estado' no existe en el archivo.")
        return

    anio_actual = st.session_state.get('año_actual', datetime.today().year)

    # ===== filtros =====
    estados_unicos = sorted(df['Estado'].dropna().unique())
    columnas_totales = [f'Total {a}' for a in range(2018, anio_actual)]
    meses_actuales = [f'{m} {anio_actual}' for m in MESES_ES]
    # Solo mostrar columnas disponibles
    columnas_disponibles = [c for c in (columnas_totales + meses_actuales) if c in df.columns]

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

    # aseguramos numéricos en las columnas seleccionadas
    df[columnas_existentes] = df[columnas_existentes].apply(pd.to_numeric, errors='coerce').fillna(0)
    df_filtrado = df[df['Estado'].isin(estados_seleccionados)].copy()
    df_grouped = df_filtrado.groupby("Estado")[columnas_existentes].sum().reset_index()

    # columnas mes año anterior disponibles (para comparar)
    prev_year = anio_actual - 1
    prev_months_all = [f"{m} {prev_year}" for m in MESES_ES]
    prev_months_existing = [c for c in prev_months_all if c in df.columns]

    df_prev_grouped = None
    if prev_months_existing:
        df[prev_months_existing] = df[prev_months_existing].apply(pd.to_numeric, errors='coerce').fillna(0)
        df_prev_grouped = df[df['Estado'].isin(estados_seleccionados)].groupby('Estado')[prev_months_existing].sum().reset_index()

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
        height=max(360, 48 * len(df_grouped) + 140),
        showlegend=False,
        margin=dict(t=60, b=40, l=70, r=30)
    )
    st.plotly_chart(fig_total, use_container_width=True)

    # ===== 2) Por Estado: Históricos | Año actual por meses =====
    st.markdown("### Totales por Estado y Periodo")

    cols_hist_sorted = sorted(
        [c for c in columnas_existentes if c.startswith("Total ")],
        key=lambda c: int(c.split()[1]) if len(c.split()) > 1 and c.split()[1].isdigit() else 0
    )
    mes_order = [f"{m} {anio_actual}" for m in MESES_ES if f"{m} {anio_actual}" in columnas_existentes]

    # posiciones relativas para anotaciones (yref='paper') - ajustables
    Y_POS_PREV = 0.92
    Y_POS_CURR = 0.97

    for estado in estados_seleccionados:
        row = df_grouped[df_grouped["Estado"] == estado]
        if row.empty:
            continue

        color_estado = COLORES_FIJOS.get(str(estado).strip().upper(), "#3b82f6")
        color_prev_light = lighten_color(color_estado, factor=0.65)

        c1, c2 = st.columns(2)

        # --- Históricos (línea + cajita negra con media)
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

            mean_hist = float(df_hist["Total"].mean() if not df_hist.empty else 0.0)
            fig_hist.add_hline(y=mean_hist, line_dash="dash", line_color=color_estado, opacity=0.9)
            fig_hist.add_annotation(
                xref="paper", x=0.98, xanchor="left",
                yref="y", y=mean_hist,
                text=f"Media<br>€ {num_es_sin_dec(mean_hist)}",
                showarrow=False,
                align="center",
                font=dict(color="#ffffff", size=12),
                bgcolor="#000000",
                borderpad=6
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

        # --- Meses: año actual vs año anterior (barras overlay + dos cajitas en top relativo) ---
        if mes_order:
            serie_mes = row[mes_order].iloc[0]
            df_mes = pd.DataFrame({"Periodo": mes_order, "Total": serie_mes.values})
            total_mes = float(df_mes["Total"].sum())

            # valores previos si existen
            prev_values = None
            if df_prev_grouped is not None and not df_prev_grouped.empty:
                prev_row = df_prev_grouped[df_prev_grouped['Estado'] == estado]
                if not prev_row.empty:
                    prev_values = []
                    for col in mes_order:
                        mes_name = col.split()[0]
                        prev_col = f"{mes_name} {prev_year}"
                        if prev_col in df_prev_grouped.columns:
                            prev_values.append(float(prev_row[prev_col].iloc[0]))
                        else:
                            prev_values.append(0.0)
                    if all(v == 0 for v in prev_values):
                        prev_values = None

            # medias para leyenda
            mean_curr = float(df_mes["Total"].mean() if not df_mes.empty else 0.0)
            prev_mean = float(pd.Series(prev_values).mean()) if (prev_values is not None) else None

            name_curr = f"{anio_actual} - Media: € {num_es_sin_dec(mean_curr)}"
            name_prev = f"{prev_year} - Media: € {num_es_sin_dec(prev_mean) if prev_mean is not None else '0'}"

            trace_curr = go.Bar(
                x=df_mes["Periodo"],
                y=df_mes["Total"],
                name=name_curr,
                marker=dict(color=color_estado, line=dict(color=color_estado, width=0.5)),
                opacity=0.98,
                text=None,
                hovertemplate="%{fullData.name}<br>%{x}<br>€ %{y:,.0f}<extra></extra>"
            )

            if prev_values is not None:
                trace_prev = go.Bar(
                    x=df_mes["Periodo"],
                    y=prev_values,
                    name=name_prev,
                    marker=dict(color=color_prev_light, line=dict(color=color_prev_light, width=0.5)),
                    opacity=0.6,
                    text=None,
                    hovertemplate="%{fullData.name}<br>%{x}<br>€ %{y:,.0f}<extra></extra>"
                )
                fig_mes = go.Figure(data=[trace_curr, trace_prev])
                fig_mes.update_layout(barmode='overlay', template="plotly_white")
                combined = pd.Series(list(prev_values) + df_mes["Total"].tolist())
                y_min, y_max = 0.0, float(combined.max() if not combined.empty else 0.0)
            else:
                fig_mes = go.Figure(data=[trace_curr])
                fig_mes.update_layout(barmode='overlay', template="plotly_white")
                y_min, y_max = 0.0, float(df_mes["Total"].max() if not df_mes.empty else 0.0)

            # margen mayor para que haya sitio en top relativo
            layout_margin_top = 140
            fig_mes.update_layout(
                title=f"{estado} — {anio_actual} por meses (Total: € {num_es(total_mes)})",
                height=560,
                margin=dict(t=layout_margin_top, b=90, l=70, r=40),
                yaxis_zeroline=True, yaxis_zerolinewidth=2, yaxis_zerolinecolor="#888",
                showlegend=True
            )

            # Añadimos anotaciones en coordenadas relativas (yref='paper'):
            for i, periodo in enumerate(df_mes["Periodo"]):
                val_curr = float(df_mes["Total"].iloc[i])
                val_prev = float(prev_values[i]) if (prev_values is not None) else 0.0

                if val_curr == 0 and val_prev == 0:
                    continue

                # adaptar font según magnitud
                total_max = max(val_curr, val_prev)
                font_curr = 11
                font_prev = 10
                if total_max > 1_000_000:
                    font_curr = 10
                    font_prev = 9
                if total_max > 10_000_000:
                    font_curr = 9
                    font_prev = 8

                # cajita año previo (clara) - texto negro
                if prev_values is not None:
                    fig_mes.add_annotation(
                        x=periodo,
                        y=Y_POS_PREV,
                        xref="x",
                        yref="paper",
                        text=f"€ {num_es_sin_dec(val_prev)}",
                        showarrow=False,
                        xanchor="center",
                        yanchor="bottom",
                        font=dict(color="#000000", size=font_prev),
                        bgcolor=color_prev_light,
                        bordercolor="#999999",
                        borderwidth=1,
                        borderpad=4
                    )

                # cajita año actual (oscura) - texto blanco (encima)
                fig_mes.add_annotation(
                    x=periodo,
                    y=Y_POS_CURR,
                    xref="x",
                    yref="paper",
                    text=f"€ {num_es_sin_dec(val_curr)}",
                    showarrow=False,
                    xanchor="center",
                    yanchor="bottom",
                    font=dict(color="#ffffff", size=font_curr),
                    bgcolor=color_estado,
                    bordercolor="#333333",
                    borderwidth=1,
                    borderpad=4
                )

            # añadir padding al eje Y para que barras no toquen la parte superior
            span = max(1.0, y_max - y_min)
            extra_pad = max(span * 0.12, 1.0)
            fig_mes.update_yaxes(range=[0, y_max + extra_pad])

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
                height=560,
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

    # Guardar con claves EIM y genérica
    st.session_state["descarga_global_eim"] = df_final
    st.session_state["descarga_global"] = df_final

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

    # Informe HTML (simplificado; las anotaciones relativas no se renderizan exactamente igual en HTML)
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
        color_estado = COLORES_FIJOS.get(str(estado).strip().upper(), "#3b82f6")

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
            mean_hist = float(df_hist["Total"].mean() if not df_hist.empty else 0.0)
            fig_hist.add_hline(y=mean_hist, line_dash="dash", line_color=color_estado, opacity=0.9)
            fig_hist.add_annotation(
                xref="paper", x=0.98, xanchor="left",
                yref="y", y=mean_hist,
                text=f"Media<br>€ {num_es_sin_dec(mean_hist)}",
                showarrow=False,
                align="center",
                font=dict(color="#ffffff", size=12),
                bgcolor="#000000",
                borderpad=6
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
            fig_pago.update_layout(height=560)
            html_buffer.write("<h2>Distribución Forma de Pago (filtrada)</h2>")
            html_buffer.write(pio.to_html(fig_pago, include_plotlyjs='cdn', full_html=False))

    html_buffer.write("</body></html>")

    html_value = html_buffer.getvalue()
    # Guardar HTML en session_state (EIM y genérico)
    st.session_state["html_global_eim"] = html_value
    st.session_state["html_global"] = html_value

    st.download_button(
        label="📄 Descargar informe HTML",
        data=html_value,
        file_name="reporte_estado.html",
        mime="text/html"
    )

    os.makedirs("uploaded", exist_ok=True)
    with open("uploaded/reporte_estado.html", "w", encoding="utf-8") as f:
        f.write(html_value)
