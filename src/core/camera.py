import math
import random
from typing import Tuple

class DynamicCamera:
    """
    Dynamic 2.5D/3D camera with Trauma-based screen shake, Dutch roll, and zoom.
    Based on the game-feel camera trauma formula:
      shake = trauma^2
      offset_x = max_x * shake * noise(t)
      offset_y = max_y * shake * noise(t)
      rotation = max_rot * shake * noise(t)
    """
    def __init__(self, width: int = 1920, height: int = 1080):
        self.width = width
        self.height = height
        self.target_x = width / 2.0
        self.target_y = height / 2.0
        self.zoom = 1.0
        self.trauma = 0.0
        self.trauma_decay = 0.92
        self.max_offset_x = 40.0
        self.max_offset_y = 30.0
        self.max_angle_deg = 5.0
        self.time = 0.0

    def add_trauma(self, amount: float):
        self.trauma = min(1.0, max(0.0, self.trauma + amount))

    def update(self, dt: float = 1.0 / 60.0):
        self.time += dt
        self.trauma = max(0.0, self.trauma * (self.trauma_decay ** (dt * 60.0)))

    def get_transform(self) -> Tuple[float, float, float, float]:
        """
        Returns (offset_x, offset_y, rotation_deg, zoom)
        """
        shake = self.trauma * self.trauma
        if shake < 0.001:
            return 0.0, 0.0, 0.0, self.zoom

        # Pseudo-random noise with high-frequency oscillation
        freq = 35.0
        noise_x = math.sin(self.time * freq * 1.1) + 0.5 * math.sin(self.time * freq * 2.3)
        noise_y = math.cos(self.time * freq * 0.9) + 0.5 * math.cos(self.time * freq * 1.7)
        noise_rot = math.sin(self.time * freq * 1.4)

        offset_x = self.max_offset_x * shake * (noise_x / 1.5)
        offset_y = self.max_offset_y * shake * (noise_y / 1.5)
        rot_deg = self.max_angle_deg * shake * noise_rot

        return offset_x, offset_y, rot_deg, self.zoom
