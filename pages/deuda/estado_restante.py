# pages/deuda/estado_restante.py
# (Estados seleccionables - versión SINGLE SELECT, gemelo de pendiente.py)

import io
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from plotly.io import to_html

# ======================================================
# Configuración
# ======================================================
ESTADOS_OPCIONES = [
    "DOMICILIACIÓN CONFIRMADA",
    "DOMICILIACIÓN EMITIDA",
    "DUDOSO COBRO",
    "NO COBRADO",
    "INCOBRABLE",
]

# ======================================================
# Utilidades
# ======================================================
def _eu(n):
    """Formatea en estilo EU con coma decimal y punto de miles, preservando el signo delante."""
    try:
        f = float(n)
    except Exception:
        return "0,00"
    s = f"{f:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s  # ej: -19.858,01

def _bar_chart(resumen_df, title):
    """
    Dibuja un bar chart que soporta positivos/negativos y muestra anotaciones arriba/abajo.
    resumen_df: columnas -> Periodo, Total_Deuda, Num_Clientes
    """
    if resumen_df.empty:
        return None

    fig = px.bar(
        resumen_df, x="Periodo", y="Total_Deuda",
        color="Total_Deuda", color_continuous_scale=["#f5eaea", "#0b375b"],
        template="plotly_white", height=560, title=title
    )
    fig.update_traces(marker_line_color="black", marker_line_width=0.6, hovertemplate=None, hoverinfo="skip")

    # Rango Y para incluir negativos/positivos con padding
    min_y = float(resumen_df["Total_Deuda"].min())
    max_y = float(resumen_df["Total_Deuda"].max())
    pad_pos = max_y * 0.22 if max_y > 0 else 0
    pad_neg = abs(min_y) * 0.22 if min_y < 0 else 0
    y_min = min(0.0, min_y - pad_neg)
    y_max = max(0.0, max_y + pad_pos)
    if y_min == y_max:  # caso extremo todos 0
        y_min, y_max = -1, 1
    fig.update_yaxes(range=[y_min, y_max], title="Total")
    fig.update_xaxes(title="Periodo")

    # Anotaciones: arriba si positivo; un poco por debajo si negativo
    annotations = []
    for _, r in resumen_df.iterrows():
        val = float(r["Total_Deuda"])
        y_anno = val * (1.045 if val >= 0 else 0.955)
        annotations.append(dict(
            x=r["Periodo"], y=y_anno,
            yanchor="bottom" if val >= 0 else "top",
            xanchor="center",
            text=f"€ {_eu(val)}<br>👥 {int(r['Num_Clientes'])}",
            showarrow=False, font=dict(color="white", size=16),
            align="center", bgcolor="rgba(0,0,0,0.95)", bordercolor="black", borderwidth=1.2, opacity=1
        ))
    fig.update_layout(margin=dict(l=20, r=20, t=40, b=50), annotations=annotations)
    return fig

def _card(title, amount, ncli, variant="blue"):
    """
    variant: "blue" (por defecto) | "red" (para '{LABEL} {MesActual}')
    """
    if variant == "red":
        bg = "#fff1f1"; border = "#ffc9c9"; title_color = "#7a1f1f"; amount_color = "#a32020"; people_color = "#7a1f1f"
    else:
        bg = "#f1f9ff"; border = "#dbe9ff"; title_color = "#0b5394"; amount_color = "#00335c"; people_color = "#2a6aa5"

    return f"""
    <div style="background:{bg};border:1px solid {border};border-radius:12px;
                padding:14px 16px;box-shadow:0 2px 6px rgba(0,0,0,0.06);
                display:flex;flex-direction:column;gap:6px;min-height:92px">
      <div style="font-weight:700;color:{title_color}">{title}</div>
      <div style="display:flex;gap:12px;align-items:baseline;">
        <div style="font-size:26px;font-weight:800;color:{amount_color}">€ {_eu(amount)}</div>
        <div style="font-size:14px;color:{people_color}">👥 {int(ncli)}</div>
      </div>
    </div>
    """

resultado_exportacion = {}
_FIG_18_21 = None
_FIG_22_25_RESTO = None

