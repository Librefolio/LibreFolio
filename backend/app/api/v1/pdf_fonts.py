"""The PDF viewer's CJK fonts, served by the instance: ``GET /files/pdf-fonts/{package}/{file}`` (lot H-55, decision (c)).

Owner: workstream H (platform). The viewer's worker asks for a font here only when a PDF needs it
(``services/files/pdf_fonts.py`` fetches it once from its fixed source, checks its sha256 and keeps it). A signed-in user
only: an anonymous caller must not make the instance fetch tens of megabytes. Out of the OpenAPI schema: the viewer
reads it, never the generated client.
"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import User
from backend.app.services.files import pdf_fonts

router = APIRouter(prefix="/files/pdf-fonts", tags=["Files"])

FONT_MEDIA_TYPE = "font/otf"
#: Private: the answer needs a session. Immutable: a file of the list never changes at the same version.
FONT_CACHE_CONTROL = "private, max-age=31536000, immutable"


@router.get("/{package}/{file}", response_class=FileResponse, include_in_schema=False)
async def get_pdf_font(package: str, file: str, _user: User = Depends(get_current_user)) -> FileResponse:
    """The font ``package``/``file`` of the list, fetched and checked the first time it is asked."""
    if pdf_fonts.font_entry(package, file) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    try:
        path = await asyncio.to_thread(pdf_fonts.cached_font, package, file)
    except pdf_fonts.PdfFontUnknown:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found") from None
    except pdf_fonts.PdfFontUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"code": "pdf_font_unavailable", "message": "The font cannot be fetched now"}) from exc
    except pdf_fonts.PdfFontMismatch as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail={"code": "pdf_font_mismatch", "message": "The font from the source is not the expected file"}) from exc
    return FileResponse(path, media_type=FONT_MEDIA_TYPE, headers={"Cache-Control": FONT_CACHE_CONTROL})
