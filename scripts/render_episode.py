import bpy, math, os, json, random, argparse, sys
from mathutils import Vector
p=argparse.ArgumentParser(); p.add_argument('--duration',type=float,default=60); p.add_argument('--fps',type=int,default=24); p.add_argument('--width',type=int,default=1280); p.add_argument('--height',type=int,default=720); p.add_argument('--output',default='/home/user/anime01/render'); p.add_argument('--seed',type=int,default=7319)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
BASE=os.environ.get('ANIME_ASSET_DIR','/home/user/anime01'); MOT=os.path.join(BASE,'mocap'); random.seed(a.seed)
def material(name,c,metal=0,rough=.4):
 m=bpy.data.materials.new(name); m.diffuse_color=(*c,1); m.use_nodes=True; n=m.node_tree.nodes.get('Principled BSDF')
 if n: n.inputs['Base Color'].default_value=(*c,1); n.inputs['Metallic'].default_value=metal; n.inputs['Roughness'].default_value=rough; (n.inputs.get('Emission Color') or n.inputs.get('Emission')).default_value=(*c,1); n.inputs['Emission Strength'].default_value=.45
 return m
def import_objects(path):
 old=set(bpy.context.scene.objects); bpy.ops.import_scene.fbx(filepath=path,use_anim=True); return [o for o in bpy.context.scene.objects if o not in old]
def character(file,name,x,rot):
 objs=import_objects(os.path.join(BASE,file)); arm=next((o for o in objs if o.type=='ARMATURE'),None); mesh=next((o for o in objs if o.type=='MESH'),None)
 if arm is None or mesh is None: raise RuntimeError('Invalid FBX rig/mesh: '+file)
 root=bpy.data.objects.new(name+'_ROOT',None); bpy.context.scene.collection.objects.link(root)
 for o in objs:
  w=o.matrix_world.copy(); o.parent=root; o.matrix_world=w
 root.location=(0,0,0); root.rotation_euler.z=0
 for b in arm.pose.bones: b.rotation_mode='QUATERNION'
 arm.name=name+'_RIG'; arm.animation_data_create(); arm.animation_data.action=None
 # Pack imported diffuse, normal, specular and glow maps for deterministic headless rendering.
 for im in bpy.data.images:
  if im.source=='FILE' and im.size[0]>0 and not im.packed_file:
   try: im.pack()
   except Exception: pass
 root.location.x=x; root.rotation_euler.z=rot
 return {'root':root,'arm':arm,'mesh':mesh,'bones':set(b.name for b in arm.data.bones)}
def action_from(rel,name,bones):
 objs=import_objects(os.path.join(MOT,rel)); src=next((o for o in objs if o.type=='ARMATURE'),None)
 if src is None or not src.animation_data or not src.animation_data.action: raise RuntimeError('No animation on '+rel)
 act=src.animation_data.action.copy(); act.name=name; removed=0
 for fc in list(act.fcurves):
  path=fc.data_path
  if not path.startswith('pose.bones['): bpy.data.actions.remove(act) if False else None; act.fcurves.remove(fc); removed+=1; continue
  try: bn=path.split('pose.bones["',1)[1].split('"]',1)[0]
  except Exception: bn=''
  if bn not in bones: act.fcurves.remove(fc); removed+=1
 for o in objs: bpy.data.objects.remove(o,do_unlink=True)
 print('MOTION',name,'channels',len(act.fcurves),'removed',removed,'frames',list(act.frame_range),flush=True)
 if len(act.fcurves)<80: raise RuntimeError('Not enough compatible Mixamo channels in '+name)
 return act
def segment(arm,act,start,duration,fps,label):
 tr=arm.animation_data.nla_tracks.new(); tr.name=label[:60]; fr=1+round(start*fps); length=max(2,round(duration*fps)); st=tr.strips.new(label,fr,act); st.action_frame_start=act.frame_range[0]; st.action_frame_end=act.frame_range[1]; st.scale=length/max(1,st.action_frame_end-st.action_frame_start); st.blend_type='REPLACE'; st.extrapolation='NOTHING'; st.blend_in=min(8,length*.06); st.blend_out=min(8,length*.06)
def root_keys(root,rows,fps):
 for t,loc,rz in rows:
  f=1+round(t*fps); root.location=loc; root.rotation_euler.z=rz; root.keyframe_insert(data_path='location',frame=f); root.keyframe_insert(data_path='rotation_euler',frame=f)
 if root.animation_data and root.animation_data.action:
  for fc in root.animation_data.action.fcurves:
   for k in fc.keyframe_points:k.interpolation='BEZIER'
