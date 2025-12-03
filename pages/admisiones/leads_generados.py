# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import plotly.express as px
import unicodedata
from datetime import datetime
from io import BytesIO
from responsive import get_screen_size
import base64
import requests
import msal
import re
import json
import time
import html  # para escapar chips en HTML

# =========================
# CONFIG BÁSICA Y RUTAS
# =========================
UPLOAD_FOLDER = "uploaded_admisiones"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
LEADS_GENERADOS_FILE_LOCAL = os.path.join(UPLOAD_FOLDER, "leads_generados.xlsx")
VENTAS_FILE_LOCAL = os.path.join(UPLOAD_FOLDER, "ventas.xlsx")

ANIO_ACTUAL = datetime.now().year

# SharePoint fallback URLs (si no están en st.secrets['admisiones_bdd'])
DEFAULT_LEADS_SHARE_URL = (
    "https://grupomainjobs.sharepoint.com/:x:/r/sites/GrupoMainjobs928/"
    "_layouts/15/Doc.aspx?sourcedoc=%7B83D0FFB4-3216-4127-AB3B-D3A71EDD3516%7D&"
    "file=LEADS-A%C3%91O%20ANTERIOR.xlsx&action=default&mobileredirect=true"
)
DEFAULT_VENTAS_SHARE_URL = (
    "https://grupomainjobs.sharepoint.com/:x:/r/sites/GrupoMainjobs928/"
    "_layouts/15/Doc.aspx?sourcedoc=%7B40F3AD21-8968-46F5-AE20-CF5840B5BFA6%7D&"
    "file=VENTAS-A%C3%91O%20ANTERIOR.xlsx&action=default&mobileredirect=true"
)

MES_COLORS_BAR = {
    "Enero": "#1e88e5", "Febrero": "#fb8c00", "Marzo": "#43a047", "Abril": "#e53935",
    "Mayo": "#8e24aa", "Junio": "#6d4c41", "Julio": "#ec407a", "Agosto": "#9e9e9e",
    "Septiembre": "#3fca33", "Octubre": "#00acc1", "Noviembre": "#5c6bc0", "Diciembre": "#f4511e",
}
USE_SAME_COLORS_FOR_CARDS = False
CARDS_LIGHTEN_FACTOR = 0.83

# =========================
# LISTA CLIENTIFY (FIJA)
# =========================
KNOWN_PEOPLE = {
    "nrodriguez@grupomainjobs.com": "Nuria Rodriguez Barroso",
    "aroldan@eiposgrados.com":       "Agata Roldan Rodriguez",
    "aperez@grupomainjobs.com":      "Alicia Pérez Moreno",
    "amugica@grupomainjobs.com":     "Ana Múgica Jiménez",
    "lgonzalez@grupomainjobs.com":   "Lorena González Perich",
    "iherreradiaz@eiposgrados.com":  "Irene Herrera",
    "pserrano@eiposgrados.com":    "Paloma Serrano",
    "pcedeno@eiposgrados.com":       "Priscila Cedeño Loor",
    "cheredia@eiposgrados.com":      "Cristina Heredia",
    "agarcia@grupomainjobs.com":     "Ángel Garcia Martin",
    "erueda@grupomainjobs.com":        "Estrella Rueda Sanz",
    "kmoreno@grupomainjobs.com":       "Kika Moreno",
    "vlopez@grupomainjobs.com":        "Victor López Hernanz",
    "clobato@grupomainjobs.com":     "Carmen Lobato Rosa",
    "lsanchez@grupomainjobs.com":    "Laly Sánchez Arjona",
    "cmoreno@grupomainjobs.com":     "Chelo Moreno Cabeza",
    "marceiz@grupomainjobs.com":     "Miguel Arcéiz",
    "mdiazf@grupomainjobs.com":      "Mónica Díaz",
    "mavalle@grupomainjobs.com":     "María Ángeles Valle Rodríguez",
    "sleon@grupomainjobs.com":       "Sara León",
    "epacheco@eiposgrados.com":    "Eduardo Pacheco",
    "rmvela@grupomainjobs.com":      "Rosa María Vela",
}
KNOWN_EMAILS = sorted(KNOWN_PEOPLE.keys())

# =========================
# SHAREPOINT / GRAPH HELPERS (token + descarga por share link)
# =========================
def _get_graph_token_from_secrets_section(secret_section: dict) -> str | None:
    try:
        tenant = secret_section["tenant_id"]
        client = secret_section["client_id"]
        client_secret = secret_section["client_secret"]
    except Exception:
        return None
    authority = f"https://login.microsoftonline.com/{tenant}"
    scope = ["https://graph.microsoft.com/.default"]
    try:
        app = msal.ConfidentialClientApplication(client, authority=authority, client_credential=client_secret)
        result = app.acquire_token_silent(scope, account=None)
        if not result:
            result = app.acquire_token_for_client(scopes=scope)
        return result.get("access_token") if result and "access_token" in result else None
    except Exception:
        return None

def download_sharepoint_file_by_shareurl(share_url: str, token: str, timeout: int = 60) -> bytes | None:
    try:
        if not share_url or not token:
            return None
        raw = share_url
        encoded = base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8").rstrip("=")
        share_id = f"u!{encoded}"
        endpoint = f"https://graph.microsoft.com/v1.0/shares/{share_id}/driveItem/content"
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get(endpoint, headers=headers, timeout=timeout)
        if r.status_code == 200:
            return r.content
        else:
            try:
                st.warning(f"SharePoint download status: {r.status_code}")
                st.info(r.text[:800])
            except Exception:
                pass
            return None
    except Exception as e:
        st.warning(f"Exception descargando sharelink: {str(e)}")
        return None