# ======================================================
# Vista principal
# ======================================================
def vista_estado_unico():
    # Ensancha el contenedor
    st.markdown("""
    <style>
      .block-container {max-width: 100% !important; padding-left: 1rem; padding-right: 1rem;}
      .stDataFrame { font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

    st.header("📄 Estados")

    if "excel_data" not in st.session_state or st.session_state["excel_data"] is None:
        st.warning("⚠️ No hay archivo cargado. Ve a la sección Gestión de Datos.")
        return

    df = st.session_state["excel_data"].copy()
    df.columns = df.columns.str.strip()

    if "Estado" not in df.columns:
        st.error("❌ Falta la columna 'Estado' en el Excel.")
        return

    # Normaliza estado a mayúsculas con tildes conservadas
    df["Estado"] = (
        df["Estado"].astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip().str.upper()
    )

    # ---------- Selector de estado (uno solo) ----------
    st.markdown("### 🎯 Selecciona el estado a analizar")
    estado_default = st.session_state.get("estado_restante_estado_sel", ESTADOS_OPCIONES[0])
    estado_sel = st.selectbox(
        "Estado",
        options=ESTADOS_OPCIONES,
        index=ESTADOS_OPCIONES.index(estado_default) if estado_default in ESTADOS_OPCIONES else 0,
        key="estado_restante_estado_sel"
    )

    df_target = df[df["Estado"] == estado_sel].copy()
    if df_target.empty:
        st.info(f"ℹ️ No hay registros para el estado seleccionado: **{estado_sel}**.")
        return

    # Etiqueta para tarjetas
    LABEL = estado_sel.title()

    # ---------- Fechas ----------
    año_actual = datetime.today().year
    mes_actual = datetime.today().month
    meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
             "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
    mes_actual_nombre = meses[mes_actual - 1]

    total_clientes_unicos = set()

    # ---------------- 2018–2021 (tabla + gráfico SIEMPRE que haya dato) ----------------
    st.markdown("## 🕰️ Periodo 2018–2021")
    cols_18_21 = [f"Total {a}" for a in range(2018, 2022) if f"Total {a}" in df_target.columns]

    global _FIG_18_21
    _FIG_18_21 = None

    # Guardaremos estos DF para el cómputo de la suma del bloque
    df1 = pd.DataFrame()
    resumen_18_21 = pd.DataFrame()
    total_18_21 = 0.0
    n_cli_18_21 = 0

    if cols_18_21:
        df1 = df_target[["Cliente"] + cols_18_21].copy()
        df1[cols_18_21] = df1[cols_18_21].apply(pd.to_numeric, errors="coerce").fillna(0)
        # permitir negativos/positivos distintos de 0
        df1 = df1.groupby("Cliente", as_index=False)[cols_18_21].sum()
        df1 = df1[df1[cols_18_21].sum(axis=1) != 0]
        total_clientes_unicos.update(df1["Cliente"].unique())

        st.dataframe(df1, use_container_width=True)

        total_18_21 = float(df1[cols_18_21].sum().sum())
        n_cli_18_21 = int(df1["Cliente"].nunique())
        st.markdown(
            f"**👥 Clientes (2018–2021): {n_cli_18_21} – 🏅 Total: € {_eu(total_18_21)}**"
        )
        resultado_exportacion["2018_2021"] = df1

        # 👉 Gráfico para 2018–2021 si hay alguna columna con suma != 0
        resumen_18_21 = pd.DataFrame({
            "Periodo": cols_18_21,
            "Total_Deuda": [df1[c].sum() for c in cols_18_21],
            "Num_Clientes": [(df1.groupby("Cliente")[c].sum() != 0).sum() for c in cols_18_21],
        })
        # quitar columnas 0/0
        resumen_18_21 = resumen_18_21[~((resumen_18_21["Total_Deuda"] == 0) & (resumen_18_21["Num_Clientes"] == 0))].reset_index(drop=True)
        if not resumen_18_21.empty:
            _FIG_18_21 = _bar_chart(resumen_18_21, "Totales 2018–2021")
            st.plotly_chart(_FIG_18_21, use_container_width=True)

    # ---------------- 2022–Año actual (tabla + gráfico si hay dato) ----------------
    st.markdown("## 📅 Periodo 2022–2025")

    cols_22_24 = [f"Total {a}" for a in range(2022, 2025) if f"Total {a}" in df_target.columns]
    cols_year_meses = [f"{m} {año_actual}" for m in meses if f"{m} {año_actual}" in df_target.columns]

    key_meses_actual = "filtro_meses_2025_restante_single"
    default_2025 = cols_22_24 + [c for c in cols_year_meses if meses.index(c.split()[0]) < mes_actual]

    cols_22_25 = st.multiselect(
        "📌 Selecciona columnas del periodo 2022–2025:",
        cols_22_24 + cols_year_meses,
        default=st.session_state.get(key_meses_actual, default_2025),
        key=key_meses_actual
    )

    global _FIG_22_25_RESTO
    _FIG_22_25_RESTO = None
    df2 = pd.DataFrame()
    resumen2 = pd.DataFrame()
    total_22_25 = 0.0
    n_cli_22_25 = 0

    if cols_22_25:
        df2 = df_target[["Cliente"] + cols_22_25].copy()
        df2[cols_22_25] = df2[cols_22_25].apply(pd.to_numeric, errors="coerce").fillna(0)
        df2 = df2.groupby("Cliente", as_index=False)[cols_22_25].sum()
        df2 = df2[df2[cols_22_25].sum(axis=1) != 0]  # permitir negativos
        total_clientes_unicos.update(df2["Cliente"].unique())

        st.dataframe(df2, use_container_width=True)

        total_22_25 = float(df2[cols_22_25].sum().sum())
        n_cli_22_25 = int(df2["Cliente"].nunique())
        st.markdown(
            f"**👥 Clientes (2022–{año_actual}): {n_cli_22_25} – 🏅 Total: € {_eu(total_22_25)}**"
        )

        resultado_exportacion["2022_2025"] = df2

        resumen2 = pd.DataFrame({
            "Periodo": cols_22_25,
            "Total_Deuda": [df2[c].sum() for c in cols_22_25],
            "Num_Clientes": [(df2.groupby("Cliente")[c].sum() != 0).sum() for c in cols_22_25],
        })
        resumen2 = resumen2[~((resumen2["Total_Deuda"] == 0) & (resumen2["Num_Clientes"] == 0))].reset_index(drop=True)

        if not resumen2.empty:
            _FIG_22_25_RESTO = _bar_chart(resumen2, f"Totales 2022–{año_actual}")
            st.plotly_chart(_FIG_22_25_RESTO, use_container_width=True)

    # ========= BLOQUE RESUMEN ÚNICO (SUMA DE AMBOS PERIODOS) =========
    # Se muestra justo ANTES de “🧮 Totales (por año)”
    st.markdown("## 📊 Suma de periodos con gráfico")

    hay_18_21 = not resumen_18_21.empty
    hay_22_25 = not resumen2.empty

    if hay_18_21 or hay_22_25:
        # Suma directa de ambos bloques (tal y como pides)
        n_cli_comb = (n_cli_18_21 if hay_18_21 else 0) + (n_cli_22_25 if hay_22_25 else 0)
        total_comb = (total_18_21 if hay_18_21 else 0.0) + (total_22_25 if hay_22_25 else 0.0)

        # Etiqueta compacta de rango total
        etiqueta = f"2018–{año_actual}"

        # Línea única en el formato exacto que usas
        st.markdown(f"**👥 Clientes ({etiqueta}): {n_cli_comb} – 🏅 Total: € {_eu(total_comb)}**")

        # Guardar en exportación como fila única
        resultado_exportacion["Totales_Graficos"] = pd.DataFrame([{
            "Periodo": etiqueta,
            "Clientes (suma de ambos bloques)": n_cli_comb,
            "Total (€) (suma de ambos bloques)": total_comb
        }])
    else:
        st.info("No hay datos con los que generar gráficos en los periodos definidos.")

    # ---------------- Tarjetas (con mes actual en rojo claro) ----------------
    def _year_from_total(col):
        try:
            return int(col.split()[-1])
        except Exception:
            return None

    all_cols = list(df_target.columns)

    col_totales = [c for c in all_cols if c.startswith("Total ") and c.split()[-1].isdigit()]
    years_totales = sorted({_year_from_total(c) for c in col_totales if _year_from_total(c) is not None})

    meses_por_año = {}
    for c in all_cols:
        for i, m in enumerate(meses, start=1):
            if c.startswith(f"{m} "):
                try:
                    y = int(c.split()[-1])
                except Exception:
                    continue
                meses_por_año.setdefault(y, []).append((i, c))

    numeric_cols = col_totales[:]
    for y, lst in meses_por_año.items():
        numeric_cols += [col for _, col in lst]
    if numeric_cols:
        df_target[numeric_cols] = df_target[numeric_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

    def _sum_and_clients(cols):
        if not cols:
            return 0.0, 0
        tmp = df_target[["Cliente"] + cols].copy()
        g = tmp.groupby("Cliente", as_index=False)[cols].sum()
        total = float(g[cols].sum().sum())
        ncli = int((g[cols].sum(axis=1) != 0).sum())
        return total, ncli

    tarjetas = []

    years_meses = sorted(meses_por_año.keys())
    all_years_present = sorted(set(years_totales) | set(years_meses))

    # Años pasados
    for y in [yy for yy in all_years_present if yy < año_actual]:
        cols = []
        if f"Total {y}" in df_target.columns:
            cols = [f"Total {y}"]
        elif y in meses_por_año:
            cols = [col for _, col in sorted(meses_por_año[y])]
        total, ncli = _sum_and_clients(cols)
        if total != 0:
            tarjetas.append(("Total " + str(y), total, ncli))

    # Año actual → tres particiones con prefijo LABEL
    if año_actual in all_years_present:
        cols_mes_año = {m: f"{m} {año_actual}" for m in meses}
        cols_existentes = set(df_target.columns)

        # 1) enero..mes-1
        meses_pasados = meses[:max(mes_actual - 1, 0)]
        cols_pasados = [cols_mes_año[m] for m in meses_pasados if cols_mes_año[m] in cols_existentes]

        # 2) mes actual (rojo)
        col_mes_actual = cols_mes_año[mes_actual_nombre]
        cols_mes_actual = [col_mes_actual] if col_mes_actual in cols_existentes else []

        # 3) mes+1..diciembre
        meses_fut = meses[mes_actual:]
        cols_futuro = [cols_mes_año[m] for m in meses_fut if cols_mes_año[m] in cols_existentes]

        tiene_mensuales_actual = any(c.endswith(f" {año_actual}") for c in cols_existentes)
        if not tiene_mensuales_actual and f"Total {año_actual}" in cols_existentes:
            total, ncli = _sum_and_clients([f"Total {año_actual}"])
            if total != 0:
                tarjetas.append((f"{LABEL} actual", total, ncli))
        else:
            if cols_pasados:
                total_pas, ncli_pas = _sum_and_clients(cols_pasados)
                if total_pas != 0:
                    tarjetas.append((f"{LABEL} actual", total_pas, ncli_pas))
            if cols_mes_actual:
                total_act, ncli_act = _sum_and_clients(cols_mes_actual)
                if total_act != 0:
                    tarjetas.append((f"{LABEL} {mes_actual_nombre}", total_act, ncli_act, "red"))
            if cols_futuro:
                total_fut, ncli_fut = _sum_and_clients(cols_futuro)
                if total_fut != 0:
                    tarjetas.append((f"{LABEL} {año_actual} futuro", total_fut, ncli_fut))

    # Años futuros
    for y in [yy for yy in all_years_present if yy > año_actual]:
        cols = []
        if y in meses_por_año:
            cols += [col for _, col in sorted(meses_por_año[y])]
        if f"Total {y}" in df_target.columns:
            cols.append(f"Total {y}")
        total, ncli = _sum_and_clients(cols)
        if total != 0:
            tarjetas.append((f"{LABEL} {y}", total, ncli))

    # Render tarjetas
    if tarjetas:
        st.markdown("## 🧮 Totales (por año)")
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
                col.markdown(_card(title, amount, ncli, variant=variant), unsafe_allow_html=True)

    # ---------------- Totales consolidados ----------------
    total_clientes_unicos |= set(df_target["Cliente"].unique())

    # “actual” = Total YYYY + bloque actual + mes actual
    importe_actual = 0.0
    importe_futuro = 0.0
    for item in tarjetas:
        title, amount = item[0], item[1]
        if title.startswith("Total ") or title.endswith(" actual") or title.endswith(f" {mes_actual_nombre}"):
            importe_actual += amount
        elif title.endswith(" futuro") or title.split()[-1].isdigit():
            importe_futuro += amount

    total_importe = importe_actual + importe_futuro

    st.markdown(
        f"**📌 {LABEL} — actual:** € {_eu(importe_actual)}  &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"**🔮 {LABEL} — futuro:** € {_eu(importe_futuro)}  &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"**🧮 TOTAL:** € {_eu(total_importe)}"
    )

    st.session_state["total_importe_estado_unico"] = total_importe

    # ---------------- DETALLE: TABLA SIMPLE (con filtros) ----------------
    st.markdown("### 📋 Detalle por cliente")

    email_col = next((c for c in ["Email", "Correo", "E-mail"] if c in df_target.columns), None)
    tel_col   = next((c for c in ["Teléfono", "Telefono", "Tel"] if c in df_target.columns), None)

    columnas_info = ["Cliente", "Proyecto", "Curso", "Comercial", "Forma Pago", "Estado"]
    if email_col: columnas_info.append(email_col)
    if tel_col:   columnas_info.append(tel_col)

    # Columnas numéricas candidatas (igual que arriba)
    columnas_sumatorias = []
    columnas_sumatorias += [f"Total {a}" for a in range(2018, 2022) if f"Total {a}" in df_target.columns]
    columnas_sumatorias += list(resumen2["Periodo"]) if not resumen2.empty else []
    columnas_sumatorias = [c for c in columnas_sumatorias if c in df_target.columns]

    if columnas_sumatorias:
        columnas_finales = list(dict.fromkeys(columnas_info + columnas_sumatorias))
        df_detalle = df_target[columnas_finales].copy()
        df_detalle[columnas_sumatorias] = df_detalle[columnas_sumatorias].apply(pd.to_numeric, errors="coerce").fillna(0)
        df_detalle["Total importe"] = df_detalle[columnas_sumatorias].sum(axis=1)

        # ===== Filtros del detalle =====
        with st.expander("🔎 Filtros del detalle"):
            col_f1, col_f2, col_f3 = st.columns([1.2, 1, 1])
            texto_cliente = col_f1.text_input("Buscar cliente contiene...", "")

            lista_comerciales = sorted({
                c.strip()
                for s in df_detalle["Comercial"].dropna().astype(str)
                for c in s.split(",")
                if c.strip()
            }) if "Comercial" in df_detalle.columns else []
            sel_comerciales = col_f2.multiselect("Comercial", options=lista_comerciales)

            # Slider que soporta negativos: [min_total, max_total]
            if not df_detalle.empty:
                min_total = float(df_detalle["Total importe"].min())
                max_total = float(df_detalle["Total importe"].max())
            else:
                min_total = 0.0
                max_total = 0.0

            if min_total == max_total:
                col_f3.caption(f"Rango Total importe (€): { _eu(min_total) } (sin rango)")
                rango = None
            else:
                paso = max(0.01, round((max_total - min_total) / 100, 2))
                rango = col_f3.slider(
                    "Rango Total importe (€)",
                    min_total, max_total,
                    (min_total, max_total),
                    step=paso
                )

        # Aplicar filtros
        if texto_cliente:
            df_detalle = df_detalle[df_detalle["Cliente"].str.contains(texto_cliente, case=False, na=False)]
        if sel_comerciales and "Comercial" in df_detalle.columns:
            df_detalle = df_detalle[df_detalle["Comercial"].apply(
                lambda s: any(c in [x.strip() for x in str(s).split(",")] for c in sel_comerciales)
            )]
        if rango:
            df_detalle = df_detalle[(df_detalle["Total importe"] >= rango[0]) & (df_detalle["Total importe"] <= rango[1])]

        # Tabla nativa con formato €
        column_config = {
            "Total importe": st.column_config.NumberColumn("Total importe", format="€ %.2f", help="Suma de columnas seleccionadas"),
        }
        st.dataframe(
            df_detalle,
            use_container_width=True,
            hide_index=True,
            column_config=column_config
        )

        resultado_exportacion["ResumenClientes"] = df_detalle
        st.session_state["detalle_filtrado_estado_unico"] = df_detalle
    else:
        st.info("No hay columnas seleccionadas o disponibles para calcular el detalle.")

    st.markdown("---")


def vista_export_resumen():
    """Solo prepara datos para exportación (sin gráfico)."""
    if "excel_data" not in st.session_state or st.session_state["excel_data"] is None:
        return

    df = st.session_state["excel_data"].copy()
    df.columns = df.columns.str.strip()
    if "Estado" not in df.columns:
        return
    df["Estado"] = df["Estado"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip().str.upper()

    estado_sel = st.session_state.get("estado_restante_estado_sel", ESTADOS_OPCIONES[0])
    df_target = df[df["Estado"] == estado_sel]

    año_actual = datetime.today().year
    columnas_totales = [c for c in df_target.columns
                        if c.startswith("Total ") and c.split()[-1].isdigit()
                        and int(c.split()[-1]) <= año_actual]
    if not columnas_totales:
        return

    df_target[columnas_totales] = df_target[columnas_totales].apply(pd.to_numeric, errors="coerce").fillna(0)
    resumen_total = pd.DataFrame({
        "Periodo": columnas_totales,
        "Suma_Total": [df_target[c].sum() for c in columnas_totales],
        "Num_Clientes": [(df_target.groupby("Cliente")[c].sum() != 0).sum() for c in columnas_totales]
    })
    resultado_exportacion["Totales_Años_Meses"] = resumen_total


def render():
    vista_estado_unico()
    vista_export_resumen()

    if resultado_exportacion:
        st.session_state["descarga_estado_restante"] = resultado_exportacion

        # Excel
        buffer_excel = io.BytesIO()
        with pd.ExcelWriter(buffer_excel, engine="xlsxwriter") as writer:
            for sheet_name, df_export in resultado_exportacion.items():
                if isinstance(df_export, pd.DataFrame):
                    df_export.to_excel(writer, index=False, sheet_name=sheet_name[:31])
        buffer_excel.seek(0)
        st.download_button(
            label="📥 Descargar Excel (estado seleccionado)",
            data=buffer_excel.getvalue(),
            file_name="exportacion_estado_seleccionado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # HTML
        html_buffer = io.StringIO()
        html_buffer.write("<html><head><meta charset='utf-8'><title>Exportación — Estado seleccionado</title></head><body>")
        if "Totales_Graficos" in resultado_exportacion:
            html_buffer.write("<h1>Suma de periodos con gráfico</h1>")
            html_buffer.write(resultado_exportacion["Totales_Graficos"].to_html(index=False))
            if _FIG_18_21 is not None:
                html_buffer.write(to_html(_FIG_18_21, include_plotlyjs='cdn', full_html=False))
            if _FIG_22_25_RESTO is not None:
                html_buffer.write(to_html(_FIG_22_25_RESTO, include_plotlyjs='cdn', full_html=False))
        if "2018_2021" in resultado_exportacion:
            html_buffer.write("<h1>Resumen 2018–2021</h1>")
            html_buffer.write(resultado_exportacion["2018_2021"].to_html(index=False))
        if "2022_2025" in resultado_exportacion:
            html_buffer.write("<h1>Resumen 2022–2025</h1>")
            html_buffer.write(resultado_exportacion["2022_2025"].to_html(index=False))
        if "Totales_Años_Meses" in resultado_exportacion:
            html_buffer.write("<h2>Totales por año</h2>")
            html_buffer.write(resultado_exportacion["Totales_Años_Meses"].to_html(index=False))
        html_buffer.write("</body></html>")
        st.download_button(
            label="🌐 Descargar reporte HTML",
            data=html_buffer.getvalue(),
            file_name="reporte_estado_seleccionado.html",
            mime="text/html"
        )
