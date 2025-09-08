# pagesEIM/deuda/pendiente.py

import io
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from plotly.io import to_html
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

from utils.eim_normalizer import prepare_eim_df  # <- normalizador EIM

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

# ===========================
# Vista principal
# ===========================
def vista_clientes_pendientes():
    # Ensancha el contenedor
    st.markdown("""
    <style>
      .block-container {max-width: 100% !important; padding-left: 1rem; padding-right: 1rem;}
    </style>
    """, unsafe_allow_html=True)

    st.header("📄 Clientes con Estado PENDIENTE")

    if DATA_KEY not in st.session_state or st.session_state[DATA_KEY] is None:
        st.warning("⚠️ No hay archivo cargado. Ve a la sección Gestión de Datos (EIM).")
        return

    # Normaliza/estandariza el DF EIM
    df_raw = st.session_state[DATA_KEY]
    df = prepare_eim_df(df_raw).copy()
    df.columns = df.columns.str.strip()
    if "Estado" not in df.columns:
        st.error("❌ La columna 'Estado' no existe tras la normalización.")
        return

    # Normaliza Estado
    df["Estado"] = (
        df["Estado"].astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip().str.upper()
    )

    df_pendiente = df[df["Estado"] == "PENDIENTE"].copy()
    if df_pendiente.empty:
        st.info("ℹ️ No hay registros con estado PENDIENTE.")
        return

    año_actual = datetime.today().year
    mes_actual = datetime.today().month
    meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
             "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

    total_clientes_unicos = set()

    # ---------------- 2018–2021 (solo tabla)
    st.markdown("## 🕰️ Periodo 2018–2021")
    cols_18_21 = [f"Total {a}" for a in range(2018, 2022) if f"Total {a}" in df_pendiente.columns]

    if cols_18_21:
        df1 = df_pendiente[["Cliente"] + cols_18_21].copy()
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

    # ---------------- 2022–año actual (meses incluidos)
    st.markdown("## 📅 Periodo 2022–{} + meses {}".format(año_actual-1, año_actual))

    cols_22_prev = [f"Total {a}" for a in range(2022, año_actual) if f"Total {a}" in df_pendiente.columns]
    cols_year_months = [f"{m} {año_actual}" for m in meses if f"{m} {año_actual}" in df_pendiente.columns]

    # Por defecto: hasta el mes actual (no incluye meses futuros)
    default_months = [c for i, c in enumerate(cols_year_months, start=1) if i <= mes_actual]

    cols_22_aa = st.multiselect(
        "📌 Selecciona columnas del periodo:",
        cols_22_prev + cols_year_months,
        default=cols_22_prev + default_months,
        key="eim_pendiente_cols"
    )

    total_deuda_22_aa = 0.0
    if cols_22_aa:
        df2 = df_pendiente[["Cliente"] + cols_22_aa].copy()
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

        # Resumen para la barra
        resumen2 = pd.DataFrame({
            "Periodo": cols_22_aa,
            "Total_Deuda": [df2[c].sum() for c in cols_22_aa],
            "Num_Clientes": [(df2.groupby("Cliente")[c].sum() > 0).sum() for c in cols_22_aa],
        })

        fig2 = px.bar(
            resumen2, x="Periodo", y="Total_Deuda",
            color="Total_Deuda", color_continuous_scale=["#eaf5ea", "#0b5b1d"],
            template="plotly_white", height=560
        )
        fig2.update_traces(marker_line_color="black", marker_line_width=0.6, hovertemplate=None, hoverinfo="skip")
        max_y = float(resumen2["Total_Deuda"].max()) if len(resumen2) else 0.0
        fig2.update_yaxes(range=[0, max_y * 1.22])
        fig2.update_layout(margin=dict(l=20, r=20, t=20, b=50), xaxis_title="Periodo", yaxis_title="Total")

        # Píldoras negras encima de cada barra
        annotations = []
        for _, r in resumen2.iterrows():
            annotations.append(dict(
                x=r["Periodo"], y=float(r["Total_Deuda"]) * 1.045,
                yanchor="bottom", xanchor="center",
                text=f"€ {_eu(r['Total_Deuda'])}<br>👥 {int(r['Num_Clientes'])}",
                showarrow=False, font=dict(color="white", size=16),
                align="center", bgcolor="rgba(0,0,0,0.95)", bordercolor="black", borderwidth=1.2, opacity=1
            ))
        fig2.update_layout(annotations=annotations)

        st.markdown("### ")
        st.plotly_chart(fig2, use_container_width=True)

        # Guardar para HTML
        global _FIG_22_25
        _FIG_22_25 = fig2
    else:
        _FIG_22_25 = None

    # ---------------- Cards por año (Pendiente TOTAL)
    st.markdown("## 🧮 Pendiente TOTAL (por año)")
    columnas_totales = [c for c in df_pendiente.columns
                        if c.startswith("Total ") and c.split()[-1].isdigit()
                        and int(c.split()[-1]) <= año_actual]
    df_pendiente[columnas_totales] = df_pendiente[columnas_totales].apply(pd.to_numeric, errors="coerce").fillna(0)

    resumen_total = pd.DataFrame({
        "Año": [c.split()[-1] for c in columnas_totales],
        "Suma_Total": [df_pendiente[c].sum() for c in columnas_totales],
        "Num_Clientes": [(df_pendiente.groupby("Cliente")[c].sum() > 0).sum() for c in columnas_totales],
    })

    # 🔴 nuevo: ocultar años con suma 0
    resumen_total = resumen_total[resumen_total["Suma_Total"] > 0].reset_index(drop=True)

    if resumen_total.empty:
        st.info("No hay importes > 0 para mostrar.")
    else:
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

        for i in range(0, len(resumen_total), 4):
            cols = st.columns(4)
            for j, c in enumerate(cols):
                if i + j >= len(resumen_total): break
                row = resumen_total.iloc[i + j]
                c.markdown(_card(f"Total {row['Año']}", row["Suma_Total"], row["Num_Clientes"]), unsafe_allow_html=True)

        # ---------------- Totales consolidados
        num_clientes_total = len(total_clientes_unicos)
        deuda_total_acumulada = total_deuda_18_21 + total_deuda_22_aa
        st.markdown(f"**👥 Total clientes con deuda en 2018–{año_actual}:** {num_clientes_total} – 🏅 Total deuda: {_eu(deuda_total_acumulada)} €")
        st.session_state["total_clientes_unicos"] = num_clientes_total
        st.session_state["total_deuda_acumulada"] = deuda_total_acumulada

    # ---------------- DETALLE: AG Grid sin hueco a la derecha
    st.markdown("### 📋 Detalle de deuda por cliente")

    columnas_info_posibles = ["Cliente", "Proyecto", "Curso", "Comercial", "Forma Pago"]
    columnas_info = [c for c in columnas_info_posibles if c in df_pendiente.columns]
    columnas_sumatorias = cols_18_21 + (cols_22_aa if "cols_22_aa" in locals() else [])

    if columnas_sumatorias and columnas_info:
        df_detalle = df_pendiente[df_pendiente["Cliente"].isin(total_clientes_unicos)][
            columnas_info + columnas_sumatorias
        ].copy()
        df_detalle[columnas_sumatorias] = df_detalle[columnas_sumatorias].apply(pd.to_numeric, errors="coerce").fillna(0)
        df_detalle["Total deuda"] = df_detalle[columnas_sumatorias].sum(axis=1)
        df_detalle = (
            df_detalle.groupby(["Cliente"], as_index=False)
            .agg({
                "Proyecto": lambda x: ", ".join(sorted(set(str(v) for v in x if pd.notna(v)))),
                "Curso": lambda x: ", ".join(sorted(set(str(v) for v in x if pd.notna(v)))),
                "Comercial": lambda x: ", ".join(sorted(set(str(v) for v in x if pd.notna(v)))),
                "Forma Pago": lambda x: ", ".join(sorted(set(str(v) for v in x if pd.notna(v)))),
                "Total deuda": "sum"
            })
            .sort_values(by="Total deuda", ascending=False)
        )

        # Ajuste automático de columnas SIEMPRE que cambie el tamaño del grid
        auto_fit = JsCode("function(p){ p.api.sizeColumnsToFit(); }")

        gb = GridOptionsBuilder.from_dataframe(df_detalle)
        gb.configure_default_column(
            filter=True, sortable=True, resizable=True, wrapText=True, autoHeight=True, flex=1
        )
        gb.configure_grid_options(
            domLayout='normal',
            suppressRowClickSelection=True,
            pagination=False,
            onFirstDataRendered=auto_fit,
            onGridSizeChanged=auto_fit,
        )

        # Reparto de ancho por importancia + mínimos
        if "Cliente" in df_detalle.columns:   gb.configure_column("Cliente",   flex=2, min_width=260)
        if "Proyecto" in df_detalle.columns:  gb.configure_column("Proyecto",  flex=2, min_width=220)
        if "Curso" in df_detalle.columns:     gb.configure_column("Curso",     flex=2, min_width=300)
        if "Comercial" in df_detalle.columns: gb.configure_column("Comercial", flex=1, min_width=180)
        if "Forma Pago" in df_detalle.columns:gb.configure_column("Forma Pago",flex=1, min_width=200)
        gb.configure_column("Total deuda", type=["numericColumn","rightAligned"], flex=1, min_width=140)

        AgGrid(
            df_detalle,
            gridOptions=gb.build(),
            update_mode=GridUpdateMode.NO_UPDATE,
            allow_unsafe_jscode=True,
            theme="streamlit",
            height=600,
            use_container_width=True
        )

        resultado_exportacion["ResumenClientes"] = df_detalle
        st.session_state["detalle_filtrado"] = df_detalle

    st.markdown("---")


