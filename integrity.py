"""Verify security-sensitive bundled game assets before startup."""

from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path


class AssetIntegrityError(RuntimeError):
    """Raised when a packaged asset is absent, unexpected or modified."""


def _safe_asset_path(asset_root: Path, relative_name: str) -> Path:
    relative_path = Path(relative_name)
    if (
        not relative_name
        or relative_path.is_absolute()
        or ".." in relative_path.parts
        or relative_path.as_posix() != relative_name
    ):
        raise AssetIntegrityError("Invalid asset path.")
    candidate = (asset_root / relative_path).resolve()
    try:
        candidate.relative_to(asset_root)
    except ValueError as exc:
        raise AssetIntegrityError("Asset path escapes the package.") from exc
    return candidate


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_bundled_assets(asset_directory: str | Path) -> None:
    """Validate every asset listed in the deterministic SHA-256 manifest."""
    asset_root = Path(asset_directory).resolve()
    manifest_path = asset_root / "manifest.json"
    try:
        raw_manifest = manifest_path.read_text(encoding="utf-8")
        manifest = json.loads(raw_manifest)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AssetIntegrityError("Asset manifest could not be read.") from exc

    if (
        not isinstance(manifest, dict)
        or manifest.get("schema") != 1
        or manifest.get("algorithm") != "sha256"
        or not isinstance(manifest.get("assets"), dict)
    ):
        raise AssetIntegrityError("Invalid asset manifest schema.")

    assets = manifest["assets"]
    if not 1 <= len(assets) <= 64:
        raise AssetIntegrityError("Unexpected asset manifest length.")

    for relative_name, expected in assets.items():
        if not isinstance(relative_name, str) or not isinstance(expected, dict):
            raise AssetIntegrityError("Invalid asset record.")
        size = expected.get("size")
        digest = expected.get("sha256")
        if (
            not isinstance(size, int)
            or size < 0
            or not isinstance(digest, str)
            or len(digest) != 64
        ):
            raise AssetIntegrityError("Invalid asset digest.")
        path = _safe_asset_path(asset_root, relative_name)
        try:
            actual_size = path.stat().st_size
        except OSError as exc:
            raise AssetIntegrityError(f"Missing asset: {relative_name}") from exc
        if actual_size != size or not hmac.compare_digest(_sha256(path), digest):
            raise AssetIntegrityError(f"Modified asset: {relative_name}")
