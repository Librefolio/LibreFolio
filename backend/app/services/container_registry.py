"""Public container-registry availability checks for LibreFolio releases."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

from backend.app.schemas.system import ContainerImageStatusResponse

GHCR_SERVICE = "ghcr.io"
GHCR_REPOSITORY = "librefolio/librefolio"
GHCR_SCOPE = f"repository:{GHCR_REPOSITORY}:pull"
GHCR_TOKEN_PATH = "/token"
GHCR_MANIFEST_ACCEPT = ", ".join(
    (
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.docker.distribution.manifest.v2+json",
    )
)
GHCR_MANIFEST_URL = f"https://{GHCR_SERVICE}/v2/{GHCR_REPOSITORY}/manifests"
REGISTRY_TIMEOUT_SECONDS = 5.0

_TAG_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
_AUTH_TOKEN_CHARS = frozenset("!#$%&'*+-.^_`|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
_BEARER_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9\-._~+/]+=*$")


@dataclass(frozen=True)
class _BearerChallenge:
    realm: str
    service: str
    scope: str


def _skip_ows(value: str, index: int) -> int:
    while index < len(value) and value[index] in " \t":
        index += 1
    return index


def _read_auth_key(value: str, index: int) -> tuple[str, int] | None:
    index = _skip_ows(value, index)
    start = index
    while index < len(value) and value[index] in _AUTH_TOKEN_CHARS:
        index += 1
    if index == start:
        return None
    return value[start:index].lower(), index


def _read_quoted_auth_value(value: str, index: int) -> tuple[str, int] | None:
    index = _skip_ows(value, index)
    if index >= len(value) or value[index] != '"':
        return None
    index += 1
    decoded: list[str] = []

    while index < len(value):
        char = value[index]
        index += 1
        if char == '"':
            return "".join(decoded), index
        if char == "\\":
            if index >= len(value):
                return None
            char = value[index]
            index += 1
        if ord(char) < 0x20 or ord(char) == 0x7F:
            return None
        decoded.append(char)
    return None


def _parse_auth_params(value: str) -> dict[str, str] | None:
    """Parse quoted RFC 7235 auth params without accepting duplicate keys."""
    params: dict[str, str] = {}
    index = 0

    while index < len(value):
        parsed_key = _read_auth_key(value, index)
        if parsed_key is None:
            return None
        key, index = parsed_key

        index = _skip_ows(value, index)
        if index >= len(value) or value[index] != "=":
            return None
        index += 1

        parsed_value = _read_quoted_auth_value(value, index)
        if parsed_value is None or key in params:
            return None
        params[key], index = parsed_value

        index = _skip_ows(value, index)
        if index == len(value):
            break
        if value[index] != ",":
            return None
        index += 1
        if not value[index:].strip():
            return None

    return params


def _parse_bearer_challenge(header: str | None) -> _BearerChallenge | None:
    """Return a trusted GHCR pull challenge, or ``None`` for any mismatch."""
    if not header:
        return None
    match = re.match(r"^\s*Bearer\s+(.+?)\s*$", header, flags=re.IGNORECASE)
    if not match:
        return None
    params = _parse_auth_params(match.group(1))
    if not params:
        return None

    realm = params.get("realm")
    service = params.get("service")
    scope = params.get("scope")
    if not realm or service != GHCR_SERVICE or scope != GHCR_SCOPE:
        return None

    try:
        parsed_realm = urlsplit(realm)
        port = parsed_realm.port
    except ValueError:
        return None
    if (
        parsed_realm.scheme.lower() != "https"
        or parsed_realm.hostname is None
        or parsed_realm.hostname.lower() != GHCR_SERVICE
        or port not in (None, 443)
        or parsed_realm.username is not None
        or parsed_realm.password is not None
        or parsed_realm.path != GHCR_TOKEN_PATH
        or parsed_realm.query
        or parsed_realm.fragment
    ):
        return None

    return _BearerChallenge(realm=realm, service=service, scope=scope)


def _read_bearer_token(response: httpx.Response) -> str | None:
    try:
        payload = response.json()
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None

    token = payload.get("token")
    access_token = payload.get("access_token")
    if token is not None and (not isinstance(token, str) or not _BEARER_TOKEN_PATTERN.fullmatch(token)):
        return None
    if access_token is not None and (not isinstance(access_token, str) or not _BEARER_TOKEN_PATTERN.fullmatch(access_token)):
        return None
    if token and access_token and token != access_token:
        return None
    return token or access_token or None


def _manifest_result(response: httpx.Response) -> ContainerImageStatusResponse:
    if response.is_success:
        return ContainerImageStatusResponse(status="published")
    if response.status_code == 404:
        return ContainerImageStatusResponse(status="pending")
    return ContainerImageStatusResponse(status="error", reason="image-request-failed")


async def _probe_with_client(tag: str, client: httpx.AsyncClient) -> ContainerImageStatusResponse:
    manifest_url = f"{GHCR_MANIFEST_URL}/{tag}"
    manifest_headers = {"Accept": GHCR_MANIFEST_ACCEPT}
    try:
        initial = await client.head(manifest_url, headers=manifest_headers)
    except httpx.HTTPError:
        return ContainerImageStatusResponse(status="error", reason="image-request-failed")

    if initial.status_code != 401:
        return _manifest_result(initial)

    challenge = _parse_bearer_challenge(initial.headers.get("WWW-Authenticate"))
    if challenge is None:
        return ContainerImageStatusResponse(status="error", reason="image-auth-request-failed")

    try:
        token_response = await client.get(
            challenge.realm,
            params={"service": challenge.service, "scope": challenge.scope},
            headers={"Accept": "application/json"},
        )
    except httpx.HTTPError:
        return ContainerImageStatusResponse(status="error", reason="image-auth-request-failed")
    if not token_response.is_success:
        return ContainerImageStatusResponse(status="error", reason="image-auth-request-failed")

    token = _read_bearer_token(token_response)
    if token is None:
        return ContainerImageStatusResponse(status="error", reason="image-auth-request-failed")

    try:
        authenticated = await client.head(
            manifest_url,
            headers={**manifest_headers, "Authorization": f"Bearer {token}"},
        )
    except httpx.HTTPError:
        return ContainerImageStatusResponse(status="error", reason="image-request-failed")
    return _manifest_result(authenticated)


async def probe_container_image(tag: str, client: httpx.AsyncClient | None = None) -> ContainerImageStatusResponse:
    """Check one normalized LibreFolio image tag through GHCR's public token flow."""
    if not _TAG_PATTERN.fullmatch(tag):
        return ContainerImageStatusResponse(status="error", reason="image-request-failed")
    if client is not None:
        return await _probe_with_client(tag, client)

    async with httpx.AsyncClient(timeout=REGISTRY_TIMEOUT_SECONDS, follow_redirects=False) as owned_client:
        return await _probe_with_client(tag, owned_client)
