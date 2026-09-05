"""적 캐릭터 시트(적 1/적 2) → 64px 애니메이션 시트 + 미리보기 GIF.
사용: python enemy_anim.py <시트.png> <출력폴더> <이름> <walk프레임순서 예: 1,2,3,4,3,2>
"""
import sys, os, json
import numpy as np
from PIL import Image
from scipy import ndimage

src, outdir, name, walk_order = sys.argv[1], sys.argv[2], sys.argv[3], [int(x) for x in sys.argv[4].split(",")]
SHADOW_MAX = int(sys.argv[5]) if len(sys.argv) > 5 else 150   # 그림자 최대 명도
SHADOW_COOL = (sys.argv[6] == "1") if len(sys.argv) > 6 else False  # 차가운 회색만 그림자로 볼지
SMALL_MIN = int(sys.argv[7]) if len(sys.argv) > 7 else 120   # 몸에서 떨어진 조각 제거 기준(0=끔)
os.makedirs(outdir, exist_ok=True)
FOOT_Y = 62          # 발바닥 선 (0부터) — 주인공·A2 시트와 동일
KEY_H = 58           # 대기 포즈 키(px). 주인공 60px보다 살짝 낮게
im = Image.open(src).convert("RGB")
A = np.asarray(im).astype(int)

# ---------- 1. 셀 탐지 ----------
lum = A.max(axis=2)
m = ndimage.binary_dilation(ndimage.binary_opening(lum > 60, iterations=1), iterations=6)
lab, _ = ndimage.label(m)
boxes = []
for sl in ndimage.find_objects(lab):
    y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
    if (y1 - y0) > 150 and (x1 - x0) > 40:
        boxes.append((x0, y0, x1, y1))
boxes.sort(key=lambda b: (round(b[1] / 120), b[0]))
names = ["front", "back", "left", "right"] + [f"walk{i}" for i in range(1, 9)] + ["idle", "run", "attack", "hit", "skill"]
cells = dict(zip(names, boxes[:17]))

# ---------- 2. 셀 정리 ----------
def clean(box, pad=10, strip_light_fx=False):
    x0, y0, x1, y1 = box
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad); x1, y1 = min(A.shape[1], x1 + pad), min(A.shape[0], y1 + pad)
    c = A[y0:y1, x0:x1].copy()
    l = c.max(axis=2); mn = c.min(axis=2); sat = l - mn
    # 배경: 가장자리와 이어진 어두운 영역
    lab2, _ = ndimage.label(l < 48)
    border = set(np.unique(np.concatenate([lab2[0], lab2[-1], lab2[:, 0], lab2[:, -1]]))) - {0}
    alpha = ~np.isin(lab2, list(border))
    # 다리 사이처럼 막힌 순수 검정(배경색) 영역: 면적 큰 것만 제거(눈구멍은 남김)
    lab_bk, _ = ndimage.label(l <= 15)
    for i, sl in enumerate(ndimage.find_objects(lab_bk), 1):
        comp = lab_bk == i
        if comp.sum() > 400:
            alpha &= ~comp
    # 세로 구분선(얇고 긴 회색) 제거
    lab3, _ = ndimage.label(alpha & (sat < 30))
    for i, sl in enumerate(ndimage.find_objects(lab3), 1):
        hh, ww = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if hh > 3 * ww and ww < 20 and hh > 120:
            alpha &= ~(lab3 == i)
    # 바닥 그림자: 스프라이트 아래 30% 띠 안의 저채도 중간 회색. 그림자 중심 x를 앵커로 기록
    ys = np.where(alpha.any(axis=1))[0]
    band_top = ys.min() + int((ys.max() - ys.min()) * 0.70)
    shadow = alpha & (sat < 30) & (l >= 35) & (l <= SHADOW_MAX)
    if SHADOW_COOL: shadow &= (c[..., 0] - c[..., 2]) < 12
    shadow[:band_top] = False
    sx = np.where(shadow.any(axis=0))[0]
    anchor = float((sx.min() + sx.max()) / 2) if len(sx) > 20 else None
    alpha &= ~shadow
    # 밝은 참격 이펙트(고블린 공격 셀): 크고 밝은 저채도 덩어리 제거
    if strip_light_fx:
        light = alpha & (sat < 45) & (l > 175)
        lab4, _ = ndimage.label(light)
        for i, sl in enumerate(ndimage.find_objects(lab4), 1):
            comp = (lab4 == i)
            hh = sl[0].stop - sl[0].start
            if comp.sum() > 800:   # 참격 호 조각(2570·1008px) 제거. 칼날(546px)은 남김
                alpha &= ~ndimage.binary_dilation(comp, iterations=1)
        # 남은 세로로 긴 밝은 조각(호의 가장자리): 칼날은 대각선이라 bbox가 정방형에 가까움
        light2 = alpha & (sat < 75) & (l > 150)
        lab6, _ = ndimage.label(light2)
        for i, sl in enumerate(ndimage.find_objects(lab6), 1):
            comp = (lab6 == i); hh = sl[0].stop - sl[0].start; ww = sl[1].stop - sl[1].start
            if comp.sum() > 120 and hh > 2.2 * ww:
                alpha &= ~ndimage.binary_dilation(comp, iterations=1)
    # 고립 조각 정리
    core = ndimage.binary_opening(alpha, iterations=2)
    alpha = alpha & ndimage.binary_dilation(core, iterations=4)
    # 몸에서 떨어진 작은 조각(이펙트 파편·충격선) 제거: 500px 미만 성분
    lab5, _ = ndimage.label(alpha)
    for i, sl in enumerate(ndimage.find_objects(lab5), 1):
        comp = lab5 == i
        if comp.sum() < (500 if strip_light_fx else SMALL_MIN):
            alpha &= ~comp
    ys, xs = np.where(alpha)
    y0c, y1c, x0c, x1c = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    if anchor is None: anchor = (x0c + x1c) / 2
    rgba = np.dstack([c, alpha * 255]).astype(np.uint8)[y0c:y1c, x0c:x1c]
    return rgba, anchor - x0c

