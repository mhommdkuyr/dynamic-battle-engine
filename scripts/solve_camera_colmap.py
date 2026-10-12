#!/usr/bin/env python3
"""Optional CPU-only sparse 3D camera solve with COLMAP.

Outputs camera poses as diagnostics only. Do not retarget the generated episode to these
poses; hand-authored camera choreography in build_blender_scene.py is independent.
"""
from __future__ import annotations
import argparse
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np


def run(cmd, timeout=1800):
    print("+", " ".join(map(str,cmd)),flush=True)
    subprocess.run(list(map(str,cmd)),check=True,timeout=timeout)


def quat_to_rotation(q):
    qw,qx,qy,qz=map(float,q)
    return np.array([
        [1-2*(qy*qy+qz*qz),2*(qx*qy-qz*qw),2*(qx*qz+qy*qw)],
        [2*(qx*qy+qz*qw),1-2*(qx*qx+qz*qz),2*(qy*qz-qx*qw)],
        [2*(qx*qz-qy*qw),2*(qy*qz+qx*qw),1-2*(qx*qx+qy*qy)]
    ],dtype=float)


def extract_stills(video: Path, directory: Path, interval: float, max_width: int):
    cap=cv2.VideoCapture(str(video))
    if not cap.isOpened(): raise RuntimeError(f"Cannot open input video: {video}")
    fps=cap.get(cv2.CAP_PROP_FPS) or 24.0
    frame_count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration=frame_count/fps if frame_count else 0.0
    times=np.arange(0,max(duration,interval),interval)
    saved=[]
    for idx,t in enumerate(times):
        if t>=duration and idx>0: break
        cap.set(cv2.CAP_PROP_POS_FRAMES,int(t*fps))
        ok,frame=cap.read()
        if not ok: continue
        h,w=frame.shape[:2]
        if w>max_width:
            frame=cv2.resize(frame,(max_width,max(1,int(h*max_width/w))),interpolation=cv2.INTER_AREA)
        name=f"frame_{idx:05d}.jpg"
        path=directory/name
        if not cv2.imwrite(str(path),frame,[cv2.IMWRITE_JPEG_QUALITY,88]):
            raise RuntimeError(f"Failed to write diagnostic still {path}")
        saved.append((name,float(t)))
    cap.release()
    return saved,fps,duration


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--sample-interval",type=float,default=1.5)
    parser.add_argument("--max-width",type=int,default=640)
    parser.add_argument("--threads",type=int,default=2)
    args=parser.parse_args()
    colmap=shutil.which("colmap")
    if not colmap: raise RuntimeError("COLMAP is not installed; install it or skip this optional solve.")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="prism-colmap-") as temp:
        root=Path(temp); images=root/"images"; images.mkdir()
        saved,fps,duration=extract_stills(args.input,images,args.sample_interval,args.max_width)
        if len(saved)<8: raise RuntimeError(f"Not enough readable stills for SfM: {len(saved)}")
        db=root/"database.db"; sparse=root/"sparse"; sparse.mkdir()
        run([colmap,"feature_extractor","--database_path",db,"--image_path",images,
             "--ImageReader.single_camera","1","--FeatureExtraction.use_gpu","0",
             "--SiftExtraction.use_gpu","0","--SiftExtraction.max_num_features","2048",
             "--SiftExtraction.max_image_size",str(args.max_width),
             "--SiftExtraction.num_threads",str(args.threads)],timeout=3600)
        run([colmap,"sequential_matcher","--database_path",db,
             "--FeatureMatching.use_gpu","0","--SiftMatching.use_gpu","0",
             "--SiftMatching.max_num_matches","2048","--SiftMatching.max_num_trials","3000",
             "--SiftMatching.num_threads",str(args.threads)],timeout=3600)
        run([colmap,"mapper","--database_path",db,"--image_path",images,
             "--output_path",sparse,"--Mapper.ba_global_max_num_iterations","25",
             "--Mapper.num_threads",str(args.threads)],timeout=3600)
        models=sorted([p for p in sparse.iterdir() if p.is_dir() and (p/"images.bin").exists()],
                      key=lambda p:len(list(p.iterdir())),reverse=True)
        if not models: raise RuntimeError("COLMAP did not register a sparse camera model for this stylized video.")
        txt=root/"txt"; txt.mkdir()
        run([colmap,"model_converter","--input_path",models[0],"--output_path",txt,"--output_type","TXT"],timeout=300)
        # Build a frame-to-time table using our sample filenames; COLMAP may register only a subset.
        time_map={name:t for name,t in saved}
        lines=(txt/"images.txt").read_text(encoding="utf-8").splitlines()
        cameras=[]
        i=0
        while i<len(lines):
            s=lines[i].strip(); i+=1
            if not s or s.startswith("#"): continue
            p=s.split()
            if len(p)<10: continue
            image_name=p[9]
            q=list(map(float,p[1:5])); trans=np.array(list(map(float,p[5:8])),dtype=float)
            R=quat_to_rotation(q); center=(-R.T@trans).tolist()
            cameras.append({"image":image_name,"time_seconds":time_map.get(image_name),
                            "quaternion_wxyz":[round(v,8) for v in q],
                            "translation_world":[round(v,8) for v in trans.tolist()],
                            "camera_center_up_to_scale":[round(v,8) for v in center]})
            # Ignore the following observations row; it has no image pose.
            if i<len(lines): i+=1
        report={
            "method":"COLMAP sparse structure-from-motion, CPU feature extraction/matching",
            "purpose":"camera-path diagnostic only; not wired into new choreography",
            "source":{"file_name":args.input.name,"duration_seconds":round(duration,3),
                      "source_fps":fps,"sample_interval_seconds":args.sample_interval,
                      "stills_extracted":len(saved)},
            "registered_cameras":len(cameras),
            "camera_poses":cameras,
            "limitations":["Monocular translation scale is ambiguous.",
                           "Stylized 2D animation, scene cuts, occlusion and animated backgrounds may make reconstruction degenerate.",
                           "These poses are not used to recreate the source video's shots or animation."]
        }
        args.output.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({"output":str(args.output),"registered_cameras":len(cameras),
                      "stills_extracted":len(saved),"duration":duration},indent=2))


if __name__=="__main__":
    main()
