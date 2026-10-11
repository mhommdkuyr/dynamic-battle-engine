import bpy, math, os, re, json, traceback
from mathutils import Vector
BASE=os.environ.get('ASSET_DIR','/mnt/files'); OUT=os.environ.get('OUTPUT_DIR','/tmp/episode_01'); FRAMES=int(os.environ.get('FRAME_COUNT','480')); FPS=int(os.environ.get('RENDER_FPS','8'))
os.makedirs(OUT+'/frames',exist_ok=True)
# Fast deterministic clean scene
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.render.resolution_x=480; scene.render.resolution_y=270; scene.render.resolution_percentage=100
scene.render.fps=FPS; scene.frame_start=1; scene.frame_end=FRAMES
scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGBA'; scene.render.film_transparent=False
scene.render.filepath=OUT+'/frames/f_'
scene.render.image_settings.color_depth='8'
scene.render.resolution_percentage=100
scene.render.use_file_extension=True
scene.render.engine='CYCLES'
scene.cycles.device='CPU'; scene.cycles.samples=1; scene.cycles.use_denoising=False
scene.render.threads_mode='FIXED'; scene.render.threads=4
scene.eevee.taa_render_samples=8
scene.render.image_settings.color_mode='RGBA'
scene.world=bpy.data.worlds.new('Midnight Atmosphere'); scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.get('Background'); bg.inputs['Color'].default_value=(0.003,0.006,0.018,1); bg.inputs['Strength'].default_value=0.18
scene.view_settings.view_transform='AgX'
# helpers
def mat(name, color, metallic=0.0, rough=0.5, emission=None, strength=0.0):
 m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
 p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=(*color,1); p.inputs['Metallic'].default_value=metallic; p.inputs['Roughness'].default_value=rough
 if emission:
  if 'Emission Color' in p.inputs: p.inputs['Emission Color'].default_value=(*emission,1); p.inputs['Emission Strength'].default_value=strength
  elif 'Emission' in p.inputs: p.inputs['Emission'].default_value=(*emission,1)
 return m
def emm(name,color,strength=3):
 m=bpy.data.materials.new(name); m.use_nodes=True; n=m.node_tree.nodes; n.clear(); o=n.new('ShaderNodeOutputMaterial'); e=n.new('ShaderNodeEmission'); e.inputs['Color'].default_value=(*color,1); e.inputs['Strength'].default_value=strength; m.node_tree.links.new(e.outputs[0],o.inputs['Surface']); return m
def cube(name, loc, scale, material, bevel=0):
 bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o=bpy.context.object; o.name=name; o.dimensions=scale; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(material)
 if bevel: mod=o.modifiers.new('Worn edges','BEVEL'); mod.width=bevel; mod.segments=2; o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
 return o
def animate(o, path, vals):
 for f,v in vals:
  setattr(o,path,v); o.keyframe_insert(data_path=path,frame=f)
def smooth_keys(o):
 if o.animation_data and o.animation_data.action:
  for fc in o.animation_data.action.fcurves:
   for kp in fc.keyframe_points: kp.interpolation='BEZIER'
def add_area(name,loc,color,power,size,target=(0,0,1)):
 d=bpy.data.lights.new(name,'AREA'); d.energy=power; d.color=color; d.shape='DISK'; d.size=size; o=bpy.data.objects.new(name,d); scene.collection.objects.link(o); o.location=loc; o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler(); return o
def add_point(name,loc,color,power,radius):
 d=bpy.data.lights.new(name,'POINT'); d.energy=power; d.color=color; d.shadow_soft_size=radius; o=bpy.data.objects.new(name,d); scene.collection.objects.link(o); o.location=loc; return o
# Stage and arena
stone=mat('Obsidian stone',(0.025,0.034,0.055),0.55,0.34)
metal=mat('Blackened steel',(0.055,0.075,0.11),0.85,0.24)
rock=mat('Broken basalt',(0.035,0.043,0.06),0.15,0.78)
blue=emm('Ion blue',(0.015,0.35,1.0),5.5); red=emm('Crimson plasma',(1.0,0.018,0.06),3.5); gold=emm('Ember',(1.0,0.25,0.035),3.0)
floor=stone
bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=5.1, depth=0.32, location=(0,0,-0.19)); arena=bpy.context.object; arena.name='Ancient combat platform'; arena.data.materials.append(stone); arena.modifiers.new('Soft edge','BEVEL').width=.18; arena.modifiers.new('Normals','WEIGHTED_NORMAL')
for rad, minor, z, material in [(4.55,.035,.005,metal),(3.55,.018,.008,blue),(2.55,.015,.01,red)]:
 bpy.ops.mesh.primitive_torus_add(major_radius=rad,minor_radius=minor,major_segments=96,minor_segments=8,location=(0,0,z)); bpy.context.object.name='Inlaid arena ring'; bpy.context.object.data.materials.append(material)
