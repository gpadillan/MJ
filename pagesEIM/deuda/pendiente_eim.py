# pagesEIM/deuda/pendiente_eim.py
# (Pendiente Total - versión sin AG Grid, alineada con EIM)

import io
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from plotly.io import to_html

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
    <style>
      .block-container {max-width: 100% !important; padding-left: 1rem; padding-right: 1rem;}
      .stDataFrame { font-size: 14px; }
    </style>
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
    mes_actual_nombre = meses[mes_actual - 1]

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

        # quitar periodos sin datos
        resumen2 = resumen2[~((resumen2["Total_Deuda"] == 0) & (resumen2["Num_Clientes"] == 0))].reset_index(drop=True)

        if not resumen2.empty:
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

    # ----- Tarjetas por año (con mes-actual separado en ROJO)
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

    # Año actual → 3 particiones:
    #   1) "Pendiente actual" = enero..mes-1
    #   2) "Pendiente {MesActual}" = solo mes actual (card roja)
    #   3) "Pendiente {AñoActual} futuro" = mes+1..diciembre
    if año_actual in all_years_present:
        cols_mes_año = {m: f"{m} {año_actual}" for m in meses}
        cols_existentes = set(df_pend.columns)

        # 1) enero..mes-1
        meses_pasados = meses[:max(mes_actual - 1, 0)]  # vacío si es enero
        cols_pasados = [cols_mes_año[m] for m in meses_pasados if cols_mes_año[m] in cols_existentes]

        # 2) mes actual
        col_mes_actual = cols_mes_año[mes_actual_nombre]
        cols_mes_actual = [col_mes_actual] if col_mes_actual in cols_existentes else []

        # 3) mes+1..diciembre
        meses_fut = meses[mes_actual:]  # desde el siguiente
        cols_futuro = [cols_mes_año[m] for m in meses_fut if cols_mes_año[m] in cols_existentes]

        # Si no hay mensuales pero sí Total del año → único bloque "Pendiente actual"
        tiene_mensuales_actual = any(c.endswith(f" {año_actual}") for c in cols_existentes)
        if not tiene_mensuales_actual and f"Total {año_actual}" in cols_existentes:
            total, ncli = _sum_and_clients([f"Total {año_actual}"])
            if total != 0:
                tarjetas.append(("Pendiente actual", total, ncli))
        else:
            if cols_pasados:
                total_act, ncli_act = _sum_and_clients(cols_pasados)
                if total_act != 0:
                    tarjetas.append(("Pendiente actual", total_act, ncli_act))
            if cols_mes_actual:
                total_mes, ncli_mes = _sum_and_clients(cols_mes_actual)
                if total_mes != 0:
                    tarjetas.append((f"Pendiente {mes_actual_nombre}", total_mes, ncli_mes, "red"))
            if cols_futuro:
                total_fut, ncli_fut = _sum_and_clients(cols_futuro)
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

    # Render tarjetas (cuadrados)
    if tarjetas:
        st.markdown("## 🧮 Pendiente TOTAL (por año)")
        for i in range(0, len(tarjetas), 4):
            cols_stream = st.columns(4)
            for j, col in enumerate(cols_stream):
                if i + j >= len(tarjetas): break
                item = tarjetas[i + j]
                if len(item) == 4:
                    title, amount, ncli, variant = item
                else:
                    title, amount, ncli = item
                    variant = "blue"
                col.markdown(_card(title, amount, ncli, variant), unsafe_allow_html=True)

    # ----- Resumen superior: pendiente con deuda | futuro | total
    total_clientes_unicos |= set(df_pend["Cliente"].unique())
    num_clientes_total = len(total_clientes_unicos)

    pendiente_con_deuda = 0.0
    pendiente_futuro = 0.0
    for item in tarjetas:
        title = item[0]
        amount = item[1]
        if title.startswith("Total ") or title == "Pendiente actual" or title == f"Pendiente {mes_actual_nombre}":
            pendiente_con_deuda += amount
        elif title.startswith("Pendiente "):
            pendiente_futuro += amount

    total_pendiente = pendiente_con_deuda + pendiente_futuro

    st.markdown(
        f"**📌 Pendiente con deuda:** {_eu(pendiente_con_deuda)} €  &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"**🔮 Pendiente futuro:** {_eu(pendiente_futuro)} €  &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"**🧮 TOTAL pendiente:** {_eu(total_pendiente)} €"
    )

    # Guardamos por si quieres exportar/usar después
    st.session_state["total_clientes_unicos_eim"] = num_clientes_total
    st.session_state["total_deuda_acumulada_eim"] = total_pendiente

    # ================== DETALLE ==================
    st.markdown("### 📋 Detalle de deuda por cliente")

    email_col = next((c for c in ["Email", "Correo", "E-mail"] if c in df_pend.columns), None)
    tel_col   = next((c for c in ["Teléfono", "Telefono", "Tel"] if c in df_pend.columns), None)

    columnas_info = ["Cliente", "Proyecto", "Curso", "Comercial", "Forma Pago"]
    if email_col: columnas_info.append(email_col)
    if tel_col:   columnas_info.append(tel_col)

    # Columnas numéricas candidatas
    columnas_sumatorias = []
    columnas_sumatorias += [f"Total {a}" for a in range(2018, 2022) if f"Total {a}" in df_pend.columns]
    columnas_sumatorias += (cols_22_aa if cols_22_aa else [])
    columnas_sumatorias = [c for c in columnas_sumatorias if c in df_pend.columns]

    if columnas_sumatorias:
        columnas_finales = list(dict.fromkeys(columnas_info + columnas_sumatorias))
        df_detalle = df_pend[columnas_finales].copy()
        df_detalle[columnas_sumatorias] = df_detalle[columnas_sumatorias].apply(pd.to_numeric, errors="coerce").fillna(0)
        df_detalle["Total deuda"] = df_detalle[columnas_sumatorias].sum(axis=1)

        # Agrupar por cliente
        def _join_unique(series):
            vals = [str(v).strip() for v in series if pd.notna(v) and str(v).strip()]
            return ", ".join(sorted(set(vals)))

        agg_dict = {
            "Proyecto": _join_unique,
            "Curso": _join_unique,
            "Comercial": _join_unique,
            "Forma Pago": lambda x: ", ".join(sorted(set(str(i) for i in x if pd.notna(i) and str(i).strip()))),
            "Total deuda": "sum",
        }
        if email_col:
            agg_dict[email_col] = _join_unique
        if tel_col:
            agg_dict[tel_col] = _join_unique

        df_detalle = (
            df_detalle.groupby(["Cliente"], as_index=False)
                      .agg(agg_dict)
                      .sort_values(by="Total deuda", ascending=False)
                      .reset_index(drop=True)
        )

        # excluir filas con Total deuda == 0
        df_detalle = df_detalle[df_detalle["Total deuda"] > 0]

        # Filtros ligeros
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

        # Tabla
        column_config = {
            "Total deuda": st.column_config.NumberColumn(
                "Total deuda", format="€ %.2f",
                help="Suma de todas las columnas de deuda seleccionadas"
            ),
        }
        st.dataframe(
            df_detalle,
            use_container_width=True,
            hide_index=True,
            column_config=column_config
        )

        resultado_exportacion["ResumenClientes"] = df_detalle
        st.session_state["detalle_filtrado_eim"] = df_detalle
    else:
        st.info("No hay columnas seleccionadas o disponibles para calcular el detalle.")

    st.markdown("---")


def _card(title, amount, ncli, variant="blue"):
    """
    variant: "blue" (default) | "red" (para 'Pendiente {MesActual}')
    """
    if variant == "red":
        bg = "#fff1f1"; border = "#ffc9c9"; title_color = "#7a1f1f"; amount_color = "#a32020"; people_color = "#7a1f1f"
    else:
        bg = "#f1f9ff"; border = "#dbe9ff"; title_color = "#0b5394"; amount_color = "#00335c"; people_color = "#2a6aa5"

    return f"""
    <div style="background:{bg};border:1px solid {border};border-radius:12px;
                padding:14px 16px;box-shadow:0 2px 6px rgba(0,0,0,.06);
                display:flex;flex-direction:column;gap:6px;min-height:92px">
      <div style="font-weight:700;color:{title_color}">{title}</div>
      <div style="display:flex;gap:12px;align-items:baseline;">
        <div style="font-size:26px;font-weight:800;color:{amount_color}">€ {_eu(amount)}</div>
        <div style="font-size:14px;color:{people_color}">👥 {int(ncli)}</div>
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
