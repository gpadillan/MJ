import os
import io  # 👈 para Excel en memoria
from datetime import datetime
import smtplib  # 👈 para enviar email
from email.message import EmailMessage  # 👈 para adjunto

import pandas as pd
import plotly.express as px
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
        "Máster en Inteligencia Artificial": "MÁSTER IA"
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
    incluir_sin_fecha = True  # no se usa directamente pero mantenido por compatibilidad
    incluir_programa_blanco = True  # idem

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

    with col1:
        titulo_anio = anio_sel if anio_sel else "—"
        st.metric(f"Total matrículas — {titulo_anio}", value=int(base.shape[0]))

        conteo_programa = df_filtrado["programa_categoria"].value_counts().reset_index()
        conteo_programa.columns = ["programa", "cantidad"]

        if not conteo_programa.empty:
            colores = px.colors.qualitative.Plotly
            color_map = {row["programa"]: colores[i % len(colores)] for i, row in conteo_programa.iterrows()}
            fig1 = px.bar(
                conteo_programa, x="programa", y="cantidad",
                color="programa", text="cantidad",
                color_discrete_map=color_map,
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

        current_year = datetime.now().year
        if modo_todos_anios:
            label_kpi = "Matrículas (todos los años)"
        else:
            label_kpi = "Matrícula en curso" if (anio_sel_int == current_year) else f"Matrícula {anio_sel}"

        st.metric(label=label_kpi, value=df_final.shape[0])

        if propietario_seleccionado == "Todos":
            conteo_prop = df_final["propietario"].value_counts().reset_index()
            conteo_prop.columns = ["propietario", "cantidad"]
            if not conteo_prop.empty:
                fig2 = px.funnel(conteo_prop, y="propietario", x="cantidad", text="cantidad", color_discrete_sequence=["#1f77b4"])
                fig2.update_layout(xaxis_title="Cantidad", yaxis_title=None, showlegend=False)
                fig2.update_traces(texttemplate="%{x}", textfont_size=16, textposition="inside")
                st.plotly_chart(fig2, use_container_width=True)
        else:
            tabla_programas = df_final.groupby("programa_categoria").size().reset_index(name="Cantidad").sort_values("Cantidad", ascending=False)
            st.dataframe(tabla_programas, use_container_width=True)

    # --- Promedio de PVP ---
    st.markdown("---")
    if "PVP" in df_final.columns and not df_final.empty:
        df_final = df_final.copy()
        df_final["PVP"] = pd.to_numeric(df_final["PVP"], errors="coerce").fillna(0)
        promedio_pvp = df_final["PVP"].sum() / df_final.shape[0] if df_final.shape[0] else 0
        st.metric(label="Promedio de PVP", value=f"{promedio_pvp:,.0f} €")
    else:
        st.metric(label="Promedio de PVP", value="0 €")

    # ===== Análisis =====
    st.subheader("📊 Análisis")
    col3, col4 = st.columns([1, 1])

    with col3:
        st.subheader("Forma de Pago")
        if "Forma de Pago" in df_final.columns and not df_final.empty:
            tmp = df_final.copy()
            forma_pago_str = tmp["Forma de Pago"].astype(str).str.strip()
            tmp["Forma de Pago (vist)"] = forma_pago_str.replace(["", "nan", "NaN", "NONE", "None"], "(En Blanco)")
            conteo_pago = tmp["Forma de Pago (vist)"].value_counts().reset_index()
            conteo_pago.columns = ["forma_pago", "cantidad"]

            if not conteo_pago.empty:
                formas_pago = conteo_pago["forma_pago"].tolist()
                color_palette = px.colors.qualitative.Bold
                color_map_fp = {fp: color_palette[i % len(color_palette)] for i, fp in enumerate(formas_pago)}
                fig3 = px.pie(conteo_pago, names="forma_pago", values="cantidad", hole=0.4,
                              color="forma_pago", color_discrete_map=color_map_fp)
                fig3.update_layout(showlegend=True, legend_title="Forma de pago")
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("No hay datos de 'Forma de Pago' para los filtros seleccionados.")
        else:
            st.info("La columna 'Forma de Pago' no está disponible en el archivo.")

    with col4:
        st.subheader("Suma de PVP por Forma de Pago")
        if "Forma de Pago" in df_final.columns and "PVP" in df_final.columns and not df_final.empty:
            tmp = df_final.copy()
            tmp["Forma de Pago"] = tmp["Forma de Pago"].astype(str).str.strip().replace(
                ["", "nan", "NaN", "NONE", "None"], "(En Blanco)"
            )
            tmp["PVP"] = pd.to_numeric(tmp["PVP"], errors="coerce").fillna(0)
            suma_pvp = tmp.groupby("Forma de Pago")["PVP"].sum().reset_index().sort_values("PVP", ascending=True)

            fig4 = px.funnel(suma_pvp, y="Forma de Pago", x="PVP", color="Forma de Pago")
            fig4.update_layout(width=650, xaxis_title="Suma de PVP (€)", yaxis=dict(showticklabels=False), showlegend=False)
            fig4.update_traces(texttemplate="%{x:,.0f} €", textfont_size=16, textposition="inside")
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("No hay datos suficientes para mostrar el embudo de PVP por forma de pago.")

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

            # Mostrar la tabla como siempre
            st.dataframe(
                faltantes[["propietario", "Programa", "Forma de Pago", "PVP", "Campos en blanco"]]
                .reset_index(drop=True),
                use_container_width=True
            )

            # ✅ Preparar Excel en memoria
            export_df = faltantes[["propietario", "Programa", "Forma de Pago", "PVP", "Campos en blanco"]].reset_index(drop=True)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                export_df.to_excel(writer, sheet_name="Registros en blanco", index=False)
            buffer.seek(0)

            # 👉 Opción 1: Descargar
            st.download_button(
                label="📥 Descargar en Excel",
                data=buffer,
                file_name="Situacion Actual-Registros en blanco.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