# Cracked radial seams
for i in range(18):
 a=2*math.pi*i/18
 x,y=2.0*math.cos(a),2.0*math.sin(a)
 o=cube('Crack in basalt',(x,y,.004),(.025,1.5,.012),metal,.008); o.rotation_euler[2]=a
# Ruined colonnade and debris
for i in range(12):
 a=2*math.pi*i/12; rad=6.0
 x,y=rad*math.cos(a),rad*math.sin(a); h=1.1+(i%4)*.48
 bpy.ops.mesh.primitive_cylinder_add(vertices=6 if i%3==0 else 10, radius=.32+(i%2)*.13, depth=h, location=(x,y,h/2-.05)); p=bpy.context.object; p.name='Ruined arena column'; p.data.materials.append(metal if i%2 else rock); p.rotation_euler[0]=.04*math.sin(a); p.rotation_euler[1]=.05*math.cos(a)
 # ember glows on selected columns
 if i in [1,4,7,10]: add_point('Column ember',(x,y,h*.72),(1,.035,.01),110,1.2)
for i in range(34):
 a=i*2.399; r=3.0+(i%8)*.27; x=r*math.cos(a); y=r*math.sin(a)
 bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=.15+(i%4)*.045,location=(x,y,.07)); o=bpy.context.object; o.name='Fallen stone'; o.scale=(1.6,.85,.6+(i%3)*.2); o.rotation_euler=(.17*(i%5),.21*(i%4),a); o.data.materials.append(rock if i%3 else metal)
# Floating ember particles animated
for i in range(42):
 x=math.sin(i*17.3)*4.6; y=math.cos(i*9.1)*3.8; z=.25+(i%11)*.19
 bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=.018+(i%3)*.01,location=(x,y,z)); o=bpy.context.object; o.name='Suspended ember'; o.data.materials.append(gold if i%4 else blue)
 o.location=(x,y,z); o.keyframe_insert('location',frame=1); o.location=(x+.22*math.sin(i),y+.35,z+.65); o.keyframe_insert('location',frame=FRAMES)
# Character imports with preserved model transforms and a motion-only BVH source rig
def import_character(path, label, x, color_hint):
 before=set(bpy.data.objects)
 bpy.ops.import_scene.fbx(filepath=path, automatic_bone_orientation=True)
 new=[o for o in bpy.data.objects if o not in before]
 arm=next(o for o in new if o.type=='ARMATURE'); mesh=next(o for o in new if o.type=='MESH')
 arm.name=label+'_Armature'; mesh.name=label+'_Mesh'
 root=bpy.data.objects.new(label+'_MotionRoot',None); scene.collection.objects.link(root); root.empty_display_type='CIRCLE'; root.empty_display_size=.4
 for ob in (arm,mesh):
  world=ob.matrix_world.copy(); ob.parent=root; ob.matrix_world=world
 root.location=(x,0,0); root.rotation_euler[2]= math.radians(-65 if x<0 else 115)
 # Slightly polish existing FBX materials without overriding their appearance
 for m in mesh.data.materials:
  if m and m.use_nodes:
   p=m.node_tree.nodes.get('Principled BSDF')
   if p:
    p.inputs['Metallic'].default_value=max(float(p.inputs['Metallic'].default_value),.2)
    p.inputs['Roughness'].default_value=min(float(p.inputs['Roughness'].default_value),.42)
 return root,arm,mesh
def import_bvh(path, label, start_frame):
 bpy.ops.import_anim.bvh(filepath=path, frame_start=1, global_scale=1.0, use_fps_scale=False, update_scene_fps=False, update_scene_duration=False)
 src=next(o for o in bpy.context.selected_objects if o.type=='ARMATURE')
 src.name=label+'_MotionSource'; src.hide_render=True; src.hide_viewport=True
 act=src.animation_data.action
 # keep the most active 60 seconds from the extracted 2D motion; retime it over our 60s production shot
 src_start,src_end=start_frame,start_frame+719
 factor=(FRAMES-1)/(src_end-src_start)
 for fc in act.fcurves:
  for kp in fc.keyframe_points:
   kp.co.x=1+(kp.co.x-src_start)*factor
   kp.handle_left.x=1+(kp.handle_left.x-src_start)*factor
   kp.handle_right.x=1+(kp.handle_right.x-src_start)*factor
  fc.update()
 return src,act
