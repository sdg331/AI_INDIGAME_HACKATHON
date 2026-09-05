# -*- coding: utf-8 -*-
"""보스 대기 프레임(64×64) → 파츠 분할.
각 픽셀을 정확히 하나의 파츠에 배정한다(겹침 없음) → 파츠를 전부 겹치면 원본과 동일.
산출: 파츠분할/00_원본_합본.png · NN_이름.png(64×64, 제자리) · 파츠지도_1x.png · 미리보기_파츠지도_8x.png ·
      미리보기_파츠별_6x.png · 범례.png · 파츠_좌표.json
실행: 프로젝트 루트에서 python outputs/보스_바르갈_v1/_생성스크립트/parts_split.py [대기|공격]
"""
import os, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DIR = os.path.join(ROOT, 'outputs', '보스_바르갈_v1')
FONT = 'C:/Windows/Fonts/malgun.ttf'

PALETTE = [(0xFC,0xE8,0xDF),(0xF6,0xCF,0xC5),(0xE7,0xA1,0xAC),(0x6D,0x32,0x5B),
           (0xEA,0xD7,0xD5),(0xBD,0x96,0xA4),(0x96,0x56,0x7B),(0x28,0x1F,0x2B),
           (0x61,0x31,0x53),(0x4D,0x32,0x45),(0x2F,0x22,0x30),(0x43,0x2B,0x36)]
SKIN = {0, 1, 2}          # 살색 계열 (허벅지 판정용)

# ---------------------------------------------------------------- 구성 (대기 = 정면 3/4 · 공격 = 측면 런지, 캡쳐 2 원본)
# 파츠: 번호, 이름, 색, 피벗(관절), 규칙 목록. 규칙은 위에서부터 적용, 먼저 배정된 픽셀은 바꾸지 않는다. 영역 (x0, x1, y0, y1) 포함.
CONFIGS = {
    '대기': dict(src='대기_64x64.png', out='파츠분할', parts=[
        ('01', '뒷머리',   (120, 200, 255), (29, 36), [dict(box=(0, 18, 36, 52)), dict(box=(40, 63, 36, 52))]),
        ('02', '꼬리',     (255, 170, 60),  (38, 54), [dict(box=(38, 46, 54, 62))]),
        ('03', '왼다리',   (90, 220, 120),  (23, 53), [dict(box=(18, 28, 54, 62)), dict(box=(19, 26, 50, 53), cls=SKIN)]),
        ('04', '오른다리', (40, 170, 90),   (32, 53), [dict(box=(29, 37, 54, 62)), dict(box=(29, 35, 50, 53), cls=SKIN)]),
        ('05', '치마',     (200, 90, 200),  (29, 46), [dict(box=(12, 45, 46, 54))]),
        ('06', '몸통',     (255, 90, 90),   (29, 36), [dict(box=(19, 39, 36, 37)), dict(box=(26, 33, 38, 45))]),
        ('07', '왼팔',     (255, 230, 80),  (22, 38), [dict(box=(19, 25, 38, 47))]),
        ('08', '오른팔',   (230, 200, 40),  (36, 38), [dict(box=(34, 39, 38, 47))]),
        ('09', '머리',     (120, 255, 240), (29, 35), [dict(box=(0, 63, 0, 35))]),
    ]),
    '공격': dict(src='공격_몸만_64x64.png', out='파츠분할_공격', parts=[
        ('01', '뒷머리',   (120, 200, 255), (30, 22), [dict(box=(0, 29, 19, 36))]),                          # 뒤로 흩날리는 머리카락
        ('02', '뒷팔',     (230, 200, 40),  (22, 38), [dict(box=(8, 22, 37, 45))]),                           # 몸 뒤쪽 팔 · 어깨
        ('03', '뒷다리',   (40, 170, 90),   (20, 47), [dict(box=(8, 24, 46, 58))]),                           # 뒤로 뻗은 다리
        ('04', '앞다리',   (90, 220, 120),  (30, 49), [dict(box=(28, 55, 50, 62)), dict(box=(24, 31, 46, 49), cls=SKIN)]),  # 앞으로 내디딘 다리 + 허벅지 살
        ('05', '치마',     (200, 90, 200),  (28, 43), [dict(box=(10, 46, 43, 50))]),
        ('06', '몸통',     (255, 90, 90),   (30, 37), [dict(box=(23, 38, 36, 43))]),
        ('07', '앞팔',     (255, 230, 80),  (37, 38), [dict(box=(38, 55, 36, 43))]),                          # 앞으로 뻗은 팔 · 손끝 (52, 41)
        ('08', '머리',     (120, 255, 240), (36, 36), [dict(box=(0, 63, 0, 37))]),                            # 뿔 · 귀 · 얼굴 · 앞머리
    ]),
    '걷기': dict(src='이동1_64x64.png', out='파츠분할_걷기', parts=[
        ('01', '꼬리',     (255, 170, 60),  (39, 53), [dict(box=(39, 47, 53, 60))]),                            # 반전 프레임이라 몸 앞에 있음 → 리그에서 등 뒤로 옮긴다
        ('02', '뒷머리',   (120, 200, 255), (42, 30), [dict(box=(45, 52, 30, 52)), dict(box=(40, 44, 30, 39)), dict(box=(40, 44, 48, 52))]),  # 오른쪽으로 흘러내린 긴 머리
        ('03', '뒷팔',     (230, 200, 40),  (22, 37), [dict(box=(17, 24, 37, 46))]),                            # 몸 뒤쪽(화면 왼쪽) 팔
        ('04', '뒷다리',   (40, 170, 90),   (24, 50), [dict(box=(18, 30, 51, 62))]),
        ('05', '앞다리',   (90, 220, 120),  (34, 50), [dict(box=(31, 38, 51, 62)), dict(box=(29, 34, 49, 50), cls=SKIN)]),   # 앞다리 + 허벅지 살
        ('06', '치마',     (200, 90, 200),  (30, 47), [dict(box=(17, 46, 47, 50))]),
        ('07', '몸통',     (255, 90, 90),   (30, 36), [dict(box=(25, 35, 36, 46))]),
        ('08', '앞팔',     (255, 230, 80),  (37, 37), [dict(box=(36, 44, 40, 47))]),                            # 몸 앞쪽(화면 오른쪽) 팔 · 손 (38~44, 45~47)
        ('09', '머리',     (120, 255, 240), (30, 35), [dict(box=(0, 63, 0, 35))]),                              # 뿔 · 귀 · 얼굴 · 앞머리 · 왼쪽 옆머리
    ]),
}
import sys
CFG_NAME = sys.argv[1] if len(sys.argv) > 1 else '대기'
CFG = CONFIGS[CFG_NAME]
OUT = os.path.join(DIR, CFG['out']); os.makedirs(OUT, exist_ok=True)
SRC = os.path.join(DIR, '원본프레임', CFG['src'])
PARTS = CFG['parts']
img = np.asarray(Image.open(SRC).convert('RGBA')).copy()
H, W = img.shape[:2]
alpha = img[..., 3] > 0
idx = np.full((H, W), -1, int)
for i, c in enumerate(PALETTE):
    idx[np.all(img[..., :3] == np.array(c), axis=2) & alpha] = i

