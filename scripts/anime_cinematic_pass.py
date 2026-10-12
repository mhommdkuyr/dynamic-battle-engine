import argparse
import json
import math
import pathlib
import random
import subprocess
import time
from collections import Counter

import cv2
import numpy as np

from repaint_reference import repaint_frame


def detect_head_candidates(source):
    """Detect only strong, circle-like head regions; reject most smears and impact rings."""
    h, w = source.shape[:2]
    small = cv2.resize(source, (w // 2, h // 2), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    gray = cv2.medianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), 5)
    circles = cv2.HoughCircles(
        gray, cv2.HOUGH_GRADIENT, dp=1.2, minDist=25,
        param1=100, param2=28, minRadius=14, maxRadius=120
    )
    candidates = []
    red = (((hsv[:, :, 0] <= 15) | (hsv[:, :, 0] >= 168)) &
           (hsv[:, :, 1] > 35) & (hsv[:, :, 2] > 30))
    dark = (hsv[:, :, 2] < 65) & (hsv[:, :, 1] < 120)
    yy, xx = np.ogrid[:small.shape[0], :small.shape[1]]
    angles = np.arange(0, 2 * np.pi, 0.15)

    if circles is not None:
        for sx, sy, sr in np.round(circles[0]).astype(int):
            dist2 = (xx - sx) ** 2 + (yy - sy) ** 2
            core = dist2 < (sr * 0.62) ** 2
            if not core.any():
                continue
            red_ratio = float(red[core].mean())
            dark_ratio = float(dark[core].mean())
            ix = np.clip(np.round(sx + sr * 0.78 * np.cos(angles)).astype(int), 0, small.shape[1] - 1)
            iy = np.clip(np.round(sy + sr * 0.78 * np.sin(angles)).astype(int), 0, small.shape[0] - 1)
            ox = np.clip(np.round(sx + sr * 1.08 * np.cos(angles)).astype(int), 0, small.shape[1] - 1)
            oy = np.clip(np.round(sy + sr * 1.08 * np.sin(angles)).astype(int), 0, small.shape[0] - 1)
            contrast = float(np.mean(np.abs(gray[iy, ix].astype(np.int16) - gray[oy, ox].astype(np.int16))))
            red_edge = float(np.mean(red[iy, ix] & ~red[oy, ox]))
            dark_edge = float(np.mean(dark[iy, ix] & ~dark[oy, ox]))
            if red_ratio > 0.72 and contrast > 18 and red_edge > 0.42:
                candidates.append((sx * 2, sy * 2, sr * 2, "azure", contrast, red_ratio))
            elif dark_ratio > 0.80 and contrast > 25 and dark_edge > 0.35:
                candidates.append((sx * 2, sy * 2, sr * 2, "obsidian", contrast, dark_ratio))

    # A conservative fallback for upright red silhouettes when blur defeats the circle detector.
    if not any(c[3] == "azure" for c in candidates):
        hsv_full = cv2.cvtColor(source, cv2.COLOR_BGR2HSV)
        red_full = (((hsv_full[:, :, 0] <= 15) | (hsv_full[:, :, 0] >= 168)) &
                    (hsv_full[:, :, 1] >= 45) & (hsv_full[:, :, 2] >= 35)).astype(np.uint8) * 255
        n, labels, stats, _ = cv2.connectedComponentsWithStats(red_full, 8)
        fallback = []
        for label in range(1, n):
            x, y, bw, bh, area = [int(v) for v in stats[label]]
            if (area < 9000 or bw < 50 or bh < 250 or bh / max(1, bw) < 1.6 or
                    bw > w * 0.32 or y < 1 or x < 4 or x + bw >= w - 4):
                continue
            radius = int(max(35, min(bw * 0.43, bh * 0.085, 96)))
            cx = x + bw // 2
            cy = y + min(int(bh * 0.12), int(radius * 1.05))
            fill = area / max(1, bw * bh)
            if fill > 0.10 and cy - radius * 0.65 > 0 and cy + radius < h:
                fallback.append((cx, cy, radius, "azure", 0.0, fill))
        if fallback:
            candidates.append(max(fallback, key=lambda c: c[5]))

    selected = []
    for kind in ("azure", "obsidian"):
        group = [c for c in candidates if c[3] == kind and c[2] >= 34]
        if group:
            best = max(group, key=lambda c: c[4] + c[2] * 0.03 + c[5] * 20)
            if all(math.hypot(best[0] - o[0], best[1] - o[1]) > max(best[2], o[2]) * 0.62 for o in selected):
                selected.append(best)
    return selected


def draw_anime_head(frame, candidate, opponent_x=None):
    """Paint two original, skin-tone-free anime fighter designs inside tracked source head regions."""
    cx, cy, radius, kind, _, _ = candidate
    cx, cy, radius = int(cx), int(cy), int(radius)
    h, w = frame.shape[:2]
    if radius < 34 or cx < -radius or cx > w + radius or cy < -radius or cy > h + radius:
        return
    direction = 1 if opponent_x is None or opponent_x >= cx else -1
    overlay = frame.copy()
    thick = max(2, int(radius * 0.028))

    if kind == "azure":
        hair = (205, 106, 24)
        hair_outline = (86, 43, 16)
        hair_glint = (255, 224, 133)
        face = (205, 221, 233)
        ink = (20, 28, 41)
        iris = (48, 218, 255)
        shadow = (112, 133, 158)
        hp = [
            (cx-int(.82*radius), cy-int(.10*radius)),
            (cx-int(1.02*radius), cy-int(.48*radius)),
            (cx-int(.57*radius), cy-int(.43*radius)),
            (cx-int(.42*radius), cy-int(1.04*radius)),
            (cx-int(.10*radius), cy-int(.63*radius)),
            (cx+int(.20*radius), cy-int(1.10*radius)),
            (cx+int(.40*radius), cy-int(.60*radius)),
            (cx+int(.78*radius), cy-int(.83*radius)),
            (cx+int(.73*radius), cy-int(.17*radius)),
            (cx+int(.34*radius), cy-int(.30*radius)),
            (cx-int(.12*radius), cy-int(.25*radius)),
        ]
        cv2.fillPoly(overlay, [np.array(hp, np.int32)], hair, cv2.LINE_AA)
        cv2.polylines(overlay, [np.array(hp, np.int32)], True, hair_outline, thick, cv2.LINE_AA)
        strands = [
            [(cx-int(.65*radius),cy-int(.33*radius)),(cx-int(.44*radius),cy-int(.72*radius)),(cx-int(.33*radius),cy-int(.40*radius))],
            [(cx-int(.12*radius),cy-int(.43*radius)),(cx+int(.18*radius),cy-int(.82*radius)),(cx+int(.21*radius),cy-int(.41*radius))],
            [(cx+int(.42*radius),cy-int(.42*radius)),(cx+int(.66*radius),cy-int(.65*radius))],
        ]
        for points in strands:
            cv2.polylines(overlay,[np.array(points,np.int32)],False,hair_glint,max(2,int(radius*.022)),cv2.LINE_AA)
    else:
        hair = (22, 24, 38)
        hair_outline = (6, 8, 16)
        hair_glint = (175, 68, 223)
        face = (69, 76, 91)
        ink = (4, 6, 13)
        iris = (210, 80, 255)
        shadow = (35, 43, 64)
        hp = [
            (cx-int(.86*radius),cy-int(.08*radius)),
            (cx-int(1.05*radius),cy-int(.60*radius)),
            (cx-int(.60*radius),cy-int(.42*radius)),
            (cx-int(.50*radius),cy-int(1.04*radius)),
            (cx-int(.17*radius),cy-int(.65*radius)),
            (cx+int(.12*radius),cy-int(1.14*radius)),
            (cx+int(.42*radius),cy-int(.60*radius)),
            (cx+int(.82*radius),cy-int(.94*radius)),
            (cx+int(.72*radius),cy-int(.14*radius)),
            (cx+int(.28*radius),cy-int(.28*radius)),
            (cx-int(.18*radius),cy-int(.25*radius)),
        ]
        cv2.fillPoly(overlay,[np.array(hp,np.int32)],hair,cv2.LINE_AA)
        cv2.polylines(overlay,[np.array(hp,np.int32)],True,hair_outline,thick,cv2.LINE_AA)
        cv2.polylines(overlay,[np.array([(cx-int(.66*radius),cy-int(.43*radius)),(cx-int(.46*radius),cy-int(.78*radius)),(cx-int(.34*radius),cy-int(.42*radius))],np.int32)],False,hair_glint,max(2,int(radius*.024)),cv2.LINE_AA)
        cv2.polylines(overlay,[np.array([(cx+int(.14*radius),cy-int(.48*radius)),(cx+int(.43*radius),cy-int(.77*radius))],np.int32)],False,hair_glint,max(2,int(radius*.024)),cv2.LINE_AA)

    y, x = np.ogrid[:h, :w]
    circle = (x-cx)**2 + (y-cy)**2 <= int(radius*.91)**2
    face_mask = np.zeros((h,w),np.uint8)
    face_points = [
        (cx-int(.45*radius),cy-int(.38*radius)),
        (cx+int(.35*radius),cy-int(.43*radius)),
        (cx+int(.49*radius),cy-int(.08*radius)),
        (cx+int(.38*radius),cy+int(.39*radius)),
        (cx+int(.08*radius),cy+int(.57*radius)),
        (cx-int(.28*radius),cy+int(.43*radius)),
        (cx-int(.48*radius),cy+int(.08*radius)),
    ]
    cv2.fillPoly(face_mask,[np.array(face_points,np.int32)],255)
    face_mask = (face_mask > 0) & circle
    overlay[face_mask] = np.array(face,np.uint8)

    cheek = [(cx-int(.34*radius),cy+int(.22*radius)),
             (cx-int(.06*radius),cy+int(.46*radius)),
             (cx+int(.14*radius),cy+int(.29*radius))]
    cv2.fillPoly(overlay,[np.array(cheek,np.int32)],shadow,cv2.LINE_AA)

    for ex in (-.22, .18):
        cv2.line(overlay,(cx+int(ex*radius),cy-int(.17*radius)),
                 (cx+int((ex+.16)*radius),cy-int(.23*radius)),
                 ink,max(2,int(radius*.035)),cv2.LINE_AA)
    for ex in (-.22, .20):
        ecx = cx + int(ex*radius) + int(direction*radius*.025)
        ecy = cy + int(.015*radius)
        axes = (max(3,int(radius*.115)), max(2,int(radius*.07)))
        cv2.ellipse(overlay,(ecx,ecy),axes,0,0,360,ink,max(1,int(radius*.018)),cv2.LINE_AA)
        sclera = (238,244,248) if kind == "azure" else (155,157,178)
        cv2.ellipse(overlay,(ecx,ecy),(max(2,int(axes[0]*.78)),max(2,int(axes[1]*.72))),
                    0,0,360,sclera,-1,cv2.LINE_AA)
        ix = ecx + int(direction*axes[0]*.22)
        cv2.circle(overlay,(ix,ecy),max(2,int(radius*.045)),iris,-1,cv2.LINE_AA)
        cv2.circle(overlay,(ix,ecy),max(1,int(radius*.018)),ink,-1,cv2.LINE_AA)
        cv2.circle(overlay,(ix-int(radius*.012),ecy-int(radius*.022)),max(1,int(radius*.012)),(255,255,255),-1,cv2.LINE_AA)

    cv2.polylines(overlay,[np.array([
        (cx+int(direction*radius*.04),cy+int(.04*radius)),
        (cx+int(direction*radius*.09),cy+int(.20*radius)),
        (cx+int(direction*radius*.02),cy+int(.23*radius))],np.int32)],False,ink,max(1,int(radius*.018)),cv2.LINE_AA)
    if kind == "azure":
        cv2.polylines(overlay,[np.array([(cx-int(.22*radius),cy+int(.31*radius)),
                  (cx,cy+int(.36*radius)),(cx+int(.20*radius),cy+int(.28*radius))],np.int32)],
                  False,ink,max(1,int(radius*.025)),cv2.LINE_AA)
        cv2.line(overlay,(cx+int(.29*radius),cy+int(.18*radius)),
                 (cx+int(.37*radius),cy+int(.10*radius)),hair_glint,max(1,int(radius*.025)),cv2.LINE_AA)
    else:
        cv2.ellipse(overlay,(cx,cy+int(.32*radius)),(max(3,int(.28*radius)),max(2,int(.13*radius))),
                    0,0,180,ink,max(2,int(radius*.03)),cv2.LINE_AA)
        cv2.line(overlay,(cx-int(.21*radius),cy+int(.32*radius)),
                 (cx+int(.21*radius),cy+int(.32*radius)),hair_glint,max(1,int(radius*.025)),cv2.LINE_AA)
    frame[:] = overlay


def add_armour_segments(source, result, candidates):
    """Add clipped, transverse armor plates to elongated fighter-mask components."""
    h, w = source.shape[:2]
    hsv = cv2.cvtColor(source, cv2.COLOR_BGR2HSV)
    masks = {
        "azure": ((((hsv[:, :, 0] <= 15) | (hsv[:, :, 0] >= 168)) &
                   (hsv[:, :, 1] >= 45) & (hsv[:, :, 2] >= 35)).astype(np.uint8) * 255),
        "obsidian": (((hsv[:, :, 2] < 55) & (hsv[:, :, 1] < 115)).astype(np.uint8) * 255),
    }
    for cand in candidates:
        cx, cy, radius, kind = int(cand[0]), int(cand[1]), int(cand[2]), cand[3]
        mask = masks[kind]
        # Remove isolated spark pixels while preserving broad limbs and their joints.
        clean = cv2.morphologyEx(mask, cv2.MORPH_CLOSE,
                                 cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
        count, labels, stats, _ = cv2.connectedComponentsWithStats(clean, 8)
        if not (0 <= cx < w and 0 <= cy < h):
            continue
        label = int(labels[cy, cx])
        if label == 0:
            # Circle centres can sit a few pixels outside the source matte after antialiasing.
            x1, x2 = max(0, cx-radius//6), min(w, cx+radius//6+1)
            y1, y2 = max(0, cy-radius//6), min(h, cy+radius//6+1)
            roi = labels[y1:y2, x1:x2]
            vals = roi[roi > 0]
            if vals.size == 0:
                continue
            ids, freq = np.unique(vals, return_counts=True)
            label = int(ids[int(np.argmax(freq))])
        x, y, bw, bh, area = [int(v) for v in stats[label]]
        if area < 2500 or bw > w*.82 or bh > h*.82:
            continue
        if x < 2 or y < 2 or x+bw >= w-2 or y+bh >= h-2:
            continue
        comp = (labels[y:y+bh, x:x+bw] == label)
        ys, xs = np.where(comp)
        if len(xs) < 500:
            continue
        # PCA finds the limb's own direction, so the armor stripes rotate with the pose.
        pts = np.column_stack((xs.astype(np.float32), ys.astype(np.float32)))
        centre = pts.mean(axis=0)
        cov = np.cov(pts, rowvar=False)
        vals, vecs = np.linalg.eigh(cov)
        axis = vecs[:, int(np.argmax(vals))]
        minor = np.array([-axis[1], axis[0]], dtype=np.float32)
        along = (pts-centre) @ axis
        across = (pts-centre) @ minor
        long_span = float(along.max()-along.min())
        short_span = float(across.max()-across.min())
        if long_span < 150 or long_span/max(1.0,short_span) < 1.75 or short_span < 18:
            continue
        accent = (245, 225, 155) if kind == "azure" else (198, 102, 224)
        shadow = (72, 84, 120) if kind == "azure" else (24, 30, 55)
        line_mask = np.zeros((bh,bw),np.uint8)
        step = max(45, min(105, int(short_span*1.30)))
        positions = np.arange(along.min()+step*.45, along.max()-step*.25, step)
        for pos in positions:
            mid = centre + axis*pos
            p1 = tuple(np.round(mid-minor*short_span*.39).astype(int))
            p2 = tuple(np.round(mid+minor*short_span*.39).astype(int))
            p1 = (int(np.clip(p1[0],0,bw-1)),int(np.clip(p1[1],0,bh-1)))
            p2 = (int(np.clip(p2[0],0,bw-1)),int(np.clip(p2[1],0,bh-1)))
            cv2.line(line_mask,p1,p2,255,max(2,int(min(6,short_span*.06))),cv2.LINE_AA)
        etched=(line_mask>0)&comp
        if np.any(etched):
            roi=result[y:y+bh,x:x+bw]
            before=roi[etched].astype(np.float32)
            col=np.array(accent,np.float32)
            roi[etched]=np.clip(before*.28+col*.72,0,255).astype(np.uint8)
            # Narrow secondary shadow lines create separated armor plates instead of plain tubes.
            shadow_mask=np.zeros((bh,bw),np.uint8)
            for pos in positions:
                mid=centre+axis*(pos+max(3,short_span*.10))
                p1=tuple(np.round(mid-minor*short_span*.33).astype(int))
                p2=tuple(np.round(mid+minor*short_span*.33).astype(int))
                p1=(int(np.clip(p1[0],0,bw-1)),int(np.clip(p1[1],0,bh-1)))
                p2=(int(np.clip(p2[0],0,bw-1)),int(np.clip(p2[1],0,bh-1)))
                cv2.line(shadow_mask,p1,p2,255,max(1,int(min(3,short_span*.025))),cv2.LINE_AA)
            m=(shadow_mask>0)&comp
            roi[m]=np.array(shadow,np.uint8)


class RuinedAnimeEnvironment:
    """Stable ruined skyline, fractured concrete, and foreground rubble."""
    def __init__(self, width, height):
        self.width, self.height = width, height
        self.art = np.zeros((height,width,3),np.uint8)
        rng = random.Random(901)
        horizon = int(height*.585)
        x = -25
        while x < width:
            bw = rng.randint(48,112)
            bh = rng.randint(int(height*.07),int(height*.23))
            top = horizon - bh
            pts = [
                (x,horizon),(x,top+rng.randint(0,18)),
                (x+int(bw*.18),top),(x+int(bw*.39),top+rng.randint(4,25)),
                (x+int(bw*.56),top-rng.randint(3,17)),
                (x+int(bw*.78),top+rng.randint(0,16)),(x+bw,horizon)
            ]
            cv2.fillPoly(self.art,[np.array(pts,np.int32)],(72,72,81),cv2.LINE_AA)
            cv2.polylines(self.art,[np.array(pts,np.int32)],False,(126,124,130),2,cv2.LINE_AA)
            for wx in range(x+10,x+bw-8,18):
                for wy in range(top+17,horizon-8,22):
                    if rng.random()<.50 and 0<=wx<width and 0<=wy<height:
                        cv2.rectangle(self.art,(wx,wy),(min(width-1,wx+6),min(height-1,wy+10)),(32,35,45),-1)
            if rng.random()<.70:
                cv2.line(self.art,(x+int(bw*.25),top+12),(x+int(bw*.37),top+int(bh*.46)),(42,45,56),2,cv2.LINE_AA)
            x += bw + rng.randint(5,18)
        vanx, vany = width//2, horizon
        for i in range(17):
            bx = int((i/16)*width + rng.randint(-18,18))
            by = rng.randint(horizon+18,height-4)
            mx = int((bx+vanx)*.52+rng.randint(-28,28))
            my = int((by+vany)*.55+rng.randint(-13,13))
            ex = int(np.clip(vanx+rng.randint(-190,191),0,width-1))
            ey = min(height-1,by+rng.randint(14,95))
            cv2.polylines(self.art,[np.array([(bx,by),(mx,my),(ex,ey)],np.int32)],False,
                          (39,43,54),max(1,int((by-horizon)/150)),cv2.LINE_AA)
            if i%2==0:
                ex2=int(np.clip(mx+rng.randint(-100,100),0,width-1))
                ey2=min(height-1,my+rng.randint(12,58))
                cv2.line(self.art,(mx,my),(ex2,ey2),(61,62,72),2,cv2.LINE_AA)
        for _ in range(46):
            bx=rng.randint(0,width-1); by=rng.randint(max(horizon,height-180),height-4); size=rng.randint(5,22)
            pts=[(bx-size,by),(bx-size//2,by-size),(bx+size//4,by-size//2),
                 (bx+size,by),(bx+size//2,by+2)]
            cv2.fillPoly(self.art,[np.array(pts,np.int32)],(66,67,77),cv2.LINE_AA)
            cv2.polylines(self.art,[np.array(pts,np.int32)],True,(139,134,139),1,cv2.LINE_AA)
        self.art = cv2.GaussianBlur(self.art,(3,3),0.25)

    def apply(self, original, result):
        hsv = cv2.cvtColor(original,cv2.COLOR_BGR2HSV)
        bg = ((hsv[:,:,1] < 65) & (hsv[:,:,2] > 52) & (hsv[:,:,2] < 218))
        count = int(np.count_nonzero(bg))
        if count < original.shape[0]*original.shape[1]*.10:
            return result, count
        art_mask = cv2.cvtColor(self.art,cv2.COLOR_BGR2GRAY) > 5
        mask = bg & art_mask
        if not np.any(mask):
            return result, count
        old = result[mask].astype(np.float32)
        set_art = self.art[mask].astype(np.float32)
        result[mask] = np.clip(old*.42+set_art*.58,0,255).astype(np.uint8)
        return result, count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='Original source frames used for detection and the audio track')
    parser.add_argument('--base-video', default=None, help='Optional aligned repaint output to enhance without repeating the repaint pass')
    parser.add_argument('--output', required=True)
    parser.add_argument('--start', type=float, default=0.0)
    parser.add_argument('--duration', type=float, default=0.0, help='0 processes to the source end')
    parser.add_argument('--crf', type=int, default=15)
    parser.add_argument('--preset', default='medium')
    parser.add_argument('--scale', type=int, default=2, choices=(1,2))
    parser.add_argument('--mux-audio', action='store_true')
    args = parser.parse_args()

    src = pathlib.Path(args.input)
    out = pathlib.Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    reference_cap = None
    if args.base_video:
        reference_cap = cv2.VideoCapture(str(src))
        cap = cv2.VideoCapture(str(args.base_video))
        if not reference_cap.isOpened() or not cap.isOpened():
            raise RuntimeError('Cannot open original source or base video.')
        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        ref_fps = reference_cap.get(cv2.CAP_PROP_FPS) or 24.0
        ref_total = int(reference_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if abs(ref_fps-fps) > 0.01 or ref_total != total_frames:
            raise ValueError('Base video must match the source frame rate and frame count.')
        if (int(reference_cap.get(cv2.CAP_PROP_FRAME_WIDTH)),int(reference_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))) != (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))):
            raise ValueError('Base video and original source must have matching frame dimensions.')
    else:
        cap = cv2.VideoCapture(str(src))
        if not cap.isOpened():
            raise RuntimeError('Cannot open source: '+str(src))
        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    start_frame = max(0,int(round(args.start*fps)))
    end_frame = total_frames if args.duration <= 0 else min(total_frames,start_frame+int(round(args.duration*fps)))
    if start_frame >= total_frames or end_frame <= start_frame:
        raise ValueError('Requested frame range is outside source video.')
    cap.set(cv2.CAP_PROP_POS_FRAMES,start_frame)
    if reference_cap is not None:
        reference_cap.set(cv2.CAP_PROP_POS_FRAMES,start_frame)

    temp_video = out.with_name(out.stem+'_video_only.mp4')
    log_path = out.with_name(out.stem+'_encode.log')
    encode_log = log_path.open('wb')
    target_w,target_h = width*args.scale,height*args.scale
    vf = 'scale='+str(target_w)+':'+str(target_h)+':flags=lanczos,unsharp=7:7:0.45:5:5:0.10,format=yuv420p'
    command = [
        'ffmpeg','-y','-hide_banner','-loglevel','error',
        '-filter_threads','1','-filter_complex_threads','1',
        '-f','rawvideo','-pix_fmt','bgr24','-s',str(width)+'x'+str(height),
        '-r',str(fps),'-i','pipe:0','-an','-vf',vf,
        '-c:v','libx264','-threads','1','-x264-params','threads=1:lookahead-threads=1:rc-lookahead=4:sync-lookahead=0:bframes=2',
        '-preset',args.preset,'-crf',str(args.crf),
        '-pix_fmt','yuv420p','-fps_mode','passthrough','-movflags','+faststart',str(temp_video)
    ]
    proc = subprocess.Popen(command,stdin=subprocess.PIPE,stderr=encode_log,stdout=subprocess.DEVNULL)
    stats = Counter()
    env = RuinedAnimeEnvironment(width,height)
    t0=time.time()
    last_candidates=[]
    for idx in range(start_frame,end_frame):
        ok,frame=cap.read()
        if not ok:
            break
        if reference_cap is not None:
            ok_source, source_frame = reference_cap.read()
            if not ok_source:
                break
            result = frame.copy()
            base_stats = Counter()
        else:
            source_frame=frame.copy()
            base_stats=Counter()
            result=repaint_frame(frame,idx,fps,base_stats)
        candidates=detect_head_candidates(source_frame)
        smoothed=[]
        for cand in candidates:
            prior=next((p for p in last_candidates if p[3]==cand[3] and
                        math.hypot(p[0]-cand[0],p[1]-cand[1]) < max(170,p[2]*1.2)),None)
            if prior is not None:
                cand=(int(.72*cand[0]+.28*prior[0]),int(.72*cand[1]+.28*prior[1]),
                      int(.82*cand[2]+.18*prior[2]),cand[3],cand[4],cand[5])
            smoothed.append(cand)
        add_armour_segments(source_frame,result,smoothed)
        for cand in smoothed:
            opponents=[other[0] for other in smoothed if other[3]!=cand[3]]
            draw_anime_head(result,cand,opponents[0] if opponents else None)
        result,env_pixels=env.apply(source_frame,result)
        try:
            proc.stdin.write(result.tobytes())
        except BrokenPipeError:
            break
        stats['frames'] += 1
        stats['heads_detected'] += len(smoothed)
        stats['azure_heads'] += sum(1 for c in smoothed if c[3]=='azure')
        stats['obsidian_heads'] += sum(1 for c in smoothed if c[3]=='obsidian')
        stats['environment_pixels'] += env_pixels
        stats['red_pixels'] += base_stats['red_mask_pixels']
        stats['yellow_fx_pixels'] += base_stats['yellow_mask_pixels']
        stats['white_character_pixels'] += base_stats['white_character_pixels']
        last_candidates=smoothed
        rel=idx-start_frame
        if rel % max(1,int(fps*5)) == 0:
            print('processed '+str(rel)+'/'+str(end_frame-start_frame)+
                  ' frames; heads='+str(stats['heads_detected'])+
                  '; elapsed='+str(round(time.time()-t0,1))+'s',flush=True)
    cap.release()
    if reference_cap is not None:
        reference_cap.release()
    proc.stdin.close()
    code=proc.wait()
    encode_log.close()
    if code != 0 or not temp_video.exists() or temp_video.stat().st_size < 100_000:
        detail=log_path.read_text(errors='replace')[-3000:] if log_path.exists() else ''
        raise RuntimeError('Encoding failed, code='+str(code)+' '+detail)

    if args.mux_audio:
        audio_tmp=out.with_name(out.stem+'_mux.mp4')
        mux=['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(temp_video)]
        if args.start>0:
            mux += ['-ss',str(args.start)]
        mux += ['-i',str(src),'-map','0:v:0','-map','1:a:0?','-c:v','copy','-c:a','copy']
        if args.start==0 and args.duration<=0:
            mux += ['-map_metadata','1','-movflags','+faststart',str(audio_tmp)]
        else:
            mux += ['-t',str((end_frame-start_frame)/fps),'-map_metadata','1','-movflags','+faststart',str(audio_tmp)]
        subprocess.run(mux,check=True)
        audio_tmp.replace(out)
        temp_video.unlink(missing_ok=True)
    else:
        temp_video.replace(out)

    report={
        'input':str(src),'base_video':str(args.base_video) if args.base_video else None,'output':str(out),
        'source_resolution':[width,height],'output_resolution':[target_w,target_h],
        'fps':fps,'source_total_frames':total_frames,'processed_frames':stats['frames'],
        'start_frame':start_frame,'end_frame_exclusive':start_frame+stats['frames'],
        'video_duration_seconds':stats['frames']/fps,'scale_factor':args.scale,
        'crf':args.crf,'preset':args.preset,
        'azure_head_overlays':stats['azure_heads'],'obsidian_head_overlays':stats['obsidian_heads'],
        'total_head_overlays':stats['heads_detected'],
        'background_pixels_treated':stats['environment_pixels'],
        'red_pixels_repainted':stats['red_pixels'],'energy_pixels_repainted':stats['yellow_fx_pixels'],
        'white_pixels_treated':stats['white_character_pixels'],
        'camera_motion_frame_order_and_audio':'source timebase and frame order preserved; audio copied when --mux-audio is used',
        'quality_note':'1440p is a high-quality 2x upscale of 720p source, with added manga hair/face overlays on confidently detected head-like regions, clipped armor seams, and stylized ruined-city/concrete detail; it is not native 1440p footage or a full generative scene reconstruction'
    }
    out.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('ANIME_ENHANCEMENT_COMPLETE '+json.dumps(report),flush=True)


if __name__ == '__main__':
    main()
