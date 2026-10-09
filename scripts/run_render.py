import os
import sys
import cv2
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.engines.opencv_renderer import CombatRenderer
from src.core.timeline import Timeline

def main():
    print("=== Dynamic Battle Engine: Headless Combat Renderer ===")
    config_file = "configs/combat_gods_scene_0310.json"
    timeline = Timeline(config_file)
    renderer = CombatRenderer(width=1280, height=720, fps=60)

    os.makedirs("output", exist_ok=True)
    video_path = "output/combat_clash_0310.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(video_path, fourcc, 60.0, (1280, 720))

    total_frames = 90
    print(f"Rendering {total_frames} frames (Clash at Frame 18, Recoil at Frame 60)...")

    for f in range(total_frames):
        ev = timeline.get_event_at_frame(f)
        p1 = ev.get("p1", {"x": 300 + f * 5, "y": 500, "state": "dash", "velocity": (30, 0)})
        p2 = ev.get("p2", {"x": 980 - f * 5, "y": 500, "state": "dash", "velocity": (-30, 0)})
        impact = ev.get("impact", None)

        if f == 18 or f == 60:
            renderer.camera.add_trauma(0.9)

        frame_img = renderer.render_frame(f, p1, p2, impact)
        out.write(frame_img)

        if f in [18, 24, 60]:
            snapshot_path = f"output/frame_{f:03d}.png"
            cv2.imwrite(snapshot_path, frame_img)
            print(f"Saved keyframe snapshot: {snapshot_path}")

    out.release()
    print(f"Render complete! Video saved to: {video_path}")

if __name__ == "__main__":
    main()
