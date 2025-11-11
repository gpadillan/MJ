# pagesEIM/deuda/pendiente_eim.py
# (Pendiente Total - versión sin AG Grid, alineada 1:1 con EIP)

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
_FIG_22_25 = None  # para exportar a HTML si se genera

# ===========================
# Vista principal
# ===========================
def vista_clientes_pendientes():
    # Ensancha el contenedor
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

    df_pendiente = df[df["Estado"] == "PENDIENTE"].copy()
    if df_pendiente.empty:
        st.info("ℹ️ No hay registros con estado PENDIENTE.")
        return

    # Fechas
    año_actual = datetime.today().year
    mes_actual = datetime.today().month
    meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
             "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
    mes_actual_nombre = meses[mes_actual - 1]

    total_clientes_unicos = set()

    # ---------------- 2018–2021 (solo tabla) ----------------
    st.markdown("## 🕰️ Periodo 2018–2021")
    cols_18_21 = [f"Total {a}" for a in range(2018, 2022) if f"Total {a}" in df_pendiente.columns]

    # Para poder mostrar la “Suma de periodos con gráfico”
    df1 = pd.DataFrame()
    total_deuda_18_21 = 0.0
    n_cli_18_21 = 0

    if cols_18_21:
        df1 = df_pendiente[["Cliente"] + cols_18_21].copy()
        df1[cols_18_21] = df1[cols_18_21].apply(pd.to_numeric, errors="coerce").fillna(0)
        df1 = df1.groupby("Cliente", as_index=False)[cols_18_21].sum()
        df1 = df1[df1[cols_18_21].sum(axis=1) > 0]
        total_clientes_unicos.update(df1["Cliente"].unique())

        st.dataframe(df1, use_container_width=True)
        total_deuda_18_21 = float(df1[cols_18_21].sum().sum())
        n_cli_18_21 = int(df1["Cliente"].nunique())

        st.markdown(
            f"**👥 Total clientes con deuda en 2018–2021:** "
            f"{n_cli_18_21} – 🏅 Total deuda: {_eu(total_deuda_18_21)} €"
        )

        resultado_exportacion["2018_2021"] = df1

    # ---------------- 2022–{año_actual} (tabla + gráfico si hay) ----------------
    st.markdown("## 📅 Periodo 2022–2025")

    cols_22_24 = [f"Total {a}" for a in range(2022, 2025) if f"Total {a}" in df_pendiente.columns]
    cols_2025_meses = [f"{m} {año_actual}" for m in meses if f"{m} {año_actual}" in df_pendiente.columns]

    key_meses_actual = "eim_pendiente_cols"
    default_2025 = cols_22_24 + [c for c in cols_2025_meses if meses.index(c.split()[0]) < mes_actual]

    cols_22_25 = st.multiselect(
        "📌 Selecciona columnas del periodo 2022–2025:",
        cols_22_24 + cols_2025_meses,
        default=st.session_state.get(key_meses_actual, default_2025),
        key=key_meses_actual
    )

    global _FIG_22_25
    _FIG_22_25 = None
    total_deuda_22_25 = 0.0
    df2 = pd.DataFrame()
    n_cli_22_25 = 0

    if cols_22_25:
        df2 = df_pendiente[["Cliente"] + cols_22_25].copy()
        df2[cols_22_25] = df2[cols_22_25].apply(pd.to_numeric, errors="coerce").fillna(0)
        df2 = df2.groupby("Cliente", as_index=False)[cols_22_25].sum()
        df2 = df2[df2[cols_22_25].sum(axis=1) > 0]
        total_clientes_unicos.update(df2["Cliente"].unique())

        st.dataframe(df2, use_container_width=True)

        total_deuda_22_25 = float(df2[cols_22_25].sum().sum())
        n_cli_22_25 = int(df2["Cliente"].nunique())

        st.markdown(
            f"**👥 Total clientes con deuda en 2022–{año_actual}:** "
            f"{n_cli_22_25} – 🏅 Total deuda: {_eu(total_deuda_22_25)} €"
        )

        resultado_exportacion["2022_2025"] = df2

        # Resumen para barras
        resumen2 = pd.DataFrame({
            "Periodo": cols_22_25,
            "Total_Deuda": [df2[c].sum() for c in cols_22_25],
            "Num_Clientes": [(df2.groupby("Cliente")[c].sum() > 0).sum() for c in cols_22_25],
        })

        # quitar periodos sin datos
        resumen2 = resumen2[~((resumen2["Total_Deuda"] == 0) & (resumen2["Num_Clientes"] == 0))].reset_index(drop=True)

        if not resumen2.empty:
            fig = px.bar(
                resumen2, x="Periodo", y="Total_Deuda",
                color="Total_Deuda", color_continuous_scale=["#eaf5ea", "#0b375b"],
                template="plotly_white", height=560
            )
            fig.update_traces(marker_line_color="black", marker_line_width=0.6, hovertemplate=None, hoverinfo="skip")
            max_y = float(resumen2["Total_Deuda"].max()) if len(resumen2) else 0.0
            fig.update_yaxes(range=[0, max_y * 1.22], title="Total")
            fig.update_xaxes(title="Periodo")
            fig.update_layout(margin=dict(l=20, r=20, t=20, b=50))

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
            _FIG_22_25 = fig
    else:
        resumen2 = pd.DataFrame()

    # ========= BLOQUE RESUMEN ÚNICO (SUMA DE AMBOS PERIODOS) =========
    # Se muestra ANTES de “🧮 Pendiente TOTAL (por año)”
    st.markdown("## 📊 Suma de periodos")
    hay_18_21 = not df1.empty
    hay_22_25 = not df2.empty

    if hay_18_21 or hay_22_25:
        n_cli_comb = (n_cli_18_21 if hay_18_21 else 0) + (n_cli_22_25 if hay_22_25 else 0)
        total_comb = (total_deuda_18_21 if hay_18_21 else 0.0) + (total_deuda_22_25 if hay_22_25 else 0.0)
        etiqueta = f"2018–{año_actual}"
        st.markdown(f"**👥 Clientes ({etiqueta}): {n_cli_comb} – 🏅 Total: € {_eu(total_comb)}**")

        # Guardar en exportación como fila única
        resultado_exportacion["Totales_Graficos"] = pd.DataFrame([{
            "Periodo": etiqueta,
            "Clientes (suma de ambos bloques)": n_cli_comb,
            "Total (€) (suma de ambos bloques)": total_comb
        }])
    else:
        st.info("No hay datos con los que generar el resumen combinado.")

    # ---------------- Tarjetas por año (con triple lógica para el año actual) ----------------
    def _year_from_total(col):
        try:
            return int(col.split()[-1])
        except Exception:
            return None

    all_cols = list(df_pendiente.columns)

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

    # Fuerza numéricos
    numeric_cols = col_totales[:]
    for y, lst in meses_por_año.items():
        numeric_cols += [col for _, col in lst]
    if numeric_cols:
        df_pendiente[numeric_cols] = df_pendiente[numeric_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

    def _sum_and_clients(cols):
        if not cols:
            return 0.0, 0
        tmp = df_pendiente[["Cliente"] + cols].copy()
        g = tmp.groupby("Cliente", as_index=False)[cols].sum()
        total = float(g[cols].sum().sum())
        ncli = int((g[cols].sum(axis=1) > 0).sum())
        return total, ncli

    tarjetas = []

    years_meses = sorted(meses_por_año.keys())
    all_years_present = sorted(set(years_totales) | set(years_meses))

    # Años pasados
    for y in [yy for yy in all_years_present if yy < año_actual]:
        cols = []
        if f"Total {y}" in df_pendiente.columns:
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
        cols_existentes = set(df_pendiente.columns)

        # 1) enero..mes-1
        meses_pasados = meses[:max(mes_actual - 1, 0)]
        cols_pasados = [cols_mes_año[m] for m in meses_pasados if cols_mes_año[m] in cols_existentes]

        # 2) mes actual
        col_mes_actual = cols_mes_año[mes_actual_nombre]
        cols_mes_actual = [col_mes_actual] if col_mes_actual in cols_existentes else []

        # 3) mes+1..diciembre
        meses_fut = meses[mes_actual:]
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

    # Años futuros
    for y in [yy for yy in all_years_present if yy > año_actual]:
        cols = []
        if y in meses_por_año:
            cols += [col for _, col in sorted(meses_por_año[y])]
        if f"Total {y}" in df_pendiente.columns:
            cols.append(f"Total {y}")
        total, ncli = _sum_and_clients(cols)
        if total != 0:
            tarjetas.append((f"Pendiente {y}", total, ncli))

    # Render tarjetas
    if tarjetas:
        st.markdown("## 🧮 Pendiente TOTAL (por año)")
        for i in range(0, len(tarjetas), 4):
            cols_stream = st.columns(4)
            for j, col in enumerate(cols_stream):
                if i + j >= len(tarjetas):
                    break
                item = tarjetas[i + j]
                if len(item) == 4:
                    title, amount, ncli, variant = item
                else:
                    title, amount, ncli = item
                    variant = "blue"
                col.markdown(_card(title, amount, ncli, variant), unsafe_allow_html=True)

    # ---------------- Totales consolidados ----------------
    total_clientes_unicos |= set(df_pendiente["Cliente"].unique())
    num_clientes_total = len(total_clientes_unicos)

    # Pendiente con deuda y futuro (sumando por tarjetas)
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

    # Normalización de posibles nombres para email/teléfono
    email_col = next((c for c in ["Email", "Correo", "E-mail"] if c in df_pendiente.columns), None)
    tel_col   = next((c for c in ["Teléfono", "Telefono", "Tel"] if c in df_pendiente.columns), None)

    # Columnas base pedidas (solo si existen)
    base_cols = [
        "ID Factura","Proyecto","Curso","Cliente",
        "Provincia","Localidad","Nacionalidad","País",
        "Nº Factura","Importe Total Factura","Fecha Factura",
        "Fecha Inicio","Fecha Fin","Forma Pago","Estado",
        "Comercial","Observaciones","Cobrados mes actual",
        "Pendientes mes actual","Fecha estimada mes actual","Periodo"
    ]
    if email_col: base_cols.insert(4, email_col)
    if tel_col:   base_cols.insert(5 if email_col else 4, tel_col)

    # Columnas mes-a-mes y totales por año 2018-2029
    mensual_cols = []
    total_cols   = []
    for year in range(2018, 2030):
        total_name = f"Total {year}"
        if total_name in df_pendiente.columns:
            total_cols.append(total_name)
        for m in meses:
            col = f"{m} {year}"
            if col in df_pendiente.columns:
                mensual_cols.append(col)

    desired_cols = base_cols + mensual_cols + total_cols
    final_cols = [c for c in desired_cols if c in df_pendiente.columns]
    if not final_cols:
        st.info("No se han encontrado en el archivo las columnas solicitadas para el detalle.")
        return

    df_detalle = df_pendiente[final_cols].copy()

    # Detectar columnas numéricas y convertir
    numeric_candidates = set(mensual_cols + total_cols)
    if "Importe Total Factura" in df_detalle.columns:
        numeric_candidates.add("Importe Total Factura")
    numeric_cols_present = [c for c in numeric_candidates if c in df_detalle.columns]
    if numeric_cols_present:
        df_detalle[numeric_cols_present] = df_detalle[numeric_cols_present].apply(pd.to_numeric, errors="coerce").fillna(0)

    # Total deuda por fila
    cols_suma_fila = [c for c in (mensual_cols + total_cols) if c in df_detalle.columns]
    if cols_suma_fila:
        df_detalle["Total deuda (fila)"] = df_detalle[cols_suma_fila].sum(axis=1)
    else:
        df_detalle["Total deuda (fila)"] = 0.0

    # ===== Filtros del detalle =====
    with st.expander("🔎 Filtros del detalle"):
        col_f1, col_f2, col_f3 = st.columns([1.2, 1, 1])
        texto_cliente = col_f1.text_input("Buscar cliente contiene...", "")
        lista_comerciales = sorted(df_detalle["Comercial"].dropna().astype(str).unique()) if "Comercial" in df_detalle.columns else []
        sel_comerciales = col_f2.multiselect("Comercial", options=lista_comerciales)
        max_total = float(df_detalle["Total deuda (fila)"].max()) if not df_detalle.empty else 0.0
        rango = col_f3.slider("Rango Total deuda (€)", 0.0, max_total, (0.0, max_total), step=max(1.0, max_total/100 if max_total else 1.0))

    if texto_cliente and "Cliente" in df_detalle.columns:
        df_detalle = df_detalle[df_detalle["Cliente"].str.contains(texto_cliente, case=False, na=False)]
    if sel_comerciales and "Comercial" in df_detalle.columns:
        df_detalle = df_detalle[df_detalle["Comercial"].isin(sel_comerciales)]
    if rango:
        df_detalle = df_detalle[(df_detalle["Total deuda (fila)"] >= rango[0]) & (df_detalle["Total deuda (fila)"] <= rango[1])]

    # Config de formato €
    column_config = {
        "Total deuda (fila)": st.column_config.NumberColumn("Total deuda (fila)", format="€ %.2f"),
    }
    for c in numeric_cols_present:
        column_config[c] = st.column_config.NumberColumn(c, format="€ %.2f")

    st.dataframe(
        df_detalle,
        use_container_width=True,
        hide_index=True,
        column_config=column_config
    )

    # Guardamos para exportación
    resultado_exportacion["DetalleFilas"] = df_detalle.copy()
    st.session_state["detalle_filtrado_eim"] = df_detalle

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
    """Solo para exportación (sin gráfico)."""
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

        if "Totales_Graficos" in resultado_exportacion:
            html_buffer.write("<h1>Suma de periodos</h1>")
            html_buffer.write(resultado_exportacion["Totales_Graficos"].to_html(index=False))
            if _FIG_22_25 is not None:
                html_buffer.write(to_html(_FIG_22_25, include_plotlyjs='cdn', full_html=False))

        if "2018_2021" in resultado_exportacion:
            html_buffer.write("<h1>Resumen 2018–2021</h1>")
            html_buffer.write(resultado_exportacion["2018_2021"].to_html(index=False))

        if "2022_2025" in resultado_exportacion:
            html_buffer.write("<h1>Resumen 2022–2025</h1>")
            html_buffer.write(resultado_exportacion["2022_2025"].to_html(index=False))

        if "Totales_Años_Meses" in resultado_exportacion:
            html_buffer.write("<h2>Totales por año (deuda anual)</h2>")
            html_buffer.write(resultado_exportacion["Totales_Años_Meses"].to_html(index=False))

        if "DetalleFilas" in resultado_exportacion:
            html_buffer.write("<h2>Detalle de deuda por cliente (filas)</h2>")
            html_buffer.write(resultado_exportacion["DetalleFilas"].to_html(index=False))

        html_buffer.write("</body></html>")

        html_str = html_buffer.getvalue()
        st.session_state[SAVE_KEY_HTML] = html_str
        st.download_button(
            label="🌐 Descargar reporte HTML completo (EIM)",
            data=html_str,
            file_name="reporte_pendiente_eim.html",
            mime="text/html"
        )