def curve(name,pts,mat,bevel=.02,cyclic=False):
 d=bpy.data.curves.new(name,'CURVE'); d.dimensions='3D'; d.bevel_depth=bevel; d.bevel_resolution=2; sp=d.splines.new('POLY'); sp.points.add(len(pts)-1)
 for q,v in zip(sp.points,pts):q.co=(*v,1)
 sp.use_cyclic_u=cyclic; ob=bpy.data.objects.new(name,d); bpy.context.scene.collection.objects.link(ob); ob.data.materials.append(mat); return ob
def make_arena(fps):
 s=material('Wet Obsidian',(0.022,.032,.055),.42,.2); rock=material('Ruined Concrete',(.105,.13,.18),.2,.65); steel=material('Black Steel',(.08,.12,.18),.8,.28); cyan=material('Cyan Plasma',(.06,.64,1),.2,.2); violet=material('Rift Violet',(.42,.09,1),.2,.25); fire=material('Molten Sparks',(1,.19,.025),.1,.25); white=material('Impact White',(.94,.98,1),0,.2); rain=material('Storm Rain',(.23,.42,.6),0,.35)
 bpy.ops.mesh.primitive_plane_add(size=120,location=(0,0,-.07)); bpy.context.object.name='Rain_Slick_Arena'; bpy.context.object.data.materials.append(s)
 for i in range(38):
  bpy.ops.mesh.primitive_cube_add(size=1,location=(random.uniform(-8,8),random.uniform(2,10),random.uniform(.1,.5))); o=bpy.context.object; o.name='Broken_Basalt'; o.dimensions=(random.uniform(.25,1.3),random.uniform(.25,1.3),random.uniform(.15,.65)); o.rotation_euler=(random.uniform(-.3,.3),random.uniform(-.3,.3),random.uniform(-math.pi,math.pi)); o.data.materials.append(rock if i%3 else steel); b=o.modifiers.new('Chipped edges','BEVEL'); b.width=.06; b.segments=1
 for side in (-1,1):
  for j in range(3):
   bpy.ops.mesh.primitive_cube_add(size=1,location=(side*(4.5+j*.95),3.5+j*1.35,1.7+random.uniform(-.35,.45))); o=bpy.context.object; o.name='Ruined_Pillar'; o.dimensions=(.45,.55,3.5+random.random()); o.rotation_euler=(random.uniform(-.16,.16),random.uniform(-.3,.3),random.uniform(-.12,.12)); o.data.materials.append(steel); b=o.modifiers.new('Shattered edges','BEVEL'); b.width=.08; b.segments=1
 for i in range(18):
  x=random.uniform(-4,4); y=random.uniform(-2,3); curve('Hairline_Fracture',[(x,y,.005),(x+random.uniform(-.5,.5),y-.35,.005),(x+random.uniform(-.8,.8),y-.8,.005)],steel,.012)
 # Rain streaks cycle through the shot; each streak is rendered as geometry rather than a particle placeholder.
 for i in range(100):
  x=random.uniform(-8,8); y=random.uniform(-2,8); z=random.uniform(2,9); dz=random.uniform(.3,.75); dx=random.uniform(-.12,.12); o=curve('Rain_Streak',[(x,y,z),(x+dx,y-.02,z-dz)],rain,random.uniform(.003,.007)); o.location=(0,0,0); o.keyframe_insert(data_path='location',frame=1); o.location=(random.uniform(-.4,.4),0,-4); o.keyframe_insert(data_path='location',frame=1+max(2,round(1.2*fps)))
  if o.animation_data and o.animation_data.action:
   for fc in o.animation_data.action.fcurves: fc.modifiers.new('CYCLES').mode_after='REPEAT'; fc.modifiers[-1].mode_before='REPEAT'
 # Six slashes/spark bursts and four expanding shockwaves are timed to the attack beats.
 for i,t in enumerate((15.5,21.8,30.4,39.2,47.3,50.2)):
  c=cyan if i%2==0 else violet; x=-.7 if i%2==0 else .6; o=curve('Plasma_Slash',[(x-1.25,-.65,1.2),(x-.45,-.9,1.85),(x+.2,-.75,2.05),(x+1.15,-.8,1.45)],c,.055)
  for sec,scale in ((t-.18,.001),(t,1),(t+.13,.7),(t+.34,.001)):o.scale=(scale,)*3;o.keyframe_insert(data_path='scale',frame=1+round(sec*fps))
 for burst,t in enumerate((16,22,31,40,48,50.5)):
  for k in range(16):
   start=Vector((random.uniform(-.25,.25),-.6,random.uniform(1.2,1.9))); direction=Vector((random.uniform(-1,1),random.uniform(-.35,.35),random.uniform(-.1,1))).normalized(); bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=random.uniform(.018,.05),location=start); o=bpy.context.object; o.name='Collision_Spark'; o.data.materials.append(fire if k%4 else white)
   f0=1+round((t-.04)*fps); f1=1+round((t+.1)*fps); f2=1+round((t+.42)*fps); o.scale=(.001,)*3;o.keyframe_insert(data_path='scale',frame=f0);o.scale=(1,)*3;o.keyframe_insert(data_path='scale',frame=f1);o.location=start+direction*random.uniform(.35,1.65);o.keyframe_insert(data_path='location',frame=f2);o.scale=(.001,)*3;o.keyframe_insert(data_path='scale',frame=f2)
 for i,t in enumerate((17,32,42,49.5)):
  bpy.ops.mesh.primitive_torus_add(major_radius=1,minor_radius=.025,major_segments=48,minor_segments=6,location=(0,-.1,.02)); o=bpy.context.object;o.name='Impact_Shockwave';o.data.materials.append(cyan if i%2==0 else fire)
  for sec,scale in ((t-.12,.001),(t+.15,.7),(t+.9,3.2)):o.scale=(scale,scale,scale);o.keyframe_insert(data_path='scale',frame=1+round(sec*fps))
 return {'cyan':cyan,'violet':violet,'white':white}
