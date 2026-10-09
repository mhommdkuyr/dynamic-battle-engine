import unittest
import numpy as np
from src.core.camera import DynamicCamera
from src.core.fx_engine import FXEngine

class TestEngine(unittest.TestCase):
    def test_camera_trauma_decay(self):
        cam = DynamicCamera()
        cam.add_trauma(1.0)
        self.assertEqual(cam.trauma, 1.0)
        cam.update(0.1)
        self.assertLess(cam.trauma, 1.0)

    def test_fx_action_lines(self):
        img = np.zeros((720, 1280, 3), dtype=np.uint8)
        res = FXEngine.render_action_lines(img, (640, 360), num_lines=10)
        self.assertEqual(res.shape, (720, 1280, 3))
        self.assertTrue(np.any(res > 0))

    def test_fx_impact_frame(self):
        img = np.full((720, 1280, 3), 200, dtype=np.uint8)
        impact = FXEngine.render_impact_frame(img, (640, 360), frame_idx=0)
        self.assertEqual(impact.shape, (720, 1280, 3))

if __name__ == "__main__":
    unittest.main()
