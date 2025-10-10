import os
import io  # 👈 para Excel en memoria
from datetime import datetime
import smtplib  # 👈 para enviar email
from email.message import EmailMessage  # 👈 para adjunto

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from responsive import get_screen_size

UPLOAD_FOLDER = "uploaded_admisiones"
EXCEL_FILE = os.path.join(UPLOAD_FOLDER, "matricula_programas_25.xlsx")


# ----------------- Helpers -----------------
def _fill_blank(s: pd.Series, blank_label="(En Blanco)"):
    out = s.astype(str).str.strip()
    out = out.replace(["", "nan", "NaN", "NONE", "None"], blank_label)
    return out.fillna(blank_label)


def _is_blank_series(s: pd.Series):
    s2 = s.astype(str).str.strip()
    return s2.isin(["", "nan", "NaN", "NONE", "None"])


@st.cache_data(show_spinner=False)
def _read_excel_cached(path: str, mtime: float, sheet_name="Contactos") -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl", dtype=str)


def _send_mail_with_attachment(recipients, subject, body, attachment_bytes, filename):
    """
    Envía un correo con adjunto (Excel). Requiere credenciales SMTP en st.secrets['smtp'].
    """
    if "smtp" not in st.secrets:
        raise RuntimeError("Faltan credenciales SMTP en st.secrets['smtp'].")

    smtp_conf = st.secrets["smtp"]
    user = smtp_conf.get("user")
    password = smtp_conf.get("password")
    host = smtp_conf.get("host", "smtp.office365.com")
    port = int(smtp_conf.get("port", 587))

    if not user or not password:
        raise RuntimeError("smtp.user y smtp.password son obligatorios en st.secrets.")

    if isinstance(recipients, str):
        recipients = [r.strip() for r in recipients.split(",") if r.strip()]

    if not recipients:
        raise RuntimeError("Debe indicar al menos un destinatario.")

    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject.strip() if subject else "(sin asunto)"
    msg.set_content(body or "")

    # Adjuntar Excel
    msg.add_attachment(
        attachment_bytes,
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
    )

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)


# ---- Admin helpers ----
def _admin_authenticated() -> bool:
    """Devuelve True si la sesión ya validó como admin."""
    return st.session_state.get("_admin_ok", False)


def _admin_gate():
    """
    Dibuja un área protegida para admin.
    Si no has validado, pide clave.
    """
    with st.expander("🔐 Área admin", expanded=False):
        if _admin_authenticated():
            st.success("Acceso admin concedido.")
            return True
        # pide clave
        pwd = st.text_input("Introduce la clave de admin", type="password", key="__admin_pwd")
        if st.button("Validar clave de admin", key="__admin_btn"):
            secret_pwd = st.secrets.get("admin_password", None)
            if secret_pwd and pwd == secret_pwd:
                st.session_state["_admin_ok"] = True
                st.success("Acceso admin concedido.")
                return True
            else:
                st.error("Clave incorrecta o no configurada en st.secrets.")
                return False
    return _admin_authenticated()


