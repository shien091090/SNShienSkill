# python rec.py <name>  — records the whole main screen (ffmpeg ddagrab, 30 fps) plus what the speakers play
# (WASAPI loopback via the soundcard package) until a file named STOP appears next to this script's parent folder,
# then muxes them into ../<name>.mkv. Audio is clocked by wall time: gaps the loopback skips (silence) are filled with
# zeros so sound stays in sync with the picture over long takes.
import os, sys, time, threading, subprocess, wave
import numpy as np
import soundcard as sc

name = sys.argv[1]
here = os.path.dirname(os.path.abspath(__file__))
out = os.path.dirname(here)
FF = sys.argv[2] if len(sys.argv) > 2 else os.environ['FFMPEG']
stop_file = os.path.join(out, 'STOP')
if os.path.exists(stop_file): os.remove(stop_file)
vid, wav, final = [os.path.join(out, f'_{name}.video.mkv'), os.path.join(out, f'_{name}.wav'), os.path.join(out, f'{name}.mkv')]

SR = 48000
# encoder: the AMD iGPU's AMF (frees the CPU for the game; libx264 on the CPU fell to ~44 fps while a game ran).
# REC_ENC=x264 falls back to the CPU.
ENC = (['-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '16'] if os.environ.get('REC_ENC') == 'x264'
       else ['-c:v', 'h264_amf', '-quality', 'quality', '-rc', 'cqp', '-qp_i', '16', '-qp_p', '18'])
# 30 fps by default: on this hybrid-GPU laptop the capture itself can't keep 60 (a 60 fps take came out at ~38 with
# uneven frame gaps), while 30 stays even. REC_FPS=60 to try again on a stronger machine.
FPS = int(os.environ.get('REC_FPS', '30'))
stop = threading.Event()
audio_t0 = []

def audio():
    spk = sc.default_speaker()
    mic = sc.get_microphone(id=str(spk.name), include_loopback=True)
    w = wave.open(wav, 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    written = 0
    with mic.recorder(samplerate=SR, channels=2) as r:
        t0 = time.perf_counter(); audio_t0.append(t0)
        while not stop.is_set():
            d = r.record(numframes=SR // 20)
            due = int((time.perf_counter() - t0) * SR)
            if due - written > len(d) + SR // 50:  # loopback went quiet and skipped time: pad with silence
                pad = due - written - len(d)
                w.writeframes(np.zeros((pad, 2), np.int16).tobytes()); written += pad
            w.writeframes((np.clip(d, -1, 1) * 32767).astype(np.int16).tobytes()); written += len(d)
    w.close()

th = threading.Thread(target=audio, daemon=True); th.start()
while not audio_t0: time.sleep(0.01)
v = subprocess.Popen([FF, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', f'ddagrab=framerate={FPS}',
                      '-vf', 'hwdownload,format=bgra,format=nv12', *ENC, vid], stdin=subprocess.PIPE)
video_t0 = time.perf_counter()
print('REC', name, flush=True)
while not os.path.exists(stop_file) and v.poll() is None: time.sleep(0.2)
v.stdin.write(b'q'); v.stdin.flush(); v.wait()
stop.set(); th.join()
os.remove(stop_file) if os.path.exists(stop_file) else None
off = video_t0 - audio_t0[0]  # audio started this much earlier: cut it off the front
subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-i', vid, '-ss', f'{off:.3f}', '-i', wav,
                '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'flac', '-shortest', final], check=True)
os.remove(vid); os.remove(wav)
print('DONE', final, flush=True)