def _get_share_urls_from_secrets():
    leads_url = DEFAULT_LEADS_SHARE_URL
    ventas_url = DEFAULT_VENTAS_SHARE_URL
    try:
        sec = st.secrets.get("admisiones_bdd", {})
        leads_url = sec.get("leads_share_url", leads_url)
        ventas_url = sec.get("ventas_share_url", ventas_url)
    except Exception:
        pass
    return leads_url, ventas_url

def load_bytes_for_leads(year_selected: int):
    if year_selected == ANIO_ACTUAL:
        if os.path.exists(LEADS_GENERADOS_FILE_LOCAL):
            try:
                return open(LEADS_GENERADOS_FILE_LOCAL, "rb").read()
            except Exception:
                return None
        return None
    try:
        secret_section = st.secrets.get("admisiones_bdd", None)
    except Exception:
        secret_section = None
    token = _get_graph_token_from_secrets_section(secret_section) if secret_section else None
    leads_url, _ = _get_share_urls_from_secrets()
    if leads_url and token:
        data = download_sharepoint_file_by_shareurl(leads_url, token)
        if data:
            return data
    if os.path.exists(LEADS_GENERADOS_FILE_LOCAL):
        try:
            return open(LEADS_GENERADOS_FILE_LOCAL, "rb").read()
        except Exception:
            return None
    return None

def load_bytes_for_ventas(year_selected: int):
    if year_selected == ANIO_ACTUAL:
        if os.path.exists(VENTAS_FILE_LOCAL):
            try:
                return open(VENTAS_FILE_LOCAL, "rb").read()
            except Exception:
                return None
        return None
    try:
        secret_section = st.secrets.get("admisiones_bdd", None)
    except Exception:
        secret_section = None
    token = _get_graph_token_from_secrets_section(secret_section) if secret_section else None
    _, ventas_url = _get_share_urls_from_secrets()
    if ventas_url and token:
        data = download_sharepoint_file_by_shareurl(ventas_url, token)
        if data:
            return data
    if os.path.exists(VENTAS_FILE_LOCAL):
        try:
            return open(VENTAS_FILE_LOCAL, "rb").read()
        except Exception:
            return None
    return None

# =========================
# UTILIDADES LOCALES
# =========================
def _to_blank_label(series_like) -> pd.Series:
    s = pd.Series(series_like, copy=True).astype(str).str.strip()
    s = s.replace(["", "nan", "NaN", "NONE", "None", "NULL"], "(En Blanco)")
    return s.fillna("(En Blanco)")

