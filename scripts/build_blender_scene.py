#!/usr/bin/env python3
"""Create and optionally render an original animated 3D stick-fighter scene in Blender.

The choreography, character rigs, stage changes, shockwaves and camera path are authored
new for Prism Break. Reference-video camera estimates are diagnostics only and are not
used as keyframes.
"""
from __future__ import annotations

import argparse
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

DURATION = 291.318
FPS = 24
IMPACTS = [28.333, 39.444, 47.222, 58.333, 72.778, 94.444, 108.889,
           124.444, 139.444, 158.333, 177.778, 195.556, 214.444, 233.889,
           253.333, 269.444, 280.0]
PATHS = {
    "blue": [(0,245,475),(8,300,478),(18,475,463),(28,610,455),(38,770,425),(47,655,375),(58,420,420),(70,515,350),(82,700,282),(94,635,300),(101,465,245),(111,365,205),(124,515,326),(137,760,370),(150,660,318),(163,435,275),(177,540,225),(190,675,260),(203,435,270),(215,600,340),(228,740,386),(242,620,425),(253,460,438),(265,540,378),(276,700,330),(284,640,440),(291.318,640,458)],
    "red": [(0,1035,475),(8,970,478),(18,800,463),(28,665,455),(38,515,425),(47,600,375),(58,850,420),(70,720,350),(82,545,282),(94,610,300),(101,795,245),(111,915,205),(124,765,326),(137,530,370),(150,600,318),(163,785,275),(177,700,225),(190,585,260),(203,815,270),(215,680,340),(228,520,386),(242,650,425),(253,795,438),(265,700,378),(276,530,330),(284,640,440),(291.318,640,458)],
    "gold": [(0,1430,450),(88,1420,235),(94,1210,190),(101,1010,230),(108,820,308),(118,650,280),(130,560,292),(145,700,340),(158,620,260),(173,670,290),(188,640,235),(203,560,280),(215,640,350),(228,730,388),(240,610,420),(252,650,448),(263,600,370),(276,620,330),(284,645,440),(291.318,650,458)]
}
COLORS = {
    "blue": (0.02, 0.75, 1.0, 1.0),
    "red": (1.0, 0.035, 0.09, 1.0),
    "gold": (1.0, 0.62, 0.025, 1.0),
    "white": (0.93, 0.97, 1.0, 1.0),
    "stone": (0.10, 0.11, 0.14, 1.0),
    "ground": (0.25, 0.26, 0.28, 1.0),
    "space": (0.018, 0.008, 0.045, 1.0),
}


def reset_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def emission_material(name, color, strength=1.0, roughness=0.85):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    em = nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = color
    em.inputs["Strength"].default_value = strength
    mat.node_tree.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat


