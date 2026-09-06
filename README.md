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

After the first workflow completes:

- GitHub Pages: `https://cesarpetrescu.github.io/emptyrepo/`
- Immediate static preview: `https://raw.githack.com/CesarPetrescu/emptyrepo/main/dist/index.html`

## Rebuild

The GitHub Actions workflow downloads and verifies Blender 5.2.1, runs `blender/generate_assets.py` headlessly, validates all outputs, creates a ZIP bundle, commits the generated `dist/` directory, and attempts a GitHub Pages deployment.

```bash
ASSET_OUT="$PWD/dist" blender --background --factory-startup --python blender/generate_assets.py
```

The geometry is original and generated entirely from Blender primitives and Python-authored meshes. Pack contents are released under CC0-1.0.
