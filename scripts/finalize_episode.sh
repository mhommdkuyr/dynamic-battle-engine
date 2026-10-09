#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
mkdir -p audio output/frames
: "${ANIME_ASSET_DIR:=$ROOT/assets/private}"
export ANIME_ASSET_DIR
required=(
  "$ANIME_ASSET_DIR/nightshade.fbx"
  "$ANIME_ASSET_DIR/prisoner.fbx"
  "$ANIME_ASSET_DIR/mocap/Superhero/WatchOverCity_mixamo.fbx"
  "$ANIME_ASSET_DIR/mocap/Superhero/IronMan_Combat_mixamo.fbx"
  "$ANIME_ASSET_DIR/mocap/Superhero/MutantClaws_mixamo.fbx"
  "$ANIME_ASSET_DIR/mocap/Superhero/SuperHeroLanding_Takeoff_mixamo.fbx"
  "$ANIME_ASSET_DIR/mocap/Superhero/SuperHeroFlying_mixamo.fbx"
  "$ANIME_ASSET_DIR/mocap/Superhero/HulkTransformation_mixamo.fbx"
  "$ANIME_ASSET_DIR/mocap/MagicPack/Mixamo/DrStrangeMagic_mixamo.fbx"
  "$ANIME_ASSET_DIR/mocap/MagicPack/Mixamo/Fireballs_mixamo.fbx"
  "$ANIME_ASSET_DIR/mocap/MagicPack/Mixamo/GiantEnergyBlast_mixamo.fbx"
  "$ANIME_ASSET_DIR/mocap/MagicPack/Mixamo/MagicShields_mixamo.fbx"
  "$ANIME_ASSET_DIR/mocap/MagicPack/Mixamo/MagicExplosion_mixamo.fbx"
)
for f in "${required[@]}"; do
  if [[ ! -s "$f" ]]; then echo "Required private asset missing: $f" >&2; exit 2; fi
done
python3 scripts/make_episode_audio.py
edge-tts --voice ja-JP-KeitaNeural --rate=-12% --pitch=-12Hz --text '鎖を解いたところで、貴様はただの野獣に過ぎん。' --write-media audio/nightshade_open.mp3
edge-tts --voice ja-JP-KeitaNeural --rate=-8% --pitch=+5Hz --text 'なら見せてやる……その野獣が貴様の牢獄をどう叩き潰すかをな！' --write-media audio/prisoner_open.mp3
edge-tts --voice ja-JP-KeitaNeural --rate=-12% --pitch=-12Hz --text '悪くない……獣にしてはな。' --write-media audio/nightshade_end.mp3
edge-tts --voice ja-JP-KeitaNeural --rate=-8% --pitch=+5Hz --text '次の一戦が、俺たちの運命を決める。' --write-media audio/prisoner_end.mp3
ffmpeg -hide_banner -loglevel error -y -i audio/score_sfx.wav -i audio/nightshade_open.mp3 -i audio/prisoner_open.mp3 -i audio/nightshade_end.mp3 -i audio/prisoner_end.mp3 \
  -filter_complex "[0:a]volume=0.82[bed];[1:a]volume=1.15,adelay=2200|2200[v1];[2:a]volume=1.12,adelay=7180|7180[v2];[3:a]volume=1.15,adelay=52850|52850[v3];[4:a]atempo=1.08,volume=1.12,adelay=56050|56050[v4];[bed][v1][v2][v3][v4]amix=inputs=5:duration=first:normalize=0:dropout_transition=0,alimiter=limit=0.94,afade=t=in:st=0:d=0.4,afade=t=out:st=58.9:d=1.1[a]" \
  -map '[a]' -t 60 -ar 48000 -ac 2 -c:a pcm_s16le audio/episode01_master.wav
blender -b --python scripts/render_episode.py -- --duration 60 --fps 12 --width 1280 --height 720 --output "$ROOT/output/frames"
ffmpeg -hide_banner -loglevel warning -y -framerate 12 -start_number 1 -i "$ROOT/output/frames/frame_%04d.png" -i "$ROOT/audio/episode01_master.wav" \
  -vf "minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,scale=1920:1080:flags=lanczos,eq=gamma=1.08:brightness=0.01:contrast=1.04:saturation=1.10,drawbox=x=0:y=0:w=iw:h=190:color=black@0.68:t=fill:enable='between(t,0.45,4.5)',drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='SHADOWS  &  IRON':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=22:shadowcolor=black@0.95:shadowx=2:shadowy=3:enable='between(t,0.45,4.5)',drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='EPISODE 01  /  BREAK THE CAGE':fontcolor=0x64D8FF:fontsize=26:x=(w-text_w)/2:y=104:enable='between(t,0.45,4.5)',drawbox=x=iw*0.32:y=156:w=iw*0.36:h=2:color=0x38CCFF@0.9:t=fill:enable='between(t,0.45,4.5)',subtitles=$ROOT/production/episode01.ass:fontsdir=/usr/share/fonts/truetype" \
  -t 60 -map 0:v:0 -map 1:a:0 -r 60 -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -c:a aac -b:a 256k -movflags +faststart \
  "$ROOT/output/Episode01_Shadows_and_Iron_Final_1080p60.mp4"
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,r_frame_rate -of json "$ROOT/output/Episode01_Shadows_and_Iron_Final_1080p60.mp4"
