"""
Which stored types a browser may display in place (H-44, H6-2).

One list for every route that serves a file the user uploaded: the uploads (`api/v1/uploads.py`) and the broker
reports (`api/v1/brokers.py`). HTML, SVG, XML and every other type are always served as a download: a type that can
carry active content is never shown on the app's own address.
"""

INLINE_SAFE_MEDIA_TYPES = frozenset(
    {
        "application/pdf",
        "application/json",
        "text/plain",
        "text/csv",
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/webp",
        "image/bmp",
    }
)
