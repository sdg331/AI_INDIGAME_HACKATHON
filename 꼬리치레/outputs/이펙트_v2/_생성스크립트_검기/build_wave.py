# -*- coding: utf-8 -*-
# build_wave.py <scratch_dir> <out_dir> <project_dir> — 시트 · 미리보기 GIF · QA 이미지 생성
import sys, os, numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, sys.argv[1])
import wave_lib as wl
OUT, PROJ = sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
BG, RECT, GROUND = (40, 36, 44), (52, 48, 56), (72, 66, 74)
NAME = '참격파동_검기'

frames = wl.render_all()
sheet = wl.sheet(frames)
Image.fromarray(sheet).save(os.path.join(OUT, f'이펙트_{NAME}_시트_64x64x8.png'))

def font(sz):
    for p in ['C:/Windows/Fonts/malgun.ttf', 'C:/Windows/Fonts/malgunbd.ttf']:
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()

def stage(w, h):
    return Image.new('RGBA', (w, h), BG + (255,))

def blit(dst, arr_or_img, x, y):
    im = arr_or_img if isinstance(arr_or_img, Image.Image) else Image.fromarray(arr_or_img)
    dst.alpha_composite(im, (x, y))

def up(im, k):
    return im.resize((im.width * k, im.height * k), Image.NEAREST)

def to_p(frames_rgb):
    """공통 정확 팔레트로 P 변환(양자화 없음)."""
    allpix = np.concatenate([f.reshape(-1, 3) for f in frames_rgb])
    pal = np.unique(allpix, axis=0).astype(np.uint8)
    assert len(pal) <= 256, len(pal)
    penc = (pal[:, 0].astype(np.int64) << 16) | (pal[:, 1].astype(np.int64) << 8) | pal[:, 2]
    order = np.argsort(penc); sp = penc[order]
    flat = pal.flatten().tolist() + [0] * (768 - len(pal) * 3)
    out = []
    for f in frames_rgb:
        k = f.reshape(-1, 3)
        enc = (k[:, 0].astype(np.int64) << 16) | (k[:, 1].astype(np.int64) << 8) | k[:, 2]
        idx = order[np.searchsorted(sp, enc)]
        im = Image.fromarray(idx.reshape(f.shape[:2]).astype(np.uint8), 'P'); im.putpalette(flat); out.append(im)
    return out, len(pal)

# ---------------- 주인공 소재
hero_dir = os.path.join(PROJ, 'outputs', '기사_보충_v1')
atk = Image.open(os.path.join(hero_dir, '공격1타_가로베기_파츠리그_시트_96x80x8.png')).convert('RGBA')
atk_frames = [atk.crop((i * 96, 0, (i + 1) * 96, 80)) for i in range(8)]
idle = Image.fromarray(np.load(os.path.join(hero_dir, '_생성스크립트', 'frames_snap.npy'))[0])  # 64x64 걷기 f0 = 서기
right = [int(max(np.nonzero(np.array(f)[..., 3])[1])) for f in atk_frames]
contact = int(np.argmax(right))
print('가로베기 프레임별 오른쪽 끝 x:', right, '→ 접촉 프레임 index', contact)

# ---------------- 미리보기 GIF (4배): 가로베기 접촉에서 검기 발생 → 오른쪽으로 비행 → 소멸
SW, SH, SC = 176, 80, 4
HERO_PX, GY = 40, 79                        # 주인공 피벗 x · 바닥 y(1배)
OFF = 24                                    # 피벗 오프셋 (+24, 0)
wave_seq = [0, 1, 2, 3, 4, 5, 2, 3, 4, 5, 6, 7]
wave_dx = [0, 4, 12, 20, 28, 36, 44, 52, 60, 68, 72, 74]
gif_rgb, durs = [], []
total = contact + len(wave_seq) + 2
for t in range(total):
    st = stage(SW, SH)
    d = ImageDraw.Draw(st); d.line([(0, GY), (SW - 1, GY)], fill=GROUND + (255,))
    w = t - contact
    if 0 <= w < len(wave_seq):
        px = HERO_PX + OFF + wave_dx[w]
        d.rectangle([px - 32, GY - 63, px + 31, GY], fill=RECT + (255,))
    if t < 8:
        blit(st, atk_frames[t], HERO_PX - 48, GY - 79)
    else:
        blit(st, idle, HERO_PX - 32, GY - 63)
    if 0 <= w < len(wave_seq):
        fi = wave_seq[w]
        blit(st, frames[fi], px - 32, GY - 63)
        durs.append(wl.FRAME_MS[fi])
    else:
        durs.append(70 if t < contact else 200)
    gif_rgb.append(np.array(up(st, SC).convert('RGB')))
