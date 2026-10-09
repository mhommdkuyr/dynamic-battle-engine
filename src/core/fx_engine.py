import cv2
import numpy as np
import math
import random
from typing import List, Tuple

class FXEngine:
    """
    Generates action lines, smear frame hulls, and impact frame color flashes.
    """
    @staticmethod
    def render_action_lines(frame: np.ndarray, origin: Tuple[int, int], num_lines: int = 28, length_range=(180, 500), color=(255, 255, 255), alpha: float = 0.7) -> np.ndarray:
        h, w = frame.shape[:2]
        overlay = frame.copy()
        ox, oy = origin

        for _ in range(num_lines):
            angle = random.uniform(0, 2 * math.pi)
            dist_start = random.uniform(length_range[0], length_range[1] * 0.7)
            dist_end = dist_start + random.uniform(100, length_range[1])

            x1 = int(ox + math.cos(angle) * dist_start)
            y1 = int(oy + math.sin(angle) * dist_start)
            x2 = int(ox + math.cos(angle) * dist_end)
            y2 = int(oy + math.sin(angle) * dist_end)
            thickness = random.randint(1, 3)

            cv2.line(overlay, (x1, y1), (x2, y2), color, thickness, cv2.LINE_AA)

        return cv2.addWeighted(overlay, alpha, frame, 1.0 - alpha, 0)

    @staticmethod
    def render_smear_limb(canvas: np.ndarray, start_pos: Tuple[int, int], end_pos: Tuple[int, int], radius: int = 8, color=(220, 240, 255), alpha: float = 0.8):
        """
        Draws an elongated smear capsule polygon representing hyper-speed limb motion.
        """
        p1 = np.array(start_pos, dtype=np.float32)
        p2 = np.array(end_pos, dtype=np.float32)
        direction = p2 - p1
        dist = np.linalg.norm(direction)
        if dist < 2.0:
            cv2.circle(canvas, (int(start_pos[0]), int(start_pos[1])), radius, color, -1)
            return

        unit_dir = direction / dist
        perp = np.array([-unit_dir[1], unit_dir[0]], dtype=np.float32)

        poly = np.array([
            p1 + perp * radius,
            p2 + perp * (radius * 0.7),
            p2 - perp * (radius * 0.7),
            p1 - perp * radius
        ], dtype=np.int32)

        cv2.fillPoly(canvas, [poly], color, cv2.LINE_AA)
        cv2.circle(canvas, (int(p1[0]), int(p1[1])), radius, color, -1)
        cv2.circle(canvas, (int(p2[0]), int(p2[1])), int(radius * 0.7), color, -1)

    @staticmethod
    def render_impact_frame(frame: np.ndarray, center: Tuple[int, int], frame_idx: int, max_frames: int = 2) -> np.ndarray:
        """
        Generates anime impact frames: high-contrast inverted black & white strobe with shockwave ring.
        """
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # High contrast binary / inverted threshold
        _, thresh = cv2.threshold(gray, 110, 255, cv2.THRESH_BINARY_INV)
        impact = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)

        # Draw concentric shockwave rings
        radius = int(80 + (frame_idx + 1) * 90)
        cv2.circle(impact, center, radius, (255, 255, 255), 4, cv2.LINE_AA)
        cv2.circle(impact, center, max(10, radius - 40), (255, 255, 255), 2, cv2.LINE_AA)

        # Radial spikes from center
        for a in np.linspace(0, 2 * math.pi, 16, endpoint=False):
            ex = int(center[0] + math.cos(a) * (radius + 60))
            ey = int(center[1] + math.sin(a) * (radius + 60))
            cv2.line(impact, center, (ex, ey), (255, 255, 255), 2, cv2.LINE_AA)

        return impact
