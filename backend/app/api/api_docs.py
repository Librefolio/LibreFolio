"""The API's documentation pages, Swagger UI and ReDoc, on debug instances only (lot H-55, R5).

Owner: workstream H (platform). FastAPI's own pages load ``swagger-ui-dist@5`` and ``redoc@2`` from jsDelivr, at a
moving version and without integrity, and start them with an inline script. These pages are ours: the libraries come
from jsDelivr at an exact version, each tag with its Subresource Integrity hash (``LIBRARIES``: a changed file is refused
by the browser), and the start scripts are served by the instance, so nothing is inline and the pages run under
``script-src 'self' https://cdn.jsdelivr.net`` (``security_headers.py``). No Google Fonts, no third-party favicon.

They exist only where the documentation is switched on (``config.api_docs_enabled()``: ``LIBREFOLIO_API_DOCS``, which
``dev.py server --debug`` sets, or test mode). Anywhere else the pages, their start scripts and ``openapi.json`` answer
404: an instance in production publishes no map of its API.
"""

from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response

from backend.app.config import API_V1_PREFIX

DOCS_PATH = f"{API_V1_PREFIX}/docs"
REDOC_PATH = f"{API_V1_PREFIX}/redoc"
OPENAPI_PATH = f"{API_V1_PREFIX}/openapi.json"
SWAGGER_INIT_PATH = f"{DOCS_PATH}/swagger-init.js"
REDOC_INIT_PATH = f"{REDOC_PATH}/redoc-init.js"
#: The only host the pages load a library from.
LIBRARY_ORIGIN = "https://cdn.jsdelivr.net"


@dataclass(frozen=True)
class Library:
    """A file of a library at an exact version, with the Subresource Integrity hash its published bytes have."""

    url: str
    integrity: str


#: Hashes computed from the files jsDelivr publishes at these versions (H-55 R5, 22/10). A new version takes new hashes.
SWAGGER_JS = Library(f"{LIBRARY_ORIGIN}/npm/swagger-ui-dist@5.33.1/swagger-ui-bundle.js", "sha384-ZPehFMQommnnuaZ4rpxgkgTT2DKFVp4hZC/7pLit+9Lek9T1YGSo23eHFbvNkXkw")
SWAGGER_CSS = Library(f"{LIBRARY_ORIGIN}/npm/swagger-ui-dist@5.33.1/swagger-ui.css", "sha384-Ov4/wv3j2bmct8cDc5X4ngJZohVPzEmc6uDPH8WeljUxO5vtoykvMEfbu9Vh6RaW")
REDOC_JS = Library(f"{LIBRARY_ORIGIN}/npm/redoc@2.5.4/bundles/redoc.standalone.js", "sha384-w447zOpYfw/1Tv/5AK9NfHTlQIqE3RVR6KY62jCyy9zNDgO64cMwGGP1Fj0zJVf5")
LIBRARIES = (SWAGGER_JS, SWAGGER_CSS, REDOC_JS)

_HEAD = """<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LibreFolio API</title>
<link rel="icon" href="/favicon.png">"""

_SWAGGER_PAGE = f"""<!doctype html>
<html lang="en">
<head>
{_HEAD}
<link rel="stylesheet" href="{SWAGGER_CSS.url}" integrity="{SWAGGER_CSS.integrity}" crossorigin="anonymous">
</head>
<body>
<div id="swagger-ui" data-openapi-url="{OPENAPI_PATH}"></div>
<script src="{SWAGGER_JS.url}" integrity="{SWAGGER_JS.integrity}" crossorigin="anonymous"></script>
<script src="{SWAGGER_INIT_PATH}"></script>
</body>
</html>
"""

_REDOC_PAGE = f"""<!doctype html>
<html lang="en">
<head>
{_HEAD}
</head>
<body>
<div id="redoc" data-openapi-url="{OPENAPI_PATH}"></div>
<script src="{REDOC_JS.url}" integrity="{REDOC_JS.integrity}" crossorigin="anonymous"></script>
<script src="{REDOC_INIT_PATH}"></script>
</body>
</html>
"""

#: Starts Swagger UI on the page's OpenAPI document; no validator badge (it would ask a third party).
_SWAGGER_INIT = """(function () {
    var root = document.getElementById('swagger-ui');
    window.ui = SwaggerUIBundle({
        url: root.getAttribute('data-openapi-url'),
        dom_id: '#swagger-ui',
        validatorUrl: null,
        deepLinking: true,
        layout: 'BaseLayout',
        presets: [SwaggerUIBundle.presets.apis],
    });
})();
"""

#: Starts ReDoc on the page's OpenAPI document.
_REDOC_INIT = """(function () {
    var root = document.getElementById('redoc');
    Redoc.init(root.getAttribute('data-openapi-url'), {}, root);
})();
"""

_SCRIPT_MEDIA_TYPE = "text/javascript"


def swagger_page() -> HTMLResponse:
    """Swagger UI over this instance's OpenAPI document."""
    return HTMLResponse(_SWAGGER_PAGE)


def redoc_page() -> HTMLResponse:
    """ReDoc over this instance's OpenAPI document."""
    return HTMLResponse(_REDOC_PAGE)


def swagger_init() -> Response:
    """The start script of the Swagger UI page."""
    return Response(_SWAGGER_INIT, media_type=_SCRIPT_MEDIA_TYPE)


def redoc_init() -> Response:
    """The start script of the ReDoc page."""
    return Response(_REDOC_INIT, media_type=_SCRIPT_MEDIA_TYPE)


def install_api_docs(app: FastAPI, *, enabled: bool) -> None:
    """Register the two documentation pages and their start scripts on ``app`` when ``enabled``; nothing otherwise."""
    if not enabled:
        return
    app.get(DOCS_PATH, include_in_schema=False, response_class=HTMLResponse)(swagger_page)
    app.get(REDOC_PATH, include_in_schema=False, response_class=HTMLResponse)(redoc_page)
    app.get(SWAGGER_INIT_PATH, include_in_schema=False)(swagger_init)
    app.get(REDOC_INIT_PATH, include_in_schema=False)(redoc_init)