assign = np.full((H, W), -1, int)
for pi, (num, name, col, piv, rules) in enumerate(PARTS):
    for r in rules:
        x0, x1, y0, y1 = r['box']
        m = np.zeros((H, W), bool); m[y0:y1 + 1, x0:x1 + 1] = True
        m &= alpha & (assign < 0)
        if 'cls' in r:
            m &= np.isin(idx, list(r['cls']))
        assign[m] = pi
# 남은 픽셀: 가장 가까운(4방향 인접 다수결) 파츠에 붙인다
left = alpha & (assign < 0)
for _ in range(6):
    ys, xs = np.where(left)
    if not len(ys): break
    for y, x in zip(ys, xs):
        votes = [assign[yy, xx] for yy, xx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)) if 0 <= yy < H and 0 <= xx < W and assign[yy, xx] >= 0]
        if votes: assign[y, x] = max(set(votes), key=votes.count)
    left = alpha & (assign < 0)
unassigned = int((alpha & (assign < 0)).sum())

# ---------------------------------------------------------------- 저장
def part_img(pi):
    out = np.zeros_like(img); m = assign == pi; out[m] = img[m]; return out

Image.fromarray(img, 'RGBA').save(os.path.join(OUT, '00_원본_합본.png'))
info = {'원본': '원본프레임/' + CFG['src'], '구성': CFG_NAME, '캔버스': [W, H], '발바닥_y': 62, '피벗': 'Bottom Center (32, 64)',
        'z순서(뒤→앞)': [p[1] for p in PARTS], '미배정_픽셀': unassigned, '파츠': {}}
recon = np.zeros_like(img)
for pi, (num, name, col, piv, rules) in enumerate(PARTS):
    pimg = part_img(pi)
    Image.fromarray(pimg, 'RGBA').save(os.path.join(OUT, f'{num}_{name}.png'))
    m = assign == pi
    ys, xs = np.where(m)
    bbox = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if len(xs) else None
    info['파츠'][f'{num}_{name}'] = {'픽셀수': int(m.sum()), 'bbox_x0y0x1y1': bbox, '관절_피벗': list(piv), '색(지도)': list(col)}
    recon[m] = img[m]
