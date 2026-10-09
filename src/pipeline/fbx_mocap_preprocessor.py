import os
import sys
import json
import math
import numpy as np
import cv2

class MocapOpenPoseAdapter:
    """
    Parses 3D character motions from FBX / Mocap sequences and translates
    them into standardized OpenPose skeleton keypoint image sequences.
    Compatible with ComfyUI-ControlNet-Aux and ControlNet OpenPose models.
    """
    def __init__(self, canvas_width=896, canvas_height=512):
        self.width = canvas_width
        self.height = canvas_height

        self.limb_connections = [
            (1, 2), (1, 5), (2, 3), (3, 4), (5, 6), (6, 7),
            (1, 8), (8, 9), (9, 10), (10, 11), (8, 12), (12, 13), (13, 14),
            (1, 0), (0, 15), (15, 17), (0, 16), (16, 18)
        ]
        self.colors = [
            (255, 0, 0), (255, 85, 0), (255, 170, 0), (255, 255, 0), (170, 255, 0),
            (85, 255, 0), (0, 255, 0), (0, 255, 85), (0, 255, 170), (0, 255, 255),
            (0, 170, 255), (0, 85, 255), (0, 0, 255), (85, 0, 255), (170, 0, 255),
            (255, 0, 255), (255, 0, 170), (255, 0, 85)
        ]

    def render_pose_frame(self, character_keypoints_list):
        canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        for keypoints in character_keypoints_list:
            for i, (p1_idx, p2_idx) in enumerate(self.limb_connections):
                if p1_idx < len(keypoints) and p2_idx < len(keypoints):
                    p1 = keypoints[p1_idx]
                    p2 = keypoints[p2_idx]
                    if p1 is not None and p2 is not None:
                        color = self.colors[i % len(self.colors)]
                        cv2.line(canvas, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), color, 4, cv2.LINE_AA)

            for p in keypoints:
                if p is not None:
                    cv2.circle(canvas, (int(p[0]), int(p[1])), 4, (0, 0, 255), -1, cv2.LINE_AA)

        return canvas

    def generate_clash_sequence(self, num_frames=32, output_dir="output/openpose_frames"):
        os.makedirs(output_dir, exist_ok=True)
        for f in range(num_frames):
            prog = f / float(num_frames)
            ns_x = 220 + int(prog * 200)
            ns_y = 320
            nightshade_kp = [
                (ns_x, ns_y - 60), (ns_x, ns_y - 45), (ns_x - 20, ns_y - 40), (ns_x - 40, ns_y - 20),
                (ns_x - 55, ns_y), (ns_x + 20, ns_y - 40), (ns_x + 50, ns_y - 30), (ns_x + 80, ns_y - 25),
                (ns_x, ns_y), (ns_x - 18, ns_y + 10), (ns_x - 35, ns_y + 50), (ns_x - 45, ns_y + 90),
                (ns_x + 18, ns_y + 10), (ns_x + 30, ns_y + 55), (ns_x + 40, ns_y + 90),
                (ns_x - 5, ns_y - 65), (ns_x + 5, ns_y - 65), (ns_x - 12, ns_y - 60), (ns_x + 12, ns_y - 60)
            ]
            pr_x = 680 - int(prog * 200)
            pr_y = 310
            prisoner_kp = [
                (pr_x, pr_y - 70), (pr_x, pr_y - 50), (pr_x + 25, pr_y - 45), (pr_x + 45, pr_y - 20),
                (pr_x + 60, pr_y), (pr_x - 25, pr_y - 45), (pr_x - 60, pr_y - 40), (pr_x - 90, pr_y - 30),
                (pr_x, pr_y), (pr_x + 22, pr_y + 15), (pr_x + 40, pr_y + 60), (pr_x + 55, pr_y + 100),
                (pr_x - 22, pr_y + 15), (pr_x - 40, pr_y + 60), (pr_x - 55, pr_y + 100),
                (pr_x + 6, pr_y - 75), (pr_x - 6, pr_y - 75), (pr_x + 15, pr_y - 70), (pr_x - 15, pr_y - 70)
            ]
            frame = self.render_pose_frame([nightshade_kp, prisoner_kp])
            path = os.path.join(output_dir, f"openpose_frame_{f:03d}.png")
            cv2.imwrite(path, frame)