# ----------------- APP -----------------
def app():
    width, height = get_screen_size()
    is_mobile = width <= 400

    traducciones_meses = {
        "January": "Enero", "February": "Febrero", "March": "Marzo", "April": "Abril",
        "May": "Mayo", "June": "Junio", "July": "Julio", "August": "Agosto",
        "September": "Septiembre", "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
    }
    now = datetime.now()
    mes_actual = traducciones_meses[now.strftime("%B")] + " " + now.strftime("%Y")

    st.markdown(f"<h1>Matrículas por Programa y Propietario - {mes_actual}</h1>", unsafe_allow_html=True)

    # Carga
    try:
        if not os.path.exists(EXCEL_FILE):
            raise FileNotFoundError(f"No existe el archivo: {EXCEL_FILE}")
        mtime = os.path.getmtime(EXCEL_FILE)
        df = _read_excel_cached(EXCEL_FILE, mtime, sheet_name="Contactos")
    except Exception as e:
        st.error(f"No se pudo cargar el archivo: {e}")
        return

    if "Programa" not in df.columns or "propietario" not in df.columns:
        st.error("Faltan columnas requeridas: 'Programa' o 'propietario'")
        return

    # Normalización
    df["Programa"] = _fill_blank(df["Programa"])
    df["propietario"] = _fill_blank(df["propietario"])

    # Clasificación de programas
    programa_mapping = {
        "Certificado oficial SAP S/4HANA Finance": "CERTIFICACIÓN SAP S/4HANA",
        "Consultoría SAP S4HANA Ventas": "CERTIFICACIÓN SAP S/4HANA",
        "Master en Auditoría de Protección de Datos, Gestión de Riesgos y Cyber Compliance": "MÁSTER DPO",
        "Máster Profesional en Auditoría de Protección de Datos, Gestión de Riesgos y Cyber Compliance": "MÁSTER DPO",
        "Máster en Dirección de Compliance & Protección de Datos": "MÁSTER DPO",
        "Master en Dirección de Ciberseguridad, Hacking Ético y Seguridad Ofensiva": "MÁSTER CIBERSEGURIDAD",
        "Máster en Dirección de Ciberseguridad, Hacking Ético y Seguridad Ofensiva": "MÁSTER CIBERSEGURIDAD",
        "Master en Gestión Eficiente de Energías Renovables": "MÁSTER EERR",
        "Máster en Gestión Eficiente de las Energías Renovables": "MÁSTER EERR",
        "Programa Movilidad California": "PROGRAMA CALIFORNIA",
        "Máster en RRHH: Dirección de Personas, Desarrollo de Talento y Gestión Laboral": "MÁSTER RRHH",
        "Master en RRHH, dirección de personas, desarrollo de talento y gestión laboral": "MÁSTER RRHH",
        "Máster en Dirección Financiera y Consultoría Funcional SAP S/4HANA Finance": "CERTIFICACIÓN SAP S/4HANA",
        "Máster en Inteligencia Artificial": "MÁSTER IA",
        "Experto Instalaciones en la Edificación": "MÁSTER EERR",
    }
    df["programa_categoria"] = df["Programa"].map(programa_mapping).fillna(df["Programa"])

    # Columna 'último contacto'
    col_ultimo = (
        "último contacto"
        if "último contacto" in df.columns
        else ("Último contacto" if "Último contacto" in df.columns else None)
    )
    if not col_ultimo:
        st.error("No se encontró la columna 'último contacto' / 'Último contacto'.")
        return

    # 🔹 EXTRAER SOLO EL AÑO antes del primer '-'
    df["_anio"] = df[col_ultimo].astype(str).str.split("-").str[0]
    df["_anio"] = pd.to_numeric(df["_anio"], errors="coerce")

    # =========================
    # CONTROLES
    # =========================
    modo_todos_anios = st.checkbox(
        "Contar TODOS los años (ignorar el filtro de año)",
        value=False
    )

    # Dataset filtrado
    anios_disponibles = sorted(df["_anio"].dropna().unique().tolist(), reverse=True)

    if modo_todos_anios:
        base = df.copy()
        anio_sel = "Todos"
        anio_sel_int = None
    else:
        if not anios_disponibles:
            st.info("No hay años disponibles en la columna de último contacto.")
            return
        anio_sel = st.selectbox("Año (último contacto)", [str(int(a)) for a in anios_disponibles], index=0)
        anio_sel_int = int(anio_sel)
        base = df[df["_anio"] == anio_sel_int].copy()

    # Filtro por programa
    st.subheader("Selecciona un programa")
    programas_unicos = sorted(base["programa_categoria"].unique())
    programa_seleccionado = st.selectbox("Programa", ["Todos"] + programas_unicos)
    df_filtrado = base if programa_seleccionado == "Todos" else base[base["programa_categoria"] == programa_seleccionado]

    # ===================== UI =====================
    col1, col2 = st.columns(2)

    # ---------- Paleta consistente para PROGRAMAS ----------
    with col1:
        titulo_anio = anio_sel if anio_sel else "—"
        st.metric(f"Total matrículas — {titulo_anio}", value=int(base.shape[0]))

        conteo_programa = df_filtrado["programa_categoria"].value_counts().reset_index()
        conteo_programa.columns = ["programa", "cantidad"]

        prog_palette = (
            px.colors.qualitative.Set2
            + px.colors.qualitative.Plotly
            + px.colors.qualitative.Safe
            + px.colors.qualitative.Set3
        )
        COLOR_MAP_PROG = {row["programa"]: prog_palette[i % len(prog_palette)]
                          for i, row in conteo_programa.iterrows()}

        if not conteo_programa.empty:
            fig1 = px.bar(
                conteo_programa, x="programa", y="cantidad",
                color="programa", text="cantidad",
                color_discrete_map=COLOR_MAP_PROG,
                title=f"Total matrículas por programa — {titulo_anio}"
            )
            fig1.update_layout(
                xaxis_title=None, yaxis_title="Cantidad",
                showlegend=not is_mobile, xaxis=dict(showticklabels=False)
            )
            st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.subheader("Propietarios")
        propietarios = ["Todos"] + sorted(df_filtrado["propietario"].unique())
        propietario_seleccionado = st.selectbox("Selecciona un propietario", propietarios)

        df_final = df_filtrado if propietario_seleccionado == "Todos" else df_filtrado[df_filtrado["propietario"] == propietario_seleccionado]

        # ❌ KPI “Matrícula en curso …” eliminado

        if propietario_seleccionado == "Todos":
            # ===== Barras apiladas por PROPIETARIO (colores por PROGRAMA) + totales al final =====
            if not df_final.empty:
                by_prop_prog = (
                    df_final.groupby(["propietario", "programa_categoria"])
                            .size()
                            .reset_index(name="cantidad")
                )
                if not by_prop_prog.empty:
                    # Ordenar propietarios por total (descendente)
                    orden_totales = (
                        by_prop_prog.groupby("propietario")["cantidad"]
                                    .sum().sort_values(ascending=False)
                                    .reset_index()
                    )
                    orden_cat = orden_totales["propietario"].tolist()
                    by_prop_prog["propietario"] = pd.Categorical(
                        by_prop_prog["propietario"], categories=orden_cat, ordered=True
                    )

                    # Completar mapa de colores si aparecen programas nuevos
                    for p in sorted(by_prop_prog["programa_categoria"].unique()):
                        if p not in COLOR_MAP_PROG:
                            idx = len(COLOR_MAP_PROG)
                            extra_palette = px.colors.qualitative.Dark24 + px.colors.qualitative.Set1
                            COLOR_MAP_PROG[p] = extra_palette[idx % len(extra_palette)]

                    figp = px.bar(
                        by_prop_prog,
                        x="cantidad", y="propietario",
                        color="programa_categoria",
                        orientation="h",
                        color_discrete_map=COLOR_MAP_PROG,
                        template="plotly_white",
                        height=max(420, 36 * by_prop_prog["propietario"].nunique() + 120),
                    )
                    figp.update_layout(
                        barmode="stack",
                        xaxis_title="Matrículas",
                        yaxis_title=None,
                        legend_title="Programa",
                        margin=dict(l=10, r=20, t=20, b=40)
                    )

                    # Totales por propietario (anotación al final)
                    totales = orden_totales
                    xmax = totales["cantidad"].max() if not totales.empty else 0
                    figp.update_xaxes(range=[0, xmax * 1.15])

                    annotations = []
                    for _, r in totales.iterrows():
                        txt = f"{int(r['cantidad']):,}".replace(",", ".")
                        annotations.append(dict(
                            x=float(r["cantidad"]) * 1.01,
                            y=r["propietario"],
                            xanchor="left",
                            yanchor="middle",
                            text=f"<b>{txt}</b>",
                            showarrow=False,
                            font=dict(color="white", size=12),
                            align="center",
                            bgcolor="rgba(0,0,0,0.95)",
                            bordercolor="black",
                            borderwidth=1,
                            borderpad=4,
                        ))
                    figp.update_layout(annotations=annotations)

                    st.plotly_chart(figp, use_container_width=True)
        else:
            # Un propietario concreto → tabla por programa
            tabla_programas = (
                df_final.groupby("programa_categoria")
                        .size()
                        .reset_index(name="Cantidad")
                        .sort_values("Cantidad", ascending=False)
            )
            st.dataframe(tabla_programas, use_container_width=True)

    # --- Promedio de PVP (encima de la raya) ---
    if "PVP" in df_final.columns and not df_final.empty:
        df_final = df_final.copy()
        df_final["PVP"] = pd.to_numeric(df_final["PVP"], errors="coerce").fillna(0)
        promedio_pvp = df_final["PVP"].sum() / df_final.shape[0] if df_final.shape[0] else 0
        st.metric(label="Promedio de PVP", value=f"{promedio_pvp:,.0f} €")
    else:
        st.metric(label="Promedio de PVP", value="0 €")

    # Separador visual
    st.markdown("---")

    # ===== Análisis =====
    st.subheader("📊 Análisis")
    col3, col4 = st.columns([1, 1])

    # ---------- Mapeo de colores ÚNICO por forma de pago ----------
    def _normalize_fp(s: pd.Series) -> pd.Series:
        return s.astype(str).str.strip().replace(["", "nan", "NaN", "NONE", "None"], "(En Blanco)")

    tmp_all = df_final.copy()
    if "Forma de Pago" in tmp_all.columns:
        tmp_all["FP_norm"] = _normalize_fp(tmp_all["Forma de Pago"])
        formas_global = sorted(tmp_all["FP_norm"].unique().tolist())
    else:
        formas_global = []

    palette = px.colors.qualitative.Plotly + px.colors.qualitative.Safe + px.colors.qualitative.Set3
    COLOR_MAP_FP = {fp: palette[i % len(palette)] for i, fp in enumerate(formas_global)}

    with col3:
        st.subheader("Forma de Pago")
        if "Forma de Pago" in df_final.columns and not df_final.empty:
            tmp = df_final.copy()
            tmp["FP_norm"] = _normalize_fp(tmp["Forma de Pago"])
            conteo_pago = tmp["FP_norm"].value_counts().reset_index()
            conteo_pago.columns = ["forma_pago", "cantidad"]

            if not conteo_pago.empty:
                fig3 = px.pie(
                    conteo_pago, names="forma_pago", values="cantidad", hole=0.4,
                    color="forma_pago", color_discrete_map=COLOR_MAP_FP
                )
                fig3.update_layout(showlegend=True, legend_title="Forma de pago")
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("No hay datos de 'Forma de Pago' para los filtros seleccionados.")
        else:
            st.info("La columna 'Forma de Pago' no está disponible en el archivo.")

    with col4:
        st.subheader("Suma de PVP por Forma de Pago")
        # Tarjetas cuadradas (mismo tamaño) con color ligado a la forma de pago
        if "Forma de Pago" in df_final.columns and "PVP" in df_final.columns and not df_final.empty:
            tmp = df_final.copy()
            tmp["FP_norm"] = _normalize_fp(tmp["Forma de Pago"])
            tmp["PVP"] = pd.to_numeric(tmp["PVP"], errors="coerce").fillna(0)
            suma_pvp = (
                tmp.groupby("FP_norm", as_index=False)["PVP"]
                   .sum()
                   .sort_values("PVP", ascending=False)
                   .reset_index(drop=True)
            )

            if not suma_pvp.empty:
                def _tile(label: str, amount: float, color: str) -> str:
                    amt = f"{amount:,.0f} €".replace(",", ".")
                    return f"""
                    <div style="
                        height: 110px; border-radius: 14px;
                        background: {color}; color: #fff;
                        display: flex; flex-direction: column;
                        justify-content: center; gap: 6px;
                        padding: 12px 14px; box-shadow: 0 2px 6px rgba(0,0,0,.08);
                        border: 1px solid rgba(0,0,0,.15);">
                        <div style="font-weight: 800; font-size: 14px; opacity:.95;">{label}</div>
                        <div style="font-weight: 900; font-size: 22px;">{amt}</div>
                    </div>
                    """

                N = 3  # tarjetas por fila
                for i in range(0, len(suma_pvp), N):
                    cols = st.columns(N)
                    for j, c in enumerate(cols):
                        if i + j >= len(suma_pvp):
                            break
                        row = suma_pvp.iloc[i + j]
                        color = COLOR_MAP_FP.get(row["FP_norm"], "#6c757d")
                        c.markdown(_tile(row["FP_norm"], float(row["PVP"]), color), unsafe_allow_html=True)
            else:
                st.info("No hay datos suficientes para mostrar las tarjetas de PVP por forma de pago.")
        else:
            st.info("No hay datos suficientes para mostrar las tarjetas de PVP por forma de pago.")

    # ======= TABLA FALTANTES =======
    st.markdown("---")
    st.subheader("Registros con PVP, Forma de Pago o Programa en blanco")

    if "PVP" in df_final.columns and "Forma de Pago" in df_final.columns and not df_final.empty:
        tmp = df_final.copy()

        fp_blank_flag  = _is_blank_series(tmp["Forma de Pago"])
        prog_blank_flag = _is_blank_series(tmp["Programa"]) | (
            tmp["Programa"].astype(str).str.strip().str.lower() == "(en blanco)"
        )

        tmp["PVP_NUM"] = pd.to_numeric(tmp["PVP"], errors="coerce")
        pvp_blank_text_flag = _is_blank_series(tmp["PVP"])
        pvp_zero_flag = tmp["PVP_NUM"].fillna(0) == 0
        pvp_blank_flag = pvp_blank_text_flag | pvp_zero_flag

        faltantes = tmp[fp_blank_flag | pvp_blank_flag | prog_blank_flag].copy()

        if not faltantes.empty:
            faltantes["Forma de Pago"] = faltantes["Forma de Pago"].astype(str).str.strip().replace(
                ["", "nan", "NaN", "NONE", "None"], "(En Blanco)"
            )
            faltantes["Programa"] = faltantes["Programa"].astype(str).str.strip().replace(
                ["", "nan", "NaN", "NONE", "None"], "(En Blanco)"
            )

            def _pvp_display(row):
                val_num = pd.to_numeric(row.get("PVP_NUM"), errors="coerce")
                if pd.isna(val_num) or val_num <= 0:
                    return "(En Blanco)"
                return f"{val_num:,.0f} €".replace(",", ".")
            faltantes["PVP"] = faltantes.apply(_pvp_display, axis=1)

            def _faltan(row):
                missing = []
                if str(row["Programa"]).strip().lower() == "(en blanco)":
                    missing.append("Programa")
                if str(row["Forma de Pago"]).strip().lower() == "(en blanco)":
                    missing.append("Forma de Pago")
                val_num = pd.to_numeric(row.get("PVP_NUM"), errors="coerce")
                if pd.isna(val_num) or val_num <= 0:
                    missing.append("PVP")
                return ", ".join(missing) if missing else ""
            faltantes["Campos en blanco"] = faltantes.apply(_faltan, axis=1)

            st.dataframe(
                faltantes[["propietario", "Programa", "Forma de Pago", "PVP", "Campos en blanco"]]
                .reset_index(drop=True),
                use_container_width=True
            )

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                faltantes[["propietario", "Programa", "Forma de Pago", "PVP", "Campos en blanco"]].to_excel(
                    writer, sheet_name="Registros en blanco", index=False
                )
            buffer.seek(0)

            st.download_button(
                label="📥 Descargar en Excel",
                data=buffer,
                file_name="Situacion Actual-Registros en blanco.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("No hay datos suficientes para mostrar el detalle de faltantes.")
