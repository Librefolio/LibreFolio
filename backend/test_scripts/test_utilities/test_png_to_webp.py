"""``scripts/docker/png_to_webp.py``: the Docker stage that turns the default avatars into WebP (lane 84).

The image carries the 30 default avatars as WebP (quality 85, about a tenth of the PNG weight) while the repository keeps
the full-size PNG. The ``avatars-webp`` stage runs this script on a copy of the folder. It makes three promises:

* a folder of PNG becomes the same names as WebP and the PNG are gone, so none reaches the image;
* a PNG that cannot be converted, an empty folder and a missing folder fail the build (exit 1), never a silent success
  that ships an image without avatars; the PNG that could not be converted is left where it was;
* run as a script, the way the Dockerfile runs it, it finds its converter (``scripts/gallery_webp.py``) and prints a count.

PURE: every folder lives in ``tmp_path``; Pillow only. No DB, no server, no network.
"""

import subprocess
import sys
from pathlib import Path

from PIL import Image

from backend.app.config import PROJECT_ROOT
from scripts.docker.png_to_webp import convert_folder, main
from scripts.gallery_webp import WEBP_QUALITY


def make_png(path: Path, mode: str = "RGB", size: tuple[int, int] = (64, 48)) -> Path:
    colour = {"RGB": (30, 120, 200), "RGBA": (30, 120, 200, 128), "P": 3}[mode]
    Image.new(mode, size, colour).save(path, format="PNG")
    return path


def test_pngs_become_webp_under_the_same_names_and_are_deleted(tmp_path):
    for name in ("men_01", "woman_01"):
        make_png(tmp_path / f"{name}.png")

    assert convert_folder(tmp_path) == []

    assert sorted(p.name for p in tmp_path.iterdir()) == ["men_01.webp", "woman_01.webp"]
    with Image.open(tmp_path / "men_01.webp") as image:
        assert image.format == "WEBP" and image.size == (64, 48)


def test_alpha_is_kept(tmp_path):
    make_png(tmp_path / "a.png", "RGBA")

    assert convert_folder(tmp_path) == []

    with Image.open(tmp_path / "a.webp") as image:
        assert image.mode == "RGBA"


def test_a_broken_png_fails_the_run_and_stays_in_place(tmp_path):
    make_png(tmp_path / "good.png")
    (tmp_path / "broken.png").write_bytes(b"\x89PNG\r\n\x1a\n not an image")

    problems = convert_folder(tmp_path)

    assert len(problems) == 1 and problems[0].startswith("broken.png:")
    assert (tmp_path / "good.webp").is_file() and not (tmp_path / "good.png").exists()
    assert (tmp_path / "broken.png").is_file() and not (tmp_path / "broken.webp").exists()
    assert not list(tmp_path.glob("*.tmp"))


def test_an_empty_or_missing_folder_is_a_problem(tmp_path):
    assert "holds no PNG" in convert_folder(tmp_path)[0]
    assert "is not a folder" in convert_folder(tmp_path / "absent")[0]


def test_only_the_png_directly_inside_are_converted(tmp_path):
    make_png(tmp_path / "top.png")
    (tmp_path / "sub").mkdir()
    make_png(tmp_path / "sub" / "deep.png")
    (tmp_path / "note.txt").write_text("keep")

    assert convert_folder(tmp_path) == []

    assert (tmp_path / "sub" / "deep.png").is_file() and (tmp_path / "note.txt").is_file()


def test_the_quality_defaults_to_the_gallerys_and_can_be_given(tmp_path):
    assert WEBP_QUALITY == 85  # the image's avatars and the gallery's screenshots share one setting
    sizes = {}
    for quality in (None, 20):
        folder = tmp_path / str(quality)
        folder.mkdir()
        noisy = Image.effect_noise((256, 256), 80).convert("RGB")
        noisy.save(folder / "a.png")
        assert main(["png_to_webp.py", str(folder)] + ([] if quality is None else [str(quality)])) == 0
        sizes[quality] = (folder / "a.webp").stat().st_size

    assert sizes[20] < sizes[None]


def test_run_as_a_script_like_the_dockerfile_does(tmp_path):
    make_png(tmp_path / "men_01.png")

    result = subprocess.run([sys.executable, "-I", str(PROJECT_ROOT / "scripts" / "docker" / "png_to_webp.py"), str(tmp_path)], capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr
    assert "1 PNG converted to WebP (quality 85)" in result.stdout
    assert [p.name for p in tmp_path.iterdir()] == ["men_01.webp"]


def test_the_script_exits_1_on_a_problem_and_2_on_a_bad_call(tmp_path):
    script = str(PROJECT_ROOT / "scripts" / "docker" / "png_to_webp.py")

    empty = subprocess.run([sys.executable, "-I", script, str(tmp_path)], capture_output=True, text=True, check=False)
    bad_call = subprocess.run([sys.executable, "-I", script], capture_output=True, text=True, check=False)

    assert empty.returncode == 1 and "holds no PNG" in empty.stderr
    assert bad_call.returncode == 2
