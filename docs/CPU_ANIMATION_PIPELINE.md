# CPU Animation Production Pipeline

This repository contains two render paths for the original *Prism Break — Three Forces* episode:

- **Blender 3D + Cycles CPU**: authored three-dimensional fighter rigs, a real perspective camera with keyframed position/rotation/focal length, a ground/desert stage, a planet/star-field stage, geometric impact rings, and an original camera path.
- **OpenCV CPU fallback**: a previously smoke-tested, faster stylized 2.5D renderer. GitHub Actions uses it if the full Blender episode does not finish in the configured CPU window.

The source video is used, when credentials are configured, only to produce separate diagnostic reports (metadata, candidate cuts, approximate 2D image-plane motion, and optionally COLMAP sparse camera poses). The source frames, source music, and recovered camera poses are **not** used to drive the new episode's animation or soundtrack.

## Files

- `scripts/build_blender_scene.py` — authors and saves the editable `.blend` scene; `--render` renders the whole animation.
- `scripts/render_prism_break.py` — CPU fallback and original-score generator.
- `scripts/generate_score.py` — creates a new procedural score; no source track is sampled.
- `scripts/analyze_reference.py` — low-resolution metadata, scene-change and image-plane motion analysis.
- `scripts/solve_camera_colmap.py` — optional CPU sparse structure-from-motion analysis; output is for diagnosis only.
- `scripts/drive_io.py` — OAuth refresh, reference download, and chunked/resumable MP4 upload.

## GitHub Actions

Open **Actions → Prism Break — CPU 3D/2D Animation Pipeline → Run workflow**. The optional `run_colmap` input enables COLMAP CPU reconstruction if the reference video was downloaded successfully. Pushes to the pipeline files also trigger the build.

The workflow:

1. Installs Blender, FFmpeg, OpenCV and NumPy on a CPU runner.
2. Runs Python syntax checks and the repository's engine tests.
3. Downloads the reference only if Drive OAuth secrets are available, then writes diagnostic reports. It does not include the source media in artifacts.
4. Builds the editable 3D scene and verifies a real Blender camera render.
5. Tries the full Blender Cycles CPU render for up to 25 minutes. If it cannot finish, the workflow renders the full episode with the validated OpenCV CPU fallback.
6. Adds the procedural original score, verifies MP4 duration, 1280×720 resolution, 24 fps, H.264 video and AAC audio.
7. Uploads a build artifact and publishes an MP4/Blend-file GitHub Release.
8. Uploads to Drive only when Drive OAuth secrets are configured; this step is intentionally non-destructive and creates a new file.

## Optional Google Drive secrets

Configure these in **Repository → Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Purpose |
| --- | --- |
| `GOOGLE_DRIVE_CLIENT_ID` | OAuth client ID |
| `GOOGLE_DRIVE_CLIENT_SECRET` | OAuth client secret |
| `GOOGLE_DRIVE_REFRESH_TOKEN` | Refresh token with required Drive permissions |
| `GOOGLE_DRIVE_FOLDER_ID` | ID of the folder containing the reference; can also be the output folder |
| `GOOGLE_DRIVE_OUTPUT_FOLDER_ID` | Optional separate folder ID for rendered outputs |
| `GOOGLE_DRIVE_REFERENCE_FILE_ID` | Optional exact reference file ID; if absent, the script searches the configured folder by filename |

Keep secrets out of source code and logs. The refresh token needs read permission to download the reference and write/create permission to upload renders. The separate output folder is recommended so the input is never overwritten.

## Notes on reconstruction

OpenCV's affine optical-flow estimate is a **2D diagnostic**, not a metrically correct 3D solve. COLMAP can estimate sparse camera poses from sampled frames on CPU, but monocular scale remains ambiguous and stylized animation, camera cuts, occlusion, and moving backgrounds can produce unreliable results. Neither estimate is treated as ground truth or used to recreate the reference shot-by-shot.

CoTracker is not part of the default pipeline: its upstream repository states that most of its code is CC-BY-NC and that a GPU is strongly recommended. COLMAP/CPU is the optional sparse reconstruction route here; its documented CPU mode is slower than GPU mode.

The default release workflow publishes files to a public repository's GitHub Releases. Do not enable public publishing for material you cannot publicly redistribute.
