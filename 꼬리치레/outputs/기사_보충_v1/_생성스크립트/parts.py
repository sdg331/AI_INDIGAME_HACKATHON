# 기준 옆모습(걷기 f0) 파츠 분할 → 파츠별 64x64 PNG(제자리) + 색 구분 지도 + 확대 미리보기 + 좌표 JSON
import os, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from kb import *

PD = os.path.join(OUT, "파츠분할")
os.makedirs(PD, exist_ok=True)
ys, xs = np.mgrid[0:64, 0:64]
a = alpha(BASE)

# ---- 마스크 정의 (그리는 순서 = 뒤 → 앞) ----
hair_back = a & (ys >= 22) & (ys <= 45) & (xs <= 29)
legs = a & (ys >= 52)
leg_back = legs & (xs <= 35)
leg_front = legs & (xs >= 36)
# 앞팔: 사용자가 캡쳐/앞팔.png에 빨간 원으로 지정한 영역(64격자로 매핑) — 견갑(31~36,30)에서 허리 옆 손(28~32,49~50)까지
arm = np.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "arm_user_mask.npy")) & a
hair_back = hair_back & ~arm   # x 27~29 · y 36~43은 손(앞팔)이 우선
hips = a & (ys >= 42) & (ys <= 51) & ~hair_back & ~arm
torso = a & (ys >= 30) & (ys <= 41) & ~hair_back & ~arm
head = a & ~hair_back & ~legs & ~hips & ~arm & ~torso

PARTS = [  # (파일 번호_이름, 마스크, 지도 색, 설명)
    ("01_뒷머리",   hair_back, (240, 120, 60),  "등 뒤로 흘러내린 머리. 파동 · 흘림용"),
    ("02_뒷다리",   leg_back,  (60, 120, 240),  "왼쪽(뒤) 다리 + 발. 발바닥 y 61~62"),
    ("03_앞다리",   leg_front, (60, 200, 240),  "오른쪽(앞) 다리 + 발. 발바닥 y 62"),
    ("04_허리치마", hips,      (160, 90, 200),  "벨트 · 튜닉 밑단. 다리 윗부분을 덮음"),
    ("05_몸통",     torso,     (90, 200, 90),   "가슴 갑옷 (앞팔 · 견갑 제외)"),
    ("06_앞팔",     arm,       (250, 220, 60),  "견갑 + 팔 + 손, 사용자 지정(빨간 원). 어깨축 (33,31), 손 (30,49)"),
    ("07_머리",     head,      (250, 90, 140),  "얼굴 · 앞머리 · 옆머리 (뒷머리 제외)"),
]

# 누락 검사(앞팔 밑을 채우므로 몸통·허리·뒷머리는 앞팔과 겹치는 것이 정상)
cover = np.zeros((64, 64), int)
for _, m, _, _ in PARTS: cover += m
assert (cover[a] >= 1).all(), "파츠 누락"

# ---- 앞팔에 가려진 몸 채우기: 팔이 움직여도 몸이 비지 않도록 몸통 · 허리치마 · 뒷머리를 앞팔 영역 안으로 이어 그린다 ----
FILLED = {}
def nearest(row_mask, row_img, x, direction):
    xx = x
    while 0 <= xx < 64:
        if row_mask[xx]: return row_img[xx]
        xx += direction
    return None
def fill_part(mask, region, x_edge, direction, outline_edge):
    """mask 파츠를 region(앞팔 영역) 안으로 확장. 같은 행에서 direction 쪽 가장 가까운 자기 픽셀 색을 복사(갑옷 · 천은 가로 띠라 자연스럽다)."""
    img = extract(BASE, mask); m = mask.copy(); added = 0
    for y in range(64):
        for x in range(64):
            if region[y, x] and not mask[y, x] and x_edge(y, x):
                col = nearest(mask[y], BASE[y], x, direction)
                if col is None: continue
                img[y, x] = col; m[y, x] = True; added += 1
                if outline_edge(y, x): img[y, x] = DARK
    return img, m, added
torso_f, torso_m, n1 = fill_part(torso, arm, lambda y, x: 30 <= y <= 41 and x >= 29, +1, lambda y, x: x == 29)
hips_f, hips_m, n2 = fill_part(hips, arm, lambda y, x: 42 <= y <= 51 and x >= 25, +1, lambda y, x: x == 25 and y >= 46)
hair_f, hair_m, n3 = fill_part(hair_back, arm, lambda y, x: 30 <= y <= 45 and x <= 28, -1, lambda y, x: False)
FILLED = {"05_몸통": (torso_f, torso_m), "04_허리치마": (hips_f, hips_m), "01_뒷머리": (hair_f, hair_m)}
print("앞팔 밑 채움: 몸통", n1, "허리치마", n2, "뒷머리", n3)

