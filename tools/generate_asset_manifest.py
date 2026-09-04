"""Generate the deterministic runtime asset integrity manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = PROJECT_ROOT / "assets"
RUNTIME_ASSETS = (
    "computer-glove-3d-sheet-v2.png",
    "player-glove-3d-sheet-v2.png",
    "audio/battle_loop.wav",
    "audio/defeat_sting.wav",
    "audio/hand_whoosh.wav",
    "audio/reveal_swish.wav",
    "audio/soft_click.wav",
    "audio/soft_loop.wav",
    "audio/victory_fanfare.wav",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    assets = {}
    for relative_name in sorted(RUNTIME_ASSETS):
        path = ASSET_ROOT / relative_name
        if not path.is_file():
            raise SystemExit(f"Missing runtime asset: {relative_name}")
        assets[relative_name] = {
            "sha256": sha256(path),
            "size": path.stat().st_size,
        }
    manifest = {
        "schema": 1,
        "algorithm": "sha256",
        "assets": assets,
    }
    output = ASSET_ROOT / "manifest.json"
    output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Written: {output}")


if __name__ == "__main__":
    main()
