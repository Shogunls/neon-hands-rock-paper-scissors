import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from integrity import AssetIntegrityError, verify_bundled_assets


class IntegrityTests(unittest.TestCase):
    def make_assets(self, relative_name="sound.wav", data=b"safe"):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        path = root / relative_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        manifest = {
            "schema": 1,
            "algorithm": "sha256",
            "assets": {
                relative_name: {
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            },
        }
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return temporary, root, path

    def test_valid_asset(self):
        temporary, root, _ = self.make_assets()
        self.addCleanup(temporary.cleanup)
        verify_bundled_assets(root)

    def test_detects_tampering(self):
        temporary, root, path = self.make_assets()
        self.addCleanup(temporary.cleanup)
        path.write_bytes(b"evil")
        with self.assertRaises(AssetIntegrityError):
            verify_bundled_assets(root)

    def test_rejects_parent_traversal(self):
        temporary, root, _ = self.make_assets()
        self.addCleanup(temporary.cleanup)
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        manifest["assets"] = {"../escape": {"size": 0, "sha256": "0" * 64}}
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(AssetIntegrityError):
            verify_bundled_assets(root)


if __name__ == "__main__":
    unittest.main()
