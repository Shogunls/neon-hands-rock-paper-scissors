[app]

title = Neon Hands
package.name = rps
package.domain = com.neonhands

source.dir = .
source.include_exts = py,png,wav,json
source.include_patterns = assets/*,assets/audio/*
source.exclude_dirs = .git,.github,.venv,.vscode,.buildozer,bin,build,dist,docs,store-assets,tests,tools,__pycache__
source.exclude_patterns = assets/app-icon-source.png,assets/icon-1024.png,assets/reference-hand-cc0.png

version = 1.0.0
requirements = python3,kivy==2.3.1

presplash.filename = %(source.dir)s/assets/presplash.png
icon.filename = %(source.dir)s/assets/icon.png
orientation = portrait
fullscreen = 1

android.api = 36
android.minapi = 24
android.ndk = 28c
android.ndk_api = 24
android.permissions =
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = False
android.private_storage = True
android.release_artifact = aab
android.debug_artifact = apk
android.numeric_version = 1
android.accept_sdk_license = True

p4a.branch = v2026.05.09
p4a.commit = 8aba7685beea080d0e34375e6c0e2067a2dcad0a
p4a.bootstrap = sdl2

[buildozer]

log_level = 2
warn_on_root = 1
bin_dir = ./bin
