# -*- coding: utf-8 -*-
"""적 애니메이션 v2 파츠 편집 툴킷.
64px 스프라이트(RGBA ndarray)를 머리·몸통·다리·무기 블롭으로 나눠 이동 · 회전 · 압축 · 재합성한다.
새 프레임은 전부 여기서 만든 파츠 편집 + 픽셀 정리로 나온다(외부 생성기 없음). 팔레트는 v1 24색 고정.
"""
import numpy as np
from PIL import Image
from scipy import ndimage

FOOT_Y = 62

# ---------- 기본 ----------
def blank(W=64, H=64):
    return np.zeros((H, W, 4), np.uint8)

def paste(canvas, part, x, y):
    """part(RGBA)를 canvas 좌표 (x,y)에 알파 덮어쓰기. 캔버스 밖은 잘림."""
    H, W = canvas.shape[:2]; h, w = part.shape[:2]
    x0, y0 = max(0, x), max(0, y); x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0: return canvas
    sub = part[y0 - y:y1 - y, x0 - x:x1 - x]
    m = sub[..., 3] > 0
    canvas[y0:y1, x0:x1][m] = sub[m]
    return canvas

def crop_mask(spr, mask):
    """mask 영역만 남긴 RGBA(같은 크기)"""
    out = spr.copy(); out[~mask] = 0; return out

def bbox(a):
    ys, xs = np.where(a[..., 3] > 0)
    if len(ys) == 0: return None
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1

def tight(a):
    """투명 여백을 잘라 (array, (x, y) 오프셋) 반환"""
    b = bbox(a)
    if b is None: return a[:0, :0], (0, 0)
    x0, y0, x1, y1 = b
    return a[y0:y1, x0:x1].copy(), (x0, y0)

# ---------- 변형 ----------
def shift(a, dx, dy):
    out = np.zeros_like(a)
    h, w = a.shape[:2]
    xs, xd = (0, dx) if dx >= 0 else (-dx, 0)
    ys, yd = (0, dy) if dy >= 0 else (-dy, 0)
    ww, hh = w - abs(dx), h - abs(dy)
    if ww > 0 and hh > 0: out[yd:yd + hh, xd:xd + ww] = a[ys:ys + hh, xs:xs + ww]
    return out

def shear_rows(a, amount, top_row, bottom_row):
    """top_row 에서 amount(px) 이동, bottom_row 에서 0 으로 선형 감소하는 가로 전단"""
    out = np.zeros_like(a)
    for y in range(a.shape[0]):
        if y < top_row: off = amount
        elif y >= bottom_row: off = 0
        else: off = int(round(amount * (bottom_row - y) / max(1, bottom_row - top_row)))
        out[y] = np.roll(a[y], off, axis=0)
        if off > 0: out[y, :off] = 0
        elif off < 0: out[y, off:] = 0
    return out

def resize_nn(a, sx, sy):
    h, w = a.shape[:2]
    nw, nh = max(1, int(round(w * sx))), max(1, int(round(h * sy)))
    return np.asarray(Image.fromarray(a, 'RGBA').resize((nw, nh), Image.NEAREST))

def rotate_about(a, angle, pivot):
    """a(RGBA) 를 pivot(x,y) 기준으로 angle도(시계 방향 양수) 회전. 결과는 같은 크기 캔버스, pivot 고정.
    회전은 NEAREST. 팔레트 밖 색은 생기지 않는다."""
    h, w = a.shape[:2]
    pad = max(h, w)
    big = np.zeros((h + 2 * pad, w + 2 * pad, 4), np.uint8); big[pad:pad + h, pad:pad + w] = a
    im = Image.fromarray(big, 'RGBA')
    px, py = pivot[0] + pad, pivot[1] + pad
    r = im.rotate(-angle, resample=Image.NEAREST, center=(px, py))
    out = np.asarray(r)[pad:pad + h, pad:pad + w].copy()
    return out

def flip_h(a): return a[:, ::-1].copy()

