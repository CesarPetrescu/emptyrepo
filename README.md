# Roblox Asset Forge — Neon Salvage

A reproducible Blender asset pipeline and interactive browser gallery for a six-prop Roblox science-fiction starter pack.

## Generated assets

- NX-4 Cargo Crate
- Flux Energy Barrel
- Aegis Security Gate
- Cryon Crystal Node
- Pathfinder Beacon
- Warden Hover Drone

Every asset is exported as **GLB** and **FBX**, rendered to a preview image, measured in Roblox studs, and included in a downloadable Blender source pack.

## Viewer

- Live immutable mirror: `https://rawcdn.githack.com/CesarPetrescu/emptyrepo/eae6ce24fd7d230e3fed6e8acf21463409273dcf/dist/index.html`
- Development mirror: `https://raw.githack.com/CesarPetrescu/emptyrepo/main/dist/index.html`
- Optional GitHub Pages URL after enabling **Settings → Pages → GitHub Actions**: `https://cesarpetrescu.github.io/emptyrepo/`

## Rebuild

The GitHub Actions workflow downloads and verifies Blender 5.2.1 against Blender's official checksum manifest, runs `blender/generate_assets.py` headlessly, validates all outputs, creates a ZIP bundle, commits the generated `dist/` directory, and prepares a GitHub Pages deployment artifact.

```bash
ASSET_OUT="$PWD/dist" blender --background --factory-startup --python blender/generate_assets.py
```

The geometry is original and generated entirely from Blender primitives and Python-authored meshes. Pack contents are released under CC0-1.0.