def _norm_name(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("utf-8")
    s = " ".join(s.split())
    return s

def _find_col(cols, candidates):
    return next((c for c in candidates if c in cols), None)

def normalizar(texto: str) -> str:
    texto = str(texto) if pd.notna(texto) else ""
    texto = texto.lower()
    texto = unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode("utf-8")
    return texto.strip()

def lighten_hex(hex_color: str, factor: float = 0.85) -> str:
    try:
        hex_color = hex_color.strip().lstrip('#')
        r = int(hex_color[0:2], 16); g = int(hex_color[2:4], 16); b = int(hex_color[4:6], 16)
    except Exception:
        return "#f3f4f6"
    r_l = int(r + (255 - r) * factor); g_l = int(g + (255 - g) * factor); b_l = int(b + (255 - b) * factor)
    return f"#{r_l:02x}{g_l:02x}{b_l:02x}"

# =========================
# VALIDACIÓN DE EMAILS (idéntica a la tuya)
# =========================
def validar_emails(emails_string):
    if not emails_string or emails_string.strip() == "":
        return False, [], "Por favor ingresa al menos un email"
    separadores = [',', ';']
    emails = [emails_string]
    for sep in separadores:
        emails = [email.strip() for e in emails for email in e.split(sep)]
    emails = [e for e in emails if e]
    if not emails:
        return False, [], "No se encontraron emails válidos"

    patron_email = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    dominios_permitidos = {"@eiposgrados.com", "@grupomainjobs.com"}

    emails_invalidos, emails_dominio_incorrecto, emails_validos = [], [], []
    for email in emails:
        if not re.match(patron_email, email):
            emails_invalidos.append(email)
        elif not any(email.endswith(d) for d in dominios_permitidos):
            emails_dominio_incorrecto.append(email)
        else:
            emails_validos.append(email)

    errores = []
    if emails_invalidos: errores.append(f"Formato inválido: {', '.join(emails_invalidos)}")
    if emails_dominio_incorrecto: errores.append(
        "Dominio incorrecto (permitidos: @eiposgrados.com, @grupomainjobs.com): " + ", ".join(emails_dominio_incorrecto)
    )
    if errores: return False, [], " | ".join(errores)
    return True, emails_validos, f"✓ {len(emails_validos)} email(s) válido(s)"

# =========================
# APP PRINCIPAL
# =========================
def app():
    st.session_state.setdefault("email_last_ok", None)
    st.session_state.setdefault("email_last_msg", "")
    st.session_state.setdefault("email_last_attempt_id", None)
    st.session_state.setdefault("email_balloons_shown_for", None)
    st.session_state.setdefault("email_attempt_counter", 0)

    width, _ = get_screen_size()
    is_mobile = width <= 400

    traducciones_meses = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}

    # Selector año (igual comportamiento que en ventas_preventas)
    st.subheader("📋 Leads generados")
    year_options = [ANIO_ACTUAL, ANIO_ACTUAL - 1]
    year_labels = {ANIO_ACTUAL: f"{ANIO_ACTUAL} (Año actual)", ANIO_ACTUAL - 1: f"{ANIO_ACTUAL - 1} (Año anterior - SharePoint)"}
    selected_year = st.selectbox("Selecciona Año:", options=year_options, format_func=lambda y: year_labels.get(y, str(y)), index=0)

    # Intentar cargar bytes del archivo de leads según año
    with st.spinner("Cargando archivo(s)..."):
        leads_bytes = load_bytes_for_leads(selected_year)
        ventas_bytes = load_bytes_for_ventas(selected_year)

    if selected_year == ANIO_ACTUAL - 1:
        if leads_bytes is None:
            st.warning("Intentando cargar LEADS (Año anterior) desde SharePoint falló — uso fallback local si existe.")
        if ventas_bytes is None:
            st.info("Intentando cargar VENTAS (Año anterior) desde SharePoint falló — uso fallback local si existe.")

    # ================= CARGA DEL DF LEADS (desde bytes o local)
    if leads_bytes:
        try:
            df = pd.read_excel(BytesIO(leads_bytes))
        except Exception as e:
            st.error(f"No se pudo leer el Excel de leads desde bytes: {e}")
            return
    else:
        if os.path.exists(LEADS_GENERADOS_FILE_LOCAL):
            try:
                df = pd.read_excel(LEADS_GENERADOS_FILE_LOCAL)
            except Exception as e:
                st.error(f"No se pudo leer {LEADS_GENERADOS_FILE_LOCAL}: {e}")
                return
        else:
            st.warning("📭 No se ha subido el archivo de Leads Generados aún.")
            return

    df.columns = df.columns.str.strip().str.lower()

    if 'creado' not in df.columns:
        st.error("❌ En leads: falta la columna 'creado'.")
        return

    df['creado'] = pd.to_datetime(df['creado'], errors='coerce')
    df = df[df['creado'].notna()]
    df["mes_num"] = df["creado"].dt.month
    df["anio"] = df["creado"].dt.year
    df["mes_nombre"] = df["mes_num"].map(traducciones_meses)
    df["mes_anio"] = df["mes_nombre"] + " " + df["anio"].astype(str)

    if 'programa' not in df.columns or 'propietario' not in df.columns:
        st.error("❌ En leads: faltan las columnas 'programa' y/o 'propietario'.")
        return
    df["programa"] = _to_blank_label(df["programa"])
    df["propietario"] = _to_blank_label(df["propietario"])

    # clasificación (mismo bloque que tenías)
    CATEGORIAS_EXACTAS = {
        "MÁSTER IA": ["máster en inteligencia artificial", "máster integral en inteligencia artificial", "máster ia", "master ia", "master en inteligencia artificial"],
        "MÁSTER RRHH": ["máster recursos humanos rrhh: dirección de personas, desarrollo de talento y gestión laboral", "máster en rrhh: dirección de personas, desarrollo de talento y gestión laboral", "máster rrhh", "master rrhh", "master en rrhh, dirección de personas, desarrollo de talento y gestión laboral"],
        "MÁSTER CIBERSEGURIDAD": ["máster en dirección de ciberseguridad, hacking ético y seguridad ofensiva", "master en direccion de ciberseguridad, hacking etico y seguridad ofensiva", "la importancia de la ciberseguridad y privacidad", "máster ciber", "master ciber", "máster ciberseguridad"],
        "CERTIFICACIÓN SAP S/4HANA": ["certificado sap s/4hana finance", "certificado oficial sap s/4hana finance", "certificado oficial sap s/4hana sourcing and procurement", "certificado oficial sap s/4hana logística", "consultoría sap s4hana finanzas", "consultoría sap bw4/hana", "consultoría sap s4hana planificación de la producción y fabricación", "sap btp: la plataforma para la transformación digital", "máster en dirección financiera y consultoría funcional sap s/4hana finance", "sap s/4hana", "sap"],
        "MÁSTER DPO": ["máster profesional en auditoría de protección de datos, gestión de riesgos y cyber compliance", "master en auditoría de protección de datos, gestión de riesgos y cyber compliance", "máster en dirección de compliance & protección de datos", "máster en auditoría de protección de datos, gestión de riesgos y cyber compliance​", "dpo"],
        "MÁSTER EERR": ["master en gestión eficiente de energías renovables", "master profesional en energías renovables, redes inteligentes y movilidad eléctrica", "máster en gestión eficiente de las energías renovables", "máster en bim y gestión eficiente de la energía (no usar)", "energías renovables", "eerr"],
        "MBA + RRHH": ["doble máster oficial en rrhh + mba", "doble máster en rrhh + mba", "doble máster rrhh + mba", "doble máster en dirección financiera + dirección rrhh", "mba rrhh"],
        "PROGRAMA CALIFORNIA": ["programa movilidad california", "california state university"]
    }

    def clasificar_programa(nombre: str) -> str:
        nombre_limpio = normalizar(nombre)
        for categoria, nombres in CATEGORIAS_EXACTAS.items():
            if nombre_limpio in [normalizar(n) for n in nombres]:
                return categoria
        return "SIN CLASIFICAR"

    df["programa_categoria"] = df["programa"].apply(clasificar_programa)
    df["programa_final"] = df.apply(lambda r: r["programa"] if r["programa_categoria"] == "SIN CLASIFICAR" else r["programa_categoria"], axis=1)

    # ================= VENTAS (opcional) - ahora soporta SharePoint según selected_year
    ventas_ok = False
    df_ventas = pd.DataFrame()
    if ventas_bytes:
        try:
            df_ventas = pd.read_excel(BytesIO(ventas_bytes))
            df_ventas.columns = df_ventas.columns.str.strip().str.lower()
            ventas_ok = True
        except Exception as e:
            st.warning(f"⚠️ No se pudo leer ventas desde bytes: {e}")
            ventas_ok = False
    else:
        if os.path.exists(VENTAS_FILE_LOCAL):
            try:
                df_ventas = pd.read_excel(VENTAS_FILE_LOCAL)
                df_ventas.columns = df_ventas.columns.str.strip().str.lower()
                ventas_ok = True
            except Exception as e:
                st.warning(f"⚠️ No se pudo leer {VENTAS_FILE_LOCAL}: {e}")
                ventas_ok = False
        else:
            ventas_ok = False

    if ventas_ok:
        if "propietario" in df_ventas.columns:
            df_ventas["propietario"] = _to_blank_label(df_ventas["propietario"])
        else:
            st.warning("⚠️ En ventas.xlsx falta la columna 'propietario'. Algunas vistas se verán limitadas.")
        prog_col = 'programa' if 'programa' in df_ventas.columns else ('nombre' if 'nombre' in df_ventas.columns else None)
        if prog_col:
            df_ventas["programa_bruto"] = df_ventas[prog_col].astype(str)
            df_ventas["programa_categoria"] = df_ventas["programa_bruto"].apply(clasificar_programa)
            df_ventas["programa_final"] = df_ventas.apply(
                lambda r: r["programa_bruto"] if r.get("programa_categoria", "SIN CLASIFICAR") == "SIN CLASIFICAR" else r.get("programa_categoria"),
                axis=1
            )
        else:
            df_ventas["programa_final"] = "(Desconocido)"

        # Añadir columnas de fecha/mes si están en ventas
        if any(c in df_ventas.columns for c in ["creado", "fecha", "fecha_creacion", "fecha de cierre"]):
            fecha_col = None
            for c in ["creado", "fecha", "fecha_creacion", "fecha de cierre"]:
                if c in df_ventas.columns:
                    fecha_col = c; break
            df_ventas["creado"] = pd.to_datetime(df_ventas.get(fecha_col), errors="coerce")
            df_ventas["mes_num"] = df_ventas["creado"].dt.month
            df_ventas["anio"] = df_ventas["creado"].dt.year
            df_ventas["mes_nombre"] = df_ventas["mes_num"].map(traducciones_meses)
            df_ventas["mes_anio"] = df_ventas["mes_nombre"] + " " + df_ventas["anio"].astype(str)

    # ================= FILTROS =================
    meses_disponibles = (df[["mes_anio","mes_num","anio"]].dropna().drop_duplicates().sort_values(["anio","mes_num"]))
    opciones_meses = ["Todos"] + meses_disponibles["mes_anio"].tolist()
    col_fm, col_fp = st.columns([1, 1])
    with col_fm:
        mes_seleccionado = st.selectbox("Selecciona un mes:", opciones_meses)
    with col_fp:
        programas = ["Todos"] + sorted(df["programa_final"].unique())
        programa_seleccionado = st.selectbox("Selecciona un programa:", programas)

    df_filtrado = df.copy()
    if mes_seleccionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["mes_anio"] == mes_seleccionado]
    # Filtrar por año seleccionado también (aseguro que estamos en selected_year)
    df_filtrado = df_filtrado[df_filtrado["anio"] == selected_year]

    if programa_seleccionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["programa_final"] == programa_seleccionado]

    orden_meses = (
        df_filtrado[["mes_anio","anio","mes_num"]]
        .drop_duplicates().sort_values(["anio","mes_num"])["mes_anio"].tolist()
    ) or meses_disponibles["mes_anio"].tolist()

    color_map_mes_chart = {mes: MES_COLORS_BAR.get(mes.split(" ")[0], "#4c78a8") for mes in orden_meses}
    color_map_cards = (
        color_map_mes_chart.copy()
        if USE_SAME_COLORS_FOR_CARDS
        else {mes: lighten_hex(MES_COLORS_BAR.get(mes.split(" ")[0], "#4c78a8"), CARDS_LIGHTEN_FACTOR) for mes in orden_meses}
    )

    # ================= CHART =================
    st.subheader("📅 Total Leads por mes")
    leads_por_mes = (
        df_filtrado.groupby(["mes_anio","mes_num","anio"]).size().reset_index(name="Cantidad")
        .sort_values(["anio","mes_num"])
    )
    leads_por_mes["Mes"] = leads_por_mes["mes_anio"]

    fig_leads = px.bar(
        leads_por_mes, x="Cantidad", y="Mes", orientation="h",
        text="Cantidad", color="Mes", color_discrete_map=color_map_mes_chart,
    )
    fig_leads.update_traces(textposition="outside")
    fig_leads.update_layout(xaxis_title="Cantidad", yaxis_title=None, showlegend=False, height=420 if is_mobile else None)
    st.plotly_chart(fig_leads, use_container_width=True)

    # ================= TABLAS (USADAS PARA EXPORTS) =================
    st.markdown("### Selecciona un Propietario:")
    df_tablas_global = df_filtrado.copy()  # 👈 Importante: solo el DF filtrado (ya filtrado por año)
    propietarios_tablas = ["Todos"] + sorted(df_tablas_global["propietario"].unique().tolist())
    propietario_tablas = st.selectbox("Propietario", propietarios_tablas, key="prop_tabs")

    df_tablas = df_tablas_global.copy()
    if propietario_tablas != "Todos":
        df_tablas = df_tablas[df_tablas["propietario"] == propietario_tablas]

    colA, colB, colC = st.columns(3)

    with colA:
        t1 = df_tablas["programa_final"].value_counts(dropna=False).rename_axis("Programa").reset_index(name="Cantidad")
        total1 = int(t1["Cantidad"].sum()) if not t1.empty else 0
        st.markdown(f"#### 📘 Total Leads por Programa")
        st.markdown(f"<div style='margin:-6px 0 10px 0; font-weight:700'>TOTAL: {format(total1, ',').replace(',', '.')}</div>", unsafe_allow_html=True)
        if propietario_tablas != "Todos" and total1 > 0:
            t1 = pd.concat([pd.DataFrame([{"Programa": f"TOTAL {propietario_tablas}", "Cantidad": total1}]), t1], ignore_index=True)
        st.dataframe(t1.style.background_gradient(cmap="Blues"), use_container_width=True)

    with colB:
        origen_col_leads = "origen" if "origen" in df_tablas.columns else ("origen lead" if "origen lead" in df_tablas.columns else None)
        if origen_col_leads:
            tmp = df_tablas.copy()
            tmp[origen_col_leads] = _to_blank_label(tmp[origen_col_leads])
            conteo_origen = tmp[origen_col_leads].value_counts().reset_index()
            conteo_origen.columns = ["Origen Lead", "Cantidad"]
        else:
            conteo_origen = pd.DataFrame(columns=["Origen Lead", "Cantidad"])
        total2 = int(conteo_origen["Cantidad"].sum()) if not conteo_origen.empty else 0
        st.markdown(f"#### 📄 Origen Leads")
        st.markdown(f"<div style='margin:-6px 0 10px 0; font-weight:700'>TOTAL: {format(total2, ',').replace(',', '.')}</div>", unsafe_allow_html=True)
        if propietario_tablas != "Todos" and total2 > 0:
            conteo_origen = pd.concat([pd.DataFrame([{"Origen Lead": f"TOTAL — {propietario_tablas}", "Cantidad": total2}]), conteo_origen], ignore_index=True)
        st.dataframe(conteo_origen.style.background_gradient(cmap="Greens"), use_container_width=True)

    with colC:
        if ventas_ok and not df_ventas.empty:
            ventas_tablas = df_ventas.copy()
            # Aseguro que ventas también esté filtrado por el mismo selected_year y por filtros UI
            ventas_tablas = ventas_tablas[ventas_tablas["anio"] == selected_year] if "anio" in ventas_tablas.columns else ventas_tablas
            if mes_seleccionado != "Todos":
                ventas_tablas = ventas_tablas[ventas_tablas["mes_anio"] == mes_seleccionado]
            if programa_seleccionado != "Todos":
                ventas_tablas = ventas_tablas[ventas_tablas["programa_final"] == programa_seleccionado]
            if propietario_tablas != "Todos" and "propietario" in ventas_tablas.columns:
                ventas_tablas = ventas_tablas[ventas_tablas["propietario"] == propietario_tablas]
            origen_cols_posibles = ["origen", "origen de la venta", "origen venta", "source"]
            origen_col_v = next((c for c in origen_cols_posibles if c in ventas_tablas.columns), None)
            if origen_col_v:
                tmpv = ventas_tablas.copy()
                tmpv[origen_col_v] = _to_blank_label(tmpv[origen_col_v])
                conteo_origen_v = tmpv[origen_col_v].value_counts().reset_index()
                conteo_origen_v.columns = ["Origen", "Cantidad"]
            else:
                conteo_origen_v = pd.DataFrame(columns=["Origen", "Cantidad"])
        else:
            conteo_origen_v = pd.DataFrame(columns=["Origen", "Cantidad"])
        total3 = int(conteo_origen_v["Cantidad"].sum()) if not conteo_origen_v.empty else 0
        st.markdown(f"#### 💶 Leads - Venta")
        st.markdown(f"<div style='margin:-6px 0 10px 0; font-weight:700'>TOTAL: {format(total3, ',').replace(',', '.')}</div>", unsafe_allow_html=True)
        if propietario_tablas != "Todos" and total3 > 0:
            conteo_origen_v = pd.concat([pd.DataFrame([{"Origen": f"TOTAL — {propietario_tablas}", "Cantidad": total3}]), conteo_origen_v], ignore_index=True)
        st.dataframe(conteo_origen_v.style.background_gradient(cmap="Purples"), use_container_width=True)

    # ================= EXPORT A EXCEL (SOLO EN BLANCO) =================
    leads_detalle = df_tablas.copy()
    nombre_col_L = _find_col(leads_detalle.columns, ["nombre", "first name", "firstname"])
    apell_col_L  = _find_col(leads_detalle.columns, ["apellidos", "apellido", "last name", "lastname"])
    origen_col_L = _find_col(leads_detalle.columns, ["origen", "origen lead"])

    leads_export_cols = pd.DataFrame({
      "Propietario": leads_detalle.get("propietario", pd.Series(dtype=str)),
      "Nombre": leads_detalle.get(nombre_col_L, pd.Series(dtype=str)),
      "Apellidos": leads_detalle.get(apell_col_L, pd.Series(dtype=str)),
      "Programa": leads_detalle.get("programa_final", pd.Series(dtype=str)),
      "Origen Lead": leads_detalle.get(origen_col_L, pd.Series([""]*len(leads_detalle))) if origen_col_L else pd.Series([""]*len(leads_detalle)),
    })
    leads_export_cols["Programa"] = _to_blank_label(leads_export_cols["Programa"])
    leads_export_cols["Origen Lead"] = _to_blank_label(leads_export_cols["Origen Lead"])

    # ---------- VENTAS (para export)
    if ventas_ok and not df_ventas.empty:
        ventas_detalle = df_ventas.copy()
        ventas_detalle = ventas_detalle[ventas_detalle["anio"] == selected_year] if "anio" in ventas_detalle.columns else ventas_detalle
        if mes_seleccionado != "Todos":
            ventas_detalle = ventas_detalle[ventas_detalle["mes_anio"] == mes_seleccionado]
        if programa_seleccionado != "Todos":
            ventas_detalle = ventas_detalle[ventas_detalle["programa_final"] == programa_seleccionado]
        if propietario_tablas != "Todos" and "propietario" in ventas_detalle.columns:
            ventas_detalle = ventas_detalle[ventas_detalle["propietario"] == propietario_tablas]
    else:
        ventas_detalle = pd.DataFrame(columns=["propietario","programa_final"])

    contacto_directo = _find_col(
        ventas_detalle.columns,
        ["contacto", "contact", "contact name", "contact_name", "nombre contacto", "nombre del contacto"]
    )
    first_col = _find_col(ventas_detalle.columns, ["first name", "firstname", "nombre contacto", "nombre del contacto"])
    last_col  = _find_col(ventas_detalle.columns, ["last name", "lastname", "apellidos contacto", "apellidos del contacto", "apellidos"])

    def _serie_vacia(n): return pd.Series([""] * n, dtype=str)
    def _safe_series(df_, col): return df_.get(col, _serie_vacia(len(df_))).astype(str)

    if len(ventas_detalle) == 0:
        contacto_v = _serie_vacia(0)
    else:
        if contacto_directo:
            contacto_v = _safe_series(ventas_detalle, contacto_directo).str.strip()
        else:
            nombre_v = _safe_series(ventas_detalle, first_col) if first_col else _serie_vacia(len(ventas_detalle))
            apell_v  = _safe_series(ventas_detalle, last_col)  if last_col  else _serie_vacia(len(ventas_detalle))
            contacto_v = (nombre_v.fillna("") + " " + apell_v.fillna("")).str.strip()
        contacto_v = contacto_v.replace(["", "nan", "NaN", "NONE", "None", "NULL"], "(En Blanco)")

    forma_pago_col = _find_col(
        ventas_detalle.columns,
        ["forma de pago", "forma_pago", "payment method", "payment_method", "forma de cobro"]
    )
    forma_pago_series = (
        ventas_detalle.get(forma_pago_col, pd.Series([""] * len(ventas_detalle)))
        if forma_pago_col else pd.Series([""] * len(ventas_detalle))
    )
    forma_pago_series = _to_blank_label(forma_pago_series)

    origen_col_V = _find_col(ventas_detalle.columns, ["origen", "origen de la venta", "origen venta", "source"])

    ventas_export_cols = pd.DataFrame({
      "Propietario": ventas_detalle.get("propietario", pd.Series(dtype=str)),
      "Nombre": ventas_detalle.get("programa_final", pd.Series([""]*len(ventas_detalle))).astype(str),  # Máster/Programa
      "Contacto": contacto_v,  # persona
      "Origen": ventas_detalle.get(origen_col_V, pd.Series([""]*len(ventas_detalle))) if origen_col_V else pd.Series([""]*len(ventas_detalle)),
      "Forma de Pago": forma_pago_series,
    })
    ventas_export_cols["Origen"] = _to_blank_label(ventas_export_cols["Origen"])

    ventas_export_cols["contacto"] = ventas_export_cols["Contacto"]
    ventas_export_cols["nombre"] = ventas_export_cols["Nombre"]

    hoja1 = leads_export_cols[["Propietario","Nombre","Apellidos","Programa","Origen Lead"]].copy()
    hoja1 = hoja1[hoja1["Programa"] == "(En Blanco)"]

    hoja2 = leads_export_cols[["Propietario","Nombre","Apellidos","Programa","Origen Lead"]].copy()
    hoja2 = hoja2[hoja2["Origen Lead"] == "(En Blanco)"]

    hoja3 = ventas_export_cols[["Propietario","Nombre","Contacto","Origen","Forma de Pago"]].copy()
    hoja3 = hoja3[(hoja3["Origen"] == "(En Blanco)") | (hoja3["Forma de Pago"] == "(En Blanco)")]

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        (hoja1 if not hoja1.empty else hoja1.head(0)).to_excel(writer, index=False, sheet_name="Programas en blanco")
        (hoja2 if not hoja2.empty else hoja2.head(0)).to_excel(writer, index=False, sheet_name="Origen Leads en blanco")
        (hoja3 if not hoja3.empty else hoja3.head(0)).to_excel(writer, index=False, sheet_name="Leads-Venta (Origen en blanco)")
    excel_bytes = buffer.getvalue()

    col_download, col_email = st.columns([1, 1])
    with col_download:
        st.download_button(
            label="⬇️ Descargar detalle (Excel) — SOLO EN BLANCO",
            data=excel_bytes,
            file_name="detalle_leads_y_ventas_en_blanco.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Descarga únicamente las filas en '(En Blanco)'."
        )

    # ================== PROPIETARIOS CON BLANCOS (FRANJA AMARILLA) ==================
    props_prog_blank   = set(_norm_name(p) for p in hoja1["Propietario"].dropna().astype(str))
    props_origen_blank = set(_norm_name(p) for p in hoja2["Propietario"].dropna().astype(str))
    props_vta_blank    = set(_norm_name(p) for p in hoja3["Propietario"].dropna().astype(str))
    props_need_update_norm = props_prog_blank | props_origen_blank | props_vta_blank

    known_norm_map = {_norm_name(name): email for email, name in KNOWN_PEOPLE.items()}
    known_norm_names = set(known_norm_map.keys())

    faltantes_norm = sorted(n for n in props_need_update_norm if n not in known_norm_names)

    norm_to_original = {}
    for v in pd.concat([
            hoja1.get("Propietario", pd.Series(dtype=str)).dropna().astype(str),
            hoja2.get("Propietario", pd.Series(dtype=str)).dropna().astype(str),
            hoja3.get("Propietario", pd.Series(dtype=str)).dropna().astype(str),
        ], ignore_index=True).unique().tolist():
        norm_to_original[_norm_name(v)] = v
    faltantes_pretty = [norm_to_original.get(n, n) for n in faltantes_norm]

    # ============= ENVÍO POR CORREO — ADMIN (bloque copiado de tu original) =============
    with col_email:
        es_admin = st.session_state.get('role') == 'admin'
        if es_admin:
            st.markdown("#### 📧 Enviar por correo")
            st.markdown(
                "<div style='background:#e3f2fd;padding:10px;border-radius:8px;margin-bottom:10px;font-size:12px;'>"
                "Selecciona de la lista CLIENTIFY o <b>añade correos manualmente</b> (coma / punto y coma). "
                "🟩 <b>pendiente</b> (con blancos) · "
                "🌸 <b>presente sin pendientes</b> · "
                "🟥 <b>no encontrado</b>."
                "</div>",
                unsafe_allow_html=True
            )

            def _format_email_label(email: str) -> str:
                name = KNOWN_PEOPLE.get(email, "")
                return f"{name} <{email}>" if name else email

            seleccion_emails = st.multiselect(
                "Selecciona destinatarios (CLIENTIFY):",
                options=KNOWN_EMAILS,
                default=[],
                format_func=_format_email_label,
                help="Lista restringida a correos proporcionados."
            )

            otros_emails_input = st.text_input(
                "Añade otros correos (separados por , o ;):",
                value="",
                help="Solo dominios @eiposgrados.com y @grupomainjobs.com"
            )

            extra_validos = []
            extra_error_msg = ""
            if otros_emails_input.strip():
                es_ok, lista, msg = validar_emails(otros_emails_input)
                if not es_ok:
                    extra_error_msg = msg
                else:
                    extra_validos = lista
            if extra_error_msg:
                st.error(extra_error_msg)

            destinatarios_totales = sorted(set(seleccion_emails + extra_validos))

            # --- Estados
            props_norm_df = set(_norm_name(v) for v in df_tablas_global["propietario"].dropna().astype(str).unique())

            def _recipient_status(email: str) -> str:
                nombre = KNOWN_PEOPLE.get(email, None)
                if not nombre:
                    return "unknown"
                n = _norm_name(nombre)
                if n in props_need_update_norm:
                    return "pending"   # 🟩
                if n in props_norm_df:
                    return "present"   # 🌸
                return "unknown"       # 🟥

            def _chip_css(status: str) -> str:
                if status == "pending":   # verde
                    return "background:#dcfce7;border:1px solid #16a34a;color:#065f46"
                if status == "present":   # rosa
                    return "background:#ffe4f1;border:1px solid #d63384;color:#ad1466"
                return "background:#fee2e2;border:1px solid #ef4444;color:#991b1b"  # rojo

            chips = []
            for em in destinatarios_totales:
                name = KNOWN_PEOPLE.get(em, None)
                label_ui = f"{name} <{em}>" if name else em
                status = _recipient_status(em)
                chips.append(
                    f"<span style='display:inline-block;margin:3px 6px 0 0;padding:4px 8px;"
                    f"border-radius:8px;{_chip_css(status)}'>{html.escape(label_ui)}</span>"
                )
            if chips:
                st.markdown(
                    "<div>Previsualización:</div>" + "".join(chips) +
                    "<div style='margin-top:6px;font-size:12px;color:#6b7280'>"
                    "🟩 Pendiente · 🌸 Presente sin pendientes · 🟥 No encontrado"
                    "</div>",
                    unsafe_allow_html=True
                )

    # ================= TARJETAS POR PROPIETARIO =================
    st.subheader("Desglose por Propietario")

    # --- NUEVA LÓGICA: aseguramos que usamos datos filtrados por `selected_year`
    df_mes_prop = (
        df_filtrado.groupby(["anio","mes_num","mes_anio","propietario"]).size()
        .reset_index(name="leads").sort_values(["anio","mes_num","propietario"])
    )
    # df_filtrado ya fue filtrado por selected_year arriba, pero por seguridad:
    df_mes_prop = df_mes_prop[df_mes_prop["anio"] == selected_year]

    # Si queremos que aparezcan propietarios que sólo figuren en ventas (pero no en leads),
    # unimos la lista de propietarios de df_ventas (filtrada por año) también.
    propietarios_from_leads = set(df_mes_prop["propietario"].unique().tolist())
    propietarios_from_ventas = set()
    if ventas_ok and not df_ventas.empty:
        df_ventas_for_cards = df_ventas[df_ventas["anio"] == selected_year] if "anio" in df_ventas.columns else df_ventas.copy()
        propietarios_from_ventas = set(df_ventas_for_cards["propietario"].dropna().unique().tolist())

    all_propietarios = sorted(propietarios_from_leads | propietarios_from_ventas)

    if propietario_tablas != "Todos":
        df_mes_prop = df_mes_prop[df_mes_prop["propietario"] == propietario_tablas]

    if df_mes_prop.empty and not all_propietarios:
        st.info("No hay datos para el filtro seleccionado.")
        return

    # totales_leads_prop debe incluir todos los propietarios (leads U ventas) para que la tarjeta sea igual a ventas_preventas
    if df_mes_prop.empty:
        # si no hay leads para este filtro, construyo un índice vacío con los propietarios relevantes
        totales_leads_prop = pd.Series(0, index=all_propietarios).sort_values(ascending=False)
    else:
        totales_leads_prop = df_mes_prop.groupby("propietario")["leads"].sum().reindex(all_propietarios, fill_value=0).sort_values(ascending=False)

    # Construcción matricial leads_prop_mes y ventas_prop_mes con reindex seguros (usando only selected_year)
    leads_prop_mes = (
        df_mes_prop.pivot_table(index="propietario", columns="mes_anio", values="leads", aggfunc="sum", fill_value=0)
        .reindex(index=totales_leads_prop.index).reindex(columns=orden_meses, fill_value=0)
    )

    # ventas_prop_mes seguro (si tenemos df_ventas cargado según selected_year)
    if (ventas_ok and not df_ventas.empty and {"propietario","mes_anio"}.issubset(df_ventas.columns)):
        ventas_filtrado_cards = df_ventas[df_ventas["anio"] == selected_year] if "anio" in df_ventas.columns else df_ventas.copy()
        if mes_seleccionado != "Todos":
            ventas_filtrado_cards = ventas_filtrado_cards[ventas_filtrado_cards["mes_anio"] == mes_seleccionado]
        if programa_seleccionado != "Todos":
            ventas_filtrado_cards = ventas_filtrado_cards[ventas_filtrado_cards["programa_final"] == programa_seleccionado]
        if propietario_tablas != "Todos" and "propietario" in ventas_filtrado_cards.columns:
            ventas_filtrado_cards = ventas_filtrado_cards[ventas_filtrado_cards["propietario"] == propietario_tablas]
        ventas_prop_mes = (
            ventas_filtrado_cards.groupby(["propietario","mes_anio"]).size().unstack(fill_value=0)
            .reindex(index=totales_leads_prop.index, fill_value=0).reindex(columns=orden_meses, fill_value=0)
        )
    else:
        ventas_prop_mes = pd.DataFrame(0, index=totales_leads_prop.index, columns=orden_meses)

    # Evito divisiones por cero / NaN al calcular ratio
    ratio_prop_mes = pd.DataFrame(0.0, index=totales_leads_prop.index, columns=orden_meses)
    try:
        ratio_prop_mes = (ventas_prop_mes.div(leads_prop_mes.replace(0, pd.NA)) * 100).fillna(0).round(2)
    except Exception:
        # fallback seguro
        ratio_prop_mes = pd.DataFrame(0.0, index=totales_leads_prop.index, columns=orden_meses)

    st.markdown(
        """
        <style>
        .cards-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px}
        .card{background:#fff;border:1px solid #edf2f7;border-radius:12px;padding:14px 14px 10px 14px;box-shadow:0 1px 3px rgba(0,0,0,.05)}
        .card h4{margin:0 0 6px 0;font-size:16px;color:#1a202c}
        .row{display:flex;gap:12px;margin:6px 0 10px 0}
        .pill{background:#f3f4f6;border-radius:8px;padding:4px 8px;font-size:12px;font-weight:700;color:#111827}
        .chips{display:flex;flex-wrap:wrap;gap:6px}
        .chip{display:inline-flex;align-items:center;flex-wrap:wrap;gap:6px;height:auto;padding:6px 8px;border-radius:8px;font-size:13px;font-weight:700;color:#111827;box-shadow:inset 0 -1px 0 rgba(0,0,0,.04);border:1px solid rgba(0,0,0,.04)}
        .chip .count,.chip .count-alt{background:rgba(0,0,0,.06);padding:2px 6px;border-radius:6px;font-weight:800}
        .chip .count-alt{background:rgba(0,0,0,.10)}
        </style>
        """,
        unsafe_allow_html=True
    )

    tarjetas_html = ['<div class="cards-grid">']
    for propietario, leads_total in totales_leads_prop.items():
        # lectura segura: puede no existir la fila/columna -> 0; puede ser NaN -> 0
        try:
            ventas_total = int(ventas_prop_mes.loc[propietario].sum()) if (propietario in ventas_prop_mes.index) else 0
        except Exception:
            ventas_total = 0

        ratio_global = (ventas_total / leads_total * 100.0) if leads_total > 0 else None
        ratio_global_txt = f"{ratio_global:.2f}" if ratio_global is not None else "—"

        tarjetas_html.append('<div class="card">')
        tarjetas_html.append(f'<h4>{propietario}</h4>')
        tarjetas_html.append(
            f'<div class="row"><span class="pill">🧊 Leads: {int(leads_total)}</span>'
            f'<span class="pill">🧾 Ventas: {ventas_total}</span>'
            f'<span class="pill">🎯 Ratio: {ratio_global_txt}</span></div>'
        )
        tarjetas_html.append('<div class="chips">')

        for mes in orden_meses:
            # safe read for leads (l), ventas (v), ratio (r)
            l = 0
            v = 0
            r = 0.0
            if (propietario in leads_prop_mes.index) and (mes in leads_prop_mes.columns):
                try:
                    val = leads_prop_mes.at[propietario, mes]
                    l = 0 if pd.isna(val) else int(val)
                except Exception:
                    l = 0
            if (propietario in ventas_prop_mes.index) and (mes in ventas_prop_mes.columns):
                try:
                    valv = ventas_prop_mes.at[propietario, mes]
                    v = 0 if pd.isna(valv) else int(valv)
                except Exception:
                    v = 0
            if (propietario in ratio_prop_mes.index) and (mes in ratio_prop_mes.columns):
                try:
                    valr = ratio_prop_mes.at[propietario, mes]
                    r = 0.0 if pd.isna(valr) else float(valr)
                except Exception:
                    r = 0.0

            if (l > 0) or (v > 0):
                bg = color_map_cards.get(mes, "#718096")
                tarjetas_html.append(
                    f'<span class="chip" style="background:{bg}">{mes}'
                    f'<span class="count">L: {l}</span><span class="count">V: {v}</span>'
                    f'<span class="count-alt">{r:.2f}</span></span>'
                )

        # caso "Sin datos" — comprobación segura con .sum() y try/except
        try:
            suma_leads_prop = int(leads_prop_mes.loc[propietario].sum()) if propietario in leads_prop_mes.index else 0
        except Exception:
            suma_leads_prop = 0
        try:
            suma_ventas_prop = int(ventas_prop_mes.loc[propietario].sum()) if propietario in ventas_prop_mes.index else 0
        except Exception:
            suma_ventas_prop = 0

        if suma_leads_prop == 0 and suma_ventas_prop == 0:
            tarjetas_html.append('<span class="chip" style="background:#A0AEC0">Sin datos</span>')
        tarjetas_html.append('</div></div>')
    tarjetas_html.append('</div>')
    st.markdown("\n".join(tarjetas_html), unsafe_allow_html=True)

if __name__ == "__main__":
    app()
