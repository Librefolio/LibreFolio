"""``_resize_image`` (``GET /uploads/file/{id}?img_preview=WxH``): the preview keeps the format of the file (lane 84-F).

``Image.resize`` returns an image whose ``format`` is ``None``, and the function used to read the format after the resize:
every preview came out as PNG bytes, whatever the file was (a JPEG photo became a PNG several times its size, a WebP avatar a
PNG), still labelled with the file's type. Browsers showed it anyway, so nothing failed; the weight and the lie in the
``Content-Type`` stayed. Pinned here:

* a PNG, JPEG, WebP, GIF, BMP or TIFF preview is written in that format, the new size within the asked box, aspect kept;
* a JPEG that came from a phone (Pillow reads it as ``MPO``) is written as JPEG;
* a source already inside the box is not resized (``None``: the caller serves the file);
* a format Pillow cannot write falls back to PNG, as before.

PURE: images under ``tmp_path``, Pillow only. No DB, no server, no network.
"""

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from backend.app.api.v1.uploads import _resize_image


def make_image(path: Path, fmt: str, size: tuple[int, int] = (400, 200)) -> Path:
    """A gradient (so JPEG and WebP have something to compress) saved in ``fmt``."""
    image = Image.new("RGB", size)
    image.putdata([((x * 255) // size[0], (y * 255) // size[1], 128) for y in range(size[1]) for x in range(size[0])])
    image.save(path, format=fmt)
    return path


def format_of(data: bytes) -> str:
    with Image.open(BytesIO(data)) as image:
        return image.format


@pytest.mark.parametrize(("fmt", "suffix"), [("PNG", ".png"), ("JPEG", ".jpg"), ("WEBP", ".webp"), ("GIF", ".gif"), ("BMP", ".bmp"), ("TIFF", ".tiff")])
def test_the_preview_keeps_the_format_of_the_file(tmp_path, fmt, suffix):
    source = make_image(tmp_path / f"photo{suffix}", fmt)

    data = _resize_image(source, 100, 100)

    assert data is not None
    assert format_of(data) == fmt
    with Image.open(BytesIO(data)) as resized:
        assert resized.size == (100, 50)  # the box is 100x100, the aspect 2:1 is kept


def test_a_phone_jpeg_is_written_as_jpeg(tmp_path):
    """Pillow reads a multi-picture JPEG as ``MPO``: the preview is a plain JPEG, not an MPO and not a PNG."""
    source = tmp_path / "phone.jpg"
    first, second = Image.new("RGB", (400, 200), (200, 10, 10)), Image.new("RGB", (400, 200), (10, 10, 200))
    first.save(source, format="MPO", save_all=True, append_images=[second])  # two pictures in one file, as a phone writes it
    with Image.open(source) as probe:
        assert probe.format == "MPO", "the fixture must be an MPO file for this test to mean anything"

    data = _resize_image(source, 100, 100)

    assert data is not None and format_of(data) == "JPEG"


def test_a_jpeg_preview_is_smaller_than_the_png_it_used_to_be(tmp_path):
    source = make_image(tmp_path / "photo.jpg", "JPEG", (800, 800))

    data = _resize_image(source, 400, 400)

    assert data is not None
    png = BytesIO()
    with Image.open(source) as image:
        image.resize((400, 400)).save(png, format="PNG", optimize=True)
    assert len(data) < len(png.getvalue())


def test_a_source_inside_the_box_is_not_resized(tmp_path):
    source = make_image(tmp_path / "small.webp", "WEBP", (50, 40))

    assert _resize_image(source, 100, 100) is None


def test_a_format_that_cannot_be_written_falls_back_to_png(tmp_path):
    """Formats outside the list the preview writes (here ICO) keep the old behaviour: PNG bytes."""
    source = tmp_path / "icon.ico"
    Image.new("RGB", (256, 128), (10, 20, 30)).save(source, format="ICO", sizes=[(256, 128)])

    data = _resize_image(source, 64, 64)

    assert data is not None and format_of(data) == "PNG"
