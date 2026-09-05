# 고블린 v2.3 공격 접촉 포즈 재추출: 원본 `적 2.png` 「공격」 셀을 낮은 배경 문턱값으로 다시 잘라 조끼·몸통을 살린다.
# v1 은 명도 < 48 을 배경으로 봐서 거의 검은 가죽 조끼와 몸통 대부분이 지워졌다(64px 판에서 머리·귀·다리 조각만 남음).
# 순서: 참격 호(밝은 저채도 큰 덩어리) · 바닥 그림자(저채도 회색 띠) 를 먼저 배경 취급 → 가장자리와 이어진 명도 < 14 영역을 배경으로 → 축소(v1 과 같은 배율) → 24색 스냅.
import os, numpy as np
from PIL import Image
from scipy import ndimage
from gob_lib import ROOT, PAL, BUILD, FOOT_Y, blank, snap, alpha

SRC = os.path.join(ROOT, "적 2.png")
CELL = (425, 975, 725, 1245)      # x0, y0, x1, y1 — 「공격」 셀(위 라벨 제외)
BG_THR = 14
# 조끼 재색칠(v2.2 대기 포즈의 갈색 조끼와 맞춤): 잘라낸 스프라이트 좌표에서 턱 밑 몸통 상자 안의 어둡고 채도 낮은 픽셀(원본은 거의 검은 가죽)을
# 갈색 E(#75513C) 평균으로 옮긴다. 명도 < VEST_L0 는 외곽선이라 두고, 채도 ≥ VEST_SAT 는 어깨끈·피부라 둔다.
VEST_BOX = (45, 100, 130, 135)     # x0, y0, x1, y1
# 뒷발 발목(셀 좌표 상자): 원본에서 명도 0~30 의 검은 외곽선뿐이라 문턱값 14 에 끊겨 발이 떠 있었다(v1 부터). 이 상자 안만 문턱값 3.
ANKLE_BOX, ANKLE_THR = (50, 155, 80, 172), 3
VEST_L0, VEST_L1, VEST_SAT = 12, 45, 16
VEST_TARGET = np.array([0x75, 0x51, 0x3C])
SCALE = BUILD["scale"]            # v1 과 동일 = 58 / 대기 셀 높이

def extract():
    A = np.asarray(Image.open(SRC).convert("RGB")).astype(int)
    c = A[CELL[1]:CELL[3], CELL[0]:CELL[2]]
    l = c.max(2); sat = l - c.min(2)
    H, W = l.shape
    # 1. 참격 호: 밝고 채도 낮은 큰 덩어리(> 800px). 칼날(~550px)은 남는다
    light = (sat < 45) & (l > 175)
    lab, _ = ndimage.label(light); arc = np.zeros_like(light); blade = np.zeros_like(light)
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        comp = lab == i
        if comp.sum() > 800: arc |= comp
        elif comp.sum() > 200: blade |= comp
    # 호의 안쪽 어두운 가장자리(안티에일리어싱 띠)까지 지우려고 6px 넓히되, 칼날은 보호
    arc = ndimage.binary_dilation(arc, iterations=6) & ~ndimage.binary_dilation(blade, iterations=1)
    # 호의 가장자리(중간 밝기 저채도, 세로로 긴 조각)
    light2 = (sat < 75) & (l > 150) & ~arc
    lab2, _ = ndimage.label(light2)
    for i, sl in enumerate(ndimage.find_objects(lab2), 1):
        comp = lab2 == i; hh = sl[0].stop - sl[0].start; ww = sl[1].stop - sl[1].start
        if comp.sum() > 120 and hh > 2.2 * ww: arc |= ndimage.binary_dilation(comp, iterations=3) & ~blade
    # 2. 바닥 그림자: 아래 30% 띠의 저채도 회색
    ys_all = np.where((l > BG_THR).any(1))[0]
    band_top = ys_all.min() + int((ys_all.max() - ys_all.min()) * 0.70)
    shadow = (sat < 30) & (l >= 35) & (l <= 150); shadow[:band_top] = False
    sx = np.where(shadow.any(0))[0]; anchor = float((sx.min() + sx.max()) / 2)
    # 3. 배경 = 가장자리와 이어진 (명도 < 문턱 | 호 | 그림자)
    bgc = (l < BG_THR) | arc | shadow
    ax0, ay0, ax1, ay1 = ANKLE_BOX
    bgc[ay0:ay1, ax0:ax1] = (l[ay0:ay1, ax0:ax1] < ANKLE_THR) | arc[ay0:ay1, ax0:ax1] | shadow[ay0:ay1, ax0:ax1]
    lab3, _ = ndimage.label(bgc)
    border = set(np.unique(np.concatenate([lab3[0], lab3[-1], lab3[:, 0], lab3[:, -1]]))) - {0}
    fg = ~np.isin(lab3, list(border))
    # 4. 고립 조각 제거(몸에서 떨어진 작은 것)
    lab4, _ = ndimage.label(fg)
    sizes = ndimage.sum(fg, lab4, range(1, lab4.max() + 1))
    for i, s in enumerate(sizes, 1):
        if s < 300: fg &= ~(lab4 == i)
    ys, xs = np.where(fg)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    rgba = np.dstack([c, fg * 255]).astype(np.uint8)[y0:y1, x0:x1]
    # 5. 조끼 갈색화
    cc = rgba[..., :3].astype(int); ll = cc.max(2); ss = ll - cc.min(2)
    yy, xx = np.mgrid[0:rgba.shape[0], 0:rgba.shape[1]]
    vest = (rgba[..., 3] > 0) & (ll >= VEST_L0) & (ll < VEST_L1) & (ss < VEST_SAT)         & (xx >= VEST_BOX[0]) & (xx <= VEST_BOX[2]) & (yy >= VEST_BOX[1]) & (yy <= VEST_BOX[3])
    if vest.any():
        shift = VEST_TARGET - cc[vest].mean(0)
        rgba[vest, :3] = np.clip(cc[vest] + shift, 0, 255).astype(np.uint8)
    return rgba, anchor - x0

