"""Pure regressions for the GHCR container-image availability probe."""

from __future__ import annotations

import logging
from collections.abc import Callable
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI, HTTPException

import backend.app.api.v1.system as system_api
from backend.app.api.v1.auth import get_current_user
from backend.app.schemas.system import ContainerImageStatusResponse
from backend.app.services.container_registry import (
    GHCR_MANIFEST_ACCEPT,
    GHCR_MANIFEST_URL,
    GHCR_SCOPE,
    GHCR_SERVICE,
    GHCR_TOKEN_PATH,
    probe_container_image,
)

TAG = "2.0.0"
MANIFEST_URL = f"{GHCR_MANIFEST_URL}/{TAG}"
TOKEN_URL = f"https://{GHCR_SERVICE}{GHCR_TOKEN_PATH}"
TRUSTED_CHALLENGE = f'Bearer realm="{TOKEN_URL}",service="{GHCR_SERVICE}",scope="{GHCR_SCOPE}"'

EXPECTED_ACCEPT_TYPES = (
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
)
AUTH_SCHEME = "Bear" + "er"

# Deliberately conspicuous synthetic values: leak checks fail without echoing
# either value in pytest's assertion diagnostics.
SYNTHETIC_TOKEN = "round5-token.private-value"
SYNTHETIC_ACCESS_TOKEN = "round5-access-token.private-value"
SYNTHETIC_CREDENTIAL = "round5-credential.private-value"

MockHandler = Callable[[httpx.Request], httpx.Response]


def _assert_no_sensitive_output(
    result: ContainerImageStatusResponse,
    caplog: pytest.LogCaptureFixture,
) -> None:
    rendered = f"{result!r}\n{result.model_dump_json()}\n{caplog.text}"
    if any(
        sensitive_value in rendered
        for sensitive_value in (
            SYNTHETIC_TOKEN,
            SYNTHETIC_ACCESS_TOKEN,
            SYNTHETIC_CREDENTIAL,
        )
    ):
        raise AssertionError("container-registry probe exposed synthetic sensitive material")


def _require_token_request(request: httpx.Request) -> None:
    expected_url = httpx.URL(
        TOKEN_URL,
        params={"service": GHCR_SERVICE, "scope": GHCR_SCOPE},
    )
    if request.method != "GET" or request.url != expected_url or request.headers.get("Accept") != "application/json" or request.headers.get("Authorization") is not None or request.headers.get("Proxy-Authorization") is not None or request.headers.get("Cookie") is not None:
        raise AssertionError("GHCR token request did not match the anonymous contract")


def _require_manifest_accept(request: httpx.Request) -> None:
    accept = request.headers.get("Accept")
    if accept != GHCR_MANIFEST_ACCEPT:
        raise AssertionError("manifest request did not reuse the shared Accept contract")
    if tuple(item.strip() for item in accept.split(",")) != EXPECTED_ACCEPT_TYPES:
        raise AssertionError("manifest request did not advertise all four OCI/Docker media types")