meta = {"기준": "걷기 f0 (미리보기_걷기8.gif 복원) 64x64, Pivot Bottom Center, 발바닥 y62, 머리 중앙 x34, 어깨 (36,33)",
        "그리는 순서(뒤→앞)": [p[0] for p in PARTS], "파츠": {}}
for name, m, col, desc in PARTS:
    img = extract(BASE, m)
    if name in FILLED: img, m = FILLED[name]
    Image.fromarray(img).save(os.path.join(PD, f"{name}.png"))
    yy, xx = np.where(m)
    meta["파츠"][name] = {"설명": desc + (" (앞팔 밑 채움 포함)" if name in FILLED else ""), "픽셀수": int(m.sum()), "bbox_xywh": [int(xx.min()), int(yy.min()), int(xx.max() - xx.min() + 1), int(yy.max() - yy.min() + 1)],
                        "중심": [round(float(xx.mean()), 1), round(float(yy.mean()), 1)]}
Image.fromarray(BASE).save(os.path.join(PD, "00_원본_합본.png"))
json.dump(meta, open(os.path.join(PD, "파츠_좌표.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---- 색 구분 지도 (1x, 4x, 8x + 격자 · 좌표) ----
cmap = blank()
for name, m, col, _ in PARTS: cmap[m] = (*col, 255)
Image.fromarray(cmap).save(os.path.join(PD, "파츠지도_1x.png"))

try: font = ImageFont.truetype(r"C:\Windows\Fonts\malgun.ttf", 13); font_s = ImageFont.truetype(r"C:\Windows\Fonts\malgun.ttf", 11)
except Exception: font = font_s = None

def big(img, S, grid=8, coords=True):
    im = Image.fromarray(img).resize((64 * S, 64 * S), Image.NEAREST)
    bg = Image.new("RGBA", im.size, (40, 40, 44, 255)); bg.alpha_composite(im); d = ImageDraw.Draw(bg)
    for k in range(0, 65, grid):
        c = (255, 255, 255, 110) if k % 16 else (255, 230, 120, 200)
        d.line([(k * S, 0), (k * S, 64 * S)], fill=c); d.line([(0, k * S), (64 * S, k * S)], fill=c)
    if coords:
        for k in range(0, 64, 8):
            d.text((k * S + 2, 1), str(k), fill=(255, 230, 120, 255), font=font_s); d.text((1, k * S + 1), str(k), fill=(255, 230, 120, 255), font=font_s)
    return bg

def strip(imgs, labels, S):
    cells = [big(i, S) for i in imgs]
    W = sum(c.width + 6 for c in cells); H = cells[0].height + 22
    out = Image.new("RGBA", (W, H), (25, 25, 28, 255)); d = ImageDraw.Draw(out); x = 0
    for c, lb in zip(cells, labels):
        out.alpha_composite(c, (x, 22)); d.text((x + 3, 3), lb, fill=(255, 255, 255, 255), font=font); x += c.width + 6
    return out

# 미리보기 1: 원본 · 색지도 · 반투명 겹침(8배)
half = BASE.copy(); half[..., :3] = (half[..., :3].astype(int) * 0.45 + np.array(cmap[..., :3]).astype(int) * 0.55).astype(np.uint8); half[~a] = 0
strip([BASE, cmap, half], ["원본 (걷기 f0)", "파츠 지도", "원본 + 지도 겹침"], 8).save(os.path.join(PD, "미리보기_파츠지도_8x.png"))
# 미리보기 2: 파츠 7개 각각(6배) — 채운 판
strip([(FILLED[n][0] if n in FILLED else extract(BASE, m)) for n, m, _, _ in PARTS], [f"{n}  {meta['파츠'][n]['bbox_xywh']}" for n, _, _, _ in PARTS], 6).save(os.path.join(PD, "미리보기_파츠별_6x.png"))
# 미리보기 3: 앞팔을 뺀 몸(채움 확인용)
body_no_arm = blank()
for n, m, _, _ in PARTS:
    if n == "06_앞팔": continue
    paste(body_no_arm, FILLED[n][0] if n in FILLED else extract(BASE, m))
strip([BASE, body_no_arm], ["원본", "앞팔 뺀 몸 (밑 채움)"], 8).save(os.path.join(PD, "미리보기_앞팔뺀몸_8x.png"))
# 범례
leg = Image.new("RGBA", (420, 26 * len(PARTS) + 10), (25, 25, 28, 255)); d = ImageDraw.Draw(leg)
for i, (name, m, col, desc) in enumerate(PARTS):
    d.rectangle([8, 8 + i * 26, 28, 26 + i * 26], fill=(*col, 255)); d.text((36, 6 + i * 26), f"{name} — {desc}", fill=(255, 255, 255, 255), font=font)
leg.save(os.path.join(PD, "범례.png"))
print(json.dumps(meta, ensure_ascii=False, indent=1))
