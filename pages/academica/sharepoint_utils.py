import requests
from msal import ConfidentialClientApplication

def get_access_token(config):
    authority = f"https://login.microsoftonline.com/{config['tenant_id']}"
    app = ConfidentialClientApplication(
        client_id=config["client_id"],
        client_credential=config["client_secret"],
        authority=authority
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    return result.get("access_token", None)

def get_site_id(config, token):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.microsoft.com/v1.0/sites/{config['domain']}:/sites/{config['site_name']}"
    res = requests.get(url, headers=headers)
    return res.json()["id"] if res.ok else None

def download_excel(config, token, site_id, filename="indicadores.xlsx"):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:{config['file_path']}:/content"
    res = requests.get(url, headers=headers)
    if res.ok:
        with open(filename, "wb") as f:
            f.write(res.content)
        return filename
    return None
