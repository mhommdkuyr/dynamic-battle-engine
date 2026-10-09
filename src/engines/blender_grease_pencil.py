import os

BLENDER_GREASE_PENCIL_SCRIPT = \"\"\"import bpy
import math

def setup_scene(fps=60, width=1920, height=1080):
    scene = bpy.context.scene
    scene.render.fps = fps
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(bpy.types, 'BLENDER_EEVEE_NEXT') else 'BLENDER_EEVEE'

def create_grease_pencil_fighter(name="Warrior_P1", color=(0.1, 0.8, 1.0, 1.0)):
    gp_data = bpy.data.grease_pencils.new(name + "_Data")
    gp_obj = bpy.data.objects.new(name, gp_data)
    bpy.context.collection.objects.link(gp_obj)

    # Material
    mat = bpy.data.materials.new(name + "_Mat")
    bpy.data.materials.create_gpencil_data(mat)
    mat.grease_pencil.color = color
    gp_data.materials.append(mat)

    # Layer
    layer = gp_data.layers.new("Lines")
    return gp_obj, layer

def setup_camera_with_shake():
    cam_data = bpy.data.cameras.new("ActionCam")
    cam_data.lens = 35
    cam_obj = bpy.data.objects.new("ActionCam", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj
    cam_obj.location = (0, -10, 1.5)
    cam_obj.rotation_euler = (math.radians(85), 0, 0)
    return cam_obj

def run_headless_combat_generation():
    setup_scene()
    p1, layer1 = create_grease_pencil_fighter("P1_Cyan", (0.1, 0.8, 1.0, 1.0))
    p2, layer2 = create_grease_pencil_fighter("P2_Red", (1.0, 0.2, 0.2, 1.0))
    cam = setup_camera_with_shake()
    print("Blender Grease Pencil combat scene initialized successfully.")

if __name__ == "__main__":
    run_headless_combat_generation()
\"\"\"

def generate_blender_script(output_path: str = "scripts/blender_render.py") -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(BLENDER_GREASE_PENCIL_SCRIPT)
    return output_path