identical = bool(np.array_equal(recon[alpha], img[alpha]) and not (recon[~alpha][..., 3] > 0).any())
info['재조립_원본과_동일'] = identical
json.dump(info, open(os.path.join(OUT, '파츠_좌표.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# 파츠 지도 (색 코드)
pmap = np.zeros_like(img)
for pi, (num, name, col, piv, rules) in enumerate(PARTS):
    pmap[assign == pi] = (*col, 255)
pmap[alpha & (assign < 0)] = (255, 0, 255, 255)
Image.fromarray(pmap, 'RGBA').save(os.path.join(OUT, '파츠지도_1x.png'))

font = ImageFont.truetype(FONT, 16); font_s = ImageFont.truetype(FONT, 13)
BG = (51, 43, 47, 255)

def up(a, s):
    im = Image.fromarray(a, 'RGBA'); return im.resize((im.width * s, im.height * s), Image.NEAREST)

# 8배 지도: 원본 | 지도 | 지도 위에 원본 반투명 + 피벗
S = 8
sheet = Image.new('RGBA', (64 * S * 3 + 40, 64 * S + 40), BG)
sheet.alpha_composite(up(img, S), (10, 30))
sheet.alpha_composite(up(pmap, S), (64 * S + 20, 30))
blend = pmap.copy().astype(float); blend[..., :3] = blend[..., :3] * 0.55 + img[..., :3] * 0.45
sheet.alpha_composite(up(blend.astype(np.uint8), S), (64 * S * 2 + 30, 30))
d = ImageDraw.Draw(sheet)
for pi, (num, name, col, piv, rules) in enumerate(PARTS):
    x, y = piv
    for ox in (64 * S + 20, 64 * S * 2 + 30):
        cx, cy = ox + x * S + S // 2, 30 + y * S + S // 2
        d.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], outline=(255, 255, 255, 255), width=2)
d.text((10, 6), f'원본 {CFG_NAME} 64×64', font=font, fill=(230, 220, 220))
d.text((64 * S + 20, 6), '파츠 지도 (색 = 파츠, 흰 원 = 관절 피벗)', font=font, fill=(230, 220, 220))
d.text((64 * S * 2 + 30, 6), '지도 + 원본 겹침', font=font, fill=(230, 220, 220))
sheet.save(os.path.join(OUT, '미리보기_파츠지도_8x.png'))

# 범례
leg = Image.new('RGBA', (420, 30 * len(PARTS) + 50), BG); d = ImageDraw.Draw(leg)
d.text((10, 8), '파츠 범례 (뒤 → 앞)', font=font, fill=(230, 220, 220))
for pi, (num, name, col, piv, rules) in enumerate(PARTS):
    y = 40 + pi * 30
    d.rectangle([10, y, 34, y + 20], fill=(*col, 255))
    d.text((44, y), f'{num} {name} · 피벗 {piv} · {info["파츠"][f"{num}_{name}"]["픽셀수"]}px', font=font_s, fill=(230, 220, 220))
leg.save(os.path.join(OUT, '범례.png'))

# 파츠별 6배: 각 파츠 제자리 + 이름, 마지막에 재조립
S = 6
cols = len(PARTS) + 2
sheet = Image.new('RGBA', ((64 * S + 8) * cols + 10, 64 * S + 60), BG); d = ImageDraw.Draw(sheet)
x = 10
sheet.alpha_composite(up(img, S), (x, 40)); d.text((x, 10), '원본', font=font, fill=(230, 220, 220)); x += 64 * S + 8
for pi, (num, name, col, piv, rules) in enumerate(PARTS):
    ghost = img.copy().astype(float); ghost[..., 3] = ghost[..., 3] * 0.12
    tile = ghost.astype(np.uint8); m = assign == pi; tile[m] = img[m]
    sheet.alpha_composite(up(tile, S), (x, 40))
    px, py = piv; cx, cy = x + px * S + S // 2, 40 + py * S + S // 2
    d.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], outline=(*col, 255), width=2)
    d.text((x, 10), f'{num} {name}', font=font, fill=(*col, 255)); x += 64 * S + 8
sheet.alpha_composite(up(recon, S), (x, 40)); d.text((x, 10), '재조립 ' + ('= 원본 ✓' if identical else '≠ 원본 ✗'), font=font, fill=(230, 220, 220))
sheet.save(os.path.join(OUT, '미리보기_파츠별_6x.png'))
print('parts:', {k: v['픽셀수'] for k, v in info['파츠'].items()}, 'unassigned', unassigned, 'identical', identical)