raw = {}
for k in ["walk1", "walk2", "walk3", "walk4", "walk5", "walk6", "walk7", "walk8", "idle", "run", "attack", "hit"]:
    raw[k] = clean(cells[k], strip_light_fx=(k == "attack"))

# ---------- 3. 64px 밀도로 축소 + 공통 팔레트 ----------
scale = KEY_H / raw["idle"][0].shape[0]
def shrink(rgba, ax):
    h, w = rgba.shape[:2]
    img = Image.fromarray(rgba, "RGBA")
    # 프리멀티플라이로 배경색 번짐 방지
    arr = np.asarray(img).astype(float); a = arr[..., 3:4] / 255
    pm = Image.fromarray(np.dstack([arr[..., :3] * a, arr[..., 3]]).astype(np.uint8), "RGBA")
    s = pm.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.BOX)
    sa = np.asarray(s).astype(float); al = sa[..., 3:4]
    rgb = np.where(al > 0, sa[..., :3] / np.maximum(al / 255, 1e-6), 0)
    keep = (al[..., 0] >= 110)
    out = np.dstack([np.clip(rgb, 0, 255), keep * 255]).astype(np.uint8)
    return out, ax * scale

small = {k: shrink(*v) for k, v in raw.items()}
# 팔레트 통일(모든 프레임 합쳐 24색)
allpx = np.concatenate([s[0][s[0][..., 3] > 0][:, :3] for s in small.values()])
pal_img = Image.fromarray(allpx.reshape(1, -1, 3), "RGB").quantize(colors=24, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
palette = np.array(pal_img.getpalette()[:24 * 3]).reshape(-1, 3)
def quantize(arr):
    px = arr[..., :3].reshape(-1, 3).astype(int)
    d = ((px[:, None, :] - palette[None, :, :]) ** 2).sum(-1)
    q = palette[d.argmin(1)].reshape(arr.shape[0], arr.shape[1], 3)
    return np.dstack([q, arr[..., 3]]).astype(np.uint8)
small = {k: (quantize(v[0]), v[1]) for k, v in small.items()}

# ---------- 4. 프레임 합성 유틸 ----------
def place(sprite, ax, W=64, dx=0, dy=0, sy=1.0, sx=1.0, shear=0):
    """sprite를 W×64 캔버스에 발=FOOT_Y, 앵커 x=W/2 로 놓는다. sy/sx 는 바닥 고정 스케일, shear는 상체 기울임(px)."""
    arr, h, w = sprite, sprite.shape[0], sprite.shape[1]
    img = Image.fromarray(arr, "RGBA")
    nh, nw = max(1, round(h * sy)), max(1, round(w * sx))
    if (nh, nw) != (h, w):
        img = img.resize((nw, nh), Image.NEAREST); ax = ax * sx
    if shear:
        a = np.asarray(img).copy(); out = np.zeros_like(a)
        for y in range(nh):
            off = int(round(shear * (1 - y / max(1, nh - 1))))  # 위쪽이 많이, 발은 0
            out[y] = np.roll(a[y], off, axis=0)
            if off > 0: out[y, :off] = 0
            elif off < 0: out[y, off:] = 0
        img = Image.fromarray(out, "RGBA")
    canvas = Image.new("RGBA", (W, 64), (0, 0, 0, 0))
    x = int(round(W / 2 - ax + dx)); y = FOOT_Y - img.height + 1 + dy
    canvas.alpha_composite(img, (x, y)) if (0 <= x and x + img.width <= W and y >= 0) else canvas.paste(img, (x, y), img)
    return canvas

def flash(canvas, body=(255, 241, 230), edge=(216, 200, 192)):
    a = np.asarray(canvas).copy(); al = a[..., 3] > 0
    inner = ndimage.binary_erosion(al, iterations=1)
    a[al] = (*edge, 255); a[inner] = (*body, 255)
    return Image.fromarray(a, "RGBA")

def dim(canvas, f=0.82):
    a = np.asarray(canvas).astype(float); a[..., :3] *= f
    return Image.fromarray(a.astype(np.uint8), "RGBA")

S = small
frames = {}
# 대기 4: 기본 → 들숨(몸 1px 위로 늘림) → 유지 → 기본
i, iax = S["idle"]
frames["대기"] = (64, [place(i, iax), place(i, iax, sy=(i.shape[0] + 1) / i.shape[0]), place(i, iax, sy=(i.shape[0] + 1) / i.shape[0]), place(i, iax)])
# 이동: 시트 프레임 순서 + 접지 프레임 사이 1px 바운스
walk = []
for n, k in enumerate(walk_order):
    sp, ax = S[f"walk{k}"]
    bounce = -1 if n % 2 == 1 else 0
    walk.append(place(sp, ax, 64, dy=bounce))
frames["이동"] = (64, walk)
# 공격 10 (80×64): 예고 5 → 휘두름 2 → 회수 3
at, aax = S["attack"]
frames["공격"] = (80, [
    place(i, iax, 80),                                   # 1 서기
    place(i, iax, 80, dx=-2, shear=-2),                  # 2 예고: 뒤로 젖힘
    place(i, iax, 80, dx=-4, dy=1, sy=0.97, shear=-4),   # 3 예고: 최대 백스윙(웅크림)
    place(i, iax, 80, dx=-4, dy=1, sy=0.97, shear=-4),   # 4 홀드
    place(i, iax, 80, dx=-3, dy=1, sy=0.97, shear=-3),   # 5 홀드 떨림
    place(at, aax, 80, dx=2, sx=1.12, shear=3),          # 6 스미어: 앞으로 늘림
    place(at, aax, 80, dx=4),                            # 7 접촉
    place(at, aax, 80, dx=4),                            # 8 홀드
    place(at, aax, 80, dx=1, sx=0.96),                   # 9 회수
    place(i, iax, 80),                                   # 10 서기
])
# 피격 4: 플래시 → 밀림 → 복귀 중 → 기본
h_, hax = S["hit"]
frames["피격"] = (64, [flash(place(h_, hax)), place(h_, hax, dx=-3, shear=-2), place(h_, hax, dx=-1), place(i, iax)])
# 그로기 6: 진입 3(앞쏠림·뒤젖힘·가라앉음) → 멈춤 1 → 유지 2
frames["그로기"] = (64, [
    place(h_, hax, dx=2, shear=3),
    place(h_, hax, dx=-2, shear=-3),
    place(h_, hax, dy=0, sy=0.95, shear=-1),
    dim(place(h_, hax, sy=0.93, shear=-2)),
    dim(place(h_, hax, sy=0.93, shear=-2)),
    dim(place(h_, hax, sy=0.92, shear=-2)),
])

# ---------- 5. 저장 ----------
speed = {"대기": 180, "이동": 110, "공격": 110, "피격": 100, "그로기": 150}
report = {}
for key, (W, fr) in frames.items():
    sheet = Image.new("RGBA", (W * len(fr), 64), (0, 0, 0, 0))
    for n, f in enumerate(fr): sheet.alpha_composite(f, (n * W, 0))
    fn = f"{name}_{key}_시트_{W}x64x{len(fr)}.png"
    sheet.save(f"{outdir}/{fn}")
    big = [f.resize((W * 4, 256), Image.NEAREST) for f in fr]
    bg = Image.new("RGBA", big[0].size, (40, 30, 30, 255))
    gif = [Image.alpha_composite(bg, b).convert("P", palette=Image.ADAPTIVE) for b in big]
    gif[0].save(f"{outdir}/미리보기_{key}.gif", save_all=True, append_images=gif[1:], duration=speed[key], loop=0, disposal=2)
    report[key] = fn
json.dump({"scale": scale, "palette": [f"#{r:02X}{g:02X}{b:02X}" for r, g, b in palette], "files": report,
           "idle_size": [int(S["idle"][0].shape[1]), int(S["idle"][0].shape[0])], "walk_order": walk_order},
          open(f"{outdir}/_build.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(name, "scale", round(scale, 4), "idle", S["idle"][0].shape[:2], report)