def retarget(dst, src, label):
 mapping={'Hips':'mixamorig:Hips','Spine':'mixamorig:Spine','Neck':'mixamorig:Neck','Head':'mixamorig:Head','LeftShoulder':'mixamorig:LeftShoulder','LeftElbow':'mixamorig:LeftForeArm','LeftHand':'mixamorig:LeftHand','RightShoulder':'mixamorig:RightShoulder','RightElbow':'mixamorig:RightForeArm','RightHand':'mixamorig:RightHand','LeftUpLeg':'mixamorig:LeftUpLeg','LeftKnee':'mixamorig:LeftLeg','LeftFoot':'mixamorig:LeftFoot','RightUpLeg':'mixamorig:RightUpLeg','RightKnee':'mixamorig:RightLeg','RightFoot':'mixamorig:RightFoot'}
 weights={'Hips':.26,'Spine':.22,'Neck':.3,'Head':.42,'LeftShoulder':.28,'RightShoulder':.28,'LeftElbow':.45,'RightElbow':.45,'LeftHand':.35,'RightHand':.35,'LeftUpLeg':.28,'RightUpLeg':.28,'LeftKnee':.34,'RightKnee':.34,'LeftFoot':.24,'RightFoot':.24}
 added=[]
 for sname,dname in mapping.items():
  if sname not in src.data.bones or dname not in dst.data.bones: continue
  c=dst.pose.bones[dname].constraints.new('COPY_ROTATION'); c.name='Retarget '+sname; c.target=src; c.subtarget=sname; c.owner_space='LOCAL'; c.target_space='LOCAL'; c.mix_mode='REPLACE'; c.influence=weights.get(sname,.3); added.append(sname)
 print('RETARGET',label,'mapped',added)
# import both actual FBX models and two motion tracks
night_root,night_arm,night_mesh=import_character(BASE+'/Nightshade J Friedrich.fbx','NIGHTSHADE',-1.7,'blue')
prison_root,prison_arm,prison_mesh=import_character(BASE+'/Prisoner B Styperek.fbx','PRISONER',1.7,'red')
red_src,red_act=import_bvh(BASE+'/motion_extracted/Motion_Extracted_Red.bvh','RED',241)
black_src,black_act=import_bvh(BASE+'/motion_extracted/Motion_Extracted_Black.bvh','BLACK',2101)
retarget(night_arm,red_src,'NIGHTSHADE'); retarget(prison_arm,black_src,'PRISONER')
# choreograph root motion using the source motion as the base, then layered dramatic blocking
for root, vals in [
 (night_root,[(1,(-1.75,0,0)),(70,(-1.55,0,0)),(112,(-.55,-.04,0)),(148,(-.20,-.10,.32)),(180,(-1.2,-.15,0)),(224,(-1.65,0,0)),(268,(-1.05,-.1,.55)),(304,(-.55,-.12,.9)),(334,(-1.1,0,.3)),(360,(-1.6,0,0)),(398,(-.3,-.08,.15)),(421,(.0,-.12,.05)),(430,(-.35,0,.02)),(455,(-1.0,0,0)),(480,(-.95,0,0))]),
 (prison_root,[(1,(1.7,0,0)),(70,(1.52,0,0)),(112,(.58,.03,0)),(148,(.18,.06,.1)),(180,(1.2,.10,0)),(224,(1.62,0,0)),(268,(1.0,.08,.32)),(304,(.5,.12,.55)),(334,(1.02,0,.15)),(360,(1.55,0,0)),(398,(.28,.10,.05)),(421,(.08,.12,.05)),(430,(.42,0,0)),(455,(1.05,0,0)),(480,(1.00,0,0))])]:
 for f,loc in vals:
  root.location=loc; root.keyframe_insert(data_path='location',frame=f)
 smooth_keys(root)
# Sword composed of emissive curved blade attached to Nightshade, hilt and pommel
swordcurve=bpy.data.curves.new('Ion blade curve','CURVE'); swordcurve.dimensions='3D'; swordcurve.resolution_u=2; swordcurve.bevel_depth=.045; swordcurve.bevel_resolution=3
sp=swordcurve.splines.new('POLY'); sp.points.add(3)
for p,co in zip(sp.points,[(.42,-.04,1.02,1),(.62,-.03,1.28,1),(.92,-.01,1.77,1),(1.10,0,2.12,1)]): p.co=co
sword=bpy.data.objects.new('Nightshades cyan energy blade',swordcurve); scene.collection.objects.link(sword); sword.parent=night_root; sword.data.materials.append(blue)
# blade flickers through main clash and final impact
for f,sc in [(1,(.001,)*3),(24,(1,1,1)),(80,(1,1,1)),(97,(.01,.01,.01)),(106,(1,1,1)),(214,(1,1,1)),(226,(.01,.01,.01)),(242,(1,1,1)),(350,(1,1,1)),(373,(.01,.01,.01)),(390,(1,1,1)),(435,(1,1,1)),(480,(1,1,1))]:
 sword.scale=sc; sword.keyframe_insert('scale',frame=f)