def squash_rows(a, y_from, sy):
    """y_from 아래 영역을 세로 sy 배로 압축(바닥 고정), 위 영역은 그만큼 내려온다."""
    h, w = a.shape[:2]
    top, low = a[:y_from], a[y_from:]
    nh = max(1, int(round(low.shape[0] * sy)))
    low2 = np.asarray(Image.fromarray(low, 'RGBA').resize((w, nh), Image.NEAREST))
    out = np.zeros((h, w, 4), np.uint8)
    drop = low.shape[0] - nh
    out[y_from + drop:y_from + drop + nh] = low2
    paste(out, top, 0, drop)
    return out

# ---------- 파츠 분리 ----------
def split_rows(a, y):
    """(위, 아래) 두 장. 둘 다 원본 크기 캔버스."""
    up = a.copy(); up[y:] = 0
    lo = a.copy(); lo[:y] = 0
    return up, lo

def split_legs(a, hip_y, split_x=None):
    """hip_y 아래를 다리 영역으로 보고 (뒤다리, 앞다리) 두 블롭으로 나눈다.
    split_x 가 있으면 그 열을 기준으로 좌/우 분할(닿아 있는 다리용). 없으면 연결 성분 2개."""
    _, legs = split_rows(a, hip_y)
    m = legs[..., 3] > 0
    if split_x is None:
        lab, n = ndimage.label(m)
        if n >= 2:
            sizes = ndimage.sum(m, lab, range(1, n + 1))
            ids = np.argsort(sizes)[::-1][:2] + 1
            cx = [np.where(lab == i)[1].mean() for i in ids]
            back, front = (ids[0], ids[1]) if cx[0] < cx[1] else (ids[1], ids[0])
            return crop_mask(legs, lab == back), crop_mask(legs, lab == front)
        split_x = int(np.where(m.any(axis=0))[0].mean())
    left = m.copy(); left[:, split_x:] = False
    right = m.copy(); right[:, :split_x] = False
    return crop_mask(legs, left), crop_mask(legs, right)

# ---------- 배치 ----------
def place(spr, ax, W=64, dx=0, dy=0):
    """spr(RGBA, 발이 마지막 행)을 W×64 캔버스에 앵커 x=W/2, 발=FOOT_Y 로 놓는다. (v1 place 와 동일 규칙)"""
    h = spr.shape[0]
    x = int(round(W / 2 - ax + dx)); y = FOOT_Y - h + 1 + dy
    return paste(blank(W), spr, x, y)

def clean_feet(canvas, foot_y=FOOT_Y, rows=4):
    """발바닥 선 아래를 지우고, 바닥 rows 줄에서 위쪽 몸과 이어지지 않은 조각(그림자 잔여)을 지운다."""
    c = canvas.copy()
    c[foot_y + 1:] = 0
    m = c[..., 3] > 0
    top = m.copy(); top[foot_y - rows + 1:] = False          # 발 윗부분은 확실한 몸
    lab, n = ndimage.label(m)
    keep = np.zeros_like(m)
    for i in range(1, n + 1):
        comp = lab == i
        if (comp & top).any(): keep |= comp
    c[~keep] = 0
    return c

def trim_shadow_grey(canvas, palette_idx_grey, foot_y=FOOT_Y, rows=3):
    """바닥 rows 줄에서 지정 팔레트색(그림자 회색)만 지운다."""
    c = canvas.copy()
    band = c[foot_y - rows + 1:foot_y + 1]
    for col in palette_idx_grey:
        m = (band[..., :3] == np.array(col)).all(-1) & (band[..., 3] > 0)
        band[m] = 0
    return c

def flash(canvas, body=(255, 241, 230), edge=(216, 200, 192)):
    a = canvas.copy(); al = a[..., 3] > 0
    inner = ndimage.binary_erosion(al, iterations=1)
    a[al] = (*edge, 255); a[inner] = (*body, 255)
    return a

def dim_to_palette(canvas, palette, f=0.82):
    """명도 f 배 후 팔레트로 재양자화(새 색 없음)"""
    a = canvas.astype(float); a[..., :3] *= f
    return quantize(np.clip(a, 0, 255).astype(np.uint8), palette)

