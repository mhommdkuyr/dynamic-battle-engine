import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.engines.blender_grease_pencil import generate_blender_script

if __name__ == "__main__":
    path = generate_blender_script()
    print(f"Blender script exported to: {path}")
