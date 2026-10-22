"""The file routes refuse to be loaded as a script (lot H-55 v2, security review of a1f1cc5fb).

Owner: workstream H (platform). The Content-Security-Policy allows the scripts of the instance's own origin
(``script-src 'self'``), and an uploaded file is served from that origin. A page that could put
``<script src="/api/v1/import/files/<id>/download">`` somewhere (a document opened from the instance, a ``srcdoc``) would
run it with the user's rights if the file were served as JavaScript. The downloads already go out as
``application/octet-stream`` with ``nosniff`` (a browser refuses to run that type); this dependency is the second
lock: a request the browser makes for a script, a worker or a worklet (``Sec-Fetch-Dest``) is refused before the file
is read.
"""

from fastapi import HTTPException, Request, status

#: The destinations of a request whose answer the browser would run as code.
SCRIPT_DESTINATIONS = frozenset({"script", "worker", "sharedworker", "serviceworker", "audioworklet", "paintworklet"})
NOT_A_SCRIPT_CODE = "file_not_a_script"


def refuse_script_destination(request: Request) -> None:
    """403 ``file_not_a_script`` for a request the browser makes to run its answer as code; anything else passes."""
    destination = request.headers.get("sec-fetch-dest", "").strip().lower()
    if destination in SCRIPT_DESTINATIONS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": NOT_A_SCRIPT_CODE, "message": "A file of this instance is never served as a script"})
