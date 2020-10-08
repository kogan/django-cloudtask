import google.auth.transport.requests
from google.auth import jwt
from google.oauth2.id_token import _GOOGLE_OAUTH2_CERTS_URL
from google.oauth2.id_token import _fetch_certs as fetch_certs

certs = None


def verify_jwt(token: str) -> bool:
    global certs
    if certs is None:
        request = google.auth.transport.requests.Request()
        certs = fetch_certs(request, _GOOGLE_OAUTH2_CERTS_URL)

    try:
        decoded = jwt.decode(token, certs=certs)
        return decoded["iss"] == "https://accounts.google.com"
    except ValueError:
        return False
