import numpy as np, wave, math, os
from scipy.signal import butter, sosfilt
SR=48000; DUR=60.0; N=int(SR*DUR); rng=np.random.default_rng(23945)
os.makedirs('audio',exist_ok=True)
t=np.arange(N,dtype=np.float32)/SR
# Stereoscopic rain bed with darker low-pass rumble and spatial drift.
white=rng.normal(0,1,N).astype(np.float32)
low=sosfilt(butter(3,650,fs=SR,output='sos'),white).astype(np.float32)
bright=sosfilt(butter(2,3200,fs=SR,btype='highpass',output='sos'),white).astype(np.float32)
rain=(.035*low/(np.std(low)+1e-5)+.010*bright/(np.std(bright)+1e-5)).astype(np.float32)
# Original score: ominous minor-key drones with a rising pulse from the first engagement.
fade=np.clip(t/2,0,1)*np.clip((DUR-t)/2,0,1)
pulse=np.clip((t-10)/8,0,1)*(0.5+0.5*np.sin(2*np.pi*(1.3+0.025*t)*t))
pad=(.028*np.sin(2*np.pi*55*t)+.021*np.sin(2*np.pi*82.41*t+.2)+.018*np.sin(2*np.pi*110*t+.4)+.012*np.sin(2*np.pi*164.81*t+.6))
pad*=fade*(.75+.65*pulse)
mixL=(rain+pad).astype(np.float32); mixR=(rain*.91+pad*np.sin(2*np.pi*.025*t+1.1)).astype(np.float32)
# A low cinematic boom, metallic crack, and airy slash are synthesised for the marked beats.
def add_stereo(start, sig, pan=0.0):
 i=max(0,int(start*SR)); j=min(N,i+len(sig));
 if j<=i:return
 sig=sig[:j-i].astype(np.float32); l=math.sqrt((1-pan)/2); r=math.sqrt((1+pan)/2)
 mixL[i:j]+=sig*l; mixR[i:j]+=sig*r
# Low timpani heartbeat through the pursuit.
for s in np.arange(12.0,54.0,1.65):
 dur=.48; q=np.arange(int(dur*SR),dtype=np.float32)/SR; env=np.exp(-8*q)
 sig=.17*env*np.sin(2*np.pi*(72-22*q/dur)*q)
 add_stereo(float(s),sig,pan=float(np.sin(s)*.22))
# Impact signatures: deep sub-bass + noise crack + descending metal overtone.
for idx,s in enumerate((15.8,21.9,30.95,39.9,47.8,50.35)):
 dur=1.5; q=np.arange(int(dur*SR),dtype=np.float32)/SR; env=np.exp(-3.9*q)
 bass=.45*env*np.sin(2*np.pi*(46+8*np.exp(-5*q))*q)
 crack=rng.normal(0,1,len(q)).astype(np.float32)*np.exp(-28*q)*.23
 metal=.10*np.exp(-4.5*q)*np.sin(2*np.pi*(1500-650*q/dur)*q)
 add_stereo(s,bass+crack+metal,pan=(-.65 if idx%2==0 else .65))
# Wind-up / sword swish whooshes.
for idx,s in enumerate((13.4,17.0,19.7,24.7,29.5,33.2,37.4,41.4,45.7,49.3)):
 dur=.75; q=np.arange(int(dur*SR),dtype=np.float32)/SR; noise=rng.normal(0,1,len(q)).astype(np.float32)
 band=sosfilt(butter(3,[550,5000],btype='bandpass',fs=SR,output='sos'),noise).astype(np.float32)
 env=np.sin(np.pi*q/dur)**1.6
 tone=np.sin(2*np.pi*(240+1500*q/dur)*q)*.13
 add_stereo(s,(band/(np.std(band)+1e-5)*.065+tone)*env,pan=(-.5 if idx%2==0 else .5))
# Low thunder sweeps at the open and final hit.
for s in (0.25,10.7,27.8,43.4,48.2):
 dur=3.5; q=np.arange(int(dur*SR),dtype=np.float32)/SR; noise=rng.normal(0,1,len(q)).astype(np.float32); rum=sosfilt(butter(3,180,fs=SR,output='sos'),noise); env=np.exp(-1.5*q)*(.55+.45*np.sin(np.pi*q/dur))
 add_stereo(s,rum/(np.std(rum)+1e-5)*.065*env,pan=.08)
# Soft fade and limiter.
for arr in (mixL,mixR):
 arr*=.90; np.clip(arr,-.93,.93,out=arr)
stereo=np.stack([mixL,mixR],axis=1)
with wave.open('audio/score_sfx.wav','wb') as wf:
 wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes((stereo*32767).astype(np.int16).tobytes())
print('wrote 60s score/SFX',os.path.getsize('audio/score_sfx.wav'))
