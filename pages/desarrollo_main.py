import streamlit as st
import pandas as pd
import io
import requests
import msal
from datetime import datetime

# =========================
# 🔐 CARGA DESDE SHAREPOINT
# =========================
@st.cache_resource
def _msal_app_empleo():
    cfg = st.secrets["empleo"]
    return msal.ConfidentialClientApplication(
        client_id=cfg["client_id"],
        client_credential=cfg["client_secret"],
        authority=f"https://login.microsoftonline.com/{cfg['tenant_id']}",
    )

def _graph_token_empleo():
    app = _msal_app_empleo()
    scopes = ["https://graph.microsoft.com/.default"]
    result = app.acquire_token_silent(scopes, account=None) or app.acquire_token_for_client(scopes)
    if "access_token" not in result:
        raise RuntimeError(result.get("error_description", "No se pudo obtener token de Graph"))
    return result["access_token"]

@st.cache_data(show_spinner=False)
def cargar_empleo_sharepoint():
    """
    Lee el Excel 'EIP EMPLEO.xlsx' desde SharePoint usando los datos en st.secrets['empleo'].
    Necesita en secrets:
      domain = "grupomainjobs.sharepoint.com"
      site_name = "GrupoMainjobs928"
      file_path = "/EIP BBDD/EIP EMPLEO.xlsx"
      worksheet_name = "GENERAL" (o usa worksheet_index)
    """
    cfg = st.secrets["empleo"]
    token = _graph_token_empleo()
    headers = {"Authorization": f"Bearer {token}"}

    # 1) Obtener siteId a partir de domain + site_name (slug)
    #    Ejemplo: https://graph.microsoft.com/v1.0/sites/{domain}:/sites/{site_name}
    site_url = f"https://graph.microsoft.com/v1.0/sites/{cfg['domain']}:/sites/{cfg['site_name']}"
    site_resp = requests.get(site_url, headers=headers)
    site_resp.raise_for_status()
    site_id = site_resp.json()["id"]

    # 2) Listar drives del site y coger "Documentos" (o "Shared Documents" si tu tenant está en inglés)
    drives_resp = requests.get(f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives", headers=headers)
    drives_resp.raise_for_status()
    drives = drives_resp.json().get("value", [])
    drive = next((d for d in drives if d["name"].lower() in ("documentos", "shared documents")), None)
    if not drive:
        raise RuntimeError("No se encontró la biblioteca 'Documentos' (o 'Shared Documents').")
    drive_id = drive["id"]

    # 3) Descargar el archivo por ruta
    file_path = cfg["file_path"].lstrip("/")  # "EIP BBDD/EIP EMPLEO.xlsx"
    content_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{file_path}:/content"
    bin_resp = requests.get(content_url, headers=headers)
    bin_resp.raise_for_status()
    xls = io.BytesIO(bin_resp.content)

    # 4) Leer hoja
    ws_name = cfg.get("worksheet_name", "")
    ws_index = int(cfg.get("worksheet_index", 0))
    if ws_name:
        df = pd.read_excel(xls, sheet_name=ws_name)
    else:
        df = pd.read_excel(xls, sheet_name=ws_index)

    # Normaliza cabeceras como haces en tus páginas
    df.columns = df.columns.str.strip()
    return df

# =========================
# 🚀 PÁGINA
# =========================
def desarrollo_page():
    fecha_actual = datetime.today().strftime("%d/%m/%Y")

    # Botón de recarga (limpia caché de datos)
    if st.button("🔄 Recargar datos desde SharePoint"):
        st.cache_data.clear()
        st.rerun()

    st.markdown(
        f"<h1>🚀 Área de Empleo <span style='font-size:18px; color: gray;'>🗓️ {fecha_actual}</span></h1>",
        unsafe_allow_html=True
    )

    # Cargar datos de EMPLEO (SharePoint)
    try:
        df = cargar_empleo_sharepoint()
    except Exception as e:
        st.error(f"❌ Error al cargar los datos de SharePoint: {e}")
        return

    if df is None or df.empty:
        st.warning("⚠️ No se pudieron cargar datos del documento.")
        return

    st.success("✅ Datos cargados correctamente desde SharePoint (EIP EMPLEO.xlsx / GENERAL).")

    subcategorias = [
        "Principal",
        "Riesgo económico",
        "Cierre expediente total"
    ]
    seleccion = st.selectbox("Selecciona una subcategoría:", subcategorias)

    if seleccion == "Principal":
        from pages.desarrollo import principal
        principal.render(df)
    elif seleccion == "Riesgo económico":
        from pages.desarrollo import riesgo_economico
        riesgo_economico.render(df)
    elif seleccion == "Cierre expediente total":
        from pages.desarrollo import cierre_expediente_total
        cierre_expediente_total.render(df)