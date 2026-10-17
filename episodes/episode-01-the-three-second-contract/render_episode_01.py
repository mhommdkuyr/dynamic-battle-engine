#!/usr/bin/env python3
"""Deterministic original Arabic short-animation renderer. No network/API keys needed."""
import math, os, subprocess, wave
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, features

W,H,FPS,DURATION,SR = 1280,720,30,52,44100
OUT=Path(os.environ.get("EPISODE_OUTPUT_DIR","output")); OUT.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(147)
y=np.linspace(0,1,H,dtype=np.float32)[:,None]; x=np.linspace(0,1,W,dtype=np.float32)[None,:]
BASE=np.zeros((H,W,3),np.uint8)
BASE[:,:,0]=np.clip(20+21*(1-y)+9*x,0,255)
BASE[:,:,1]=np.clip(8+10*(1-y)+5*x,0,255)
BASE[:,:,2]=np.clip(11+12*(1-y)+7*x,0,255)
BUILD=[]
for bx in range(-20,W+50,64):
    bh=int(rng.integers(110,290)); bw=int(rng.integers(38,62))
    BUILD.append((bx,H-90-bh,bw,bh,int(rng.integers(14,30))))
STARS=[(int(rng.integers(10,W-10)),int(rng.integers(15,420)),float(rng.uniform(.4,1)),float(rng.uniform(0,6.28))) for _ in range(90)]
def font(size,bold=False,latin=False):
    paths=(['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'] if latin else
    (['/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'] if bold else ['/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']))
    for p in (paths if bold or latin else paths):
        if Path(p).exists():
            try: return ImageFont.truetype(p,size,layout_engine=ImageFont.Layout.RAQM if features.check('raqm') else ImageFont.Layout.BASIC)
            except Exception: return ImageFont.truetype(p,size)
    return ImageFont.load_default()
def sm(a,b,t):
    q=max(0,min(1,(t-a)/(b-a))); return q*q*(3-2*q)
def ln(im,a,b,c,w=2): cv2.line(im,tuple(map(int,a)),tuple(map(int,b)),c,w,cv2.LINE_AA)
def pg(im,pts,c,outline=(5,8,18),th=3):
    p=np.array(pts,np.int32).reshape((-1,1,2)); cv2.fillPoly(im,[p],c,lineType=cv2.LINE_AA)
    if th: cv2.polylines(im,[p],True,outline,th,cv2.LINE_AA)