# Dynamic energy slash trails - torus arcs and lines pulse at attack beats
for idx,(f0,loc,col,rad) in enumerate([(108,(0,-.3,1.45),blue,1.2),(155,(0,-.2,1.0),red,1.45),(278,(0,-.3,1.7),blue,1.55),(315,(0,-.3,1.25),red,1.8),(420,(0,-.3,1.35),blue,2.0)]):
 d=bpy.data.curves.new('Slash arc','CURVE'); d.dimensions='3D'; d.resolution_u=2; d.bevel_depth=.035; d.bevel_resolution=2
 spl=d.splines.new('POLY'); spl.points.add(36)
 for j,p in enumerate(spl.points):
  a=math.radians(-135+j*270/36); p.co=(rad*math.cos(a),.03*math.sin(a),rad*.62*math.sin(a),1)
 ob=bpy.data.objects.new('Arc of energy '+str(idx+1),d); scene.collection.objects.link(ob); ob.location=loc; ob.data.materials.append(col)
 for f,sc in [(max(1,f0-5),(.001,.001,.001)),(f0,(1,1,1)),(f0+5,(1.25,1.25,1.25)),(f0+12,(.001,.001,.001))]: ob.scale=sc; ob.keyframe_insert('scale',frame=f)
# Shock rings at impacts, scaled outward then vanished
for idx,f0 in enumerate([112,155,180,315,421]):
 for k in range(3):
  bpy.ops.mesh.primitive_torus_add(major_radius=1,minor_radius=.025-k*.004,major_segments=64,minor_segments=8,location=(0,-.2,.03+k*.035))
  o=bpy.context.object; o.name=f'Impact shock ring {idx}-{k}'; o.data.materials.append(blue if (idx+k)%2==0 else red)
  for f,sz in [(max(1,f0-1),(.001,.001,.001)),(f0,(.12,.12,.12)),(f0+5,(.8+k*.28,.55+k*.22,1)),(f0+10,(1.65+k*.28,1.25+k*.2,1)),(f0+13,(.001,.001,.001))]: o.scale=sz; o.keyframe_insert('scale',frame=f)
# Impact flash lights
flash=add_point('Impact flash',(0,-.15,1.4),(0.7,.85,1),0,1.5)
for f,power in [(1,0),(108,0),(112,2100),(115,0),(151,0),(155,1800),(158,0),(311,0),(315,2400),(318,0),(417,0),(421,3500),(424,0)]: flash.data.energy=power; flash.data.keyframe_insert('energy',frame=f)
# Stage lighting
add_area('Cold moon key',(-4,-3,6),(.12,.32,1.0),1150,5,(0,0,1.3))
add_area('Hot crimson rim',(3,3,4),(1.0,.025,.06),1450,4,(0,0,1.2))
add_area('Neutral front fill',(0,-5,3.4),(.45,.62,1.0),900,5,(0,0,1.2))
add_area('Top hard rim',(0,1,7),(.25,.35,.8),1700,3,(0,0,0.8))
add_point('Blue ground glow',(-2.5,0,.25),(.015,.12,1),220,1.5); add_point('Red ground glow',(2.5,0,.25),(1,.008,.02),230,1.5)
# Cinematic camera tracking animated target
bpy.ops.object.empty_add(location=(0,0,1.35)); target=bpy.context.object; target.name='Camera action target'
bpy.ops.object.camera_add(location=(0,-10,4.0)); cam=bpy.context.object; cam.name='Cinematic combat camera'; cam.data.lens=47; scene.camera=cam
con=cam.constraints.new('TRACK_TO'); con.target=target; con.track_axis='TRACK_NEGATIVE_Z'; con.up_axis='UP_Y'
for f,loc,lens,tloc in [(1,(0,-10.7,4.0),47,(0,0,1.25)),(72,(0,-9.3,3.5),50,(0,0,1.35)),(120,(.5,-8.4,3.0),53,(0,0,1.15)),(180,(-.5,-9.0,3.3),48,(0,0,1.25)),(224,(0,-10,3.8),46,(0,0,1.3)),(286,(0,-8.2,4.5),50,(0,0,1.65)),(335,(0,-9.1,4.0),51,(0,0,1.45)),(378,(0,-10,3.8),48,(0,0,1.3)),(420,(0,-7.9,3.0),58,(0,0,1.2)),(448,(0,-9.5,3.25),54,(0,0,1.25)),(480,(0,-9.5,3.25),54,(0,0,1.25))]:
 cam.location=loc; cam.keyframe_insert('location',frame=f); cam.data.lens=lens; cam.data.keyframe_insert('lens',frame=f); target.location=tloc; target.keyframe_insert('location',frame=f)