def make_camera(fps):
 bpy.ops.object.camera_add(location=(0,-10.5,3)); c=bpy.context.object;c.name='Cinematic_Anime_Camera';c.data.lens=48;bpy.context.scene.camera=c
 shots=[(0,(0,-10.8,3),(0,0,1.15),45),(7,(0,-9,2.4),(0,0,1.15),49),(12,(0,-7.8,2.2),(0,0,1.2),54),(16,(-.65,-6.4,2),(0,0,1.3),60),(23,(.55,-6.6,2.6),(0,0,1.25),52),(28,(0,-8.2,3.6),(0,0,1.6),45),(32,(.7,-6.2,4),(0,0,1.9),52),(39,(-.3,-6.8,3),(0,0,1.8),49),(44,(0,-7.6,2.2),(0,0,1.25),56),(49,(0,-5.2,2),(0,0,1.4),62),(50.5,(0,-4.4,2.1),(0,0,1.45),68),(54,(0,-7.4,2.6),(0,0,1.15),52),(60,(0,-8.2,2.6),(0,0,1.2),48)]
 for sec,loc,look,lens in shots:
  f=1+round(sec*fps);c.location=loc;c.rotation_euler=(Vector(look)-c.location).to_track_quat('-Z','Y').to_euler();c.keyframe_insert(data_path='location',frame=f);c.keyframe_insert(data_path='rotation_euler',frame=f);c.data.lens=lens;c.data.keyframe_insert(data_path='lens',frame=f)
 for d in (c.animation_data,c.data.animation_data):
  if d and d.action:
   for fc in d.action.fcurves:
    for k in fc.keyframe_points:k.interpolation='BEZIER'
def add_text(body,name,loc,size,material,start,end,fps):
 cv=bpy.data.curves.new(name,'FONT');cv.body=body;cv.size=size;cv.extrude=.001;ob=bpy.data.objects.new(name,cv);bpy.context.scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(math.radians(90),0,0);cv.materials.append(material)
 for sec,s in ((start,.001),(start+.35,1),(end-.35,1),(end,.001)):ob.scale=(s,)*3;ob.keyframe_insert(data_path='scale',frame=1+round(sec*fps))
