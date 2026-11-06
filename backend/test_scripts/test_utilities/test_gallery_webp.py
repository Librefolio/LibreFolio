"""WebP copies of the documentation gallery, ``scripts/gallery_webp.py`` (E8).

``./dev.py mkdocs gallery`` writes PNG and converts them to WebP when it ends. The
conversion has three promises:

* it converts only what needs it: a PNG with no WebP, or newer than its WebP, so a
  partial run converts its own shots and a second run does no work at all;
* a PNG that cannot be read is reported and stops nothing: the others are converted,
  and the broken one leaves neither a WebP nor a temporary file;
* ``dev.py`` runs it at the end of the gallery whether or not the Playwright run failed,
  and counts a PNG that could not be converted as a failure of the command.

PURE: every tree lives in ``tmp_path``; Pillow only. No DB, no server, no network.
"""

import os
from pathlib import Path

import pytest
from PIL import Image

import dev
from scripts.gallery_webp import WEBP_QUALITY, convert_gallery_webp, needs_conversion, webp_path


def make_png(path: Path, mode: str = "RGB", size: tuple[int, int] = (64, 48)) -> Path:
    """A small PNG with some structure, in the given mode."""
    path.parent.mkdir(parents=True, exist_ok=True)
    colour = {"RGB": (30, 120, 200), "RGBA": (30, 120, 200, 128), "L": 90, "P": 3}[mode]
    image = Image.new(mode, size, colour)
    image.save(path, format="PNG")
    return path


def make_tree(root: Path) -> list[Path]:
    """Three shots in the gallery's layout, of three PNG modes."""
    return [
        make_png(root / "desktop" / "en" / "light" / "dashboard" / "main.png", "RGB"),
        make_png(root / "desktop" / "it" / "dark" / "assets" / "list.png", "RGBA"),
        make_png(root / "mobile" / "en" / "light" / "fx" / "pair.png", "P"),
    ]


def test_converts_every_png_beside_itself(tmp_path):
    pngs = make_tree(tmp_path)

    report = convert_gallery_webp(tmp_path, workers=1)

    assert (report.converted, report.up_to_date, report.failed) == (3, 0, [])
    for png in pngs:
        webp = webp_path(png)
        assert webp.parent == png.parent and webp.name == png.stem + ".webp"
        with Image.open(webp) as converted, Image.open(png) as original:
            assert converted.format == "WEBP"
            assert converted.size == original.size
    # The PNGs stay: the gallery's readers and the already released images use them.
    assert all(png.exists() for png in pngs)


def test_alpha_is_kept_and_other_modes_become_rgb(tmp_path):
    rgba = make_png(tmp_path / "a.png", "RGBA")
    palette = make_png(tmp_path / "b.png", "P")

    convert_gallery_webp(tmp_path, workers=1)

    with Image.open(webp_path(rgba)) as image:
        assert image.mode == "RGBA"
    with Image.open(webp_path(palette)) as image:
        assert image.mode == "RGB"


def test_parallel_conversion_gives_the_same_result(tmp_path):
    for index in range(6):
        make_png(tmp_path / "shots" / f"shot{index}.png")

    report = convert_gallery_webp(tmp_path, workers=3)

    assert (report.converted, report.failed) == (6, [])
    assert len(list(tmp_path.rglob("*.webp"))) == 6


def test_a_second_run_does_no_work(tmp_path):
    pngs = make_tree(tmp_path)
    convert_gallery_webp(tmp_path, workers=1)
    before = {webp_path(png): webp_path(png).stat().st_mtime_ns for png in pngs}

    report = convert_gallery_webp(tmp_path, workers=1)

    assert (report.converted, report.up_to_date, report.failed) == (0, 3, [])
    assert {webp: webp.stat().st_mtime_ns for webp in before} == before