def diffuse_material(name, color, roughness=0.8, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
    return mat


def add_curve(name, points, material, bevel=0.025, cyclic=False):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = bevel
    curve.bevel_resolution = 1
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for p, coord in zip(spline.points, points):
        p.co = (coord[0], coord[1], coord[2], 1.0)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    if material:
        obj.data.materials.append(material)
    return obj


def parent_keep_local(obj, rig):
    obj.parent = rig
    return obj


def add_limb(rig, name, a, b, material, bevel=0.035):
    mid = ((a[0]+b[0])/2, (a[1]+b[1])/2, (a[2]+b[2])/2)
    obj = add_curve(name, [(a[0]-mid[0], a[1]-mid[1], a[2]-mid[2]),
                           (b[0]-mid[0], b[1]-mid[1], b[2]-mid[2])], material, bevel)
    obj.location = mid
    parent_keep_local(obj, rig)
    return obj


def add_sphere(name, location, scale, material, segments=16, rings=8):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    if material:
        obj.data.materials.append(material)
    for face in obj.data.polygons:
        face.use_smooth = True
    return obj


def interp_path(keys, t):
    if t <= keys[0][0]:
        return keys[0][1], keys[0][2]
    if t >= keys[-1][0]:
        return keys[-1][1], keys[-1][2]
    j = 0
    while j < len(keys)-2 and t > keys[j+1][0]:
        j += 1
    a,b=keys[j],keys[j+1]
    u=(t-a[0])/max(1e-6,b[0]-a[0])
    u=u*u*(3.0-2.0*u)
    return a[1]+(b[1]-a[1])*u, a[2]+(b[2]-a[2])*u


def fighter_world(identity, t):
    xpix, ypix = interp_path(PATHS[identity], t)
    x = (xpix - 640.0) / 108.0
    z = max(0.02, (475.0 - ypix) / 100.0)
    phase = {"blue":0.2,"red":2.1,"gold":4.4}[identity]
    x += math.sin(t*2.8+phase)*0.075
    z += math.sin(t*3.4+phase)*0.055
    depth = {"blue":-0.10,"red":0.42,"gold":1.0}[identity] + 0.25*math.sin(t*0.6+phase)
    return Vector((x, depth, z))


def new_rig(identity, material, white_mat):
    rig = bpy.data.objects.new(identity.title()+" Fighter Rig", None)
    bpy.context.collection.objects.link(rig)
    rig.empty_display_type = "CIRCLE"
    rig.empty_display_size = 0.25
    bones = {}
    # Torso and neck.
    bones["torso"] = add_limb(rig, identity+"_torso", (0,0,0.78), (0,0,1.43), material, 0.046)
    bones["neck"] = add_limb(rig, identity+"_neck", (0,0,1.39), (0,0,1.52), material, 0.035)
    # Arms are independent center-pivoted curves and receive authored rotations.
    bones["arm_l_upper"] = add_limb(rig, identity+"_arm_l_upper", (-0.08,0,1.37), (-0.34,0,1.13), material, 0.04)
    bones["arm_l_lower"] = add_limb(rig, identity+"_arm_l_lower", (-0.34,0,1.13), (-0.42,0,0.91), material, 0.036)
    bones["arm_r_upper"] = add_limb(rig, identity+"_arm_r_upper", (0.08,0,1.37), (0.34,0,1.13), material, 0.04)
    bones["arm_r_lower"] = add_limb(rig, identity+"_arm_r_lower", (0.34,0,1.13), (0.42,0,0.91), material, 0.036)
    bones["leg_l_upper"] = add_limb(rig, identity+"_leg_l_upper", (-0.07,0,0.79), (-0.22,0,0.44), material, 0.047)
    bones["leg_l_lower"] = add_limb(rig, identity+"_leg_l_lower", (-0.22,0,0.44), (-0.33,0,0.08), material, 0.043)
    bones["leg_r_upper"] = add_limb(rig, identity+"_leg_r_upper", (0.07,0,0.79), (0.22,0,0.44), material, 0.047)
    bones["leg_r_lower"] = add_limb(rig, identity+"_leg_r_lower", (0.22,0,0.44), (0.33,0,0.08), material, 0.043)

    head = add_sphere(identity+"_head", (0,0,1.72), (0.205,0.135,0.205), material)
    parent_keep_local(head, rig)
    head.location=(0,0,1.72)
    # Bright eye slits and a thin orbital outline remain visible at the wide camera angles.
    eye1=add_curve(identity+"_eye_l", [(-0.09,-0.145,1.75),(-0.025,-0.15,1.75)], white_mat, 0.012)
    parent_keep_local(eye1,rig); eye1.location=(0,0,0)
    eye2=add_curve(identity+"_eye_r", [(0.025,-0.15,1.75),(0.09,-0.145,1.75)], white_mat, 0.012)
    parent_keep_local(eye2,rig); eye2.location=(0,0,0)
    # Aura ellipse in the fighter plane, parented to the root.
    aura_pts=[]
    for k in range(49):
        th=2*math.pi*k/48
        aura_pts.append((0.36*math.cos(th), 0.12, 1.0+0.76*math.sin(th)))
    aura=add_curve(identity+"_energy_aura",aura_pts,material,0.012,True)
    parent_keep_local(aura,rig); aura.location=(0,0,0)
    if identity == "gold":
        halo_pts=[(0.36*math.cos(2*math.pi*k/48),-0.02,1.82+0.12*math.sin(2*math.pi*k/48)) for k in range(49)]
        halo=add_curve(identity+"_geometric_halo",halo_pts,white_mat,0.014,True)
        parent_keep_local(halo,rig); halo.location=(0,0,0)
    return rig,bones


def action_envelope(t):
    return max([math.exp(-0.5*((t-ti)/0.42)**2) for ti in IMPACTS] + [0.0])


def animate_fighter(rig, bones, identity, duration, fps):
    times={0.0,duration}
    times.update(float(k[0]) for k in PATHS[identity])
    times.update(IMPACTS)
    times.update(max(0.0,ti-0.48) for ti in IMPACTS)
    times.update(min(duration,ti+0.52) for ti in IMPACTS)
    times=sorted(times)
    phase={"blue":0.0,"red":2.2,"gold":4.6}[identity]
    depth={"blue":-0.10,"red":0.42,"gold":1.0}[identity]
    for t in times:
        frame=1+int(round(t*fps))
        pos=fighter_world(identity,t)
        rig.location=pos
        rig.location.y=depth+0.25*math.sin(t*0.6+phase)
        # Rotating the root around Y adds full 3D pitch/tilt during launches and recoil.
        recoil=sum(math.exp(-0.5*((t-ti)/0.26)**2) for ti in IMPACTS if int(ti*10)%2==0)
        rig.rotation_euler[1]=0.18*math.sin(t*1.1+phase)+min(0.8,recoil*0.35)
        scale=1.0+0.07*math.sin(t*1.4+phase)+0.13*action_envelope(t)
        if identity=="gold":
            scale*=1.08
        rig.scale=(scale,scale,scale)
        rig.keyframe_insert(data_path="location",frame=frame)
        rig.keyframe_insert(data_path="rotation_euler",frame=frame)
        rig.keyframe_insert(data_path="scale",frame=frame)
        env=action_envelope(t)
        # Use quick original attack arcs; the actors don't inherit tracked source poses.
        speed=0.55*math.sin(t*2.2+phase)
        rotations={
            "arm_l_upper":speed-0.2-env*0.82,
            "arm_l_lower":-0.25+env*0.42,
            "arm_r_upper":-speed+0.15+env*0.92,
            "arm_r_lower":0.20-env*0.52,
            "leg_l_upper":0.12*math.sin(t*3.0+phase)+env*0.62,
            "leg_l_lower":-0.15-env*0.26,
            "leg_r_upper":-0.12*math.sin(t*3.0+phase)-env*0.56,
            "leg_r_lower":0.15+env*0.22,
        }
        for bone_name, angle in rotations.items():
            bone=bones[bone_name]
            bone.rotation_euler[1]=float(angle)
            bone.keyframe_insert(data_path="rotation_euler",frame=frame)
    if rig.animation_data and rig.animation_data.action:
        for fcurve in rig.animation_data.action.fcurves:
            for key in fcurve.keyframe_points:
                key.interpolation="BEZIER"
                key.handle_left_type="AUTO_CLAMPED"
                key.handle_right_type="AUTO_CLAMPED"


def look_at(obj, target):
    direction=Vector(target)-obj.location
    obj.rotation_mode="QUATERNION"
    obj.rotation_quaternion=direction.to_track_quat("-Z","Y")


def camera_setup(scene, duration, fps):
    data=bpy.data.cameras.new("PrismBreak Cinematic Camera")
    cam=bpy.data.objects.new("PrismBreak Cinematic Camera",data)
    bpy.context.collection.objects.link(cam)
    scene.camera=cam
    data.lens=46
    keys=[
        (0,(0,-15,5.0),(0,0,1.35),42),
        (28.3,(-1,-8.7,3.5),(0,0,1.15),62),
        (55,(1,-7.4,3.8),(0,0,1.3),70),
        (63,(-2,-10.4,5.2),(0,0,2.2),48),
        (88,(0,-13,7.8),(0,0,2.8),40),
        (105,(2.5,-10.8,6.1),(0,0,2.5),46),
        (124,(-1.8,-9.3,5.5),(0,0,2.0),50),
        (145,(1.5,-11,7.0),(0,0,2.6),43),
        (160,(0,-8.5,7.2),(0,1.5,2.2),43),
        (182,(4,-3.0,6.0),(0,0.5,2.0),48),
        (197,(5,2.0,5.2),(0,0,2.0),44),
        (211,(-4,1.0,4.6),(0,0,2.0),44),
        (225,(0,-14,5.1),(0,0,1.05),44),
        (245,(-2,-9.1,3.2),(0,0,1.1),61),
        (266,(1,-8.5,4.0),(0,0,1.3),64),
        (282,(0,-15.8,5.3),(0,0,1.3),40),
        (duration,(0,-16.2,5.1),(0,0,1.3),38)
    ]
    for t,location,target,lens in keys:
        frame=1+int(round(t*fps))
        cam.location=location
        look_at(cam,target)
        cam.data.lens=lens
        cam.keyframe_insert(data_path="location",frame=frame)
        cam.keyframe_insert(data_path="rotation_quaternion",frame=frame)
        cam.data.keyframe_insert(data_path="lens",frame=frame)
    if cam.animation_data and cam.animation_data.action:
        for fc in cam.animation_data.action.fcurves:
            for k in fc.keyframe_points:
                k.interpolation="BEZIER"
                k.handle_left_type="AUTO_CLAMPED"
                k.handle_right_type="AUTO_CLAMPED"
    return cam


def stage_setup(scene, mats, duration, fps):
    # Ground plane and rough debris are true 3D objects. Their visibility changes for space.
    ground_mat=mats["ground"]
    bpy.ops.mesh.primitive_plane_add(size=180, location=(0,0,-0.11))
    ground=bpy.context.object; ground.name="Grey rocky ground"; ground.data.materials.append(ground_mat)
    rocks=[]
    random.seed(90210)
    for i in range(48):
        x=random.uniform(-13,13); y=random.uniform(-3,10); z=random.uniform(-0.06,0.12)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=random.uniform(0.08,0.42),location=(x,y,z))
        rock=bpy.context.object; rock.name=f"Debris Rock {i:03d}"
        rock.scale=(random.uniform(0.8,1.9),random.uniform(0.45,1.25),random.uniform(0.25,0.85))
        rock.data.materials.append(mats["stone"]); rocks.append(rock)
    # A distant planet, orbit ring and stars form a separate environment layer.
    planet_mat=emission_material("Distant violet planet",(0.16,0.075,0.34,1),0.8)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=3.1,location=(4.8,10.0,4.2))
    planet=bpy.context.object; planet.name="Distant planet"; planet.data.materials.append(planet_mat)
    for p in planet.data.polygons: p.use_smooth=True
    ringpts=[]
    for k in range(181):
        a=2*math.pi*k/180
        ringpts.append((4.8+4.0*math.cos(a),9.4,4.2+1.05*math.sin(a)))
    planet_ring=add_curve("Planet orbital ring",ringpts,mats["gold"],0.018,True)
    stars=[]
    for i in range(150):
        x=random.uniform(-22,22); y=random.uniform(11,23); z=random.uniform(-1,15)
        st=add_sphere(f"Star {i:03d}",(x,y,z),(random.uniform(.012,.035),)*3,mats["white"],8,4)
        stars.append(st)
    # Geometry hide keys: ground in space, celestial layer only in the orbit sequence.
    def visibility(obj, keys):
        for t,hidden in keys:
            obj.hide_render=bool(hidden)
            obj.keyframe_insert(data_path="hide_render",frame=1+int(round(t*fps)))
    surface_keys=[(0,False),(157,False),(160,True),(224,True),(228,False),(duration,False)]
    space_keys=[(0,True),(157,True),(160,False),(224,False),(228,True),(duration,True)]
    visibility(ground,surface_keys)
    for rock in rocks: visibility(rock,surface_keys)
    visibility(planet,space_keys); visibility(planet_ring,space_keys)
    for star in stars: visibility(star,space_keys)
    # Add rocks floating through the midair stage, separately depth-layered.
    for i in range(24):
        x=random.uniform(-8,8); y=random.uniform(1.5,6.5); z=random.uniform(2.4,7.5)
        size=random.uniform(.04,.18)
        rock=add_sphere(f"Floating shard {i:02d}",(x,y,z),(size*1.4,size,size*.65),mats["stone"],8,4)
        rock.location.x=x-2.0
        rock.keyframe_insert(data_path="location",frame=1+int(60*fps))
        rock.location.x=x+2.5
        rock.keyframe_insert(data_path="location",frame=1+int(150*fps))
        rock.hide_render=True; rock.keyframe_insert(data_path="hide_render",frame=1)
        rock.hide_render=False; rock.keyframe_insert(data_path="hide_render",frame=1+int(60*fps))
        rock.hide_render=True; rock.keyframe_insert(data_path="hide_render",frame=1+int(160*fps))