def shrink(rgba, ax):
    h, w = rgba.shape[:2]
    arr = rgba.astype(float); a = arr[..., 3:4] / 255
    pm = Image.fromarray(np.dstack([arr[..., :3] * a, arr[..., 3]]).astype(np.uint8), "RGBA")
    s = pm.resize((max(1, round(w * SCALE)), max(1, round(h * SCALE))), Image.BOX)
    sa = np.asarray(s).astype(float); al = sa[..., 3:4]
    rgb = np.where(al > 0, sa[..., :3] / np.maximum(al / 255, 1e-6), 0)
    keep = al[..., 0] >= 110
    return np.dstack([np.clip(rgb, 0, 255), keep * 255]).astype(np.uint8), ax * SCALE

def place(sprite, ax, W=80, dx=0, dy=0, sx=1.0, shear=0):
    """v1 enemy_anim.place 와 동일: 발 = FOOT_Y, 앵커 x = W/2 + dx. sx 가로 스케일(바닥 고정), shear 상체 기울임(px, 위쪽이 최대)."""
    h, w = sprite.shape[:2]
    img = Image.fromarray(sprite, "RGBA")
    nw = max(1, round(w * sx))
    if nw != w: img = img.resize((nw, h), Image.NEAREST); ax = ax * sx
    if shear:
        a = np.asarray(img).copy(); out = np.zeros_like(a)
        for y in range(h):
            off = int(round(shear * (1 - y / max(1, h - 1))))
            out[y] = np.roll(a[y], off, axis=0)
            if off > 0: out[y, :off] = 0
            elif off < 0: out[y, off:] = 0
        img = Image.fromarray(out, "RGBA")
    canvas = blank(W, 64)
    x = int(round(W / 2 - ax + dx)); y = FOOT_Y - img.height + 1 + dy
    arr = np.asarray(img); hh, ww = arr.shape[:2]
    ys0, xs0 = max(0, y), max(0, x); ys1, xs1 = min(64, y + hh), min(W, x + ww)
    src = arr[ys0 - y:ys1 - y, xs0 - x:xs1 - x]; m = src[..., 3] > 0
    canvas[ys0:ys1, xs0:xs1][m] = src[m]
    return snap(canvas)

_cache = None
def attack_sprite():
    global _cache
    if _cache is None: _cache = shrink(*extract())
    return _cache

if __name__ == "__main__":
    sp, ax = attack_sprite()
    print("sprite", sp.shape, "anchor", round(ax, 1), "opaque", int(alpha(sp).sum()))
    from gob_lib import contact_sheet, extents
    fr = [place(sp, ax, dx=2), place(sp, ax, dx=-1, sx=1.12, shear=3), place(sp, ax, dx=-1, sx=0.96)]
    for f in fr: print(extents(f))
    contact_sheet(fr, os.path.join(os.path.dirname(os.path.abspath(__file__)), "gas.png"), scale=8, labels=["접촉", "스미어", "회수"])
