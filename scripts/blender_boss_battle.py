# Blender 3D & Grease Pencil Headless Automation Script
# Project: Dynamic Battle Engine - Trio vs Shadow Titan
# Author: mhommdkuyr/dynamic-battle-engine

import bpy
import math
import os

def setup_blender_render_settings(fps=60, width=1920, height=1080, total_frames=1800):
    scene = bpy.context.scene
    scene.render.fps = fps
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.frame_start = 1
    scene.frame_end = total_frames
    scene.render.film_transparent = False

    # Choose EEVEE Next or EEVEE
    if hasattr(bpy.types, 'BLENDER_EEVEE_NEXT'):
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
    else:
        scene.render.engine = 'BLENDER_EEVEE'

    # Color Management (High Contrast Anime Grading)
    scene.view_settings.view_transform = 'Filmic' if 'Filmic' in [t.name for t in bpy.types.ViewSettings.bl_rna.properties['view_transform'].enum_items] else 'Standard'
    scene.view_settings.look = 'High Contrast'

def create_environment_arena():
    # Ground plane
    bpy.ops.mesh.primitive_plane_add(size=100, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = "Arena_Ground"
    mat_ground = bpy.data.materials.new("Ground_Mat")
    mat_ground.use_nodes = True
    bsdf = mat_ground.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.05, 0.05, 0.08, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.8
    ground.data.materials.append(mat_ground)

    # Volumetric Lightning Light
    light_data = bpy.data.lights.new(name="Lightning_Key", type='POINT')
    light_data.energy = 5000
    light_data.color = (0.7, 0.85, 1.0)
    light_obj = bpy.data.objects.new(name="Lightning_Key", object_data=light_data)
    bpy.context.collection.objects.link(light_obj)
    light_obj.location = (0, 0, 15)

    return ground, light_obj

def create_fighter_rig(name, location, color_tuple):
    gp_data = bpy.data.grease_pencils.new(f"{name}_GPData")
    gp_obj = bpy.data.objects.new(name, gp_data)
    bpy.context.collection.objects.link(gp_obj)
    gp_obj.location = location

    # Grease pencil stroke material
    mat = bpy.data.materials.new(f"{name}_Mat")
    bpy.data.materials.create_gpencil_data(mat)
    mat.grease_pencil.color = color_tuple
    gp_data.materials.append(mat)

    layer = gp_data.layers.new("Hero_Strokes")
    return gp_obj

def setup_dynamic_cinematic_camera():
    cam_data = bpy.data.cameras.new("Cinematic_Action_Cam")
    cam_data.lens = 28
    cam_data.dof.use_dof = True
    cam_data.dof.focus_distance = 12.0
    cam_data.dof.aperture_fstop = 2.8

    cam_obj = bpy.data.objects.new("Cinematic_Action_Cam", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj

    cam_obj.location = (0, -18, 3.5)
    cam_obj.rotation_euler = (math.radians(82), 0, 0)
    cam_obj.keyframe_insert(data_path="location", frame=1)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=1)

    cam_obj.location = (2, -8, 2.0)
    cam_obj.rotation_euler = (math.radians(85), math.radians(6), math.radians(-10))
    cam_obj.keyframe_insert(data_path="location", frame=180)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=180)

    return cam_obj

def build_boss_battle_scene():
    setup_blender_render_settings()
    create_environment_arena()

    hikari = create_fighter_rig("Hero_Hikari_Lightning", (-4, 0, 0), (1.0, 0.9, 0.1, 1.0))
    ren = create_fighter_rig("Hero_Ren_Kinetic", (0, -2, 0), (0.1, 0.9, 1.0, 1.0))
    leo = create_fighter_rig("Hero_Leo_Starlight", (4, 0, 0), (1.0, 0.35, 0.1, 1.0))

    titan = create_fighter_rig("Boss_Shadow_Titan", (0, 8, 0), (0.15, 0.05, 0.25, 1.0))
    titan.scale = (3.5, 3.5, 3.5)

    cam = setup_dynamic_cinematic_camera()
    print("Blender 3D Boss Battle Scene successfully initialized!")

if __name__ == "__main__":
    build_boss_battle_scene()
