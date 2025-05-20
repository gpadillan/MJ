import pandas as pd
import requests
import os
from msal import ConfidentialClientApplication
from dotenv import load_dotenv

# Cargar variables desde .env
load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
DOMAIN = os.getenv("DOMAIN")
SITE_NAME = os.getenv("SITE_NAME")
FILE_PATH = os.getenv("FILE_PATH")

def get_access_token():
    authority = f"https://login.microsoftonline.com/{TENANT_ID}"
    app = ConfidentialClientApplication(
        client_id=CLIENT_ID,
        client_credential=CLIENT_SECRET,
        authority=authority
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    return result.get("access_token", None)

def get_site_id(token):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.microsoft.com/v1.0/sites/{DOMAIN}:/sites/{SITE_NAME}"
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        return res.json()["id"]
    return None

def download_excel(token, site_id):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:{FILE_PATH}:/content"
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        with open("indicadores.xlsx", "wb") as f:
            f.write(res.content)
        return "indicadores.xlsx"
    return None

# ✅ Función principal que otras páginas deben usar
def cargar_excel_desde_sharepoint(anio: str) -> pd.ExcelFile | None:
    if anio == "2025":
        try:
            return pd.ExcelFile("indicadores_2025.xlsx")
        except FileNotFoundError:
            return None
    else:
        token = get_access_token()
        if not token:
            return None
        site_id = get_site_id(token)
        if not site_id:
            return None
        archivo = download_excel(token, site_id)
        if not archivo:
            return None
        try:
            return pd.ExcelFile(archivo)
        except Exception:
            return None