def _token_flow_handler(  # noqa: C901 - explicit three-phase registry protocol double
    *,
    authenticated_status: int = 200,
    authenticated_raises: bool = False,
    token_outcome: str = "success",
    require_retrieved_token: bool = False,
) -> tuple[MockHandler, list[str]]:
    phases: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:  # noqa: C901 - phase assertions are intentionally inline
        if request.method == "HEAD" and str(request.url) == MANIFEST_URL:
            _require_manifest_accept(request)
            if not phases:
                if request.headers.get("Authorization") is not None or request.headers.get("Proxy-Authorization") is not None or request.headers.get("Cookie") is not None:
                    raise AssertionError("initial manifest request was not anonymous or used the wrong media types")
                phases.append("manifest-anonymous")
                return httpx.Response(
                    401,
                    headers={"WWW-Authenticate": TRUSTED_CHALLENGE},
                )

            if phases == ["manifest-anonymous", "token"]:
                authorization = request.headers.get("Authorization")
                if require_retrieved_token and authorization != f"Bearer {SYNTHETIC_TOKEN}":
                    phases.append("manifest-authenticated")
                    return httpx.Response(401)
                if authorization is None:
                    raise AssertionError("post-token manifest request omitted the Authorization header")
                phases.append("manifest-authenticated")
                if authenticated_raises:
                    raise httpx.ConnectError(
                        "synthetic manifest endpoint failure",
                        request=request,
                    )
                return httpx.Response(authenticated_status)

        if phases == ["manifest-anonymous"]:
            _require_token_request(request)
            phases.append("token")
            if token_outcome == "network-exception":
                raise httpx.ConnectError(
                    "synthetic token endpoint failure",
                    request=request,
                )
            if token_outcome == "non-success":
                return httpx.Response(
                    503,
                    json={
                        "error": "temporarily_unavailable",
                        "credential": SYNTHETIC_CREDENTIAL,
                    },
                )
            if token_outcome == "malformed-token":
                return httpx.Response(
                    200,
                    json={
                        "token": f"{SYNTHETIC_TOKEN} invalid",
                        "credential": SYNTHETIC_CREDENTIAL,
                    },
                )
            if token_outcome == "malformed-json":
                return httpx.Response(200, content=b"not json")
            if token_outcome == "success":
                return httpx.Response(
                    200,
                    json={
                        "token": SYNTHETIC_TOKEN,
                        "credential": SYNTHETIC_CREDENTIAL,
                    },
                )

        raise AssertionError("GHCR probe issued an unexpected request")

    return handler, phases


async def _probe(handler: MockHandler) -> ContainerImageStatusResponse:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        follow_redirects=False,
    ) as client:
        return await probe_container_image(TAG, client)


