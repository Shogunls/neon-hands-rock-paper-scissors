"""Create clean GitHub and Google Play hand-off folders and ZIP files."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.0"

TOP_LEVEL_FILES = (
    ".gitattributes",
    ".gitignore",
    "ASSET_SOURCES.md",
    "AUDIO_SOURCES.md",
    "buildozer.spec",
    "CHANGELOG.md",
    "game_logic.py",
    "integrity.py",
    "LICENSE",
    "main.py",
    "pyproject.toml",
    "README.md",
    "requirements-dev.txt",
    "requirements.txt",
    "SECURITY-REPORT.txt",
    "SECURITY.md",
)
RUNTIME_ASSETS = (
    "computer-glove-3d-sheet-v2.png",
    "icon.png",
    "manifest.json",
    "player-glove-3d-sheet-v2.png",
    "presplash.png",
)
SOURCE_ART_ASSETS = ("app-icon-source.png", "icon-1024.png", "neon-hands.ico")


def copy_file(relative_name: str, destination: Path) -> None:
    source = PROJECT_ROOT / relative_name
    target = destination / relative_name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def copy_tree(relative_name: str, destination: Path) -> None:
    shutil.copytree(
        PROJECT_ROOT / relative_name,
        destination / relative_name,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".ruff_cache"),
    )


def copy_runtime_assets(destination: Path, include_sources: bool) -> None:
    for name in RUNTIME_ASSETS + (SOURCE_ART_ASSETS if include_sources else ()):
        copy_file(f"assets/{name}", destination)
    copy_tree("assets/audio", destination)


def make_zip(folder: Path, output: Path) -> None:
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(folder.parent).as_posix())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output_root = args.output.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    github = output_root / f"NeonHands-GitHub-{VERSION}"
    play = output_root / f"NeonHands-PlayStore-{VERSION}"
    github_zip = output_root / f"NeonHands-GitHub-{VERSION}.zip"
    play_zip = output_root / f"NeonHands-PlayStore-{VERSION}.zip"
    targets = (github, play, github_zip, play_zip)
    existing = [str(path) for path in targets if path.exists()]
    if existing:
        raise SystemExit(
            "Output already exists; nothing overwritten: " + ", ".join(existing)
        )

    github.mkdir()
    for name in TOP_LEVEL_FILES:
        copy_file(name, github)
    for name in (".github", "store-assets", "tests", "tools"):
        copy_tree(name, github)
    copy_file("docs/SECURITY_AUDIT.md", github)
    for screenshot in ("main-menu.png", "choice-screen.png"):
        copy_file(f"docs/screenshots/{screenshot}", github)
    copy_runtime_assets(github, include_sources=True)

    android = play / "android-source"
    listing = play / "store-listing"
    guide = play / "release-guide"
    android.mkdir(parents=True)
    listing.mkdir(parents=True)
    guide.mkdir(parents=True)
    for name in (
        "buildozer.spec",
        "game_logic.py",
        "integrity.py",
        "LICENSE",
        "main.py",
        "requirements.txt",
    ):
        copy_file(name, android)
    copy_runtime_assets(android, include_sources=False)
    for path in (PROJECT_ROOT / "store-assets").iterdir():
        if path.is_file():
            shutil.copy2(path, listing / path.name)
    shutil.copy2(PROJECT_ROOT / "PLAY-STORE-PACKAGE.md", play / "README-FIRST.md")
    shutil.copy2(PROJECT_ROOT / "docs" / "PLAY_STORE_RELEASE.md", guide)
    shutil.copy2(PROJECT_ROOT / "docs" / "SECURITY_AUDIT.md", guide)
    shutil.copy2(PROJECT_ROOT / "SECURITY-REPORT.txt", guide)

    make_zip(github, github_zip)
    make_zip(play, play_zip)
    checksum = output_root / f"NeonHands-{VERSION}-SHA256SUMS.txt"
    checksum.write_text(
        "\n".join(f"{sha256(path)}  {path.name}" for path in (github_zip, play_zip))
        + "\n",
        encoding="ascii",
    )
    print(github)
    print(play)
    print(github_zip)
    print(play_zip)
    print(checksum)


if __name__ == "__main__":
    main()
