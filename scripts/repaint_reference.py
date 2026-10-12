import cv2, numpy as np, subprocess, argparse, pathlib, json, os, tempfile, time, math
from collections import Counter


def add_armor_details(frame, mask, accent_bgr, component_min=2500, phase=0):
    """Procedurally paint new 2D armor seams/visors inside the tracked source silhouette."""
    count, labels, compstats, _ = cv2.connectedComponentsWithStats(mask, 8)
    H, W = frame.shape[:2]
    for label in range(1, count):
        x, y, w, h, area = [int(q) for q in compstats[label]]
        box = max(1, w*h)
        if area < component_min or w < 26 or h < 100 or box > H*W*0.86:
            continue
        fill = area/box
        aspect = h/max(1,w)
        if fill < 0.12 or not (0.12 <= aspect <= 8.0):
            continue
        local_labels = labels[y:y+h, x:x+w] == label
        # All paint is confined to the original character pixels; the original pose stays exact.
        art = np.zeros((h,w), dtype=np.uint8)
        cx = w//2
        thick = max(2, min(7, int(min(w,h)*0.012)))
        vis_y = max(3, int(h*0.105))
        vis_half = max(8, min(int(w*0.19), int(h*0.10)))
        # Helmet brow / single illuminated visor plus cheek-angle cuts.
        cv2.line(art, (max(0,cx-vis_half),vis_y+thick),
                 (min(w-1,cx+vis_half),vis_y), 255, thick, cv2.LINE_AA)
        cv2.line(art, (max(0,cx-vis_half),vis_y+thick),
                 (max(0,cx-int(vis_half*.60)),min(h-1,vis_y+int(h*.045))), 180, max(1,thick//2), cv2.LINE_AA)
        cv2.line(art, (min(w-1,cx+vis_half),vis_y),
                 (min(w-1,cx+int(vis_half*.60)),min(h-1,vis_y+int(h*.045))), 180, max(1,thick//2), cv2.LINE_AA)
        # Angular chest crest, with layered pauldrons and segmented abdominal plates.
        cy = int(h*0.405)
        span = max(10,min(int(w*.18),int(h*.12)))
        cv2.line(art,(max(0,cx-span),cy),(cx, min(h-1,cy+int(h*.055))),255,thick,cv2.LINE_AA)
        cv2.line(art,(cx,min(h-1,cy+int(h*.055))),(min(w-1,cx+span),cy),255,thick,cv2.LINE_AA)
        for frac in (0.49,0.535,0.58):
            py=int(h*frac)
            cv2.line(art,(max(0,cx-int(span*.45)),py),
                     (min(w-1,cx+int(span*.45)),py-int(h*.008)),180,max(1,thick//2),cv2.LINE_AA)
        # Side armor plates. These become clipped chevrons on extended arms/leg silhouettes.
        for fx,fy,sgn in ((.24,.36,1),(.76,.36,-1),(.29,.73,1),(.71,.73,-1)):
            px=int(w*fx); py=int(h*fy); dx=max(5,int(w*.045)); dy=max(5,int(h*.025))
            p1=(max(0,px-dx),max(0,py-dy)); p2=(min(w-1,px+dx),min(h-1,py+dy))
            cv2.line(art,p1,p2,180,max(1,thick//2),cv2.LINE_AA)
        glow=cv2.GaussianBlur(art,(0,0),sigmaX=max(1.0,thick*1.15))
        roi=frame[y:y+h,x:x+w]
        near=(glow>8)
        if np.any(near):
            col=np.array(accent_bgr,dtype=np.float32)
            old=roi[near].astype(np.float32)
            alpha=(glow[near].astype(np.float32)/255.0*0.55)[:,None]
            roi[near]=np.clip(old*(1-alpha)+col*alpha,0,255).astype(np.uint8)
        painted=(art>0)&local_labels
        if np.any(painted):
            # Cool/silver edge ink keeps the mask faithful while changing the character design.
            roi[painted]=np.array(accent_bgr,dtype=np.uint8)


def style_white_characters(frame, white_mask, frame_index):
    """Detect compact white character mattes and repaint them as an original silver/gold fighter."""
    H,W=frame.shape[:2]
    count,labels,cs,_=cv2.connectedComponentsWithStats(white_mask,8)
    chosen=np.zeros((H,W),dtype=np.uint8)
    frame_area=H*W
    for label in range(1,count):
        x,y,w,h,area=[int(v) for v in cs[label]]
        box=max(1,w*h)
        if area < 2200 or area > 180000 or w < 24 or h < 100:
            continue
        if w > W*0.46 or h > H*0.74 or box > frame_area*0.24:
            continue
        if x <= 1 or x+w >= W-1:
            continue
        if area/box < 0.15 or h/max(1,w) < 0.35:
            continue
        chosen[labels==label]=255
    npx=int(cv2.countNonZero(chosen))
    if npx:
        lum=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY).astype(np.float32)
        m=chosen>0
        # Platinum-gold shell preserving source silhouette brightness and anti-aliased edges.
        b=np.clip(106+0.42*lum[m],0,255)
        g=np.clip(130+0.42*lum[m],0,255)
        r=np.clip(158+0.38*lum[m],0,255)
        frame[m]=np.stack([b,g,r],axis=1).astype(np.uint8)
        add_armor_details(frame,chosen,(70,205,255),component_min=1800,phase=frame_index)
    return npx

def repaint_frame(frame, frame_index, fps, stats):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    red = (((h <= 12) | (h >= 170)) & (s >= 65) & (v >= 55)).astype(np.uint8) * 255
    yellow = ((h >= 13) & (h <= 39) & (s >= 75) & (v >= 95)).astype(np.uint8) * 255
    neutral_dark = ((s < 78) & (v < 52)).astype(np.uint8) * 255
    neutral_white = ((s < 48) & (v > 225)).astype(np.uint8) * 255

    red_area = int(cv2.countNonZero(red))
    yellow_area = int(cv2.countNonZero(yellow))
    if red_area:
        # The red fighter and red motion trails become an original blue/cyan armor-energy palette.
        hsv[red > 0, 0] = 102
        hsv[red > 0, 1] = np.clip(s[red > 0] * 0.92 + 28, 135, 255).astype(np.uint8)
        hsv[red > 0, 2] = np.clip(v[red > 0] * 0.97 + 8, 0, 255).astype(np.uint8)
    if yellow_area:
        # Gold/orange aura and energy strokes shift into a cold plasma family; white impact cores remain.
        hsv[yellow > 0, 0] = 94
        hsv[yellow > 0, 1] = np.clip(s[yellow > 0] * 0.78 + 34, 90, 235).astype(np.uint8)
        hsv[yellow > 0, 2] = np.clip(v[yellow > 0] * 1.02 + 5, 0, 255).astype(np.uint8)
    frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    if red_area:
        add_armor_details(frame, red, (245, 244, 190), component_min=6500, phase=frame_index)
    # Vectorized silver-gold treatment for bright neutral character/impact pixels. Keep full-frame flashes white.
    white_count = int(cv2.countNonZero(neutral_white))
    white_repainted = 0
    if 0 < white_count < int(frame.shape[0] * frame.shape[1] * 0.44):
        white_sel = neutral_white > 0
        lumw = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
        values = lumw[white_sel]
        frame[white_sel, 0] = np.clip(108 + values * 0.42, 0, 255).astype(np.uint8)
        frame[white_sel, 1] = np.clip(132 + values * 0.42, 0, 255).astype(np.uint8)
        frame[white_sel, 2] = np.clip(160 + values * 0.37, 0, 255).astype(np.uint8)
        white_repainted = white_count

    # Repaint neutral midtone environment pixels into a cinematic midnight/indigo palette.
    # High-energy white flashes (V >= 210) and saturated character/FX mattes are intentionally excluded.
    grade_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    gh, gs, gv = cv2.split(grade_hsv)
    environment_mask = (gs < 42) & (gv > 52) & (gv < 210)
    environment_pixels = int(np.count_nonzero(environment_mask))
    if environment_pixels:
        vfloat = gv[environment_mask].astype(np.float32)
        grade_hsv[environment_mask, 0] = 112
        grade_hsv[environment_mask, 1] = np.clip(34 + (vfloat - 52) * 0.36, 35, 100).astype(np.uint8)
        grade_hsv[environment_mask, 2] = np.clip(vfloat * 0.76 + 14, 38, 190).astype(np.uint8)
        frame = cv2.cvtColor(grade_hsv, cv2.COLOR_HSV2BGR)

    # Dark/black fighter stays a black silhouette, with a subtle midnight-blue tint.
    hsv2 = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    v2 = hsv2[:, :, 2].astype(np.float32)
    s2 = hsv2[:, :, 1]
    dark = ((s2 < 85) & (v2 < 44)).astype(np.uint8) * 255
    m = dark > 0
    if np.any(m):
        vv = v2[m]
        frame[m, 0] = np.clip(12 + vv * 0.48, 0, 78).astype(np.uint8)
        frame[m, 1] = np.clip(3 + vv * 0.24, 0, 30).astype(np.uint8)
        frame[m, 2] = np.clip(8 + vv * 0.38, 0, 48).astype(np.uint8)
    # Build an electric rim only where a dark silhouette borders a brighter pixel.
    bright = (v2 > 78).astype(np.uint8) * 255
    neighbor_bright = cv2.dilate(bright, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    rim = (dark > 0) & (neighbor_bright > 0)
    if np.any(rim):
        # Blend violet-cyan edge light, rather than replacing the black fill.
        old = frame[rim].astype(np.float32)
        glow = np.array([188, 92, 70], dtype=np.float32)  # BGR
        frame[rim] = np.clip(old * 0.42 + glow * 0.58, 0, 255).astype(np.uint8)

    if int(cv2.countNonZero(neutral_dark)) < int(frame.shape[0] * frame.shape[1] * 0.46):
        add_armor_details(frame, neutral_dark, (230, 185, 90), component_min=12000, phase=frame_index)

    # Thin plasma halo around the recoloured fighter masks, clipped outside the silhouette.
    post_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    post_h, post_s = post_hsv[:, :, 0], post_hsv[:, :, 1]
    red_now = (((post_h >= 87) & (post_h <= 113) & (post_s > 115))).astype(np.uint8) * 255
    if cv2.countNonZero(red_now):
        dil = cv2.dilate(red_now, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
        outer = (dil > 0) & (red_now == 0)
        if np.any(outer):
            old = frame[outer].astype(np.float32)
            glow = np.array([220, 155, 65], dtype=np.float32)
            frame[outer] = np.clip(old * 0.62 + glow * 0.38, 0, 255).astype(np.uint8)

    # Draw original 2D armor panel seams inside contiguous blue fighter components.
    # Source silhouette/motion remains the mask, so timing and pose geometry stay frame-exact.
    hue = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    blue_mask = (((hue[:, :, 0] >= 87) & (hue[:, :, 0] <= 113) &
                  (hue[:, :, 1] > 115) & (hue[:, :, 2] > 45))).astype(np.uint8) * 255
    num, labels, compstats, _ = cv2.connectedComponentsWithStats(blue_mask, 8)
    for label in range(1, num):
        x, y, w, hh, area = [int(z) for z in compstats[label]]
        box_area = max(1, w * hh)
        if area < 7000 or hh < 85 or w < 35 or box_area > frame.shape[0] * frame.shape[1] * 0.78:
            continue
        fill_ratio = area / box_area
        aspect = hh / max(1, w)
        if fill_ratio < 0.17 or not (0.16 <= aspect <= 6.0):
            continue
        roi_label = labels[y:y+hh, x:x+w] == label
        # Armor engraving is anchored to each connected silhouette, not screen-space.
        yy, xx = np.indices((hh, w), dtype=np.int32)
        phase = (frame_index // 2) % 83
        seam1 = (((xx + yy * 2 + phase) % 79) < 2)
        seam2 = (((xx * 2 - yy + phase * 2) % 113) < 2)
        etched = roi_label & (seam1 | seam2)
        if np.any(etched):
            roi = frame[y:y+hh, x:x+w]
            roi[etched] = np.clip(roi[etched].astype(np.int16) * 0.55 +
                                  np.array([15, 70, 35], np.int16), 0, 255).astype(np.uint8)
        # Visor and chest chevrons only where the component is tall enough to read as a figure.
        if hh > 170 and w < frame.shape[1] * 0.68 and y > 3 and y + hh < frame.shape[0] - 2:
            shape = np.zeros((hh, w), np.uint8)
            visor_y = int(hh * 0.16)
            cx = w // 2
            cv2.line(shape, (max(0, cx-int(w*0.13)), visor_y),
                     (min(w-1, cx+int(w*0.13)), visor_y-int(hh*0.012)), 255, max(2, int(w*0.012)))
            chest_y = int(hh * 0.43)
            cv2.line(shape, (max(0,cx-int(w*0.15)), chest_y),
                     (cx, chest_y+int(hh*0.05)), 255, max(2,int(w*0.018)))
            cv2.line(shape, (cx, chest_y+int(hh*0.05)),
                     (min(w-1,cx+int(w*0.15)), chest_y), 255, max(2,int(w*0.018)))
            clipped = (shape > 0) & roi_label
            if np.any(clipped):
                roi = frame[y:y+hh, x:x+w]
                roi[clipped] = np.array([245, 245, 210], np.uint8)

    # Shift saturated orange-red screen FX to blue while preserving the actual frames and camera.
    stats['red_mask_pixels'] += red_area
    stats['yellow_mask_pixels'] += yellow_area
    stats['white_character_pixels'] += white_repainted
    stats['environment_pixels'] += environment_pixels
    stats['frames'] += 1
    return frame

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--start', type=float, default=0.0)
    p.add_argument('--duration', type=float, default=0.0, help='0 means until end of source')
    p.add_argument('--crf', type=int, default=18)
    p.add_argument('--preset', default='ultrafast')
    p.add_argument('--mux-audio', action='store_true')
    args = p.parse_args()
    src = pathlib.Path(args.input); out = pathlib.Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(src))
    if not cap.isOpened():
        raise RuntimeError(f'Cannot open source: {src}')
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    start_frame = max(0, int(round(args.start * fps)))
    end_frame = total_frames if args.duration <= 0 else min(total_frames, start_frame + int(round(args.duration*fps)))
    if start_frame >= total_frames or end_frame <= start_frame:
        raise ValueError('Requested range is outside the source video.')
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    temp_video = out.with_name(out.stem + '_video_only.mp4')
    encode_log = out.with_name(out.stem + '_encode.log')
    enc_file = encode_log.open('wb')
    cmd = ['ffmpeg','-y','-hide_banner','-loglevel','error',
           '-f','rawvideo','-pix_fmt','bgr24','-s',f'{width}x{height}','-r',str(fps),'-i','pipe:0',
           '-an','-c:v','libx264','-preset',args.preset,'-crf',str(args.crf),'-pix_fmt','yuv420p',
           '-movflags','+faststart',str(temp_video)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=enc_file, stdout=subprocess.DEVNULL)
    stats=Counter(); t0=time.time()
    for idx in range(start_frame, end_frame):
        ok, frame = cap.read()
        if not ok:
            break
        processed = repaint_frame(frame, idx, fps, stats)
        try:
            proc.stdin.write(processed.tobytes())
        except BrokenPipeError:
            break
        relative = idx - start_frame
        if relative % max(1,int(fps*10)) == 0:
            print(f'processed {relative}/{end_frame-start_frame} t={relative/fps:.1f}s elapsed={time.time()-t0:.1f}s',flush=True)
    cap.release()
    proc.stdin.close()
    code=proc.wait()
    enc_file.close()
    if code != 0 or not temp_video.exists() or temp_video.stat().st_size < 100_000:
        tail=encode_log.read_text(errors='replace')[-3000:] if encode_log.exists() else ''
        raise RuntimeError(f'Video encoding failed (code={code}). {tail}')
    if args.mux_audio:
        audio_tmp = out.with_name(out.stem+'_mux.mp4')
        cmd2=['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(temp_video)]
        if args.start > 0:
            cmd2 += ['-ss',str(args.start)]
        cmd2 += ['-i',str(src),'-map','0:v:0','-map','1:a:0?','-c:v','copy','-c:a','copy']
        if args.start == 0 and args.duration <= 0:
            # Keep the complete original audio stream, including its short tail after the last video frame.
            cmd2 += ['-map_metadata','1','-movflags','+faststart',str(audio_tmp)]
        else:
            cmd2 += ['-t',str((end_frame-start_frame)/fps),'-map_metadata','1','-movflags','+faststart',str(audio_tmp)]
        subprocess.run(cmd2,check=True)
        audio_tmp.replace(out)
        temp_video.unlink(missing_ok=True)
    else:
        temp_video.replace(out)
    report={'source':str(src),'output':str(out),'source_fps':fps,'source_total_frames':total_frames,
            'processed_frames':stats['frames'],'start_frame':start_frame,'end_frame_exclusive':start_frame+stats['frames'],
            'start_seconds':args.start,'duration_seconds':stats['frames']/fps,'resolution':[width,height],
            'red_pixels_repainted':stats['red_mask_pixels'],'yellow_fx_pixels_repainted':stats['yellow_mask_pixels'],
            'white_character_pixels_repainted':stats['white_character_pixels'],'environment_pixels_repainted':stats['environment_pixels'],'frame_order_preserved':True,
            'source_audio_muxed':bool(args.mux_audio),'preserved_source_frame_order':True}
    out.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('REPAINT_COMPLETE '+json.dumps(report),flush=True)

if __name__=='__main__':
    main()
