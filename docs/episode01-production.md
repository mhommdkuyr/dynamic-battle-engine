# Episode 01 — Shadows & Iron (real FBX production path)

This production path is intended to render the two actual lead characters from the private Drive assets, rather than the older 2.5D stick-figure demo.

## Private assets

Keep character and motion data out of this public repository. Prepare an authorized ZIP whose root contains:

- `nightshade.fbx`
- `prisoner.fbx`
- `mocap/Superhero/WatchOverCity_mixamo.fbx`
- `mocap/Superhero/IronMan_Combat_mixamo.fbx`
- `mocap/Superhero/MutantClaws_mixamo.fbx`
- `mocap/Superhero/SuperHeroLanding_Takeoff_mixamo.fbx`
- `mocap/Superhero/SuperHeroFlying_mixamo.fbx`
- `mocap/Superhero/HulkTransformation_mixamo.fbx`

Set `ANIME_ASSET_DIR` to the directory containing those files. The GitHub Actions path is gated by the repository secret `ANIME_ASSETS_BUNDLE_URL`, an authorized HTTPS URL for that ZIP. The workflow deliberately runs script/unit tests without producing a fake video when the secret is absent.

## Local / CI render

Required software: Blender with FBX import enabled, FFmpeg with `libx264`, `subtitles`, and `minterpolate`, Python 3, NumPy, SciPy, and `edge-tts`.

```bash
pip install -r requirements.txt edge-tts
ANIME_ASSET_DIR=/path/to/private-assets bash scripts/finalize_episode.sh
```

The scene uses the Nightshade and Prisoner skinned FBX models; retimes compatible Mixamo bone channels from the supplied motion clips into Blender NLA tracks; creates a ruined, rain-soaked arena, timed energy slashes, collision sparks, expanding shockwaves, title cards, and a moving camera; renders 1280x720 at 12 fps; synthesizes a 60-second score/SFX bed and Japanese dialogue; then uses FFmpeg motion interpolation and Lanczos scaling to deliver a 1920x1080, 60 fps MP4 with English/Arabic subtitles.

## Important quality note

The render is a textured 3D anime-inspired action short and a reproducible baseline—not a claim that Blender Workbench, interpolation, or 1080p scaling is equivalent to a hand-keyed studio Sakuga sequence. The delivered frame cadence is interpolated from a 12 fps base render; RIFE/Real-ESRGAN and a ComfyUI/CogVideoX stylization pass can be added on an authorized GPU runner when those models and GPU resources are provisioned.

## Open-source motion references

- [Rokoko Studio Live for Blender](https://github.com/Rokoko/rokoko-studio-live-blender) — rig retargeting workflow and source.
- [Rokoko retargeting guide](https://support.rokoko.com/hc/en-us/articles/4410463481489-Retarget-an-animation-in-Blender) — source/target pose and scale guidance.
- [AnimateDiff-Evolved](https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved) — optional frame stylization/motion branch for a GPU-equipped ComfyUI host.
- [CogVideoX wrapper](https://github.com/kijai/ComfyUI-CogVideoXWrapper) — optional image/video generation branch; not required for the deterministic Blender render.

Respect each asset and motion pack's own license and terms before redistribution.
