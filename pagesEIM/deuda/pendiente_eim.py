# pagesEIM/deuda/pendiente_eim.py
import io
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from plotly.io import to_html
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

from utils.eim_normalizer import prepare_eim_df  # normalizador EIM

# ===========================
# Claves y utilidades
# ===========================
DATA_KEY = "excel_data_eim"
SAVE_KEY_XLS  = "descarga_pendiente_total_eim"
SAVE_KEY_HTML = "html_pendiente_total_eim"

def _eu(n):
    try:
        f = float(n)
    except Exception:
        return "0,00"
    s = f"{f:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s

resultado_exportacion = {}
_FIG_BARRAS = None  # para exportar a HTML si se genera

# ===========================
# Vista principal
# ===========================
def vista_clientes_pendientes():
    st.markdown("""
    <style>.block-container {max-width: 100% !important; padding-left: 1rem; padding-right: 1rem;}</style>
    """, unsafe_allow_html=True)

    st.header("📄 Clientes con Estado PENDIENTE")

    if DATA_KEY not in st.session_state or st.session_state[DATA_KEY] is None:
        st.warning("⚠️ No hay archivo cargado. Ve a la sección Gestión de Datos (EIM).")
        return

    # Normaliza EIM
    df_raw = st.session_state[DATA_KEY]
    df = prepare_eim_df(df_raw).copy()
    df.columns = df.columns.str.strip()

    if "Estado" not in df.columns:
        st.error("❌ La columna 'Estado' no existe tras la normalización.")
        return

    df["Estado"] = (
        df["Estado"].astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip().str.upper()
    )

    df_pend = df[df["Estado"] == "PENDIENTE"].copy()
    if df_pend.empty:
        st.info("ℹ️ No hay registros con estado PENDIENTE.")
        return

    año_actual = datetime.today().year
    mes_actual = datetime.today().month
    meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
             "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

    total_clientes_unicos = set()

    # ----- 2018–2021 (tabla)
    st.markdown("## 🕰️ Periodo 2018–2021")
    cols_18_21 = [f"Total {a}" for a in range(2018, 2022) if f"Total {a}" in df_pend.columns]
    if cols_18_21:
        df1 = df_pend[["Cliente"] + cols_18_21].copy()
        df1[cols_18_21] = df1[cols_18_21].apply(pd.to_numeric, errors="coerce").fillna(0)
        df1 = df1.groupby("Cliente", as_index=False)[cols_18_21].sum()
        df1 = df1[df1[cols_18_21].sum(axis=1) > 0]
        total_clientes_unicos.update(df1["Cliente"].unique())

        st.dataframe(df1, use_container_width=True)
        total_deuda_18_21 = float(df1[cols_18_21].sum().sum())
        st.markdown(
            f"**👥 Total clientes con deuda en 2018–2021:** "
            f"{df1['Cliente'].nunique()} – 🏅 Total deuda: {_eu(total_deuda_18_21)} €"
        )
        resultado_exportacion["2018_2021"] = df1
    else:
        total_deuda_18_21 = 0.0

    # ----- 2022–(año actual) con meses del año actual
    st.markdown(f"## 📅 Periodo 2022–{año_actual-1} + meses {año_actual}")
    cols_22_prev = [f"Total {a}" for a in range(2022, año_actual) if f"Total {a}" in df_pend.columns]
    cols_year_months = [f"{m} {año_actual}" for m in meses if f"{m} {año_actual}" in df_pend.columns]
    default_months = [c for i, c in enumerate(cols_year_months, start=1) if i <= mes_actual]

    cols_22_aa = st.multiselect(
        "📌 Selecciona columnas del periodo:",
        cols_22_prev + cols_year_months,
        default=cols_22_prev + default_months,
        key="eim_pendiente_cols"
    )

    total_deuda_22_aa = 0.0
    global _FIG_BARRAS
    _FIG_BARRAS = None

    if cols_22_aa:
        df2 = df_pend[["Cliente"] + cols_22_aa].copy()
        df2[cols_22_aa] = df2[cols_22_aa].apply(pd.to_numeric, errors="coerce").fillna(0)
        df2 = df2.groupby("Cliente", as_index=False)[cols_22_aa].sum()
        df2 = df2[df2[cols_22_aa].sum(axis=1) > 0]
        total_clientes_unicos.update(df2["Cliente"].unique())

        st.dataframe(df2, use_container_width=True)

        total_deuda_22_aa = float(df2[cols_22_aa].sum().sum())
        st.markdown(
            f"**👥 Total clientes con deuda 2022–{año_actual}:** "
            f"{df2['Cliente'].nunique()} – 🏅 Total deuda: {_eu(total_deuda_22_aa)} €"
        )
        resultado_exportacion["2022_actual"] = df2

        # Resumen para barras
        resumen2 = pd.DataFrame({
            "Periodo": cols_22_aa,
            "Total_Deuda": [df2[c].sum() for c in cols_22_aa],
            "Num_Clientes": [(df2.groupby("Cliente")[c].sum() > 0).sum() for c in cols_22_aa],
        })
        # Mostrar gráfico solo si hay algún valor > 0
        if (resumen2["Total_Deuda"] > 0).any():
            fig = px.bar(
                resumen2, x="Periodo", y="Total_Deuda",
                color="Total_Deuda", color_continuous_scale=["#eaf5ea", "#0b5b1d"],
                template="plotly_white", height=560
            )
            fig.update_traces(marker_line_color="black", marker_line_width=0.6, hovertemplate=None, hoverinfo="skip")
            max_y = float(resumen2["Total_Deuda"].max()) if len(resumen2) else 0.0
            fig.update_yaxes(range=[0, max_y * 1.22])
            fig.update_layout(margin=dict(l=20, r=20, t=20, b=50), xaxis_title="Periodo", yaxis_title="Total")

            annotations = []
            for _, r in resumen2.iterrows():
                annotations.append(dict(
                    x=r["Periodo"], y=float(r["Total_Deuda"]) * 1.045,
                    yanchor="bottom", xanchor="center",
                    text=f"€ {_eu(r['Total_Deuda'])}<br>👥 {int(r['Num_Clientes'])}",
                    showarrow=False, font=dict(color="white", size=16),
                    align="center", bgcolor="rgba(0,0,0,0.95)", bordercolor="black", borderwidth=1.2, opacity=1
                ))
            fig.update_layout(annotations=annotations)

            st.markdown("### ")
            st.plotly_chart(fig, use_container_width=True)
            _FIG_BARRAS = fig

    # ----- Tarjetas por año (idénticas a EIP)
    def _year_from_total(col):
        try:
            return int(col.split()[-1])
        except Exception:
            return None

    all_cols = list(df_pend.columns)

    col_totales = [c for c in all_cols if c.startswith("Total ") and c.split()[-1].isdigit()]
    years_totales = sorted({_year_from_total(c) for c in col_totales if _year_from_total(c) is not None})

    # Meses detectados por año
    meses_por_año = {}
    for c in all_cols:
        for i, m in enumerate(meses, start=1):
            if c.startswith(f"{m} "):
                try:
                    y = int(c.split()[-1])
                except Exception:
                    continue
                meses_por_año.setdefault(y, []).append((i, c))

    # fuerza numéricos
    numeric_cols = col_totales[:]
    for y, lst in meses_por_año.items():
        numeric_cols += [col for _, col in lst]
    if numeric_cols:
        df_pend[numeric_cols] = df_pend[numeric_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

    def _sum_and_clients(cols):
        if not cols:
            return 0.0, 0
        tmp = df_pend[["Cliente"] + cols].copy()
        g = tmp.groupby("Cliente", as_index=False)[cols].sum()
        total = float(g[cols].sum().sum())
        ncli = int((g[cols].sum(axis=1) > 0).sum())
        return total, ncli

    tarjetas = []

    years_meses = sorted(meses_por_año.keys())
    all_years_present = sorted(set(years_totales) | set(years_meses))

    # Pasados
    for y in [yy for yy in all_years_present if yy < año_actual]:
        cols = []
        if f"Total {y}" in df_pend.columns:
            cols = [f"Total {y}"]
        elif y in meses_por_año:
            cols = [col for _, col in sorted(meses_por_año[y])]
        total, ncli = _sum_and_clients(cols)
        if total != 0:
            tarjetas.append(("Total " + str(y), total, ncli))

    # Año actual (dividir actual vs futuro)
    if año_actual in all_years_present:
        cols_aa = [col for _, col in sorted(meses_por_año.get(año_actual, []))]
        cols_actual = [f"{m} {año_actual}" for m in meses[:mes_actual] if f"{m} {año_actual}" in df_pend.columns]
        cols_futuro = [f"{m} {año_actual}" for m in meses[mes_actual:] if f"{m} {año_actual}" in df_pend.columns]

        if not cols_aa and f"Total {año_actual}" in df_pend.columns:
            total, ncli = _sum_and_clients([f"Total {año_actual}"])
            if total != 0:
                tarjetas.append(("Pendiente actual", total, ncli))
        else:
            total_act, ncli_act = _sum_and_clients(cols_actual)
            total_fut, ncli_fut = _sum_and_clients(cols_futuro)
            if total_act != 0:
                tarjetas.append(("Pendiente actual", total_act, ncli_act))
            if total_fut != 0:
                tarjetas.append((f"Pendiente {año_actual} futuro", total_fut, ncli_fut))

    # Futuros
    for y in [yy for yy in all_years_present if yy > año_actual]:
        cols = []
        if y in meses_por_año:
            cols += [col for _, col in sorted(meses_por_año[y])]
        if f"Total {y}" in df_pend.columns:
            cols.append(f"Total {y}")
        total, ncli = _sum_and_clients(cols)
        if total != 0:
            tarjetas.append((f"Pendiente {y}", total, ncli))

    # Render tarjetas (cuadrados) — mismo aspecto que EIP
    if tarjetas:
        st.markdown("## 🧮 Pendiente TOTAL (por año)")
        for i in range(0, len(tarjetas), 4):
            cols_stream = st.columns(4)
            for j, col in enumerate(cols_stream):
                if i + j >= len(tarjetas): break
                title, amount, ncli = tarjetas[i + j]
                col.markdown(_card(title, amount, ncli), unsafe_allow_html=True)

    # ----- Resumen superior: pendiente con deuda | futuro | total
    total_clientes_unicos |= set(df_pend["Cliente"].unique())
    num_clientes_total = len(total_clientes_unicos)

    pendiente_con_deuda = sum(
        amount for title, amount, __ in tarjetas
        if title.startswith("Total ") or title == "Pendiente actual"
    )
    pendiente_futuro = sum(
        amount for title, amount, __ in tarjetas
        if title.startswith("Pendiente ") and title != "Pendiente actual"
    )
    total_pendiente = pendiente_con_deuda + pendiente_futuro

    st.markdown(
        f"**📌 Pendiente con deuda:** {_eu(pendiente_con_deuda)} €  &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"**🔮 Pendiente futuro:** {_eu(pendiente_futuro)} €  &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"**🧮 TOTAL pendiente:** {_eu(total_pendiente)} €"
    )

    # Guardamos por si quieres exportar/usar después
    st.session_state["total_clientes_unicos_eim"] = num_clientes_total
    st.session_state["total_deuda_acumulada_eim"] = total_pendiente

    # ----- Detalle (robusto, sin KeyError si faltan columnas)
    st.markdown("### 📋 Detalle de deuda por cliente")

    # Columnas base si existen
    base_posibles = ["Cliente", "Proyecto", "Curso", "Comercial", "Forma Pago"]
    columnas_info = [c for c in base_posibles if c in df_pend.columns]

    # Columnas de contacto opcionales (con/sin acentos)
    contacto_candidatas = ["Email", "Correo", "E-mail", "Teléfono", "Telefono", "Tel"]
    contacto_presentes = [c for c in contacto_candidatas if c in df_pend.columns]
    columnas_info += contacto_presentes

    # Columnas numéricas a sumar en filas de detalle
    columnas_sumatorias = cols_18_21 + (cols_22_aa if "cols_22_aa" in locals() else [])
    columnas_sumatorias = [c for c in columnas_sumatorias if c in df_pend.columns]

    if columnas_sumatorias and columnas_info:
        columnas_existentes = [c for c in columnas_info if c in df_pend.columns]
        df_detalle = df_pend[df_pend["Cliente"].isin(total_clientes_unicos)][
            columnas_existentes + columnas_sumatorias
        ].copy()

        if df_detalle.empty:
            st.info("No hay filas para mostrar en el detalle con los filtros actuales.")
        else:
            df_detalle[columnas_sumatorias] = df_detalle[columnas_sumatorias].apply(pd.to_numeric, errors="coerce").fillna(0)
            df_detalle["Total deuda"] = df_detalle[columnas_sumatorias].sum(axis=1)

            def _join_unique(series):
                vals = [str(v).strip() for v in series if pd.notna(v) and str(v).strip()]
                return ", ".join(sorted(set(vals)))

            # agg_dict solo con columnas presentes
            agg_dict = {"Total deuda": "sum"}
            for c in ["Proyecto", "Curso", "Comercial", "Forma Pago"]:
                if c in df_detalle.columns:
                    agg_dict[c] = _join_unique
            for c in contacto_presentes:
                if c in df_detalle.columns:
                    agg_dict[c] = _join_unique

            df_detalle = (
                df_detalle.groupby(["Cliente"], as_index=False)
                          .agg(agg_dict)
                          .sort_values(by="Total deuda", ascending=False)
            )

            auto_fit = JsCode("function(p){ p.api.sizeColumnsToFit(); }")
            gb = GridOptionsBuilder.from_dataframe(df_detalle)
            gb.configure_default_column(filter=True, sortable=True, resizable=True, wrapText=True, autoHeight=True, flex=1)
            gb.configure_grid_options(domLayout='normal', suppressRowClickSelection=True,
                                      pagination=False, onFirstDataRendered=auto_fit, onGridSizeChanged=auto_fit)

            if "Cliente" in df_detalle.columns:   gb.configure_column("Cliente",   flex=2, min_width=260)
            if "Proyecto" in df_detalle.columns:  gb.configure_column("Proyecto",  flex=2, min_width=220)
            if "Curso" in df_detalle.columns:     gb.configure_column("Curso",     flex=2, min_width=300)
            if "Comercial" in df_detalle.columns: gb.configure_column("Comercial", flex=1, min_width=180)
            if "Forma Pago" in df_detalle.columns:gb.configure_column("Forma Pago",flex=1, min_width=200)
            for c in contacto_presentes:
                if c in df_detalle.columns:
                    gb.configure_column(c, flex=1, min_width=180)
            gb.configure_column("Total deuda", type=["numericColumn","rightAligned"], flex=1, min_width=140)

            AgGrid(df_detalle, gridOptions=gb.build(), update_mode=GridUpdateMode.NO_UPDATE,
                   allow_unsafe_jscode=True, theme="streamlit", height=600, use_container_width=True)

            resultado_exportacion["ResumenClientes"] = df_detalle

    st.markdown("---")


def _card(title, amount, ncli):
    return f"""
    <div style="background:#f1f9ff;border:1px solid #dbe9ff;border-radius:12px;
                padding:14px 16px;box-shadow:0 2px 6px rgba(0,0,0,.06);
                display:flex;flex-direction:column;gap:6px;min-height:92px">
      <div style="font-weight:700;color:#0b5394">{title}</div>
      <div style="display:flex;gap:12px;align-items:baseline;">
        <div style="font-size:26px;font-weight:800;color:#00335c">€ {_eu(amount)}</div>
        <div style="font-size:14px;color:#2a6aa5">👥 {int(ncli)}</div>
      </div>
    </div>
    """


def vista_totales_anuales():
    """Solo para exportación (no mostramos total aquí)."""
    if DATA_KEY not in st.session_state or st.session_state[DATA_KEY] is None:
        return
    df = prepare_eim_df(st.session_state[DATA_KEY]).copy()
    if "Estado" not in df.columns:
        return
    df_pend = df[df["Estado"].astype(str).str.strip().str.upper() == "PENDIENTE"]

    año_actual = datetime.today().year
    columnas_totales = [c for c in df_pend.columns
                        if c.startswith("Total ") and c.split()[-1].isdigit()
                        and int(c.split()[-1]) <= año_actual]
    if not columnas_totales:
        return

    df_pend[columnas_totales] = df_pend[columnas_totales].apply(pd.to_numeric, errors="coerce").fillna(0)
    resumen_total = pd.DataFrame({
        "Periodo": columnas_totales,
        "Suma_Total": [df_pend[c].sum() for c in columnas_totales],
        "Num_Clientes": [(df_pend.groupby("Cliente")[c].sum() > 0).sum() for c in columnas_totales]
    })
    st.session_state["total_deuda_barras_eim"] = float(resumen_total["Suma_Total"].sum())
    resultado_exportacion["Totales_Años_Meses"] = resumen_total


def render():
    vista_clientes_pendientes()
    vista_totales_anuales()

    # Exportaciones
    if resultado_exportacion:
        st.session_state[SAVE_KEY_XLS] = resultado_exportacion

        # Excel
        buffer_excel = io.BytesIO()
        with pd.ExcelWriter(buffer_excel, engine="xlsxwriter") as writer:
            for sheet_name, df_export in resultado_exportacion.items():
                if isinstance(df_export, pd.DataFrame):
                    df_export.to_excel(writer, index=False, sheet_name=sheet_name[:31])
        buffer_excel.seek(0)
        st.download_button(
            label="📥 Descargar Excel consolidado (EIM)",
            data=buffer_excel.getvalue(),
            file_name="exportacion_pendiente_eim.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # HTML
        html_buffer = io.StringIO()
        html_buffer.write("<html><head><meta charset='utf-8'><title>Exportación PENDIENTE (EIM)</title></head><body>")
        if "2018_2021" in resultado_exportacion:
            html_buffer.write("<h1>Resumen 2018–2021</h1>")
            html_buffer.write(resultado_exportacion["2018_2021"].to_html(index=False))
        if "2022_actual" in resultado_exportacion:
            html_buffer.write(f"<h1>Resumen 2022–{datetime.today().year}</h1>")
            html_buffer.write(resultado_exportacion["2022_actual"].to_html(index=False))
            if _FIG_BARRAS is not None:
                html_buffer.write(to_html(_FIG_BARRAS, include_plotlyjs='cdn', full_html=False))
        if "Totales_Años_Meses" in resultado_exportacion:
            html_buffer.write("<h2>Totales por año (deuda anual)</h2>")
            html_buffer.write(resultado_exportacion["Totales_Años_Meses"].to_html(index=False))
        html_buffer.write("</body></html>")

        html_str = html_buffer.getvalue()
        st.session_state[SAVE_KEY_HTML] = html_str
        st.download_button(
            label="🌐 Descargar reporte HTML completo (EIM)",
            data=html_str,
            file_name="reporte_pendiente_eim.html",
            mime="text/html"
        )
