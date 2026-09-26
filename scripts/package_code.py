"""Create a code-only handoff with the small fixtures required by unit tests."""

from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / "dist"
out.mkdir(exist_ok=True)
files = []
for p in ROOT.rglob("*"):
    if not p.is_file() or any(
        x in p.relative_to(ROOT).parts
        for x in [".venv", "__pycache__", ".ruff_cache", "dist", "before", "smoke", "unpacked"]
    ):
        continue
    relative = p.relative_to(ROOT)
    if p.suffix in {".py", ".sh", ".md", ".toml"} or p.name in {
        "requirements.txt",
        "requirements-dev.txt",
        ".gitignore",
    }:
        files.append(p)
for p in (ROOT / "validation").glob("*.txt"):
    if not p.name.endswith("-before.txt"):
        files.append(p)
for name in [
    "validation/report.json",
    "validation/reproduction.json",
    "prototype/viewer.html",
    "prototype/upload.html",
    "prototype/vision/annotations/calibration.json",
    "prototype/vision/frames/00750.jpg",
    "prototype/vision/frames/06495.jpg",
]:
    files.append(ROOT / name)
with zipfile.ZipFile(out / "curling-code.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for p in sorted(set(files)):
        archive.write(p, str(Path("curling-project") / p.relative_to(ROOT)))
print(
    f"{out / 'curling-code.zip'}: {len(set(files))} files, {(out / 'curling-code.zip').stat().st_size / 1e6:.2f} MB"
)
