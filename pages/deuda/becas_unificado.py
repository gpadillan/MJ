# becas_isa_page.py

import os
import io
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go
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
        # A números
        df_beca[seleccion] = df_beca[seleccion].apply(pd.to_numeric, errors="coerce").fillna(0)

        # Sumas y nº de clientes (>0) por año
        if "Cliente" in df_beca.columns:
            num_cli_vals = [(df_beca.groupby("Cliente")[c].sum() > 0).sum() for c in seleccion]
        else:
            num_cli_vals = [(pd.to_numeric(df_beca[c], errors="coerce").fillna(0) > 0).sum() for c in seleccion]

        suma = pd.DataFrame({
            "Año_txt": [c.replace("Total ", "") for c in seleccion],
            "Suma Total": [float(df_beca[c].sum()) for c in seleccion],
            "Num_Clientes": [int(v) for v in num_cli_vals],
        })

        # Agregar (por si hay duplicados), quitar 0/0 y pasar a int para eje numérico
        suma = (suma.groupby("Año_txt", as_index=False)
                     .agg({"Suma Total": "sum", "Num_Clientes": "sum"}))
        suma = suma[~((suma["Suma Total"] == 0) & (suma["Num_Clientes"] == 0))].reset_index(drop=True)
        suma["Año"] = pd.to_numeric(suma["Año_txt"], errors="coerce")
        suma = suma.dropna(subset=["Año"]).sort_values("Año").reset_index(drop=True)

        total = float(suma["Suma Total"].sum()) if not suma.empty else 0.0
        st.markdown(
            f"<div style='display:inline-block;padding:6px 10px;border-radius:8px;"
            f"background:#eaf5ea;color:#0b5b1d;font-weight:700;'>"
            f"Total acumulado: € {_eu(total)}</div>",
            unsafe_allow_html=True,
        )
        html.write(f"<p><strong>Total acumulado: € {_eu(total)}</strong></p>")

        if not suma.empty:
            # Paleta degradado manual sin colorbar
            palette = px.colors.sequential.Sunsetdark
            vals = suma["Suma Total"].astype(float)
            vmin, vmax = float(vals.min()), float(vals.max())
            if vmax - vmin <= 0:
                idxs = [len(palette)//2] * len(vals)
            else:
                idxs = [int(round((v - vmin) / (vmax - vmin) * (len(palette) - 1))) for v in vals]
            colors = [palette[i] for i in idxs]

            fig = go.Figure()

            # Columnas VERTICALES con eje X NUMÉRICO (dtick=1)
            fig.add_bar(
                x=suma["Año"],                # <- numérico (int)
                y=suma["Suma Total"],
                marker=dict(color=colors, line=dict(color="black", width=0.8)),
                hovertemplate="Año: %{x}<br>Total: € %{y:,.0f}<extra></extra>",
            )

            ymax = float(suma["Suma Total"].max())
            fig.update_yaxes(range=[0, ymax * 1.25], title="Suma Total")
            fig.update_xaxes(
                title=None,
                tickmode="linear",            # <- ticks 2019, 2020, 2021...
                tick0=int(suma["Año"].min()),
                dtick=1,
                showgrid=False
            )
            fig.update_layout(
                template="plotly_white",
                height=420,
                margin=dict(l=20, r=20, t=30, b=40),
                bargap=0.25,
                showlegend=False,
            )

            # Cajas negras (importe + clientes) por barra
            annotations = []
            for _, r in suma.iterrows():
                annotations.append(dict(
                    x=float(r["Año"]),
                    y=float(r["Suma Total"]) * 1.06,
                    yanchor="bottom",
                    xanchor="center",
                    text=f"€ {_eu(r['Suma Total'])}<br>👥 {int(r['Num_Clientes'])}",
                    showarrow=False,
                    font=dict(color="white", size=14),
                    align="center",
                    bgcolor="rgba(0,0,0,0.95)",
                    bordercolor="black",
                    borderwidth=1.2,
                    opacity=1
                ))
            fig.update_layout(annotations=annotations)

            st.plotly_chart(fig, use_container_width=True)
            html.write(pio.to_html(fig, include_plotlyjs="cdn", full_html=False))
        else:
            st.info("No hay años con datos para mostrar.")

        # Excel de respaldo
        df_total = suma[["Año", "Suma Total", "Num_Clientes"]].copy()
        df_total.loc[len(df_total)] = [
            "TOTAL GENERAL",
            total,
            int(suma["Num_Clientes"].sum()) if not suma.empty else 0
        ]
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
    opciones_fut = disp_rest + cols_fut
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

    # tarjetas de meses primero
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

    # tarjetas de años después (incluye año actual con meses restantes)
    if sel_anios:
        df_beca[sel_anios] = df_beca[sel_anios].apply(pd.to_numeric, errors="coerce").fillna(0)
        fut = df_beca[sel_anios].sum().reset_index()
        fut.columns = ["Año", "Suma Total"]
        fut["Año"] = fut["Año"].str.replace("Total ", "")

        if total_restante > 0:
            fut = pd.concat(
                [pd.DataFrame({"Año": [str(year)], "Suma Total": [total_restante]}), fut],
                ignore_index=True
            )

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