def vista_totales_anuales():
    """Solo prepara datos para exportación (sin gráfico)."""
    if DATA_KEY not in st.session_state or st.session_state[DATA_KEY] is None:
        return

    df = prepare_eim_df(st.session_state[DATA_KEY]).copy()
    if "Estado" not in df.columns:
        return
    df_pendiente = df[df["Estado"].astype(str).str.strip().str.upper() == "PENDIENTE"]

    año_actual = datetime.today().year
    columnas_totales = [c for c in df_pendiente.columns
                        if c.startswith("Total ") and c.split()[-1].isdigit()
                        and int(c.split()[-1]) <= año_actual]
    if not columnas_totales:
        return

    df_pendiente[columnas_totales] = df_pendiente[columnas_totales].apply(pd.to_numeric, errors="coerce").fillna(0)
    resumen_total = pd.DataFrame({
        "Periodo": columnas_totales,
        "Suma_Total": [df_pendiente[c].sum() for c in columnas_totales],
        "Num_Clientes": [(df_pendiente.groupby("Cliente")[c].sum() > 0).sum() for c in columnas_totales]
    })
    st.session_state["total_deuda_barras_eim"] = float(resumen_total["Suma_Total"].sum())
    resultado_exportacion["Totales_Años_Meses"] = resumen_total


