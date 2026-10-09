import cv2
import numpy as np
import math
from typing import Dict, Any, List
from src.core.camera import DynamicCamera
from src.core.fx_engine import FXEngine

class CombatRenderer:
    """
    Headless fast 2.5D combat animation renderer using OpenCV.
    Implements stickman/warrior rigs with high-velocity smears, camera shake, action lines, and impact frames.
    """
    def __init__(self, width: int = 1920, height: int = 1080, fps: int = 60):
        self.width = width
        self.height = height
        self.fps = fps
        self.camera = DynamicCamera(width, height)
        self.prev_p1_pos = None
        self.prev_p2_pos = None

    def draw_fighter(self, canvas: np.ndarray, x: float, y: float, color: tuple, pose_state: str, velocity=(0.0, 0.0)):
        vx, vy = velocity
        speed = math.hypot(vx, vy)

        # Draw Smear if velocity is high
        if speed > 18.0:
            prev_x = x - vx * 1.4
            prev_y = y - vy * 1.4
            FXEngine.render_smear_limb(canvas, (prev_x, prev_y), (x, y), radius=16, color=color, alpha=0.5)

        # Head
        cv2.circle(canvas, (int(x), int(y - 70)), 16, color, -1, cv2.LINE_AA)
        cv2.circle(canvas, (int(x), int(y - 70)), 18, (255, 255, 255), 2, cv2.LINE_AA)

        # Torso
        cv2.line(canvas, (int(x), int(y - 54)), (int(x), int(y)), color, 5, cv2.LINE_AA)

        # Dynamic limb poses based on state
        if "punch" in pose_state:
            # Arm thrust forward
            cv2.line(canvas, (int(x), int(y - 45)), (int(x + 55), int(y - 45)), color, 4, cv2.LINE_AA)
            cv2.circle(canvas, (int(x + 55), int(y - 45)), 8, (255, 255, 255), -1, cv2.LINE_AA)
        elif "block" in pose_state:
            # Crossed arms
            cv2.line(canvas, (int(x), int(y - 45)), (int(x - 20), int(y - 55)), color, 4, cv2.LINE_AA)
            cv2.line(canvas, (int(x), int(y - 45)), (int(x - 20), int(y - 35)), color, 4, cv2.LINE_AA)
        elif "kick" in pose_state:
            # Extended leg
            cv2.line(canvas, (int(x), int(y)), (int(x + 75), int(y - 25)), color, 5, cv2.LINE_AA)
        else:
            # Normal stance
            cv2.line(canvas, (int(x), int(y - 45)), (int(x + 25), int(y - 20)), color, 4, cv2.LINE_AA)

        # Legs
        cv2.line(canvas, (int(x), int(y)), (int(x - 25), int(y + 60)), color, 5, cv2.LINE_AA)
        cv2.line(canvas, (int(x), int(y)), (int(x + 25), int(y + 60)), color, 5, cv2.LINE_AA)

    def render_frame(self, frame_idx: int, p1_data: dict, p2_data: dict, impact_data: dict = None) -> np.ndarray:
        dt = 1.0 / self.fps
        self.camera.update(dt)

        # Base background
        frame = np.full((self.height, self.width, 3), (18, 18, 24), dtype=np.uint8)

        # Floor grid line with perspective
        cv2.line(frame, (0, 810), (self.width, 810), (45, 45, 60), 3, cv2.LINE_AA)

        p1_x, p1_y = p1_data.get("x", 400), p1_data.get("y", 750)
        p2_x, p2_y = p2_data.get("x", 1500), p2_data.get("y", 750)

        # Speed / Action Lines when rushing
        speed1 = math.hypot(*p1_data.get("velocity", (0, 0)))
        speed2 = math.hypot(*p2_data.get("velocity", (0, 0)))
        if speed1 > 25.0 or speed2 > 25.0:
            focus_point = (int((p1_x + p2_x) / 2), int((p1_y + p2_y) / 2))
            frame = FXEngine.render_action_lines(frame, focus_point, num_lines=20, alpha=0.6)

        # Draw fighters
        # P1 = Cyan Warrior (0, 220, 255 in BGR)
        self.draw_fighter(frame, p1_x, p1_y, (255, 210, 0), p1_data.get("state", "idle"), p1_data.get("velocity", (0, 0)))
        # P2 = Crimson Warrior (0, 40, 240 in BGR)
        self.draw_fighter(frame, p2_x, p2_y, (40, 40, 255), p2_data.get("state", "idle"), p2_data.get("velocity", (0, 0)))

        # Impact Flash Frame if active
        if impact_data and impact_data.get("active", False):
            center = (int((p1_x + p2_x) / 2), int((p1_y + p2_y) / 2))
            frame = FXEngine.render_impact_frame(frame, center, frame_idx % 3)

        # Apply Camera Shake and Zoom
        off_x, off_y, rot_deg, zoom = self.camera.get_transform()
        center = (self.width / 2.0, self.height / 2.0)
        M = cv2.getRotationMatrix2D(center, rot_deg, zoom)
        M[0, 2] += off_x
        M[1, 2] += off_y

        transformed = cv2.warpAffine(frame, M, (self.width, self.height), borderMode=cv2.BORDER_REFLECT)
        return transformed
