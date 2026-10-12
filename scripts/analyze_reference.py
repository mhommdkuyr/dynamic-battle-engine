#!/usr/bin/env python3
"""Analyze reference metadata and coarse image-plane motion without exporting source media.

This is a diagnostic tool only. Its estimates are not wired into the new animation's
camera/choreography, so it cannot transfer shot-for-shot motion or copy source frames/audio.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np


def probe_video(path: Path) -> dict:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe is required; install FFmpeg.")
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries",
         "format=duration:stream=codec_type,width,height,r_frame_rate,avg_frame_rate,codec_name,duration",
         "-of", "json", str(path)],
        check=True, capture_output=True, text=True
    )
    metadata = json.loads(result.stdout)
    video = next((s for s in metadata["streams"] if s.get("codec_type") == "video"), None)
    audio = next((s for s in metadata["streams"] if s.get("codec_type") == "audio"), None)
    if not video:
        raise ValueError(f"No video stream found: {path}")
    duration = float(video.get("duration") or metadata.get("format", {}).get("duration") or 0)
    return {
        "file_name": path.name,
        "file_bytes": path.stat().st_size,
        "duration_seconds": duration,
        "width": int(video["width"]),
        "height": int(video["height"]),
        "frame_rate": video.get("avg_frame_rate"),
        "video_codec": video.get("codec_name"),
        "audio_codec": (audio or {}).get("codec_name"),
        "audio_duration_seconds": float((audio or {}).get("duration") or 0) if audio else None,
    }


def color_histogram(frame: np.ndarray) -> np.ndarray:
    small = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    return cv2.calcHist([hsv], [0, 1], None, [24, 16], [0, 180, 0, 256]).astype(np.float32)


def analyze(path: Path, sample_fps: float, max_width: int) -> dict:
    meta = probe_video(path)
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"OpenCV cannot open the video: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = meta["duration_seconds"]
    interval = max(1, int(round(fps / max(sample_fps, 0.25))))
    target_frames = list(range(0, max(frame_count, 1), interval))
    prev_gray = None
    prev_hist = None
    prev_idx = None
    motion = []
    cuts = []
    count = 0
    total_dx = total_dy = total_rotation = total_scale = 0.0
    while True:
        pos = cap.get(cv2.CAP_PROP_POS_FRAMES)
        ok, frame = cap.read()
        if not ok:
            break
        idx = int(pos)
        if idx % interval != 0:
            continue
        h, w = frame.shape[:2]
        if w > max_width:
            nh = max(1, int(h * max_width / w))
            frame = cv2.resize(frame, (max_width, nh), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hist = color_histogram(frame)
        t = idx / fps
        if prev_hist is not None:
            change = float(cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA))
            if change >= 0.52:
                cuts.append({"time_seconds": round(t, 3), "histogram_change": round(change, 4)})
        if prev_gray is not None:
            p0 = cv2.goodFeaturesToTrack(
                prev_gray, maxCorners=700, qualityLevel=0.012,
                minDistance=8, blockSize=7
            )
            transform = None
            inliers = 0
            if p0 is not None and len(p0) >= 8:
                p1, status, errors = cv2.calcOpticalFlowPyrLK(
                    prev_gray, gray, p0, None,
                    winSize=(21, 21), maxLevel=3,
                    criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01)
                )
                if p1 is not None and status is not None:
                    good_old = p0[status.reshape(-1) == 1].reshape(-1, 2)
                    good_new = p1[status.reshape(-1) == 1].reshape(-1, 2)
                    if len(good_old) >= 8:
                        transform, inlier_mask = cv2.estimateAffinePartial2D(
                            good_old, good_new, method=cv2.RANSAC,
                            ransacReprojThreshold=2.5, maxIters=1200,
                            confidence=0.98, refineIters=10
                        )
                        if transform is not None and inlier_mask is not None:
                            inliers = int(inlier_mask.sum())
            if transform is not None:
                a, b = float(transform[0, 0]), float(transform[1, 0])
                scale = float(np.hypot(a, b))
                rotation = float(np.degrees(np.arctan2(b, a)))
                dx, dy = float(transform[0, 2]), float(transform[1, 2])
                dt = (idx - (prev_idx or idx)) / fps
                entry = {
                    "time_seconds": round(t, 3),
                    "sample_delta_seconds": round(dt, 4),
                    "image_translation_px": [round(dx, 3), round(dy, 3)],
                    "image_rotation_degrees": round(rotation, 4),
                    "image_scale_ratio": round(scale, 5),
                    "tracked_inliers": inliers,
                }
                motion.append(entry)
                total_dx += dx
                total_dy += dy
                total_rotation += abs(rotation)
                total_scale += abs(scale - 1.0)
                count += 1
        prev_gray, prev_hist, prev_idx = gray, hist, idx
    cap.release()
    large_changes = sorted(motion, key=lambda r: abs(r["image_translation_px"][0]) + abs(r["image_translation_px"][1]), reverse=True)[:20]
    return {
        "analysis_version": 1,
        "purpose": "diagnostic_only_not_used_for_animation_retargeting",
        "source": meta,
        "sampling": {"requested_fps": sample_fps, "actual_frame_step": interval, "source_frame_rate": fps, "source_frame_count": frame_count},
        "shot_change_candidates": cuts,
        "image_plane_motion_samples": motion,
        "largest_image_plane_motion_samples": large_changes,
        "summary": {
            "motion_samples": len(motion),
            "successful_transforms": count,
            "mean_abs_rotation_per_sample_degrees": round(total_rotation / max(1, count), 5),
            "mean_abs_scale_deviation": round(total_scale / max(1, count), 6),
            "net_image_plane_translation_px": [round(total_dx, 3), round(total_dy, 3)],
            "camera_pose_warning": "2D affine flow is not a metric 3D camera solve; parallax, edits, zooms, occlusion and animated subjects can invalidate the estimate."
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sample-fps", type=float, default=2.0)
    parser.add_argument("--max-width", type=int, default=640)
    args = parser.parse_args()
    report = analyze(args.input, args.sample_fps, args.max_width)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "duration": report["source"]["duration_seconds"],
                      "motion_samples": report["summary"]["motion_samples"],
                      "shot_change_candidates": len(report["shot_change_candidates"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