@pytest.mark.asyncio
async def test_trusted_ghcr_challenge_reuses_retrieved_token(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    handler, phases = _token_flow_handler(require_retrieved_token=True)

    result = await _probe(handler)

    _assert_no_sensitive_output(result, caplog)
    assert result == ContainerImageStatusResponse(status="published")
    assert phases == [
        "manifest-anonymous",
        "token",
        "manifest-authenticated",
    ]


@pytest.mark.asyncio
async def test_authenticated_manifest_network_exception_is_request_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    handler, phases = _token_flow_handler(authenticated_raises=True)

    result = await _probe(handler)

    _assert_no_sensitive_output(result, caplog)
    assert result == ContainerImageStatusResponse(
        status="error",
        reason="image-request-failed",
    )
    assert phases == [
        "manifest-anonymous",
        "token",
        "manifest-authenticated",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "token_outcome",
    ["network-exception", "non-success", "malformed-token", "malformed-json"],
    ids=[
        "token-network-exception",
        "token-non-success",
        "token-malformed-payload",
        "token-invalid-json",
    ],
)
async def test_token_failures_are_reported_as_auth_failures_without_leaks(
    token_outcome: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    handler, phases = _token_flow_handler(token_outcome=token_outcome)

    result = await _probe(handler)

    _assert_no_sensitive_output(result, caplog)
    assert result == ContainerImageStatusResponse(
        status="error",
        reason="image-auth-request-failed",
    )
    assert phases == ["manifest-anonymous", "token"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("token_payload", "expected_token", "expected", "authenticated"),
    [
        pytest.param(
            {"token": SYNTHETIC_TOKEN},
            SYNTHETIC_TOKEN,
            ContainerImageStatusResponse(status="published"),
            True,
            id="token-only",
        ),
        pytest.param(
            {"access_token": SYNTHETIC_ACCESS_TOKEN},
            SYNTHETIC_ACCESS_TOKEN,
            ContainerImageStatusResponse(status="published"),
            True,
            id="access-token-only",
        ),
        pytest.param(
            {"token": SYNTHETIC_TOKEN, "access_token": SYNTHETIC_TOKEN},
            SYNTHETIC_TOKEN,
            ContainerImageStatusResponse(status="published"),
            True,
            id="matching-fields",
        ),
        pytest.param(
            {"token": SYNTHETIC_TOKEN, "access_token": SYNTHETIC_ACCESS_TOKEN},
            SYNTHETIC_TOKEN,
            ContainerImageStatusResponse(
                status="error",
                reason="image-auth-request-failed",
            ),
            False,
            id="conflicting-fields",
        ),
    ],
)
async def test_token_and_access_token_fields_are_reconciled(
    token_payload: dict[str, str],
    expected_token: str,
    expected: ContainerImageStatusResponse,
    authenticated: bool,
    caplog: pytest.LogCaptureFixture,
) -> None:
    phases: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "HEAD" and str(request.url) == MANIFEST_URL:
            _require_manifest_accept(request)
            if not phases:
                phases.append("manifest-anonymous")
                return httpx.Response(
                    401,
                    headers={"WWW-Authenticate": TRUSTED_CHALLENGE},
                )
            if request.headers.get("Authorization") != f"{AUTH_SCHEME} {expected_token}":
                raise AssertionError("authenticated manifest request used the wrong token")
            phases.append("manifest-authenticated")
            return httpx.Response(200)
        if phases == ["manifest-anonymous"]:
            _require_token_request(request)
            phases.append("token")
            return httpx.Response(200, json=token_payload)
        raise AssertionError("GHCR probe issued an unexpected request")

    result = await _probe(handler)

    _assert_no_sensitive_output(result, caplog)
    assert result == expected
    assert phases == (["manifest-anonymous", "token", "manifest-authenticated"] if authenticated else ["manifest-anonymous", "token"])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("authenticated_status", "expected"),
    [
        pytest.param(
            404,
            ContainerImageStatusResponse(status="pending"),
            id="authenticated-manifest-not-found",
        ),
        pytest.param(
            401,
            ContainerImageStatusResponse(
                status="error",
                reason="image-request-failed",
            ),
            id="authenticated-manifest-unauthorized",
        ),
        pytest.param(
            503,
            ContainerImageStatusResponse(
                status="error",
                reason="image-request-failed",
            ),
            id="authenticated-manifest-other-error",
        ),
    ],
)
async def test_post_token_manifest_status_mapping(
    authenticated_status: int,
    expected: ContainerImageStatusResponse,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    handler, phases = _token_flow_handler(
        authenticated_status=authenticated_status,
    )

    result = await _probe(handler)

    _assert_no_sensitive_output(result, caplog)
    assert result == expected
    assert phases == [
        "manifest-anonymous",
        "token",
        "manifest-authenticated",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "challenge",
    [
        pytest.param(None, id="challenge-header-missing"),
        pytest.param(
            f'Basic realm="{TOKEN_URL}"',
            id="challenge-scheme-malformed",
        ),
        pytest.param(
            f'Bearer service="{GHCR_SERVICE}",scope="{GHCR_SCOPE}"',
            id="challenge-realm-missing",
        ),
        pytest.param(
            f'Bearer realm="http://{GHCR_SERVICE}{GHCR_TOKEN_PATH}",' f'service="{GHCR_SERVICE}",scope="{GHCR_SCOPE}"',
            id="challenge-realm-untrusted-scheme",
        ),
        pytest.param(
            f'Bearer realm="https://registry.invalid/token",' f'service="{GHCR_SERVICE}",scope="{GHCR_SCOPE}"',
            id="challenge-realm-untrusted-host",
        ),
        pytest.param(
            f'Bearer realm="https://round5-user:{SYNTHETIC_CREDENTIAL}@' f'{GHCR_SERVICE}{GHCR_TOKEN_PATH}",service="{GHCR_SERVICE}",' f'scope="{GHCR_SCOPE}"',
            id="challenge-realm-credentials-untrusted",
        ),
        pytest.param(
            f'Bearer realm="{TOKEN_URL}",scope="{GHCR_SCOPE}"',
            id="challenge-service-missing",
        ),
        pytest.param(
            f'Bearer realm="{TOKEN_URL}",service="registry.invalid",' f'scope="{GHCR_SCOPE}"',
            id="challenge-service-untrusted",
        ),
        pytest.param(
            f'Bearer realm="{TOKEN_URL}",service="{GHCR_SERVICE}"',
            id="challenge-scope-missing",
        ),
        pytest.param(
            f'Bearer realm="{TOKEN_URL}",service="{GHCR_SERVICE}",' 'scope="repository:someone-else/private:pull"',
            id="challenge-scope-untrusted",
        ),
        pytest.param(
            f'Bearer realm="{TOKEN_URL}",service="{GHCR_SERVICE}",' f'scope="{GHCR_SCOPE}",scope="{GHCR_SCOPE}"',
            id="challenge-parameters-malformed",
        ),
    ],
)
async def test_untrusted_challenge_stops_before_token_request(
    challenge: str | None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    requests_seen = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests_seen
        requests_seen += 1
        if requests_seen != 1 or request.method != "HEAD" or str(request.url) != MANIFEST_URL:
            raise AssertionError("invalid GHCR challenge triggered a follow-up request")
        headers = {} if challenge is None else {"WWW-Authenticate": challenge}
        return httpx.Response(401, headers=headers)

    result = await _probe(handler)

    _assert_no_sensitive_output(result, caplog)
    assert result == ContainerImageStatusResponse(
        status="error",
        reason="image-auth-request-failed",
    )
    assert requests_seen == 1


def _system_app(*, authenticated: bool) -> FastAPI:
    app = FastAPI()
    app.include_router(system_api.router, prefix="/api/v1")

    async def current_user() -> SimpleNamespace:
        if not authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return SimpleNamespace(id=41)

    app.dependency_overrides[get_current_user] = current_user
    return app


@pytest.mark.asyncio
async def test_container_image_endpoint_requires_auth_before_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe_called = False

    async def unexpected_probe(_tag: str) -> ContainerImageStatusResponse:
        nonlocal probe_called
        probe_called = True
        raise AssertionError("unauthenticated request reached the registry probe")

    monkeypatch.setattr(system_api, "probe_container_image", unexpected_probe)
    app = _system_app(authenticated=False)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/system/container-image-status",
            params={"tag": TAG},
        )

    assert response.status_code == 401
    assert probe_called is False


@pytest.mark.asyncio
async def test_container_image_endpoint_returns_the_probe_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received_tags: list[str] = []

    async def fake_probe(tag: str) -> ContainerImageStatusResponse:
        received_tags.append(tag)
        return ContainerImageStatusResponse(status="pending")

    monkeypatch.setattr(system_api, "probe_container_image", fake_probe)
    app = _system_app(authenticated=True)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/system/container-image-status",
            params={"tag": "1.2.3"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "pending", "reason": None}
    assert received_tags == ["1.2.3"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_tag",
    ["latest", "v1.2.3", "1.2", "1.2.3-rc1"],
    ids=["latest", "leading-v", "incomplete-semver", "prerelease"],
)
async def test_container_image_endpoint_rejects_non_stable_tags_before_probe(
    invalid_tag: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe_called = False

    async def unexpected_probe(_tag: str) -> ContainerImageStatusResponse:
        nonlocal probe_called
        probe_called = True
        raise AssertionError("invalid tag reached the registry probe")

    monkeypatch.setattr(system_api, "probe_container_image", unexpected_probe)
    app = _system_app(authenticated=True)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/system/container-image-status",
            params={"tag": invalid_tag},
        )

    assert response.status_code == 422
    assert probe_called is False
