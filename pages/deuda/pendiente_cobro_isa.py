# pendiente_cobro_isa.py
import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import plotly.io as pio
import io
import os

# ---------------- Utilidad formato €
def _eu(n):
    try:
        f = float(n)
    except Exception:
        return "0,00"
    s = f"{f:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def render():
    # Estilos ligeros
    st.markdown("""
    <style>
      .block-container {max-width: 100% !important; padding-left: 1rem; padding-right: 1rem;}
      .stDataFrame { font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

    st.header("📄 Pendientes de Cobro – Becas ISA")

    if "excel_data" not in st.session_state or st.session_state["excel_data"] is None:
        st.warning("⚠️ No hay archivo cargado. Ve a la sección Gestión de Cobro.")
        return

    df = st.session_state["excel_data"].copy()
    df.columns = df.columns.str.strip()
    df["Estado"] = df["Estado"].astype(str).str.strip().str.upper()
    df["Forma Pago"] = df["Forma Pago"].astype(str).str.strip().str.upper()

    # Filtrado PENDIENTE + BECAS ISA
    df_pendiente = df[(df["Estado"] == "PENDIENTE") & (df["Forma Pago"] == "BECAS ISA")].copy()
    if df_pendiente.empty:
        st.info("ℹ️ No hay registros con estado PENDIENTE y forma de pago BECAS ISA.")
        return

    año_actual = datetime.today().year
    mes_actual = datetime.today().month
    meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]

    total_clientes_unicos = set()
    resultado_html_tabla = ""  # para export HTML

    # --------- 2022–2025 (tabla + gráfico) ----------
    cols_22_24 = [f"Total {a}" for a in range(2022, 2025) if f"Total {a}" in df_pendiente.columns]
    cols_2025_meses = [f"{m} 2025" for m in meses if f"{m} 2025" in df_pendiente.columns]
    cols_2025_total = ["Total 2025"] if "Total 2025" in df_pendiente.columns else []

    # Selector 2025: si estamos en 2025, ofrecemos meses; si >=2026 usamos Total 2025
    if año_actual == 2025:
        st.markdown("## 📅 Periodo 2022–2025")
        st.markdown("### Selecciona meses de 2025")
        default_2025 = [f"{m} 2025" for m in meses[:mes_actual] if f"{m} 2025" in df_pendiente.columns]
        cols_2025_final = st.multiselect(
            "Meses de 2025",
            options=cols_2025_meses,
            default=st.session_state.get("filtro_meses_becas_2025", default_2025),
            key="filtro_meses_becas_2025"
        )
    elif año_actual >= 2026:
        st.markdown("## 📅 Periodo 2022–2025")
        cols_2025_final = cols_2025_total
    else:
        # Años previos a 2025: sólo 2022–2024
        st.markdown("## 📅 Periodo 2022–2025")
        cols_2025_final = []

    cols_22_25 = cols_22_24 + cols_2025_final

    # ---- Tabla y gráfico por periodo (2022–2025 seleccionados) ----
    fig2 = None
    if cols_22_25:
        df2 = df_pendiente[["Cliente"] + cols_22_25].copy()
        df2[cols_22_25] = df2[cols_22_25].apply(pd.to_numeric, errors="coerce").fillna(0)
        df2 = df2.groupby("Cliente", as_index=False)[cols_22_25].sum()
        df2 = df2[df2[cols_22_25].sum(axis=1) > 0]

        if not df2.empty:
            # Suma hasta la última seleccionada como "Total Cliente"
            ultima_columna = cols_22_25[-1]
            idx_ult = df2.columns.get_loc(ultima_columna)
            columnas_a_sumar = df2.columns[1:idx_ult + 1]
            df2["Total Cliente"] = df2[columnas_a_sumar].sum(axis=1)

            deuda_total_22_25 = float(df2["Total Cliente"].sum())
            total_clientes_unicos.update(df2["Cliente"].unique())

            st.dataframe(df2, use_container_width=True)
            st.markdown(
                f"**👥 Total clientes con deuda en 2022–2025:** `{df2['Cliente'].nunique()}` – "
                f"💰 Total deuda: `{_eu(deuda_total_22_25)} €`"
            )

            # Resumen para gráfico
            resumen2 = df2[columnas_a_sumar].sum().reset_index()
            resumen2.columns = ["Periodo", "Total Deuda"]
            clientes_por_periodo = df2[columnas_a_sumar].gt(0).sum().reset_index()
            clientes_por_periodo.columns = ["Periodo", "Nº Clientes"]
            resumen2 = resumen2.merge(clientes_por_periodo, on="Periodo")

            # Oculta periodos 0€ y 0 clientes
            resumen2 = resumen2[~((resumen2["Total Deuda"] == 0) & (resumen2["Nº Clientes"] == 0))]

            if not resumen2.empty:
                y_max = float(resumen2["Total Deuda"].max())
                fig2 = go.Figure()
                fig2.add_trace(go.Bar(
                    x=resumen2["Periodo"],
                    y=resumen2["Total Deuda"],
                    marker_color="rgb(34,163,192)",
                    text=[f"€ {_eu(v)}<br>👥 {int(c)}"
                          for v, c in zip(resumen2["Total Deuda"], resumen2["Nº Clientes"])],
                    textposition="outside",
                    textfont=dict(color="black"),
                    hovertemplate="%{text}<extra></extra>",
                ))
                fig2.update_traces(marker_line_color="black", marker_line_width=1.2)
                fig2.update_layout(
                    title="Total Deuda y Número de Clientes por Periodo",
                    yaxis_title="Total Deuda (€)",
                    xaxis_title="Periodo",
                    yaxis=dict(range=[0, y_max * 1.15] if y_max > 0 else [0, 1]),
                    plot_bgcolor="white",
                    margin=dict(t=100, b=50),
                    height=560,
                    uniformtext_minsize=8,
                    uniformtext_mode="show"
                )
                st.plotly_chart(fig2, use_container_width=True)

    # --------- DETALLE: tabla idéntica a pages/deuda/pendiente.py ----------
    st.markdown("---")
    st.markdown("### 📋 Detalle de deuda por cliente")

    # Columnas EMAIL / TEL (opcionales)
    email_col = next((c for c in ["Email", "Correo", "E-mail"] if c in df_pendiente.columns), None)
    tel_col   = next((c for c in ["Teléfono", "Telefono", "Tel"] if c in df_pendiente.columns), None)

    columnas_info = ["Cliente", "Proyecto", "Curso", "Comercial", "Forma Pago"]
    if email_col: columnas_info.append(email_col)
    if tel_col:   columnas_info.append(tel_col)

    # Columnas numéricas candidatas (mismo criterio que en pendiente.py)
    columnas_sumatorias = []
    columnas_sumatorias += [f"Total {a}" for a in range(2018, 2022) if f"Total {a}" in df_pendiente.columns]
    columnas_sumatorias += cols_22_25
    columnas_sumatorias = [c for c in columnas_sumatorias if c in df_pendiente.columns]

    if columnas_sumatorias:
        columnas_finales = list(dict.fromkeys(columnas_info + columnas_sumatorias))
        df_detalle = df_pendiente[columnas_finales].copy()
        df_detalle[columnas_sumatorias] = df_detalle[columnas_sumatorias].apply(pd.to_numeric, errors="coerce").fillna(0)
        df_detalle["Total deuda"] = df_detalle[columnas_sumatorias].sum(axis=1)

        # Agrupar por cliente (texto -> conjuntos únicos; totales -> suma)
        def _join_unique(series):
            vals = [str(v).strip() for v in series if pd.notna(v) and str(v).strip()]
            return ", ".join(sorted(set(vals)))

        agg = {
            "Proyecto": _join_unique,
            "Curso": _join_unique,
            "Comercial": _join_unique,
            "Forma Pago": lambda x: ", ".join(sorted(set(str(i) for i in x if pd.notna(i) and str(i).strip()))),
            "Total deuda": "sum",
        }
        if email_col: agg[email_col] = _join_unique
        if tel_col:   agg[tel_col] = _join_unique

        df_detalle = (
            df_detalle.groupby(["Cliente"], as_index=False)
                      .agg(agg)
                      .sort_values(by="Total deuda", ascending=False)
                      .reset_index(drop=True)
        )

        # Ocultar filas con Total deuda == 0 exacto
        df_detalle = df_detalle[df_detalle["Total deuda"] > 0]

        # ===== Filtros ligeros iguales =====
        with st.expander("🔎 Filtros del detalle"):
            col_f1, col_f2, col_f3 = st.columns([1.2, 1, 1])
            texto_cliente = col_f1.text_input("Buscar cliente contiene...", "")
            lista_comerciales = sorted({c.strip() for s in df_detalle["Comercial"].dropna().astype(str)
                                        for c in s.split(",") if c.strip()}) if "Comercial" in df_detalle.columns else []
            sel_comerciales = col_f2.multiselect("Comercial", options=lista_comerciales)
            max_total = float(df_detalle["Total deuda"].max()) if not df_detalle.empty else 0.0
            rango = col_f3.slider(
                "Rango Total deuda (€)",
                0.0, max_total,
                (0.0, max_total),
                step=max(1.0, max_total/100 if max_total else 1.0)
            )

        if texto_cliente:
            df_detalle = df_detalle[df_detalle["Cliente"].str.contains(texto_cliente, case=False, na=False)]
        if sel_comerciales and "Comercial" in df_detalle.columns:
            df_detalle = df_detalle[df_detalle["Comercial"].apply(
                lambda s: any(c in [x.strip() for x in str(s).split(",")] for c in sel_comerciales)
            )]
        if rango:
            df_detalle = df_detalle[(df_detalle["Total deuda"] >= rango[0]) & (df_detalle["Total deuda"] <= rango[1])]

        # Mostrar tabla nativa con formato €
        column_config = {
            "Total deuda": st.column_config.NumberColumn(
                "Total deuda", format="€ %.2f",
                help="Suma de todas las columnas de deuda seleccionadas (2018–2021 + 2022–2025)."
            ),
        }
        st.dataframe(
            df_detalle,
            use_container_width=True,
            hide_index=True,
            column_config=column_config
        )

        # Para exportaciones
        resultado_html_tabla = df_detalle.to_html(index=False)
        st.session_state["descarga_pendiente_cobro_isa"] = df_detalle

        # ---- Descarga Excel ----
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df_detalle.to_excel(writer, sheet_name="detalle_deuda", index=False)
        buffer.seek(0)
        st.download_button(
            label="📥 Descargar hoja: Becas ISA Pendiente",
            data=buffer.getvalue(),
            file_name="becas_isa_pendientes.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No hay columnas seleccionadas o disponibles para calcular el detalle.")

    # --------- Export HTML con gráfico + tabla ----------
    grafico_html = pio.to_html(fig2, include_plotlyjs='cdn', full_html=False) if fig2 is not None else ""
    html_content = f"""
    <html>
      <head><meta charset='utf-8'><title>Detalle Pendiente Becas ISA</title></head>
      <body>
        <h1>Pendientes de Cobro – Becas ISA</h1>
        <h2>Gráfico Total Deuda y Nº de Clientes por Periodo</h2>
        {grafico_html}
        <hr>
        <h2>Detalle de deuda por cliente</h2>
        {resultado_html_tabla}
      </body>
    </html>
    """
    st.download_button(
        label="🌐 Descargar vista HTML",
        data=html_content.encode("utf-8"),
        file_name="becas_isa_pendientes.html",
        mime="text/html"
    )
    st.session_state["html_pendiente_cobro_isa"] = html_content

    os.makedirs("uploaded", exist_ok=True)
    with open("uploaded/reporte_pendiente_cobro_isa.html", "w", encoding="utf-8") as f:
        f.write(html_content)
