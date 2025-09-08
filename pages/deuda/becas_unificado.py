# becas_isa_page.py

import os
import io
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.io as pio
import streamlit as st


# -------------------- helpers --------------------

def _eu(v: float) -> str:
    """Formato € europeo con decimales."""
    try:
        n = float(v)
    except Exception:
        n = 0.0
    return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def _card(title: str, value: float, tone: str = "green") -> str:
    if tone == "green":
        bg, bd, titlec, valc = "#f6faf5", "#d7ead2", "#254d2c", "#0b5b1d"
    else:
        bg, bd, titlec, valc = "#f1f8ff", "#d7e8ff", "#1f3e73", "#0b5394"
    return f"""
    <div style="background:{bg};border:1px solid {bd};border-radius:12px;
                padding:12px 14px;box-shadow:0 2px 6px rgba(0,0,0,.05);
                display:flex;flex-direction:column;gap:4px;min-height:80px">
        <div style="font-weight:600;color:{titlec}">{title}</div>
        <div style="font-size:22px;font-weight:800;color:{valc}">€ {_eu(value)}</div>
    </div>
    """


# -------------------- página --------------------

def render():
    if "excel_data" not in st.session_state or st.session_state["excel_data"] is None:
        st.warning("⚠️ No hay archivo cargado. Ve a la sección Gestión de Datos.")
        return

    df = st.session_state["excel_data"].copy()
    if "Forma Pago" not in df.columns:
        st.error("La columna 'Forma Pago' no existe en el archivo.")
        return

    df["Forma Pago"] = df["Forma Pago"].astype(str)
    df_beca = df[df["Forma Pago"].str.strip().str.upper() == "BECAS ISA"].copy()
    if df_beca.empty:
        st.info("No hay registros con 'BECAS ISA'.")
        return

    export_dict = {}
    html = io.StringIO()
    html.write("<html><head><meta charset='utf-8'><title>Informe Becas ISA</title></head><body>")

    # ------------- Suma por año -------------
    st.subheader("🎓 Becas ISA – Suma por Año")
    html.write("<h2>🎓 Becas ISA – Suma por Año</h2>")

    columnas_totales = [f"Total {y}" for y in range(2018, 2030)]
    disponibles = [c for c in columnas_totales if c in df_beca.columns]
    seleccion = st.multiselect(
        "Selecciona los años a visualizar:",
        disponibles,
        default=disponibles,
        key="filtro_becas_isa_anios",
    )

    if seleccion:
        df_beca[seleccion] = df_beca[seleccion].apply(pd.to_numeric, errors="coerce").fillna(0)
        suma = df_beca[seleccion].sum().reset_index()
        suma.columns = ["Año", "Suma Total"]
        suma["Año"] = suma["Año"].str.replace("Total ", "")
        # quitar años con 0
        suma = suma[suma["Suma Total"] > 0]

        total = float(suma["Suma Total"].sum())
        st.markdown(
            f"<div style='display:inline-block;padding:6px 10px;border-radius:8px;"
            f"background:#eaf5ea;color:#0b5b1d;font-weight:700;'>"
            f"Total acumulado: € {_eu(total)}</div>",
            unsafe_allow_html=True,
        )
        html.write(f"<p><strong>Total acumulado: € {_eu(total)}</strong></p>")

        if not suma.empty:
            fig = px.bar(
                suma,
                x="Año",
                y="Suma Total",
                color="Suma Total",
                # 🔴→🟣 rojo a morado
                color_continuous_scale="Sunsetdark",
                template="plotly_white",
                height=360,
                text="Suma Total",  # <- texto dentro de la barra
            )
            fig.update_traces(
                marker_line_color="black",
                marker_line_width=0.6,
                hovertemplate="Año: %{x}<br>Total: € %{y:,}<extra></extra>",
                texttemplate="€ %{y:,.0f}",   # valor real dentro
                textposition="inside",
                textfont_color="white",
            )
            ymax = float(suma["Suma Total"].max())
            fig.update_yaxes(range=[0, ymax * 1.15], title="Suma Total")
            fig.update_layout(margin=dict(l=20, r=20, t=30, b=40), coloraxis_showscale=True)

            st.plotly_chart(fig, use_container_width=True)
            html.write(pio.to_html(fig, include_plotlyjs="cdn", full_html=False))
        else:
            st.info("No hay años con suma > 0 para mostrar.")

        # Excel de respaldo
        df_total = suma.copy()
        df_total.loc[len(df_total)] = ["TOTAL GENERAL", total]
        export_dict["Total_Anios"] = df_total

    # ------------- Mes – Año actual -------------
    st.subheader("📅 Becas ISA – Mes - Año Actual")
    html.write("<h2>📅 Becas ISA – Mes - Año Actual</h2>")

    year = datetime.today().year
    meses_nombres = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    cols_mes = [f"{m} {year}" for m in meses_nombres]
    disp_mes = [c for c in cols_mes if c in df_beca.columns]

    if disp_mes:
        sel_mes = st.multiselect(
            f"Selecciona los meses de {year}",
            disp_mes,
            default=disp_mes,
            key="filtro_becas_isa_mes",
        )
        if sel_mes:
            df_beca[sel_mes] = df_beca[sel_mes].apply(pd.to_numeric, errors="coerce").fillna(0)
            suma_mes = df_beca[sel_mes].sum().reset_index()
            suma_mes.columns = ["Mes", "Suma Total"]
            suma_mes = suma_mes[suma_mes["Suma Total"] > 0]
            total_mes = float(suma_mes["Suma Total"].sum())

            st.markdown(
                f"<div style='display:inline-block;padding:6px 10px;border-radius:8px;"
                f"background:#eaf5ff;color:#0b5394;font-weight:700;'>"
                f"Total acumulado mensual: € {_eu(total_mes)}</div>",
                unsafe_allow_html=True,
            )
            html.write(f"<p><strong>Total acumulado mensual: € {_eu(total_mes)}</strong></p>")

            if not suma_mes.empty:
                fig_mes = px.pie(
                    suma_mes,
                    names="Mes",
                    values="Suma Total",
                    hole=0.35,
                    template="plotly_white",
                    height=520,
                )
                fig_mes.update_traces(
                    texttemplate="%{label}<br>€ %{value:,.0f}",
                    textposition="inside",
                    textfont_size=14,
                    hovertemplate="%{label}: € %{value:,.0f}<extra></extra>",
                )
                st.plotly_chart(fig_mes, use_container_width=True)
                html.write(pio.to_html(fig_mes, include_plotlyjs="cdn", full_html=False))

            export_dict["Mes_Actual"] = pd.concat(
                [suma_mes, pd.DataFrame([{"Mes": "TOTAL GENERAL", "Suma Total": total_mes}])],
                ignore_index=True,
            )

    # ------------- Futuro (un único selector) -------------
    st.subheader("🔮 Becas ISA – Futuro (meses restantes y años posteriores)")
    html.write("<h2>🔮 Becas ISA – Futuro (meses restantes y años posteriores)</h2>")

    # Meses restantes (incluye el actual)
    mes_idx = datetime.today().month
    meses_restantes_cols = [f"{n} {year}" for i, n in enumerate(meses_nombres, start=1) if i >= mes_idx]
    disp_rest = [c for c in meses_restantes_cols if c in df_beca.columns]

    # Años futuros
    cols_fut = [
        c for c in df_beca.columns
        if str(c).startswith("Total ")
        and str(c).split()[1].isdigit()
        and int(str(c).split()[1]) > year
    ]

    # Un único multiselect con ambas cosas
    opciones_fut = disp_rest + cols_fut  # meses primero, años después
    sel_fut_comb = st.multiselect(
        "Selecciona periodos futuros (meses restantes y años posteriores):",
        opciones_fut,
        default=opciones_fut,
        key="filtro_becas_isa_future_all",
    )

    # separar lo escogido
    sel_meses = [c for c in sel_fut_comb if c in disp_rest]
    sel_anios = [c for c in sel_fut_comb if c in cols_fut]

    total_restante = 0.0
    total_futuro = 0.0

    # tarjetas de meses primero (sin banda amarilla)
    if sel_meses:
        df_beca[sel_meses] = df_beca[sel_meses].apply(pd.to_numeric, errors="coerce").fillna(0)
        rest = df_beca[sel_meses].sum().reset_index()
        rest.columns = ["Mes", "Suma Total"]
        st.markdown("#### 📅 Meses restantes")
        html.write("<h3>Meses restantes (tarjetas)</h3>")
        for i in range(0, len(rest), 4):
            row = st.columns(4)
            for j, c in enumerate(row):
                if i + j >= len(rest):
                    break
                r = rest.iloc[i + j]
                c.markdown(_card(r["Mes"], r["Suma Total"], tone="green"), unsafe_allow_html=True)
                html.write(_card(r["Mes"], r["Suma Total"], tone="green"))
        total_restante = float(rest["Suma Total"].sum())

        export_dict["Futuro_MesesRestantes"] = pd.concat(
            [rest, pd.DataFrame([{"Mes": "TOTAL GENERAL", "Suma Total": total_restante}])],
            ignore_index=True,
        )

    # tarjetas de años después (incluye 2025 con total de meses restantes)
    if sel_anios:
        df_beca[sel_anios] = df_beca[sel_anios].apply(pd.to_numeric, errors="coerce").fillna(0)
        fut = df_beca[sel_anios].sum().reset_index()
        fut.columns = ["Año", "Suma Total"]
        fut["Año"] = fut["Año"].str.replace("Total ", "")

        # Insertar la tarjeta del año actual (2025) con el TOTAL de meses restantes
        if total_restante > 0:
            fut = pd.concat(
                [pd.DataFrame({"Año": [str(year)], "Suma Total": [total_restante]}), fut],
                ignore_index=True
            )

        # Ocultar cualquier "año" con 0
        fut = fut[fut["Suma Total"] > 0].reset_index(drop=True)

        if not fut.empty:
            st.markdown("#### ⏭️ Años futuros")
            html.write("<h3>Años futuros (tarjetas)</h3>")
            for i in range(0, len(fut), 4):
                row = st.columns(4)
                for j, c in enumerate(row):
                    if i + j >= len(fut):
                        break
                    r = fut.iloc[i + j]
                    c.markdown(_card(r["Año"], r["Suma Total"], tone="blue"), unsafe_allow_html=True)
                    html.write(_card(r["Año"], r["Suma Total"], tone="blue"))

            total_futuro = float(fut["Suma Total"].sum())

            export_dict["Futuro_Anios"] = pd.concat(
                [fut, pd.DataFrame([{"Año": "TOTAL GENERAL", "Suma Total": total_futuro}])],
                ignore_index=True,
            )

    # ✅ SOLO el total de AÑOS FUTUROS
    st.markdown(f"### 🧮 Total: `€ {_eu(total_futuro)}`")
    html.write(f"<h3>Total</h3><p><strong>€ {_eu(total_futuro)}</strong></p>")
    export_dict["Futuro_Resumen"] = pd.DataFrame(
        {"Sección": ["Años futuros (tarjetas)"], "Importe": [total_futuro]}
    )

    # ---------------- descargas ----------------
    st.session_state["descarga_becas_isa"] = export_dict

    if export_dict:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
            for name, dfx in export_dict.items():
                dfx.to_excel(writer, index=False, sheet_name=name[:31])
        buf.seek(0)
        st.download_button(
            "📥 Descargar Excel Consolidado Becas ISA",
            buf.getvalue(),
            "becas_isa_consolidado.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    st.download_button(
        "🌐 Descargar informe HTML Becas ISA",
        html.getvalue().encode("utf-8"),
        "becas_isa_informe.html",
        "text/html",
    )
    st.session_state["html_becas_isa"] = html.getvalue()

    os.makedirs("uploaded", exist_ok=True)
    with open("uploaded/reporte_becas_isa.html", "w", encoding="utf-8") as f:
        f.write(html.getvalue())
