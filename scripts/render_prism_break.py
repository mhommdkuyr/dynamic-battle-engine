#!/usr/bin/env python3
"""Render an original, three-character 2D/2.5D stick-fighter short.

This project creates new vector animation and a procedurally synthesized score.
It does not sample or reuse frames, audio, or motion data from any reference video.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import time
import wave
from pathlib import Path

import cv2
import numpy as np

DEFAULT_DURATION = 291.318
DEFAULT_FPS = 24
W, H = 1280, 720
BLUE = (255, 206, 38)   # BGR: electric cyan
RED = (45, 48, 255)     # BGR: crimson
GOLD = (16, 206, 255)   # BGR: solar gold
WHITE = (245, 250, 255)
DARK = (18, 20, 27)
BPM = 108.0
BEAT = 60.0 / BPM
IMPACTS = [28.333, 39.444, 47.222, 58.333, 72.778, 94.444, 108.889,
           124.444, 139.444, 158.333, 177.778, 195.556, 214.444, 233.889,
           253.333, 269.444, 280.0]

PATHS = {
    "blue": [
        (0, 245, 475), (8, 300, 478), (18, 475, 463), (28, 610, 455),
        (38, 770, 425), (47, 655, 375), (58, 420, 420), (70, 515, 350),
        (82, 700, 282), (94, 635, 300), (101, 465, 245), (111, 365, 205),
        (124, 515, 326), (137, 760, 370), (150, 660, 318), (163, 435, 275),
        (177, 540, 225), (190, 675, 260), (203, 435, 270), (215, 600, 340),
        (228, 740, 386), (242, 620, 425), (253, 460, 438), (265, 540, 378),
        (276, 700, 330), (284, 640, 440), (291.318, 640, 458)
    ],
    "red": [
        (0, 1035, 475), (8, 970, 478), (18, 800, 463), (28, 665, 455),
        (38, 515, 425), (47, 600, 375), (58, 850, 420), (70, 720, 350),
        (82, 545, 282), (94, 610, 300), (101, 795, 245), (111, 915, 205),
        (124, 765, 326), (137, 530, 370), (150, 600, 318), (163, 785, 275),
        (177, 700, 225), (190, 585, 260), (203, 815, 270), (215, 680, 340),
        (228, 520, 386), (242, 650, 425), (253, 795, 438), (265, 700, 378),
        (276, 530, 330), (284, 640, 440), (291.318, 640, 458)
    ],
    "gold": [
        (0, 1430, 450), (88, 1420, 235), (94, 1210, 190), (101, 1010, 230),
        (108, 820, 308), (118, 650, 280), (130, 560, 292), (145, 700, 340),
        (158, 620, 260), (173, 670, 290), (188, 640, 235), (203, 560, 280),
        (215, 640, 350), (228, 730, 388), (240, 610, 420), (252, 650, 448),
        (263, 600, 370), (276, 620, 330), (284, 645, 440), (291.318, 650, 458)
    ]
}

def smooth_path(keys, t):
    if t <= keys[0][0]:
        return float(keys[0][1]), float(keys[0][2])
    if t >= keys[-1][0]:
        return float(keys[-1][1]), float(keys[-1][2])
    seg = 0
    while seg < len(keys) - 2 and t > keys[seg + 1][0]:
        seg += 1
    a, b = keys[seg], keys[seg + 1]
    u = (t - a[0]) / max(1e-6, b[0] - a[0])
    u = u * u * (3.0 - 2.0 * u)
    x = a[1] + (b[1] - a[1]) * u
    y = a[2] + (b[2] - a[2]) * u
    return float(x), float(y)

def gradient_background(top, bottom):
    v = np.linspace(0.0, 1.0, H, dtype=np.float32)[:, None, None]
    a = np.asarray(top, dtype=np.float32).reshape(1, 1, 3)
    b = np.asarray(bottom, dtype=np.float32).reshape(1, 1, 3)
    row = a * (1.0 - v) + b * v
    return np.repeat(row, W, axis=1).astype(np.uint8)

def build_backgrounds():
    rng = np.random.default_rng(20261012)
    wasteland = gradient_background((56, 57, 63), (150, 149, 145))
    airborne = gradient_background((30, 29, 38), (76, 77, 86))
    space = gradient_background((8, 5, 20), (28, 16, 40))
    aftermath = gradient_background((25, 28, 35), (62, 59, 63))

    # Distant ridges and foreground rocks: silhouettes are original geometric art.
    for bg, tops, shade in [
        (wasteland, [(0,450),(100,415),(220,455),(355,410),(490,450),(650,405),(830,445),(1000,400),(1180,450),(1280,425)], (83,84,88)),
        (airborne, [(0,500),(120,465),(280,500),(450,430),(610,495),(780,450),(960,495),(1110,440),(1280,500)], (53,54,64)),
        (aftermath, [(0,485),(110,450),(260,510),(400,455),(570,500),(760,438),(920,505),(1080,450),(1280,500)], (42,43,51))
    ]:
        polygon = np.array(tops + [(W, 585), (0, 585)], dtype=np.int32)
        cv2.fillPoly(bg, [polygon], shade, lineType=cv2.LINE_AA)

    cv2.line(wasteland, (0, 545), (W, 545), (87, 87, 91), 3, cv2.LINE_AA)
    cv2.line(airborne, (0, 580), (W, 580), (47, 49, 58), 2, cv2.LINE_AA)
    cv2.line(aftermath, (0, 548), (W, 548), (36, 37, 44), 4, cv2.LINE_AA)
    for bg in (wasteland, aftermath):
        for _ in range(30):
            x = int(rng.integers(0, W))
            y = int(rng.integers(548, H))
            r = int(rng.integers(8, 33))
            col = (83, 84, 87) if bg is wasteland else (32, 33, 40)
            cv2.ellipse(bg, (x, y), (r, max(3, r // 3)), int(rng.integers(-30,30)), 0, 360, col, -1, cv2.LINE_AA)

    # A distant world and thin ring; the planet is not based on source imagery.
    cv2.circle(space, (1000, 340), 240, (46, 30, 65), -1, cv2.LINE_AA)
    cv2.circle(space, (970, 320), 210, (61, 42, 83), -1, cv2.LINE_AA)
    for rr in range(180, 0, -18):
        cv2.ellipse(space, (975, 315), (rr, max(1, int(rr * 0.78))), -18, 30, 320, (65 + rr//8, 51 + rr//9, 95 + rr//6), 1, cv2.LINE_AA)
    cv2.ellipse(space, (1000, 360), (300, 95), -14, 0, 360, (102, 73, 133), 2, cv2.LINE_AA)
    stars = []
    for _ in range(300):
        stars.append((int(rng.integers(0, W)), int(rng.integers(0, H)), int(rng.integers(1, 3)), int(rng.integers(100, 255))))
    for x, y, r, lum in stars:
        cv2.circle(space, (x, y), r, (lum, min(255, lum + 8), min(255, lum + 25)), -1, cv2.LINE_AA)
    # Floating stone silhouettes along the aerial stage.
    for _ in range(48):
        x = int(rng.integers(0, W))
        y = int(rng.choice([rng.integers(45,180), rng.integers(555,690)]))
        r = int(rng.integers(3, 18))
        cv2.fillPoly(airborne, [np.array([[x-r,y],[x,y-r],[x+r,y-2],[x+r//2,y+r],[x-r,y+r//2]], np.int32)], (35, 35, 43), cv2.LINE_AA)
    return wasteland, airborne, space, aftermath, stars

def line(img, p1, p2, color, width=4):
    a = (int(p1[0]), int(p1[1]))
    b = (int(p2[0]), int(p2[1]))
    cv2.line(img, a, b, (12, 13, 19), width + 3, cv2.LINE_AA)
    cv2.line(img, a, b, color, width, cv2.LINE_AA)
    if width >= 4:
        hi = tuple(min(255, int(c * 0.45 + 120)) for c in color)
        cv2.line(img, a, b, hi, max(1, width // 3), cv2.LINE_AA)

def draw_fighter(img, x, y, color, t, state, facing, scale, power, identity):
    if identity == "gold":
        scale *= 1.1
    bob = math.sin(t * (8.5 if state in ("dash", "attack", "kick") else 4.0) + identity.__len__()) * (3 if state != "recoil" else 8)
    x, y = float(x), float(y + bob)
    s = scale
    facing = 1 if facing >= 0 else -1
    cx, cy = int(x), int(y)
    accent = tuple(min(255, int(c * 0.55 + 95)) for c in color)

    # Aura is drawn in layers rather than sampled from any reference.
    aura = int(34 + power * 20)
    cv2.ellipse(img, (cx, int(cy - 29*s)), (int((28 + aura*0.22)*s), int((52 + aura*0.20)*s)),
                int(math.sin(t*2.4)*18), 0, 360, color, max(1, int(2*s)), cv2.LINE_AA)
    cv2.ellipse(img, (cx, int(cy - 30*s)), (int(25*s), int(48*s)), int(math.sin(t*3)*25), 0, 360,
                accent, 1, cv2.LINE_AA)
    head = (cx, int(cy - 76*s))
    shoulders = [(cx - int(12*s), int(cy - 50*s)), (cx + int(12*s), int(cy - 50*s))]
    hip = (cx, cy)
    # Cape/energy crests give each fighter a distinct silhouette.
    if identity == "blue":
        cv2.fillPoly(img, [np.array([[cx-int(14*s),cy-int(45*s)],[cx-int(34*s),cy-int(27*s)],[cx-int(12*s),cy-int(20*s)]], np.int32)], color, cv2.LINE_AA)
        cv2.fillPoly(img, [np.array([[cx+int(14*s),cy-int(45*s)],[cx+int(34*s),cy-int(27*s)],[cx+int(12*s),cy-int(20*s)]], np.int32)], accent, cv2.LINE_AA)
    elif identity == "red":
        # Three angular flame spikes around the shoulder aura.
        for k in range(3):
            ang = -1.0 + k * 0.65 + math.sin(t*5+k)*0.12
            p1 = (int(cx + math.cos(ang)*25*s), int(cy-25*s + math.sin(ang)*32*s))
            p2 = (int(cx + math.cos(ang+0.25)*46*s), int(cy-25*s + math.sin(ang+0.25)*50*s))
            cv2.line(img, p1, p2, color, max(1,int(3*s)), cv2.LINE_AA)
    else:
        # A geometric halo and small crown are the gold fighter's signature.
        cv2.ellipse(img, (cx, int(cy - 83*s)), (int(34*s), int(11*s)), -8, 0, 360, GOLD, 2, cv2.LINE_AA)
        pts = np.array([[cx-int(16*s),head[1]-int(12*s)],[cx-int(7*s),head[1]-int(24*s)],[cx,head[1]-int(12*s)],[cx+int(8*s),head[1]-int(23*s)],[cx+int(17*s),head[1]-int(12*s)]], np.int32)
        cv2.polylines(img, [pts], False, WHITE, max(1,int(2*s)), cv2.LINE_AA)

    # Head, eyes, torso.
    cv2.circle(img, head, max(2,int(18*s)), (8, 10, 15), -1, cv2.LINE_AA)
    cv2.circle(img, head, max(2,int(16*s)), color, -1, cv2.LINE_AA)
    cv2.circle(img, head, max(2,int(17*s)), WHITE, max(1,int(2*s)), cv2.LINE_AA)
    eye_y = head[1] - int(1*s)
    cv2.line(img, (head[0]-int(9*s),eye_y), (head[0]-int(3*s),eye_y), WHITE, max(2,int(3*s)), cv2.LINE_AA)
    cv2.line(img, (head[0]+int(3*s),eye_y), (head[0]+int(9*s),eye_y), WHITE, max(2,int(3*s)), cv2.LINE_AA)
    line(img, (cx,cy-int(57*s)), (cx,cy-int(3*s)), color, max(3,int(6*s)))

    # Arms: actions extend or guard the forward hand.
    left_sh, right_sh = shoulders[0], shoulders[1]
    rear_sh = left_sh if facing > 0 else right_sh
    front_sh = right_sh if facing > 0 else left_sh
    if state == "attack":
        rear_el = (rear_sh[0] - facing*int(19*s), rear_sh[1] + int(12*s))
        rear_hand = (rear_el[0] - facing*int(8*s), rear_el[1] + int(13*s))
        front_el = (front_sh[0] + facing*int(30*s), front_sh[1] - int(10*s))
        front_hand = (front_el[0] + facing*int(28*s), front_el[1] - int(4*s))
    elif state == "block":
        front_el = (cx + facing*int(19*s), cy - int(62*s))
        front_hand = (cx + facing*int(12*s), cy - int(37*s))
        rear_el = (cx - facing*int(12*s), cy - int(55*s))
        rear_hand = (cx + facing*int(18*s), cy - int(47*s))
    elif state == "charge":
        front_el = (cx + facing*int(28*s), cy - int(76*s))
        front_hand = (cx + facing*int(36*s), cy - int(101*s))
        rear_el = (cx - facing*int(24*s), cy - int(30*s))
        rear_hand = (cx - facing*int(37*s), cy - int(12*s))
    elif state == "recoil":
        front_el = (front_sh[0] + facing*int(8*s), front_sh[1] + int(20*s))
        front_hand = (front_el[0] + facing*int(10*s), front_el[1] + int(20*s))
        rear_el = (rear_sh[0] - facing*int(10*s), rear_sh[1] + int(14*s))
        rear_hand = (rear_el[0] - facing*int(18*s), rear_el[1] + int(16*s))
    else:
        sway = math.sin(t*7 + (0 if identity=="blue" else 1.8))*int(7*s)
        front_el = (front_sh[0] + facing*int(22*s), front_sh[1] + int(2*s))
        front_hand = (front_el[0] + facing*int(12*s), front_el[1] + int(18*s) + int(sway))
        rear_el = (rear_sh[0] - facing*int(14*s), rear_sh[1] + int(10*s))
        rear_hand = (rear_el[0] - facing*int(8*s), rear_el[1] + int(17*s) - int(sway))
    for sh, el, hand in [(front_sh,front_el,front_hand),(rear_sh,rear_el,rear_hand)]:
        line(img, sh, el, color, max(3,int(5*s)))
        line(img, el, hand, color, max(3,int(5*s)))
        cv2.circle(img, hand, max(3,int(7*s)), accent, -1, cv2.LINE_AA)
        cv2.circle(img, hand, max(2,int(4*s)), WHITE, -1, cv2.LINE_AA)

    # Legs, with an extended front kick and separate recoil/landing poses.
    hip_l = (cx-int(7*s), cy)
    hip_r = (cx+int(7*s), cy)
    if state == "kick":
        front_hip = hip_r if facing > 0 else hip_l
        rear_hip = hip_l if facing > 0 else hip_r
        knee1 = (cx + facing*int(25*s), cy + int(7*s))
        foot1 = (cx + facing*int(76*s), cy - int(19*s))
        knee2 = (cx - facing*int(17*s), cy + int(27*s))
        foot2 = (cx - facing*int(29*s), cy + int(55*s))
        line(img, front_hip, knee1, color, max(3,int(6*s)))
        line(img, knee1, foot1, color, max(3,int(6*s)))
        line(img, rear_hip, knee2, color, max(3,int(6*s)))
        line(img, knee2, foot2, color, max(3,int(6*s)))
    else:
        stride = math.sin(t*11 + (0 if identity=="blue" else 2.3))*int(19*s) if state == "dash" else math.sin(t*4)*int(5*s)
        knee_l = (cx-int(21*s)+int(stride*0.35), cy+int(25*s))
        foot_l = (cx-int(28*s)+int(stride), cy+int(57*s))
        knee_r = (cx+int(21*s)-int(stride*0.35), cy+int(26*s))
        foot_r = (cx+int(29*s)-int(stride), cy+int(58*s))
        if state == "recoil":
            knee_l = (cx-int(26*s),cy+int(12*s)); foot_l=(cx-int(48*s),cy+int(40*s))
            knee_r = (cx+int(12*s),cy+int(22*s)); foot_r=(cx+int(23*s),cy+int(59*s))
        line(img, hip_l, knee_l, color, max(3,int(6*s)))
        line(img, knee_l, foot_l, color, max(3,int(6*s)))
        line(img, hip_r, knee_r, color, max(3,int(6*s)))
        line(img, knee_r, foot_r, color, max(3,int(6*s)))

def choose_state(identity, t, speed):
    if identity == "gold" and t < 90:
        return "offscreen"
    near = [(abs(t-x), i) for i,x in enumerate(IMPACTS) if abs(t-x) < 0.82]
    if near:
        idx = min(near)[1]
        if identity == "gold" and t > 94:
            return "block" if idx % 2 == 0 else "attack"
        if identity == "blue":
            return "attack" if idx % 2 == 0 else "kick"
        if identity == "red":
            return "block" if idx % 2 == 0 else "recoil"
    if identity == "gold" and any(a < t < b for a,b in [(104,112),(151,160),(184,198),(256,270)]):
        return "charge"
    if any(a < t < b for a,b in [(54,64),(72,82),(120,132),(174,184),(191,203),(260,272)]):
        return "charge" if identity == "red" and int(t*2)%2 else "dash"
    if speed > 14:
        return "dash"
    return "stance"

def draw_sparks(img, x, y, t, intensity, seed):
    if intensity <= 0:
        return
    rng = np.random.default_rng(seed)
    count = int(16 * intensity) + 2
    age = min(1.0, intensity)
    for k in range(count):
        angle = (2*math.pi*k/count) + 0.18*math.sin(t*11+k)
        radius = (25 + k*3.3) * (1.0-age*0.15)
        x2 = int(x + math.cos(angle)*radius)
        y2 = int(y + math.sin(angle)*radius*0.68)
        c = WHITE if k % 3 else (70, 150, 255)
        cv2.line(img, (int(x),int(y)), (x2,y2), c, 1 if intensity < .5 else 2, cv2.LINE_AA)

def generate_music(path, duration, sample_rate=22050):
    rng = np.random.default_rng(2481)
    total = int(duration * sample_rate)
    roots = np.array([55.0, 65.406, 49.0, 58.27], dtype=np.float64)
    impacts = np.asarray(IMPACTS, dtype=np.float64)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2); wav.setsampwidth(2); wav.setframerate(sample_rate)
        chunk = sample_rate * 2
        for start in range(0, total, chunk):
            end = min(total, start + chunk)
            sample = np.arange(start, end, dtype=np.float64)
            t = sample / sample_rate
            beat_i = np.floor(t / BEAT).astype(np.int32)
            beat_phase = np.mod(t, BEAT)
            kick_env = np.exp(-beat_phase*23.0) * ((beat_i % 4) == 0)
            kick = np.sin(2*np.pi*(52.0 - 17.0*beat_phase)*t) * kick_env * 0.44
            snare_phase = np.mod(t + BEAT*0.5, BEAT)
            snare_env = np.exp(-snare_phase*34.0) * np.isin(beat_i % 4, [1,3]) * (snare_phase < 0.10)
            noise = rng.normal(0.0, 1.0, len(t))
            snare = noise * snare_env * 0.18
            hat_phase = np.mod(t, BEAT/2.0)
            hats = rng.normal(0.0, 1.0, len(t)) * np.exp(-hat_phase*105.0) * 0.055
            chord_i = (np.floor(t / 8.0).astype(np.int32) % 4)
            bass_f = roots[chord_i]
            bass = np.sin(2*np.pi*bass_f*t) * (0.10 + 0.035*(beat_i % 2 == 0))
            pad_f = np.array([110.0,130.81,98.0,116.54])[chord_i]
            pad = 0.035*np.sin(2*np.pi*pad_f*t) + 0.018*np.sin(2*np.pi*pad_f*1.5*t)
            hit = np.zeros_like(t)
            for ti in impacts:
                d = t - ti
                m = np.abs(d) < 0.36
                if np.any(m):
                    env = np.exp(-np.abs(d[m])*8.5)
                    hit[m] += (np.sin(2*np.pi*(42.0 + 12.0*np.maximum(0,d[m]))*d[m]) * env * 0.45
                               + noise[m] * env * 0.055)
            signal = np.clip(kick + snare + hats + bass + pad + hit, -0.92, 0.92)
            left = signal * (0.92 + 0.08*np.sin(t*0.7))
            right = signal * (0.92 + 0.08*np.cos(t*0.63))
            stereo = np.stack([left, right], axis=1)
            wav.writeframes((stereo*32767).astype(np.int16).tobytes())

def render(args):
    duration = args.duration
    fps = args.fps
    width, height = args.width, args.height
    # This episode's master canvas is 1280x720; other sizes are scaled at final encode.
    if width != W or height != H:
        raise ValueError("Render master is fixed at 1280x720; change final scaling separately.")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    raw = output.with_name(output.stem + "_raw.mp4")
    wav_path = output.with_name(output.stem + "_score.wav")
    backgrounds = build_backgrounds()
    wasteland, airborne, space, aftermath, stars = backgrounds
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(raw), fourcc, float(fps), (width,height))
    if not writer.isOpened():
        raise RuntimeError("OpenCV could not create the video writer")
    frames = int(math.ceil(duration * fps))
    started = time.time()
    rng = np.random.default_rng(7751)
    action_lines = [(int(rng.integers(0,width)), int(rng.integers(0,height))) for _ in range(50)]
    snapshots = {int(34*fps): output.parent/"prism_break_ground_clash.png",
                 int(112*fps): output.parent/"prism_break_gold_entry.png",
                 int(198*fps): output.parent/"prism_break_orbit.png",
                 int(267*fps): output.parent/"prism_break_final_burst.png"}
    for f in range(frames):
        t = min(duration, f / fps)
        if t < 60:
            frame = wasteland.copy()
        elif t < 160:
            frame = airborne.copy()
        elif t < 225:
            frame = space.copy()
        else:
            frame = aftermath.copy()

        # Subtle atmosphere and action lines respond to speed.
        if t < 60 or t >= 225:
            cv2.rectangle(frame, (0,548), (width,height), (48,48,54), -1)
            for j in range(0, width, 80):
                xx = j + int(8*math.sin(t*2+j))
                cv2.line(frame, (xx,548), (xx+int(20*math.sin(j)),height), (56,56,61), 1, cv2.LINE_AA)
        elif 60 <= t < 160:
            for j in range(14):
                dx = int((j*113 + t*35) % (width+150)) - 75
                dy = 80 + (j*41) % 520
                cv2.line(frame, (dx,dy), (dx+20,dy+8), (54,55,64), 2, cv2.LINE_AA)
        else:
            # Bright star points pulse softly; no reference imagery is used.
            for k,(sx,sy,r,lum) in enumerate(stars[:70]):
                if (k + f//8) % 5 == 0:
                    cv2.circle(frame,(sx,sy),r,(lum, min(255,lum+8), min(255,lum+22)),-1,cv2.LINE_AA)

        actors = {}
        for identity, keys in PATHS.items():
            if identity == "gold" and t < 90:
                continue
            x,y = smooth_path(keys,t)
            # Original hand-drawn-style drift; path timing is newly authored.
            phase = {"blue":0.2,"red":2.1,"gold":4.4}[identity]
            x += math.sin(t*2.8+phase)*8
            y += math.sin(t*3.4+phase)*7
            x0,y0 = smooth_path(keys, max(0,t-0.05))
            x1,y1 = smooth_path(keys, min(duration,t+0.05))
            speed = math.hypot(x1-x0,y1-y0) / 0.1
            actors[identity] = (x,y,speed)
        focus_x = int(np.mean([a[0] for a in actors.values()]))
        focus_y = int(np.mean([a[1]-20 for a in actors.values()]))

        # Motion streaks, shaped to the direction of travel.
        for identity, (x,y,speed) in actors.items():
            if speed > 10:
                col = {"blue":BLUE,"red":RED,"gold":GOLD}[identity]
                for k in range(5):
                    tail = (x - (x - smooth_path(PATHS[identity], max(0,t - 0.04*(k+1)))[0])*1.7,
                            y - (y - smooth_path(PATHS[identity], max(0,t - 0.04*(k+1)))[1])*1.7)
                    cv2.line(frame, (int(tail[0]),int(tail[1])), (int(x),int(y-20)), col, max(1,5-k), cv2.LINE_AA)

        # Energy beams are triggered by original timeline beats.
        if 55 < t < 62 or 128 < t < 141 or 190 < t < 205 or 257 < t < 271:
            pair = ("blue","red") if t < 90 or 150 < t < 230 else ("gold","red")
            if pair[0] in actors and pair[1] in actors:
                p = actors[pair[0]]; q = actors[pair[1]]
                c = BLUE if t < 90 else (GOLD if pair[0]=="gold" else RED)
                p1=(int(p[0]),int(p[1]-30)); p2=(int(q[0]),int(q[1]-30))
                cv2.line(frame,p1,p2,c,18,cv2.LINE_AA)
                cv2.line(frame,p1,p2,WHITE,3,cv2.LINE_AA)
                cv2.circle(frame,p1,16,c,2,cv2.LINE_AA); cv2.circle(frame,p2,16,c,2,cv2.LINE_AA)

        # Impacts, radial shock rings, and debris bursts.
        impact_strength = 0.0
        for idx, ti in enumerate(IMPACTS):
            d = abs(t-ti)
            if d < 0.32:
                strength = 1.0 - d/0.32
                impact_strength = max(impact_strength, strength)
                radius = int((32 + (0.32-d)*270))
                cv2.circle(frame,(focus_x,focus_y),radius,WHITE if d < 0.035 else (90,190,255),2,cv2.LINE_AA)
                cv2.circle(frame,(focus_x,focus_y),max(3,radius-26),RED if idx%2 else BLUE,1,cv2.LINE_AA)
                draw_sparks(frame, focus_x, focus_y, t, strength, 9100+idx)
        # Small debris falls naturally after big impacts in the rocky stages.
        if (t < 160 or t > 225) and impact_strength > 0.1:
            for k in range(24):
                angle = k*math.pi*2/24 + t*0.5
                rr = 55 + 125*impact_strength
                px = int(focus_x + math.cos(angle)*rr)
                py = int(focus_y + math.sin(angle)*rr*0.55 + (1-impact_strength)*30)
                cv2.fillPoly(frame,[np.array([[px,py],[px+4,py-7],[px+9,py+1]],np.int32)],(95,96,101),cv2.LINE_AA)

        # The third fighter appears after the opening duel.
        for identity, (x,y,speed) in actors.items():
            col = {"blue":BLUE,"red":RED,"gold":GOLD}[identity]
            opponent_candidates = [v for k,v in actors.items() if k != identity]
            other_x = opponent_candidates[0][0] if opponent_candidates else (width/2)
            facing = 1 if other_x >= x else -1
            state = choose_state(identity,t,speed)
            power = 0.55 + 0.4*(0.5+0.5*math.sin(t*2.3+len(identity)))
            if identity == "gold":
                power = min(1.0, power+0.2)
            draw_fighter(frame,x,y,col,t,state,facing,1.0,power,identity)

        # One-frame negative flashes add impact weight without copying source frames.
        if impact_strength > 0.88:
            frame = cv2.addWeighted(frame,0.18,np.full_like(frame,255),0.82,0)
        if t < 5.0:
            alpha = min(1.0,t/0.5,(5.0-t)/0.7)
            if alpha > 0:
                layer = frame.copy()
                cv2.putText(layer,"PRISM BREAK",(350,260),cv2.FONT_HERSHEY_DUPLEX,1.8,(245,248,255),3,cv2.LINE_AA)
                cv2.putText(layer,"THREE FORCES  /  ORIGINAL ANIMATION",(354,305),cv2.FONT_HERSHEY_SIMPLEX,0.65,(180,206,246),2,cv2.LINE_AA)
                frame = cv2.addWeighted(layer,alpha,frame,1-alpha,0)
        if t > duration - 5.5:
            alpha = min(1.0,(t-(duration-5.5))/0.7,(duration-t)/0.4)
            layer = frame.copy()
            cv2.putText(layer,"PRISM BREAK",(355,285),cv2.FONT_HERSHEY_DUPLEX,1.65,WHITE,3,cv2.LINE_AA)
            cv2.putText(layer,"THE END",(542,329),cv2.FONT_HERSHEY_SIMPLEX,0.72,GOLD,2,cv2.LINE_AA)
            frame = cv2.addWeighted(layer,max(0,min(1,alpha)),frame,1-max(0,min(1,alpha)),0)

        # Dynamic camera: small tracking drift and impact-weighted shake.
        shake = impact_strength * 13.0
        sx = int(math.sin(f*1.37)*shake + math.sin(t*1.7)*5)
        sy = int(math.cos(f*1.13)*shake*0.7 + math.sin(t*2.1)*3)
        zoom = 1.0 + impact_strength*0.065 + 0.012*math.sin(t*0.9)
        M = cv2.getRotationMatrix2D((width/2,height/2), math.sin(t*0.7)*0.7+impact_strength*1.5, zoom)
        M[0,2] += sx; M[1,2] += sy
        frame = cv2.warpAffine(frame,M,(width,height),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT)
        writer.write(frame)
        if f in snapshots:
            cv2.imwrite(str(snapshots[f]),frame)
        if f % max(1,int(fps*10)) == 0:
            print("rendered",f,"/",frames,"seconds",round(t,2),flush=True)
    writer.release()
    print("video_only_done",raw,"frames",frames,flush=True)

    print("generating_original_score",flush=True)
    generate_music(wav_path,duration)
    print("encoding_h264_and_muxing_audio",flush=True)
    command = ["ffmpeg","-y","-loglevel","error","-i",str(raw),"-i",str(wav_path),
               "-map","0:v:0","-map","1:a:0","-c:v","libx264","-preset","ultrafast","-crf","20",
               "-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-t",str(duration),
               "-movflags","+faststart",str(output)]
    subprocess.run(command,check=True)
    meta = {"title":"Prism Break — Three Forces","type":"original animation","duration_seconds":duration,
            "resolution":"1280x720","fps":fps,"frames_rendered":frames,
            "audio":"Original procedurally synthesized score","reference_frames_or_audio_reused":False}
    output.with_suffix(".json").write_text(json.dumps(meta,indent=2),encoding="utf-8")
    print("FINAL_VIDEO",str(output),"bytes",output.stat().st_size,flush=True)
    raw.unlink(missing_ok=True)
    wav_path.unlink(missing_ok=True)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="output/Prism_Break_Original_720p24.mp4")
    parser.add_argument("--duration",type=float,default=DEFAULT_DURATION)
    parser.add_argument("--fps",type=int,default=DEFAULT_FPS)
    parser.add_argument("--width",type=int,default=W)
    parser.add_argument("--height",type=int,default=H)
    args=parser.parse_args()
    render(args)

if __name__ == "__main__":
    main()
