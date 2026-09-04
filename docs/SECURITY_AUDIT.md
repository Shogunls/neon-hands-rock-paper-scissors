# Security Review — Neon Hands 1.0.0

Date: September 3, 2026

## Scope and threat model

Neon Hands is a fully offline, single-player game. It has no account system, server, WebView, advertising SDK, analytics, purchases, file picker, camera, microphone, location access, or user-generated content. Its meaningful risks are dependency compromise, accidental Android permissions, leaked signing material, modified assets, repackaging, and malformed local settings.

The review follows the relevant [OWASP MASVS](https://mas.owasp.org/MASVS/) categories and Android's [security checklist](https://developer.android.com/privacy-and-security/security-tips).

## Implemented controls

- Runtime code contains no network client, socket, subprocess, shell, `eval`, `exec`, pickle, or dynamic-import facility.
- The Android permission list is empty, backup is disabled, and private application storage is used.
- Saved volume values are type-checked, required to be finite, and clamped to `0..1`.
- Game moves are validated against a fixed allowlist and all nine outcomes are tested.
- Runtime sprite and audio assets are checked for size and SHA-256 digest at startup; manifest path traversal is rejected.
- Kivy is pinned. CI runs pip-audit, Bandit, Ruff, and a custom AST/secret scan. CodeQL activates when GitHub Code Scanning is available (public repositories or private repositories with GitHub Advanced Security).
- GitHub Actions dependencies are pinned to commit hashes and monitored by Dependabot.
- Keystores, certificates, environment secrets, APKs, and AABs are excluded from Git.
- The Android build configuration is pinned to API 36, NDK 28c, ARM64/ARMv7, and AAB output.

## Verification result

Python compilation, five unit tests, the project policy scanner, Ruff, Bandit, pip-audit, and a desktop startup smoke test passed. Results are recorded in `SECURITY-REPORT.txt`.

An Android binary was not produced in the Windows-only review environment and therefore no binary scan is claimed. Every final signed AAB must pass:

1. Static analysis in a trusted [MobSF](https://mobsf.org/) installation.
2. Google Play closed testing, the automated pre-launch report, and real-device testing.

## Limits

- Client code and bundled resources cannot be made permanently secret from a determined attacker. Obfuscation increases effort but is not a security boundary.
- Asset hashes detect corruption and simple modification, but cannot stop an attacker who rewrites and re-signs the complete app. Play App Signing and official store distribution provide the identity boundary.
- No test can guarantee that software remains vulnerability-free forever. Dependency and binary scans must be repeated for every release.