smooth_keys(cam); smooth_keys(target)
# 3D title cards in the upper third, designed as part of the rendered scene
white=emm('Ice title text',(.67,.82,1),2.0); muted=emm('Subtitle accent',(.08,.43,.85),2.0)
def text3d(body,name,loc,size,material):
 d=bpy.data.curves.new(name,'FONT'); d.body=body; d.align_x='CENTER'; d.align_y='CENTER'; d.size=size; d.extrude=.001; o=bpy.data.objects.new(name,d); scene.collection.objects.link(o); o.location=loc; o.rotation_euler=(math.radians(90),0,0); o.data.materials.append(material); return o
title=text3d('SHADOWS  &  IRON','Episode title',(0,-2.35,3.3),.42,white)
subtitle=text3d('EPISODE 01  /  SHADOWS AND IRON','Episode subtitle',(0,-2.33,2.92),.12,muted)
for o in [title,subtitle]:
 for f,scale in [(1,(.001,.001,.001)),(6,(1,1,1)),(55,(1,1,1)),(68,(.001,.001,.001)),(451,(.001,.001,.001)),(459,(1,1,1)),(477,(1,1,1)),(480,(.001,.001,.001))]: o.scale=scale; o.keyframe_insert('scale',frame=f)
# Small closing credit line
credit=text3d('A CINEMATIC ANIMATION TEST  |  3D CHARACTER ACTION','Closing credit',(0,-2.33,2.62),.085,muted)
for f,sc in [(1,(.001,)*3),(444,(.001,)*3),(454,(1,1,1)),(476,(1,1,1)),(480,(.001,)*3)]: credit.scale=sc; credit.keyframe_insert('scale',frame=f)
# Gentle global bloom on emission FX
scene.use_nodes=True; nt=scene.node_tree; nt.nodes.clear(); rl=nt.nodes.new('CompositorNodeRLayers'); glare=nt.nodes.new('CompositorNodeGlare'); glare.glare_type='FOG_GLOW'; glare.quality='HIGH'; glare.threshold=1.5; comp=nt.nodes.new('CompositorNodeComposite'); nt.links.new(rl.outputs['Image'],glare.inputs['Image']); nt.links.new(glare.outputs['Image'],comp.inputs['Image'])
# Set animation curves to smooth but preserve very sharp impacts/flash energy keys
for obj in scene.objects:
 if obj.animation_data and obj.animation_data.action:
  for fc in obj.animation_data.action.fcurves:
   for kp in fc.keyframe_points:
    if 'energy' in fc.data_path or 'scale' in fc.data_path and obj.name.startswith('Impact shock ring'): kp.interpolation='LINEAR'
    else: kp.interpolation='BEZIER'
# Metadata manifest
with open(OUT+'/render_manifest.json','w') as f: json.dump({'title':'Shadows & Iron — Episode 01','frames':FRAMES,'fps':FPS,'source_characters':['Nightshade J Friedrich.fbx','Prisoner B Styperek.fbx'],'motion_assets':['Motion_Extracted_Red.bvh','Motion_Extracted_Black.bvh'],'notes':'BVH motions were derived from 2D animated silhouettes and retargeted with partial per-bone rotation constraints; final frame render must be inspected.'},f,ensure_ascii=False,indent=2)
print('SCENE_READY',json.dumps({'objects':len(scene.objects),'frames':FRAMES,'night_action':night_arm.animation_data.action.name if night_arm.animation_data and night_arm.animation_data.action else None,'prison_action':prison_arm.animation_data.action.name if prison_arm.animation_data and prison_arm.animation_data.action else None,'engine':scene.render.engine}),flush=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT+'/episode_01.blend', compress=True)
if os.environ.get('SCENE_BUILD'):
 print('SCENE_BUILD_COMPLETE',flush=True)
elif os.environ.get('SCENE_ONLY'):
 scene.render.filepath=OUT+'/preview.png'; scene.frame_set(112); bpy.ops.render.render(write_still=True)
 print('PREVIEW_COMPLETE',flush=True)
else:
 bpy.ops.render.render(animation=True)
 print('RENDER_COMPLETE',flush=True)
