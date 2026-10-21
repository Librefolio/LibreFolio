"""
LibreFolio FastAPI application.
Main entry point for the backend API: the app, its middleware and its routes.

Startup and shutdown live in ``services/platform/app_lifespan.py``, the middleware stack in
``services/platform/middleware.py``, the web app and the documentation in ``services/platform/static_site.py``.
"""

import warnings

# Suppress pycountry warnings about duplicate currency names (leone, bolívar soberano)
# These are ISO 4217 duplicates (old SLL + new SLE, old VEF + new VES) — harmless.
warnings.filterwarnings("ignore", message=".*already taken in index.*")

from fastapi import FastAPI

from backend.app.api.response_validation import install_response_validation_handler
from backend.app.api.server_errors import install_server_error_handler
from backend.app.api.v1.router import router as api_v1_router
from backend.app.api.validation_errors import install_validation_error_handler
from backend.app.config import (
    API_V1_PREFIX,
    PROJECT_NAME,
    get_settings,
    get_version,
    is_test_mode,
    set_test_mode,
)
from backend.app.logging_config import configure_logging
from backend.app.services.platform.app_lifespan import lifespan
from backend.app.services.platform.middleware import install_middleware
from backend.app.services.platform.static_site import install_static_site

# Check for test mode via environment variable ONLY
# NOTE: Do NOT check sys.argv here - it causes issues when this module is imported
# by other scripts (like test_runner). The --test flag is handled by dev.py which
# sets LIBREFOLIO_TEST_MODE env var before starting uvicorn.
if is_test_mode():
    set_test_mode(True)
    print("[LibreFolio] 🧪 Test mode enabled (LIBREFOLIO_TEST_MODE env var)")

# Get settings after test mode is set
settings = get_settings()

# Configure logging with settings
configure_logging(settings.LOG_LEVEL)


# Create FastAPI app
app = FastAPI(
    title=PROJECT_NAME,
    version=get_version(),
    openapi_url=f"{API_V1_PREFIX}/openapi.json",
    docs_url=f"{API_V1_PREFIX}/docs",
    redoc_url=f"{API_V1_PREFIX}/redoc",
    lifespan=lifespan,
)

# Middleware, outermost first: services/platform/middleware.py
install_middleware(app)

# A 422 never sends the request's input back (A-35): api/validation_errors.py
install_validation_error_handler(app)

# A response that breaks its model is logged without its content (H-33): api/response_validation.py
install_response_validation_handler(app)

# A 5xx answers with a request id and the failure's type, and its cause reaches the log once (H-60): api/server_errors.py
install_server_error_handler(app)

# Mount API v1 router
app.include_router(api_v1_router, prefix=API_V1_PREFIX)

# The documentation and the web app, after every API route: the SPA catch-all stays last
install_static_site(app)
