# utils/graph_mail.py
import base64
import json
import mimetypes
import os
import typing as T

import requests


class GraphMailer:
    def __init__(self, tenant_id: str, client_id: str, client_secret: str, sender_upn: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.sender_upn = sender_upn
        self._token = None

    # ==================== AUTH ====================
    def _token_endpoint(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"

    def _get_token(self) -> str:
        if self._token:
            return self._token
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        }
        resp = requests.post(self._token_endpoint(), data=data, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"Token error {resp.status_code}: {resp.text}")
        self._token = resp.json()["access_token"]
        return self._token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._get_token()}",
                "Content-Type": "application/json"}

    # ==================== DIAGNÓSTICO ====================
    def whoami(self) -> dict:
        """Devuelve info del usuario remitente (para validar que existe el buzón)."""
        url = f"https://graph.microsoft.com/v1.0/users/{self.sender_upn}"
        r = requests.get(url, headers=self._headers(), timeout=30)
        return {"status": r.status_code, "body": _safe_json(r)}

    # ==================== ENVÍO ====================
    def send_mail(
        self,
        subject: str,
        html_body: str,
        to: T.List[str],
        cc: T.Optional[T.List[str]] = None,
        bcc: T.Optional[T.List[str]] = None,
        attachment_paths: T.Optional[T.List[str]] = None,
    ) -> dict:
        """
        Devuelve un dict con {status, body}. 202 == OK.
        """
        def _addr(addr: str) -> dict:
            return {"emailAddress": {"address": addr}}

        message = {
            "subject": subject,
            "body": {"contentType": "HTML", "content": html_body},
            "toRecipients": [_addr(a) for a in to],
        }
        if cc:
            message["ccRecipients"] = [_addr(a) for a in cc]
        if bcc:
            message["bccRecipients"] = [_addr(a) for a in bcc]

        # Adjuntos (opcionales)
        attachments = []
        for path in (attachment_paths or []):
            if not path or not os.path.exists(path):
                continue
            with open(path, "rb") as f:
                content_bytes = f.read()
            content_b64 = base64.b64encode(content_bytes).decode("utf-8")
            mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
            name = os.path.basename(path)
            attachments.append({
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": name,
                "contentType": mime,
                "contentBytes": content_b64,
            })
        if attachments:
            message["attachments"] = attachments

        url = f"https://graph.microsoft.com/v1.0/users/{self.sender_upn}/sendMail"
        payload = {"message": message, "saveToSentItems": "true"}
        r = requests.post(url, headers=self._headers(), data=json.dumps(payload), timeout=60)
        return {"status": r.status_code, "body": _safe_json(r)}


def _safe_json(resp: requests.Response):
    try:
        return resp.json()
    except Exception:
        return resp.text