def main():
 bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;fps=a.fps;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=a.width;scene.render.resolution_y=a.height;scene.render.resolution_percentage=100;scene.render.fps=fps;scene.render.fps_base=1;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.image_settings.color_depth='8';scene.render.film_transparent=False
 sh=scene.display.shading;sh.light='STUDIO'
 try:sh.studio_light='paint.sl'
 except Exception:pass
 sh.color_type='TEXTURE';sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH';sh.curvature_ridge_factor=1.6;sh.curvature_valley_factor=1.2;sh.show_specular_highlight=True;sh.show_object_outline=True;sh.background_type='WORLD';scene.world=bpy.data.worlds.new('Midnight Storm');scene.world.color=(.006,.009,.02);scene.view_settings.view_transform='Standard';scene.view_settings.look='Medium High Contrast';scene.frame_start=1;scene.frame_end=round(a.duration*fps)
 n=character('nightshade.fbx','Nightshade',-1.85,0);p=character('prisoner.fbx','Prisoner',1.85,math.pi);bones=n['bones']&p['bones']; specs=[('Superhero/WatchOverCity_mixamo.fbx','LOOKOUT'),('Superhero/IronMan_Combat_mixamo.fbx','IRON_COMBAT'),('Superhero/MutantClaws_mixamo.fbx','CLAW_COMBAT'),('Superhero/SuperHeroLanding_Takeoff_mixamo.fbx','JUMP_LAND'),('Superhero/SuperHeroFlying_mixamo.fbx','HERO_FLIGHT'),('Superhero/HulkTransformation_mixamo.fbx','TITAN_ROAR')]; acts={name:action_from(path,name,bones) for path,name in specs}
 for who,rig,sequence in [('Nightshade',n,[('LOOKOUT',0,12),('IRON_COMBAT',12,16),('JUMP_LAND',28,7.5),('HERO_FLIGHT',35.5,8.5),('IRON_COMBAT',44,12)]),('Prisoner',p,[('TITAN_ROAR',0,12),('CLAW_COMBAT',12,16),('JUMP_LAND',28,8),('IRON_COMBAT',36,8),('TITAN_ROAR',44,16)])]:
  for name,start,dur in sequence:segment(rig['arm'],acts[name],start,dur,fps,who+'_'+name+'_'+str(start))
 root_keys(n['root'],[(0,(-1.85,0,0),0),(12,(-1.8,0,0),0),(15,(-.9,-.25,0),-.12),(20,(-1.15,-.15,0),.1),(25,(-1.65,0,0),0),(28,(-1.65,0,0),0),(31,(-.9,-.1,.45),-.2),(35,(-.4,-.25,.7),.15),(39,(-1.1,-.15,.2),-.2),(44,(-1.65,0,0),0),(47,(-.7,-.2,0),-.1),(50,(-.3,-.2,.05),.12),(52,(-.8,-.15,0),-.1),(54,(-1.75,0,0),0),(60,(-1.75,0,0),0)],fps)
 root_keys(p['root'],[(0,(1.85,0,0),math.pi),(12,(1.8,0,0),math.pi),(15,(.9,.05,0),math.pi+.12),(20,(1.2,0,0),math.pi-.1),(25,(1.65,0,0),math.pi),(28,(1.65,0,0),math.pi),(31,(.85,.1,.3),math.pi+.2),(35,(.5,0,.45),math.pi-.1),(39,(1.1,.05,.2),math.pi+.15),(44,(1.65,0,0),math.pi),(47,(.65,.1,0),math.pi+.1),(50,(.3,.05,.05),math.pi-.12),(52,(.8,0,0),math.pi+.1),(54,(1.75,0,0),math.pi),(60,(1.75,0,0),math.pi)],fps)
 effects=make_arena(fps);make_camera(fps);title=material('Title Pearl',(.72,.91,1),.1,.3);add_text('SHADOWS  &  IRON','Main_Title',(-2.15,-2.5,3.15),.43,title,.6,4.5,fps);add_text('EPISODE 01  /  BREAK THE CAGE','Sub_Title',(-1.8,-2.5,2.75),.16,effects['cyan'],1.0,4.2,fps);add_text('TO BE CONTINUED','End_Title',(-1.05,-2.5,2.9),.34,title,56,60,fps)
 os.makedirs(a.output,exist_ok=True);scene.render.filepath=os.path.join(a.output,'frame_');blend=os.path.join(a.output,'episode01_scene.blend');bpy.ops.wm.save_as_mainfile(filepath=blend);print('SCENE_READY',json.dumps({'fps':fps,'duration':a.duration,'frame_end':scene.frame_end,'resolution':[a.width,a.height],'characters':['Nightshade','Prisoner'],'motions':list(acts)}),flush=True);bpy.ops.render.render(animation=True);print('RENDER_COMPLETE',a.output,flush=True)
if __name__=='__main__':main()