def test_only_the_new_shots_are_converted(tmp_path):
    make_tree(tmp_path)
    convert_gallery_webp(tmp_path, workers=1)
    new = make_png(tmp_path / "desktop" / "en" / "light" / "risk" / "lab.png")

    report = convert_gallery_webp(tmp_path, workers=1)

    assert (report.converted, report.up_to_date) == (1, 3)
    assert webp_path(new).exists()


def test_a_png_newer_than_its_webp_is_converted_again(tmp_path):
    png = make_png(tmp_path / "shot.png", "RGB")
    convert_gallery_webp(tmp_path, workers=1)
    webp = webp_path(png)
    old = webp.stat().st_mtime_ns
    # The gallery wrote the shot again: same name, newer file, another picture.
    make_png(png, "RGB", size=(80, 60))
    os.utime(png, ns=(old + 5_000_000_000, old + 5_000_000_000))
    assert needs_conversion(png)

    report = convert_gallery_webp(tmp_path, workers=1)

    assert (report.converted, report.up_to_date) == (1, 0)
    with Image.open(webp) as image:
        assert image.size == (80, 60)


def test_a_webp_newer_than_its_png_is_left_alone(tmp_path):
    png = make_png(tmp_path / "shot.png")
    webp = webp_path(png)
    webp.write_bytes(b"kept as it is")
    os.utime(webp, ns=(png.stat().st_mtime_ns + 5_000_000_000,) * 2)

    report = convert_gallery_webp(tmp_path, workers=1)

    assert (report.converted, report.up_to_date) == (0, 1)
    assert webp.read_bytes() == b"kept as it is"


@pytest.mark.parametrize("workers", [1, 2])
def test_a_broken_png_is_reported_and_stops_nothing(tmp_path, workers):
    good = [make_png(tmp_path / "good" / f"{name}.png") for name in ("a", "b", "c")]
    broken = tmp_path / "bad" / "broken.png"
    broken.parent.mkdir()
    broken.write_bytes(b"\x89PNG\r\n\x1a\n this is not a picture")
    truncated = make_png(tmp_path / "bad" / "cut.png", size=(300, 300))
    truncated.write_bytes(truncated.read_bytes()[:60])

    report = convert_gallery_webp(tmp_path, workers=workers)

    assert report.converted == 3
    assert sorted(path.name for path, _ in report.failed) == ["broken.png", "cut.png"]
    assert all(reason for _, reason in report.failed)
    assert all(webp_path(png).exists() for png in good)
    # The broken ones leave nothing behind: no WebP that looks done, no half-written file.
    assert not webp_path(broken).exists() and not webp_path(truncated).exists()
    assert not list(tmp_path.rglob("*.tmp"))
    # And they are tried again at the next run, not taken for converted.
    again = convert_gallery_webp(tmp_path, workers=1)
    assert (again.converted, again.up_to_date, len(again.failed)) == (0, 3, 2)


def test_an_empty_gallery_is_not_an_error(tmp_path):
    report = convert_gallery_webp(tmp_path / "nothing-here", workers=1)

    assert (report.converted, report.up_to_date, report.failed) == (0, 0, [])


def test_quality_is_85():
    assert WEBP_QUALITY == 85


# ---------------------------------------------------------------------------
# dev.py: the step at the end of `mkdocs gallery`
# ---------------------------------------------------------------------------


def test_dev_step_counts_the_pngs_it_could_not_convert(tmp_path, monkeypatch, capsys):
    gallery = tmp_path / "mkdocs_src" / "docs" / "gallery"
    make_png(gallery / "desktop" / "en" / "light" / "ok" / "shot.png")
    broken = gallery / "desktop" / "en" / "light" / "ko" / "bad.png"
    broken.parent.mkdir(parents=True)
    broken.write_bytes(b"not a png")
    monkeypatch.setattr(dev, "PROJECT_ROOT", tmp_path)

    failed = dev._convert_gallery_webp()

    out = capsys.readouterr().out
    assert failed == 1
    assert "1 converted" in out and "bad.png" in out
    assert (gallery / "desktop" / "en" / "light" / "ok" / "shot.webp").exists()
