# -*- coding: utf-8 -*-
"""시트 PNG → 미리보기 GIF 재생성. 손보정한 시트에도 그대로 쓴다.
프레임 시간은 _build.json의 durations_ms(임시값). 실행: 프로젝트 루트에서
  python outputs/보스_바르갈_v1/_생성스크립트/make_gifs.py
"""
import os, json, re
import numpy as np
from PIL import Image

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BG = (51, 43, 47)
SCALE = 4
build = json.load(open(os.path.join(DIR, '_build.json'), encoding='utf-8'))

def frames_from_sheet(path, w, h):
    sheet = Image.open(path).convert('RGBA')
    n = sheet.width // w
    return [sheet.crop((i * w, 0, i * w + w, h)) for i in range(n)]

def make_gif(frames, durs, out):
    # 배경 위에 합성 → RGB → 모든 프레임을 하나의 고정 팔레트로 양자화(프레임마다 팔레트가 달라지는 문제 방지)
    rgb = []
    for f in frames:
        big = f.resize((f.width * SCALE, f.height * SCALE), Image.NEAREST)
        bg = Image.new('RGBA', big.size, BG + (255,)); bg.alpha_composite(big)
        rgb.append(bg.convert('RGB'))
    strip = Image.new('RGB', (rgb[0].width, rgb[0].height * len(rgb)))
    for i, im in enumerate(rgb): strip.paste(im, (0, i * im.height))
    master = strip.quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = [im.quantize(palette=master, dither=Image.Dither.NONE) for im in rgb]
    import time
    for k in range(5):
        try:
            pal[0].save(out, save_all=True, append_images=pal[1:], duration=list(durs), loop=0, optimize=False); return
        except OSError:
            time.sleep(0.6)
    pal[0].save(out, save_all=True, append_images=pal[1:], duration=list(durs), loop=0, optimize=False)

for key, info in build['sheets'].items():
    w, h = info['canvas']
    frames = frames_from_sheet(os.path.join(DIR, info['file']), w, h)
    durs = info['durations_ms']
    if len(durs) != len(frames): durs = [100] * len(frames)
    make_gif(frames, durs, os.path.join(DIR, f'미리보기_{key}.gif'))
    print(key, len(frames), 'frames')