def effects_setup(duration, fps, mats):
    # Shock rings expand around key beats; they are geometric, newly generated effects.
    for idx, t in enumerate(IMPACTS):
        x1,z1=interp_path(PATHS["blue"],t)
        x2,z2=interp_path(PATHS["red"],t)
        x=((x1+x2)/2-640)/108
        z=max(0.7,(475-(z1+z2)/2)/100+0.9)
        bpy.ops.mesh.primitive_torus_add(major_segments=32,minor_segments=6,location=(x,-0.18,z),major_radius=0.7,minor_radius=0.018,rotation=(math.pi/2,0,0))
        ring=bpy.context.object; ring.name=f"Impact shock ring {idx:02d}"; ring.data.materials.append(mats["white"])
        ring.scale=(0.001,0.001,0.001); ring.keyframe_insert(data_path="scale",frame=1)
        f0=1+int(round(t*fps))
        ring.scale=(0.26,0.26,0.26); ring.keyframe_insert(data_path="scale",frame=max(1,f0-2))
        ring.scale=(0.62,0.62,0.62); ring.keyframe_insert(data_path="scale",frame=f0)
        ring.scale=(1.7,1.7,1.7); ring.keyframe_insert(data_path="scale",frame=min(1+int(duration*fps),f0+10))
        ring.scale=(2.2,2.2,2.2); ring.keyframe_insert(data_path="scale",frame=min(1+int(duration*fps),f0+15))
        ring.scale=(0.001,0.001,0.001); ring.keyframe_insert(data_path="scale",frame=min(1+int(duration*fps),f0+23))
        if ring.animation_data and ring.animation_data.action:
            for fc in ring.animation_data.action.fcurves:
                for k in fc.keyframe_points: k.interpolation="BEZIER"


