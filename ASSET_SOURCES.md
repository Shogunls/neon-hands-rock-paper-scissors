# Visual asset sources

## In-game 3D glove atlases

- `assets/player-glove-3d-sheet-v2.png` — rear-facing player glove with teal cuff; rock, paper, and scissors poses.
- `assets/computer-glove-3d-sheet-v2.png` — front-facing computer glove with coral cuff; rock, paper, and scissors poses.
- Production: original transparent RGBA sprite sheets generated for this project with Codex's built-in image generation tool.
- Runtime: `SpriteGloveHand` loads each sheet once and caches its three GPU texture regions.

The atlases contain no third-party brands, logos, or watermarks.

## App icon and store artwork

- Master artwork: `assets/app-icon-source.png`
- Outputs: `assets/icon.png`, `assets/icon-1024.png`, `assets/neon-hands.ico`, `assets/presplash.png`, `store-assets/app-icon-512.png`, and `store-assets/feature-graphic-1024x500.png`
- Production: an original square illustration of a teal rock glove and coral scissors glove meeting at a gold impact spark. Generated without text, watermarks, or third-party branding.
- Resizing and store composition: `tools/prepare_store_assets.py`.

Kivy uses `assets/icon.png` for the desktop window and Android app icon. `assets/neon-hands.ico` is the multi-resolution source for a future Windows executable.

## Early proportion reference

The CC0 “Hands” asset by looneybits on OpenGameArt was reviewed during early proportion studies: https://opengameart.org/content/hands-0

`assets/reference-hand-cc0.png` is excluded from runtime and final release packages. All artwork visible in the finished game is a separate original production.