def quantize(arr, palette):
    px = arr[..., :3].reshape(-1, 3).astype(int)
    d = ((px[:, None, :] - palette[None, :, :]) ** 2).sum(-1)
    q = palette[d.argmin(1)].reshape(arr.shape[0], arr.shape[1], 3)
    out = np.dstack([q, arr[..., 3]]).astype(np.uint8); out[out[..., 3] == 0] = 0
    return out

# ---------- 출력 ----------
def save_sheet(frames, path, W):
    sheet = Image.new('RGBA', (W * len(frames), 64), (0, 0, 0, 0))
    for n, f in enumerate(frames): sheet.alpha_composite(Image.fromarray(f, 'RGBA'), (n * W, 0))
    sheet.save(path); return sheet

def save_gif(frames, path, W, dur, bg=(40, 30, 30, 255), scale=4):
    big = [Image.fromarray(f, 'RGBA').resize((W * scale, 64 * scale), Image.NEAREST) for f in frames]
    b = Image.new('RGBA', big[0].size, bg)
    gif = [Image.alpha_composite(b, x).convert('P', palette=Image.ADAPTIVE) for x in big]
    gif[0].save(path, save_all=True, append_images=gif[1:], duration=dur, loop=0, disposal=2)

def strip(frames, W, scale=4, bg=(40, 30, 30, 255), gap=2):
    s = Image.new('RGBA', ((W + gap) * len(frames), 64), bg)
    for n, f in enumerate(frames): s.alpha_composite(Image.fromarray(f, 'RGBA'), (n * (W + gap), 0))
    return s.resize((s.width * scale, s.height * scale), Image.NEAREST)

def check_palette(frames, palette, extra=()):
    pal = {tuple(p) for p in palette} | {tuple(e) for e in extra}
    bad = set()
    for f in frames:
        px = f[f[..., 3] > 0][:, :3]
        for p in map(tuple, np.unique(px, axis=0)):
            if p not in pal: bad.add(p)
    return bad

def check_clip(frames_fn, W, M=16):
    """frames_fn(ox, oy, W, H) 로 여유 캔버스에 다시 그려 잘림 검사"""
    report = []
    for i, f in enumerate(frames_fn(M, M, W + 2 * M, 64 + 2 * M)):
        b = bbox(f)
        if b is None: continue
        x0, y0, x1, y1 = b; c = []
        if y0 < M: c.append(f'top{M - y0}')
        if y1 > 64 + M: c.append(f'bottom{y1 - 64 - M}')
        if x0 < M: c.append(f'left{M - x0}')
        if x1 > W + M: c.append(f'right{x1 - W - M}')
        if c: report.append((i + 1, c))
    return report

# ---------- 얼굴 방향 ----------
def face_right(a, neck, jaw_inset=(5, 4), top_rows=12):
    """두개골(0~neck 행)을 좌우 반전해 오른쪽을 보게 한다.
    원본 3/4 뷰 셀은 두개골이 화면 왼쪽으로 돌아가 있어, 몸(방패 앞)은 두고 머리만 뒤집는다.
    두개골 열 범위 = 상단 top_rows 행에서 가장 큰 연결 성분(검 · 충격선 제외). 턱 3행은 어깨와 겹치지 않게 안쪽 열만."""
    o = a.copy(); al = a[..., 3] > 0
    lab, n = ndimage.label(al[:top_rows])
    if n == 0: return o
    sizes = ndimage.sum(al[:top_rows], lab, range(1, n + 1))
    skull = lab == (np.argmax(sizes) + 1)
    cols = np.where(skull.any(axis=0))[0]; x0, x1 = int(cols.min()), int(cols.max()) + 1
    for r in range(neck):
        lo, hi = (x0 + jaw_inset[0], x1 - jaw_inset[1]) if r >= neck - 3 else (x0, x1)
        o[r, lo:hi] = a[r, lo:hi][::-1]
    return o