def add_lighting():
    bpy.ops.object.light_add(type="AREA",location=(0,-5,8))
    key=bpy.context.object; key.name="Soft overhead key"; key.data.energy=850; key.data.shape="DISK"; key.data.size=9
    key.rotation_euler=(math.radians(25),0,0)
    bpy.ops.object.light_add(type="AREA",location=(-6,-2,4))
    fill=bpy.context.object; fill.name="Cool side fill"; fill.data.energy=350; fill.data.color=(0.25,0.55,1.0); fill.data.size=6
    fill.rotation_euler=(math.radians(50),0,math.radians(-25))


def configure(scene, duration, fps, width, height, threads):
    scene.frame_start=1
    scene.frame_end=1+int(round(duration*fps))
    scene.render.resolution_x=width
    scene.render.resolution_y=height
    scene.render.resolution_percentage=100
    scene.render.fps=fps
    scene.render.fps_base=1.0
    scene.render.engine="CYCLES"
    scene.cycles.device="CPU"
    scene.cycles.samples=1
    scene.cycles.use_denoising=False
    scene.render.threads_mode="FIXED"
    scene.render.threads=threads
    scene.render.film_transparent=False
    scene.render.image_settings.file_format="FFMPEG"
    scene.render.ffmpeg.format="MPEG4"
    scene.render.ffmpeg.codec="H264"
    scene.render.ffmpeg.constant_rate_factor="HIGH"
    scene.render.ffmpeg.ffmpeg_preset="GOOD"
    scene.render.ffmpeg.audio_codec="NONE"
    scene.render.filepath="//Prism_Break_3D_video"
    scene.render.use_file_extension=True
    scene.render.image_settings.color_mode="RGB"
    scene.render.image_settings.color_depth="8"
    scene.view_settings.view_transform="Standard"
    scene.view_settings.look="Medium High Contrast"
    scene.view_settings.exposure=0
    scene.view_settings.gamma=1
    scene.world.color=(0.012,0.01,0.022)
    scene.render.use_compositing=False
    scene.render.use_sequencer=False


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--blend-output",default="output/prism_break_3d.blend")
    parser.add_argument("--output",default="output/Prism_Break_Original_3D_720p24_video.mp4")
    parser.add_argument("--duration",type=float,default=DURATION)
    parser.add_argument("--fps",type=int,default=FPS)
    parser.add_argument("--width",type=int,default=1280)
    parser.add_argument("--height",type=int,default=720)
    parser.add_argument("--threads",type=int,default=2)
    parser.add_argument("--render",action="store_true")
    args=parser.parse_args(argv)
    if bpy.app.version < (3,6,0):
        raise RuntimeError("Blender 3.6 or newer is required.")
    reset_scene()
    mats={
        "blue":emission_material("Electric cyan",COLORS["blue"],1.2),
        "red":emission_material("Crimson flare",COLORS["red"],1.2),
        "gold":emission_material("Solar gold",COLORS["gold"],1.35),
        "white":emission_material("Impact white",COLORS["white"],1.15),
        "stone":diffuse_material("Basalt debris",COLORS["stone"]),
        "ground":diffuse_material("Ash-grey ground",COLORS["ground"],0.98),
        "space":emission_material("Deep space",COLORS["space"],0.4),
    }
    scene=bpy.context.scene
    configure(scene,args.duration,args.fps,args.width,args.height,args.threads)
    stage_setup(scene,mats,args.duration,args.fps)
    fighters={}
    for identity in ("blue","red","gold"):
        rig,bones=new_rig(identity,mats[identity],mats["white"])
        animate_fighter(rig,bones,identity,args.duration,args.fps)
        fighters[identity]=rig
    camera_setup(scene,args.duration,args.fps)
    effects_setup(args.duration,args.fps,mats)
    add_lighting()
    # Authored camera/character keys use the new path definitions in this file only.
    scene.frame_set(1)
    blend_path=Path(args.blend_output)
    blend_path.parent.mkdir(parents=True,exist_ok=True)
    scene.render.filepath=str(Path(args.output).resolve())
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path.resolve()))
    print(f"BLEND_SCENE_READY {blend_path} duration={args.duration} fps={args.fps} engine=Cycles-CPU",flush=True)
    if args.render:
        output=Path(args.output).resolve()
        output.parent.mkdir(parents=True,exist_ok=True)
        scene.render.filepath=str(output)
        bpy.ops.render.render(animation=True)
        if not output.exists() or output.stat().st_size < 100_000:
            raise RuntimeError(f"Blender render did not produce a usable video at {output}")
        print(f"BLENDER_VIDEO_READY {output} bytes={output.stat().st_size}",flush=True)


if __name__=="__main__":
    # Blender uses -- to separate its own flags from script arguments.
    script_args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    main(script_args)
