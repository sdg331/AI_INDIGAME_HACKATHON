# 고블린 v2 공통: v1 시트 프레임 로드, 24색 팔레트 스냅, 픽셀 편집 유틸, 저장
import os, json, math
import numpy as np
from PIL import Image, ImageDraw

ROOT = r"C:\Users\jahy0\OneDrive\바탕 화면\꼬리치레"
V1 = os.path.join(ROOT, "outputs", "적_고블린_v1")
OUT = os.path.join(ROOT, "outputs", "적_고블린_v2")
os.makedirs(OUT, exist_ok=True)

BUILD = json.load(open(os.path.join(V1, "_build.json"), encoding="utf-8"))
PAL = np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in BUILD["palette"]], dtype=int)  # 24색
FOOT_Y = 62
KEY_H = 58

def load_sheet(name, w, n, base=V1):
    s = np.array(Image.open(os.path.join(base, name)).convert("RGBA"))
    return [s[:, i * w:(i + 1) * w].copy() for i in range(n)]

def alpha(a):
    return a[..., 3] > 0

def blank(w=64, h=64):
    return np.zeros((h, w, 4), np.uint8)

def snap(img):
    """모든 불투명 픽셀을 24색 팔레트의 최근접 색으로(새 색 유입 방지)."""
    out = img.copy(); m = alpha(out)
    px = out[m][:, :3].astype(int)
    d = ((px[:, None, :] - PAL[None, :, :]) ** 2).sum(-1)
    out[m, :3] = PAL[d.argmin(1)]
    out[m, 3] = 255
    return out

def palette_check(img):
    m = alpha(img)
    cols = {tuple(c) for c in img[m][:, :3]}
    extra = [c for c in cols if not any((PAL == np.array(c)).all(1))]
    return extra

def paste(dst, src, dx=0, dy=0, mask=None):
    h, w = src.shape[:2]; H, W = dst.shape[:2]
    m = alpha(src) if mask is None else (mask & alpha(src))
    ys, xs = np.where(m); ty, tx = ys + dy, xs + dx
    ok = (ty >= 0) & (ty < H) & (tx >= 0) & (tx < W)
    dst[ty[ok], tx[ok]] = src[ys[ok], xs[ok]]
    return dst

def extract(src, mask):
    out = blank(src.shape[1], src.shape[0]); out[mask] = src[mask]; return out

def shift(img, dx, dy):
    return paste(blank(img.shape[1], img.shape[0]), img, dx, dy)

def rect(img, x0, x1, y0, y1):
    """[x0,x1] × [y0,y1] (포함) 영역 마스크."""
    m = np.zeros(img.shape[:2], bool); m[y0:y1 + 1, x0:x1 + 1] = True; return m & alpha(img)

def shear_rows(img, pivot_y, top_shift, y_min=0):
    """pivot_y 행 0, y_min 행 top_shift만큼 x 이동(기울임). pivot 아래 행은 그대로."""
    out = blank(img.shape[1], img.shape[0]); H = img.shape[0]
    for y in range(H):
        if y >= pivot_y: s = 0
        else:
            t = (pivot_y - y) / max(1, (pivot_y - y_min)); s = int(round(top_shift * t))
        row = img[y]
        if s > 0: out[y, s:] = row[:-s]
        elif s < 0: out[y, :s] = row[-s:]
        else: out[y] = row
    return out

def shear_cols_by_row(img, y_top, k):
    """y_top 행 0, 아래로 갈수록 x 이동이 커짐(다리 기울이기). k = 맨 아래 행 이동량(px)."""
    out = blank(img.shape[1], img.shape[0]); H = img.shape[0]
    ys = np.where(alpha(img).any(1))[0]
    if len(ys) == 0: return out
    y_bot = ys.max()
    for y in range(H):
        if not alpha(img)[y].any(): continue
        t = (y - y_top) / max(1, (y_bot - y_top)); s = int(round(k * max(0.0, t)))
        row = img[y]
        if s > 0: out[y, s:] = row[:-s]
        elif s < 0: out[y, :s] = row[-s:]
        else: out[y] = row
    return out

def flip_h(img):
    return img[:, ::-1].copy()

def rotate_about(img, cx, cy, deg):
    """pivot (cx,cy) 기준 NEAREST 회전(양수 = 반시계, 화면 좌표). 팔레트 유지."""
    out = blank(img.shape[1], img.shape[0]); H, W = img.shape[:2]
    a = alpha(img)
    th = math.radians(deg); c, s = math.cos(th), math.sin(th)
    ys, xs = np.mgrid[0:H, 0:W]
    # 역매핑: 출력 픽셀 → 원본 좌표
    dx, dy = xs - cx, ys - cy
    sx = np.rint(cx + c * dx + s * dy).astype(int)   # 화면 좌표(y 아래 +)에서 반시계
    sy = np.rint(cy - s * dx + c * dy).astype(int)
    ok = (sx >= 0) & (sx < W) & (sy >= 0) & (sy < H)
    ok2 = ok.copy(); ok2[ok] = a[sy[ok], sx[ok]]
    out[ok2] = img[sy[ok2], sx[ok2]]
    return out