pframes, npal = to_p(gif_rgb)
pframes[0].save(os.path.join(OUT, f'미리보기_{NAME}.gif'), save_all=True, append_images=pframes[1:],
                duration=durs, loop=0, optimize=False)
print('GIF 프레임', len(pframes), '팔레트', npal, 'ms', durs)

# ---------------- 시트 미리보기(4배, 캔버스 범위 표시)
sv = stage(8 * 66 + 2, 68)
for i, f in enumerate(frames):
    x0 = 2 + i * 66
    ImageDraw.Draw(sv).rectangle([x0, 2, x0 + 63, 65], fill=RECT + (255,))
    blit(sv, f, x0, 2)
sv = up(sv, 4); dr = ImageDraw.Draw(sv); ft = font(15)
for i, n in enumerate(wl.FRAME_NAMES):
    dr.text((2 * 4 + i * 66 * 4 + 6, 4), f'{n} {wl.FRAME_MS[i]}ms', font=ft, fill=(230, 224, 214))
sv.convert('RGB').save(os.path.join(OUT, f'QA_{NAME}_시트_4x.png'))

# ---------------- 크기 비교 · 정렬 QA (4배)
old = Image.open(os.path.join(PROJ, 'outputs', '이펙트_v2', '이펙트_참격파동_시트_48x32x8.png')).convert('RGBA')
old_f4 = old.crop((3 * 48, 0, 4 * 48, 32))
QW, QH = 300, 170
q = stage(QW, QH); d = ImageDraw.Draw(q)
# 1행: 주인공 서기 · 기존 48x32 F4(가슴 +6,+5 부착) · 새 64x64 F4
g1 = 74
d.line([(0, g1), (QW - 1, g1)], fill=GROUND + (255,))
blit(q, idle, 40 - 32, g1 - 63)
d.rectangle([110 - 24, g1 - 5 - 31, 110 + 23, g1 - 5], fill=RECT + (255,)); blit(q, old_f4, 110 - 24, g1 - 5 - 31)
d.rectangle([200 - 32, g1 - 63, 200 + 31, g1], fill=RECT + (255,)); blit(q, frames[3], 200 - 32, g1 - 63)
# 2행: 가로베기 접촉 프레임 + F1 · F2 를 피벗 오프셋 (+24, 0) 으로 부착
g2 = 164
d.line([(0, g2), (QW - 1, g2)], fill=GROUND + (255,))
for j, fi in enumerate([0, 1]):
    hx = 60 + j * 130
    px = hx + OFF
    d.rectangle([px - 32, g2 - 63, px + 31, g2], fill=RECT + (255,))
    blit(q, atk_frames[contact], hx - 48, g2 - 79)
    blit(q, frames[fi], px - 32, g2 - 63)
q = up(q, 4); dr = ImageDraw.Draw(q); ft = font(16); ft2 = font(14)
dr.text((8, 4), '크기 비교 — 주인공 서기(키 60px) · 기존 R-05 48×32 F4 · 새 검기 64×64 F4', font=ft, fill=(230, 224, 214))
dr.text((8, g1 * 4 + 6), '정렬 — 가로베기 접촉 프레임 위에 F1(발생) · F2(피크). 이펙트 피벗 = 주인공 피벗 + (+24, 0). 밝은 사각형 = 이펙트 캔버스',
        font=ft2, fill=(230, 224, 214))
q.convert('RGB').save(os.path.join(OUT, f'QA_{NAME}_크기비교_정렬_4x.png'))

# ---------------- 수치 QA
print('--- 프레임 QA')
for i, f in enumerate(frames):
    a = f[..., 3]; ys, xs = np.nonzero(a)
    cols = {tuple(int(v) for v in c) for c in f[a > 0][:, :3]}
    body = a >= 200
    edge = bool(body[0, :].any() or body[-1, :].any() or body[:, 0].any() or body[:, -1].any())
    print(f'F{i+1} {wl.FRAME_NAMES[i]}: bbox x{xs.min()}-{xs.max()} y{ys.min()}-{ys.max()} 색 {len(cols)} '
          f'알파 {sorted({int(v) for v in a[a>0]})} 코어 {"Y" if wl.PAL["core"] in cols else "-"} '
          f'본체 가장자리 닿음 {edge} 본체px {int(body.sum())}')
allc = {tuple(int(v) for v in c) for f in frames for c in f[f[..., 3] > 0][:, :3]}
print('시트 전체 색 수(알파 제외):', len(allc), '팔레트 밖 색:', allc - set(wl.PAL.values()))