def render():
    vista_clientes_pendientes()
    vista_totales_anuales()

    total_global = st.session_state.get("total_deuda_barras_eim", 0)
    st.markdown(f"### 🧮 TOTAL desde gráfico anual: 🏅 {_eu(total_global)} €")

    if resultado_exportacion:
        # Guardar en sesión con claves EIM
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
            html_buffer.write("<h1>Resumen 2022–Actual</h1>")
            html_buffer.write(resultado_exportacion["2022_actual"].to_html(index=False))
            if '_FIG_22_25' in globals() and _FIG_22_25 is not None:
                html_buffer.write(to_html(_FIG_22_25, include_plotlyjs='cdn', full_html=False))
        if "Totales_Años_Meses" in resultado_exportacion:
            html_buffer.write("<h2>Totales por año (deuda anual)</h2>")
            html_buffer.write(resultado_exportacion["Totales_Años_Meses"].to_html(index=False))
        html_buffer.write(f"<h2>🧮 TOTAL desde gráfico anual: {_eu(st.session_state.get('total_deuda_barras_eim', 0))} €</h2>")
        html_buffer.write("</body></html>")

        # Guardar HTML en sesión EIM y botón de descarga
        html_str = html_buffer.getvalue()
        st.session_state[SAVE_KEY_HTML] = html_str
        st.download_button(
            label="🌐 Descargar reporte HTML completo (EIM)",
            data=html_str,
            file_name="reporte_pendiente_eim.html",
            mime="text/html"
        )