def close_holes(img, fill_from='left'):
    """행 안의 1px 투명 구멍을 이웃 색으로 메운다(회전 후 생기는 바늘구멍)."""
    out = img.copy(); H, W = img.shape[:2]
    a = alpha(out)
    for y in range(H):
        for x in range(1, W - 1):
            if not a[y, x] and a[y, x - 1] and a[y, x + 1]:
                out[y, x] = out[y, x - 1]
    a = alpha(out)
    for x in range(W):
        for y in range(1, H - 1):
            if not a[y, x] and a[y - 1, x] and a[y + 1, x]:
                out[y, x] = out[y - 1, x]
    return out

def fill_gaps(img, max_gap=2, y_range=(0, 64)):
    out = img.copy(); H, W = img.shape[:2]
    for y in range(y_range[0], min(H, y_range[1])):
        row = out[y]; a = row[:, 3] > 0; x = 0
        while x < W:
            if a[x]: x += 1; continue
            x0 = x
            while x < W and not a[x]: x += 1
            if x0 > 0 and x < W and (x - x0) <= max_gap: row[x0:x] = row[x0 - 1]
        out[y] = row
    return out

def despeckle(img, min_size=3):
    from collections import deque
    out = img.copy(); a = alpha(out); H, W = a.shape; seen = np.zeros_like(a)
    for y in range(H):
        for x in range(W):
            if a[y, x] and not seen[y, x]:
                comp = [(y, x)]; seen[y, x] = True; q = deque(comp)
                while q:
                    cy, cx = q.popleft()
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < H and 0 <= nx < W and a[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True; q.append((ny, nx)); comp.append((ny, nx))
                if len(comp) < min_size:
                    for cy, cx in comp: out[cy, cx] = 0
    return out

def remove_component_of_color(img, color, region_mask, min_size=30):
    """region 안에서 특정 색으로 이어진 큰 덩어리(배경 구멍)를 투명으로."""
    from collections import deque
    out = img.copy(); H, W = out.shape[:2]
    is_c = alpha(out) & (out[..., :3] == np.array(color)).all(-1) & region_mask
    seen = np.zeros((H, W), bool)
    for y in range(H):
        for x in range(W):
            if is_c[y, x] and not seen[y, x]:
                comp = [(y, x)]; seen[y, x] = True; q = deque(comp)
                while q:
                    cy, cx = q.popleft()
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < H and 0 <= nx < W and is_c[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True; q.append((ny, nx)); comp.append((ny, nx))
                if len(comp) >= min_size:
                    for cy, cx in comp: out[cy, cx] = 0
    return out

def extents(img):
    m = alpha(img)
    if not m.any(): return None
    yy, xx = np.where(m); return int(yy.min()), int(yy.max()), int(xx.min()), int(xx.max())

# ---- 저장 ----
def save_sheet(frames, key, name="고블린"):
    h, w = frames[0].shape[:2]
    sheet = np.concatenate(frames, 1)
    fn = f"{name}_{key}_시트_{w}x{h}x{len(frames)}.png"
    Image.fromarray(sheet).save(os.path.join(OUT, fn)); return fn

def save_gif(frames, key, durations, scale=4, bg=(40, 30, 30, 255)):
    h, w = frames[0].shape[:2]; ims = []
    for f in frames:
        im = Image.new("RGBA", (w, h), bg); im.alpha_composite(Image.fromarray(f))
        d = ImageDraw.Draw(im); d.line([(0, FOOT_Y + 1), (w, FOOT_Y + 1)], fill=(90, 70, 70, 255))
        ims.append(im.resize((w * scale, h * scale), Image.NEAREST).convert("RGB"))
    if isinstance(durations, int): durations = [durations] * len(frames)
    p = os.path.join(OUT, f"미리보기_{key}.gif")
    ims[0].save(p, save_all=True, append_images=ims[1:], duration=durations, loop=0, disposal=2); return p

def contact_sheet(frames, path, scale=4, bg=(40, 120, 90, 255), grid=8, labels=None):
    h, w = frames[0].shape[:2]; S = scale
    im = Image.new("RGBA", ((w * S + 4) * len(frames), h * S), bg); d = ImageDraw.Draw(im)
    for i, f in enumerate(frames):
        ox = i * (w * S + 4); im.alpha_composite(Image.fromarray(f).resize((w * S, h * S), Image.NEAREST), (ox, 0))
        for k in range(0, w + 1, grid): d.line([(ox + k * S, 0), (ox + k * S, h * S)], fill=(255, 255, 255, 60))
        for k in range(0, h + 1, grid): d.line([(ox, k * S), (ox + w * S, k * S)], fill=(255, 255, 255, 60))
        d.text((ox + 3, 3), str(i) if labels is None else labels[i], fill=(255, 255, 0, 255))
    im.save(path); return path
