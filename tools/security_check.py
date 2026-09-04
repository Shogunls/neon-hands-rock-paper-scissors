"""Fail-fast repository checks for the offline mobile game's threat model."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILES = (
    PROJECT_ROOT / "main.py",
    PROJECT_ROOT / "game_logic.py",
    PROJECT_ROOT / "integrity.py",
)
FORBIDDEN_IMPORTS = {
    "aiohttp",
    "http",
    "marshal",
    "pickle",
    "requests",
    "shelve",
    "socket",
    "subprocess",
    "urllib",
}
FORBIDDEN_CALLS = {"eval", "exec", "compile", "__import__"}
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "Google API key": re.compile(r"AIza[0-9A-Za-z_-]{35}"),
}
TEXT_SUFFIXES = {".py", ".yml", ".yaml", ".spec", ".json", ".md", ".txt"}
KEY_SUFFIXES = {".jks", ".keystore", ".p12", ".pfx", ".pem", ".key"}
SKIP_PARTS = {
    ".git",
    ".venv",
    ".buildozer",
    ".ruff_cache",
    "bin",
    "build",
    "dist",
    "__pycache__",
}


def dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def scan_runtime(path: Path) -> list[str]:
    findings = []
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [item.name.split(".")[0] for item in node.names]
            for name in names:
                if name in FORBIDDEN_IMPORTS:
                    findings.append(
                        f"{path.name}:{node.lineno}: forbidden import {name}"
                    )
        elif isinstance(node, ast.ImportFrom) and node.module:
            name = node.module.split(".")[0]
            if name in FORBIDDEN_IMPORTS:
                findings.append(f"{path.name}:{node.lineno}: forbidden import {name}")
        elif isinstance(node, ast.Call):
            call_name = dotted_name(node.func)
            if call_name in FORBIDDEN_CALLS or call_name == "os.system":
                findings.append(
                    f"{path.name}:{node.lineno}: dangerous call {call_name}"
                )
    return findings


def repository_files():
    for path in PROJECT_ROOT.rglob("*"):
        if path.is_file() and not any(part in SKIP_PARTS for part in path.parts):
            yield path


def check_spec() -> list[str]:
    path = PROJECT_ROOT / "buildozer.spec"
    if not path.is_file():
        return ["buildozer.spec eksik"]
    text = path.read_text(encoding="utf-8")
    required = {
        "Android API 36": r"(?m)^android\.api\s*=\s*36\s*$",
        "NDK 28c": r"(?m)^android\.ndk\s*=\s*28c\s*$",
        "backup disabled": r"(?m)^android\.allow_backup\s*=\s*False\s*$",
        "AAB output": r"(?m)^android\.release_artifact\s*=\s*aab\s*$",
        "empty permission list": r"(?m)^android\.permissions\s*=\s*$",
    }
    return [
        f"buildozer.spec: missing {label} setting"
        for label, pattern in required.items()
        if not re.search(pattern, text)
    ]


def main() -> int:
    findings = []
    for path in RUNTIME_FILES:
        findings.extend(scan_runtime(path))

    own_path = Path(__file__).resolve()
    for path in repository_files():
        if path.suffix.lower() in KEY_SUFFIXES:
            findings.append(
                f"Signing/private key in repository: {path.relative_to(PROJECT_ROOT)}"
            )
        if path.resolve() == own_path or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            contents = path.read_text(encoding="utf-8")
        except UnicodeError:
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(contents):
                findings.append(f"Possible {label}: {path.relative_to(PROJECT_ROOT)}")

    findings.extend(check_spec())
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from integrity import verify_bundled_assets

        verify_bundled_assets(PROJECT_ROOT / "assets")
    except Exception as exc:  # noqa: BLE001 - a failing verifier must fail CI.
        findings.append(f"Asset integrity: {exc}")

    if findings:
        print("SECURITY CHECK: FAILED")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("SECURITY CHECK: PASSED")
    print("- Runtime has no network, subprocess, or dynamic-code execution APIs.")
    print("- No known secret or private-key patterns found in the repository.")
    print("- Android permissions are empty; backup is off; AAB/API/NDK are pinned.")
    print("- SHA-256 integrity of packaged runtime assets verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
