# Episode 01 — Shadows & Iron

This file documents the reproducible Blender scene setup used for the first 60-second episode.

## Inputs

Place these assets in `ASSET_DIR`:

- `Nightshade J Friedrich.fbx`
- `Prisoner B Styperek.fbx`
- `motion_extracted/Motion_Extracted_Red.bvh`
- `motion_extracted/Motion_Extracted_Black.bvh`

The BVH files are derived pose tracks and may contain unreliable or zero-length joints. The scene retargets a subset of rotations to the Mixamo-style character rigs and layers root-motion blocking and stylized effects.

## Build the scene

Requires Blender 4.x with FBX/BVH import support.

```bash
ASSET_DIR=/path/to/assets OUTPUT_DIR=/path/to/output \
  blender -b --python scripts/render_shadows_and_iron_episode01.py
```

To generate the scene without starting a render, set `SCENE_BUILD=1`. To render one preview frame, set `SCENE_ONLY=1`. The default scene timeline is 480 frames at 8 fps (60 seconds). The production render used chunked CPU rendering to stay within a small-memory headless environment.

## Mastering steps used for delivery

The delivered MP4 was post-processed separately with FFmpeg: denoising, frame interpolation to 24 fps, 1280×720 upscale, H.264 encoding, AAC audio mix, and a selectable Arabic subtitle track. The Arabic SRT and soundtrack WAV were retained as companion files. The source character assets and generated project file are not committed to this repository.

## Output

The uploaded episode is 60 seconds, 1280×720, 24 fps, with 1,440 video frames, stereo AAC audio, and an embedded Arabic subtitle stream. The scene uses simplified materials for memory-constrained rendering; review the result before commercial use.
