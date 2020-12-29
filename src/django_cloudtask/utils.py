import functools
import time

import google.auth.transport.requests
from google.auth import jwt
from google.oauth2.id_token import _GOOGLE_OAUTH2_CERTS_URL
from google.oauth2.id_token import _fetch_certs as fetch_certs


@functools.lru_cache(1)
def _get_certs(_ttl_hash):
    request = google.auth.transport.requests.Request()
    return fetch_certs(request, _GOOGLE_OAUTH2_CERTS_URL)


def get_certs():
    """
    Refresh certificates (roughly) every 12 hours.
    """
    return _get_certs(time.time() // (3600 * 12))


def verify_jwt(token: str) -> bool:
    try:
        decoded = jwt.decode(token, certs=get_certs())
        return decoded["iss"] == "https://accounts.google.com"
    except ValueError:
        return False
