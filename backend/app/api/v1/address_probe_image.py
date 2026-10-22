"""The address probe as an image (lot H-55 v2): ``GET /auth/address-probe.png``, readable from any origin.

Owner: workstream H (platform), for workstream A's address check (``settings/users/addressProbe.ts``, reused by E's
``emailLinks.ts``). An administrator's browser asks its own instance for a signed nonce (``POST /users/address-probe``)
and checks that this very instance answers at another address. The JSON probe (``GET /auth/address-probe``,
``auth.py``) needs a ``fetch`` to that other origin, which the enforced ``connect-src`` of the web app's pages blocks;
an image is not held back (``img-src`` is not enforced), and the browser reads its ``naturalWidth`` from any origin
without CORS. So the answer is a PNG: **1×1** when this instance issued the nonce, **2×1** for anything else (forged, of
another instance, expired, empty, missing), with the same status and type either way. Nothing else is in it.

Public, like the JSON probe, and outside the routes that answer on a blocked instance (decision A6a): there it gets
the 401 of a public route, which the browser reads as «cannot verify». A module of its own, so that ``auth.py`` stays
workstream E's to change. Sync: deriving the key reads the instance key file.
"""

import struct
import zlib

from fastapi import APIRouter, Response

from backend.app.services.accounts import address_probe

router = APIRouter(prefix="/auth", tags=["Auth"])

PROBE_MEDIA_TYPE = "image/png"


def _png(width: int, height: int) -> bytes:
    """A transparent RGBA PNG of ``width`` × ``height`` pixels, built once at import."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    rows = b"".join(b"\x00" + b"\x00\x00\x00\x00" * width for _ in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b"")


#: The answer for a nonce this instance issued, and for anything else: only the width tells them apart.
MATCH_IMAGE = _png(1, 1)
MISMATCH_IMAGE = _png(2, 1)


# Out of the OpenAPI schema: an <img> reads it, never the generated client, which would only grow by one more alias (its
# zodiosApi type already sits at TypeScript's instantiation depth in a spyOn of ForgotPasswordCard.email.test.ts)
@router.get("/address-probe.png", response_class=Response, include_in_schema=False)
def answer_address_probe_image(nonce: str = "") -> Response:
    """Whether this instance issued ``nonce`` (``POST /users/address-probe``), as the width of a PNG: 1 yes, 2 no."""
    image = MATCH_IMAGE if address_probe.verify_probe_nonce(nonce) else MISMATCH_IMAGE
    return Response(content=image, media_type=PROBE_MEDIA_TYPE, headers={"Cache-Control": "no-store"})