def bg(t):
    im=BASE.copy()
    ov=im.copy(); cv2.ellipse(ov,(640,380),(420,250),0,0,360,(58,20,32),-1,cv2.LINE_AA); cv2.addWeighted(ov,.23,im,.77,0,im)
    for sx,sy,b,p in STARS:
        c=int(55+145*b*(.5+.5*math.sin(t+p))); cv2.circle(im,(sx,sy),1 if b<.7 else 2,(c,int(c*.78),int(c*.48)),-1,cv2.LINE_AA)
    shift=int(6*math.sin(t*.18))
    for bx,by,bw,bh,shade in BUILD:
        x0=bx+shift; x1=x0+bw
        cv2.rectangle(im,(x0,by),(x1,590),(shade+13,shade//2+5,shade//2+9),-1)
        for wy in range(by+15,575,25):
            for wx in range(x0+8,x1-3,17):
                if (wx*5+wy*3)%4:
                    cv2.rectangle(im,(wx,wy),(wx+4,wy+7),(28,47,77),-1)
    pg(im,[(0,588),(1280,588),(1280,720),(0,720)],(20,18,28),(5,7,15),0)
    for i in range(12):
        yy=590+i*i*1.2
        if yy<720: ln(im,(0,yy),(W,yy),(36,27,22),1)
    for xx in range(-600,1900,150): ln(im,(640,588),(xx,720),(43,27,21),1)
    return im
def fighter(im,cx,ground,scale,face,team,pose,t):
    cyan=team=="cyan"
    primary=(224,242,249) if cyan else (31,28,45)
    armor=(235,190,69) if cyan else (67,38,49)
    dark=(42,24,12) if cyan else (18,8,7)
    accent=(255,245,70) if cyan else (54,66,255)
    hair=(30,16,8) if cyan else (36,16,37)
    s=scale; x=float(cx); gy=float(ground)
    leg=math.sin(t*24)*19 if pose=="dash" else (12*math.sin(t*11) if pose=="strike" else 4*math.sin(t*3))
    dy=-12*math.sin(t*22) if pose=="dash" else 0; gy+=dy*s
    if pose in ("dash","strike") or (not cyan and 16<t<35):
        col=(255,245,120) if cyan else (54,66,255)
        for r in (int(75*s),int(52*s)):
            cv2.ellipse(im,(int(x),int(gy-120*s)),(r,int(r*1.3)),0,0,360,col,2,cv2.LINE_AA)
    hip=(x,gy-82*s)
    k1=(x+face*20*s+leg*s*.4,gy-40*s); f1=(x+face*29*s+leg*s,gy-7*s)
    k2=(x-face*24*s-leg*s*.2,gy-42*s); f2=(x-face*42*s-leg*s*.5,gy-7*s)
    ln(im,hip,k1,dark,max(12,int(22*s))); ln(im,k1,f1,primary,max(10,int(17*s)))
    ln(im,hip,k2,dark,max(12,int(22*s))); ln(im,k2,f2,armor,max(10,int(17*s)))
    cv2.ellipse(im,(int(f1[0]),int(f1[1])),(int(18*s),int(7*s)),0,0,360,dark,-1,cv2.LINE_AA)
    cv2.ellipse(im,(int(f2[0]),int(f2[1])),(int(17*s),int(7*s)),0,0,360,dark,-1,cv2.LINE_AA)
    pg(im,[(x-29*s,gy-160*s),(x+23*s,gy-164*s),(x+32*s,gy-115*s),(x+20*s,gy-78*s),(x-22*s,gy-79*s),(x-34*s,gy-118*s)],dark,(5,8,18),3)
    pg(im,[(x-24*s,gy-155*s),(x+17*s,gy-157*s),(x+22*s,gy-118*s),(x+12*s,gy-91*s),(x-17*s,gy-91*s),(x-25*s,gy-119*s)],armor,(15,22,37),2)
    pg(im,[(x-3*s,gy-143*s),(x+10*s,gy-132*s),(x-1*s,gy-116*s),(x-14*s,gy-132*s)],accent,dark,1)
    if pose=="strike": arms=[(x+face*78*s,gy-148*s),(x-face*20*s,gy-125*s)]
    elif pose=="dash": arms=[(x+face*56*s,gy-150*s),(x-face*42*s,gy-126*s)]
    else: arms=[(x+face*28*s,gy-140*s),(x-face*25*s,gy-132*s)]
    for idx,wrist in enumerate(arms):
        shoulder=(x+(face*27 if idx==0 else -face*25)*s,gy-151*s)
        elbow=(x+(face*42 if idx==0 else -face*38)*s,gy-(145 if idx==0 else 134)*s)
        ln(im,shoulder,elbow,dark,max(14,int(24*s))); ln(im,elbow,wrist,armor,max(12,int(18*s)))
        cv2.circle(im,(int(wrist[0]),int(wrist[1])),max(5,int(10*s)),accent,-1,cv2.LINE_AA)
    cv2.rectangle(im,(int(x-9*s),int(gy-185*s)),(int(x+10*s),int(gy-155*s)),(190,185,177),-1)
    cv2.ellipse(im,(int(x),int(gy-207*s)),(int(23*s),int(28*s)),0,0,360,(189,179,170),-1,cv2.LINE_AA)
    hp=[(x-27*s,gy-218*s),(x-41*s,gy-243*s),(x-19*s,gy-235*s),(x-10*s,gy-258*s),(x+2*s,gy-238*s),(x+25*s,gy-246*s),(x+21*s,gy-222*s),(x+31*s,gy-210*s),(x+16*s,gy-201*s),(x-20*s,gy-201*s)]
    pg(im,hp,hair,(4,6,12),3)
    for ex in (x+5*s,x+16*s) if face==1 else (x-16*s,x-5*s):
        ln(im,(ex,gy-209*s),(ex+face*5*s,gy-208*s),accent,max(2,int(3*s)))
def caption_layer(im,t):
    out=Image.fromarray(cv2.cvtColor(im,cv2.COLOR_BGR2RGB)).convert("RGBA"); d=ImageDraw.Draw(out,"RGBA")
    d.rounded_rectangle((36,28,286,70),radius=10,fill=(4,10,25,175),outline=(64,202,245,150),width=1)
    d.text((78,49),"RXW",font=font(16,True,True),fill=(91,222,255,255),anchor="mm")
    d.text((225,49),"الحلقة 01",font=font(18,True),fill=(224,245,255,255),anchor="mm",direction="rtl",language="ar")
    caps=[(.8,4.7,"في عالمٍ تُقاس فيه الوعود بالثواني…"),(5.2,8.2,"لا توجد فرصة ثانية."),(9,12.3,"رايان: أمامك ثلاث ثوانٍ لتتراجع."),(12.8,15.6,"الخصم: ثلاث ثوانٍ تكفيني."),(17,18.5,"ثلاثة…"),(19,20.5,"اثنان…"),(21,22.5,"واحد!"),(26.4,29,"تم تفعيل العقد."),(35.8,38.7,"انتهت الثواني."),(40,43.5,"رايان: لا… لقد بدأ للتو."),(45,48.7,"قوةٌ ثالثة كانت تراقب.")]
    cap=next((c for a,b,c in caps if a<=t<=b),None)
    if cap:
        d.rounded_rectangle((125,615,1155,684),radius=16,fill=(2,5,15,225),outline=(54,175,222,170),width=2)
        d.text((640,650),cap,font=font(27,True),fill=(250,252,255,255),anchor="mm",direction="rtl",language="ar",stroke_width=1,stroke_fill=(3,7,17,255))
    if t<.75: d.rectangle((0,0,W,H),fill=(0,0,0,int(255*(1-t/.75))))
    if t>50:
        a=int(255*sm(50.4,51.3,t))
        d.text((640,245),"العقد ذو الثواني الثلاث",font=font(52,True),fill=(242,249,255,a),anchor="mm",direction="rtl",language="ar",stroke_width=2,stroke_fill=(16,25,50,a))
        d.text((640,322),"THE THREE-SECOND CONTRACT",font=font(24,True,True),fill=(91,222,255,a),anchor="mm")
        d.text((640,382),"الحلقة الأولى",font=font(28,True),fill=(255,255,255,a),anchor="mm",direction="rtl",language="ar")
        d.text((640,424),"يتبع",font=font(24,True),fill=(91,222,255,a),anchor="mm",direction="rtl",language="ar")
        d.text((640,538),"RXW / RAYAN X WORLD",font=font(19,True,True),fill=(144,158,183,a),anchor="mm")
    return cv2.cvtColor(np.asarray(out.convert("RGB")),cv2.COLOR_RGB2BGR)
def score(path):
    n=SR*DURATION; t=np.arange(n,dtype=np.float64)/SR; a=np.zeros(n,dtype=np.float64)
    roots=[55,65.41,49,73.42,55,41.2,55]
    for i,start in enumerate(np.arange(0,DURATION,4)):
        end=min(DURATION,start+4.2); lo=int(start*SR); hi=int(end*SR); tt=t[lo:hi]-start; root=roots[i%len(roots)]
        env=np.clip(np.minimum(tt/.6,(end-start-tt)/.65),0,1)
        a[lo:hi]+=(np.sin(2*np.pi*root*tt)+.4*np.sin(2*np.pi*root*1.5*tt))*.055*env
    notes=[220,261.63,196,293.66,246.94,220,164.81,196]
    for start in np.arange(.25,DURATION,.5):
        i=int(start*SR); l=min(int(.42*SR),n-i); tt=np.arange(l)/SR; f=notes[int(start*2)%len(notes)]
        a[i:i+l]+=(np.sin(2*np.pi*f*tt)+.3*np.sin(4*np.pi*f*tt))*np.exp(-tt*7)*.07
    for start,dur,amp in [(7.8,.45,.18),(16.5,.55,.2),(24.5,.5,.25),(28.7,1.25,.48),(30,.65,.34),(34,.45,.2),(47.5,1.5,.28),(50,1.1,.2)]:
        i=int(start*SR); l=min(int(dur*SR),n-i); tt=np.arange(l)/SR
        noise=rng.normal(0,1,l); kernel=np.ones(7)/7; noise=np.convolve(noise,kernel,'same')
        env=np.sin(np.pi*np.clip(tt/dur,0,1))**2
        tone=np.sin(2*np.pi*(80+60*np.exp(-tt*3))*tt)
        a[i:i+l]+=amp*env*(noise*.45+tone*.7)
    a*=np.clip(np.minimum(t/.8,(DURATION-t)/1.2),0,1); a=np.tanh(a*1.8); a*=.85/(np.max(np.abs(a)) or 1)
    stereo=np.stack((a,np.roll(a,int(SR*.007))*.96),axis=1); pcm=(stereo*32767).astype(np.int16)
    with wave.open(str(path),"wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes(pcm.tobytes())
def main():
    frames=int(FPS*DURATION); raw=OUT/"episode_01_video_only.mp4"; wav=OUT/"episode_01_score.wav"; final=OUT/"episode_01_the_three_second_contract_ar.mp4"
    cmd=["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pixel_format","bgr24","-video_size",f"{W}x{H}","-framerate",str(FPS),"-i","pipe:0","-an","-c:v","libx264","-preset","ultrafast","-crf","26","-threads","2","-pix_fmt","yuv420p",str(raw)]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    if p.stdin is None: raise RuntimeError("FFmpeg stdin unavailable")
    for i in range(frames):
        t=i/FPS; im=bg(t)
        if t<5:
            fighter(im,360,580,.64,1,"cyan","idle",t); fighter(im,920,580,.66,-1,"red","idle",t)
        elif t<16:
            u=sm(5,10,t); fighter(im,360+50*u,585,.96,1,"cyan","guard",t); fighter(im,920-55*u,585,.98,-1,"red","guard",t)
        elif t<25:
            fighter(im,410,585,1,1,"cyan","guard",t); fighter(im,865,585,1.02,-1,"red","guard",t)
            if t>=17:
                n="3" if t<18.5 else ("2" if t<21 else "1")
                ov=im.copy(); cv2.circle(ov,(640,314),112,(255,237,190),3,cv2.LINE_AA); cv2.addWeighted(ov,.35,im,.65,0,im)
                cv2.putText(im,n,(596,368),cv2.FONT_HERSHEY_DUPLEX,3.3,(255,248,240),7,cv2.LINE_AA)
        elif t<35.5:
            u=sm(25,29.3,t); hx=360+255*u; ex=920-255*u
            pose="dash" if t<29.4 else "strike"; fighter(im,hx,586,1,1,"cyan",pose,t); fighter(im,ex,586,1,-1,"red","hit" if t>=29.4 else "dash",t)
            if 25<t<29.5:
                for k in range(14):
                    yy=200+k*25; ln(im,(hx-150,yy),(hx-85,yy-4),(241,187,90),1); ln(im,(ex+110,yy+4),(ex+50,yy),(63,57,170),1)
            if 28<t<32:
                for rad in [int(10+65*abs(math.sin((t-28)*math.pi/4))),45+int((t-28)*60),80+int((t-28)*70)]:
                    cv2.circle(im,(640,370),rad,(255,237,190),2,cv2.LINE_AA)
                for k in range(28):
                    aa=k*math.pi*2/28+t*1.5; rr=45+(t-28)*90+(k%4)*12
                    ln(im,(640+math.cos(aa)*rr,370+math.sin(aa)*rr),(640+math.cos(aa)*(rr+20),370+math.sin(aa)*(rr+20)),(255,214,110) if k%2 else (125,91,251),2)
        elif t<44:
            fighter(im,525,590,.98,1,"cyan","guard",t); fighter(im,790,590,.94,-1,"red","hit",t)
        elif t<49:
            fighter(im,525,590,.98,1,"cyan","idle",t); fighter(im,790,590,.91,-1,"red","hit",t)
            x0,gy=1020,514; cv2.ellipse(im,(x0,gy-72),(100,120),0,0,360,(145,60,244),2,cv2.LINE_AA)
            pg(im,[(x0-26,gy),(x0-19,gy-63),(x0-7,gy-88),(x0+9,gy-63),(x0+26,gy),(x0+16,gy+22),(x0-18,gy+22)],(9,8,24),(117,62,209),3)
        else:
            fighter(im,395,610,.63,1,"cyan","idle",t); fighter(im,885,610,.63,-1,"red","idle",t)
            ov=im.copy(); cv2.rectangle(ov,(0,0),(W,H),(3,4,12),-1); cv2.addWeighted(ov,.60,im,.40,0,im)
            cv2.rectangle(im,(96,120),(1184,590),(5,10,23),2,cv2.LINE_AA)
        im=caption_layer(im,t); p.stdin.write(im.tobytes())
        if i%300==0: print(f"Rendered {i}/{frames} frames",flush=True)
    p.stdin.close()
    if p.wait()!=0: raise RuntimeError("video encode failed")
    score(wav)
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",str(raw),"-i",str(wav),"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",str(final)],check=True)
    raw.unlink(missing_ok=True); wav.unlink(missing_ok=True)
    print(f"EPISODE_VIDEO={final.resolve()}",flush=True)
if __name__=="__main__": main()
