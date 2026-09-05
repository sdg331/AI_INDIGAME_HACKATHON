# 공통 유틸: 기준 프레임 로드, 파츠 마스크, 시트/GIF 저장
import numpy as np
from PIL import Image, ImageDraw
import os

SP = os.path.dirname(os.path.abspath(__file__))
OUT = r"C:\Users\jahy0\OneDrive\바탕 화면\꼬리치레\outputs\기사_보충_v1"
os.makedirs(OUT, exist_ok=True)

F = np.load(os.path.join(SP, 'frames_snap.npy'))  # 8 x 64 x 64 x 4 (걷기 v4, 미리보기 GIF에서 복원)
BASE = F[0].copy()  # 접지 프레임 = 기준 서기
DARK = np.array([51, 43, 47, 255], np.uint8)
OUTLINE = np.array([62, 54, 55, 255], np.uint8)
ARMOR_MID = np.array([137, 117, 111, 255], np.uint8)
ARMOR_LIGHT = np.array([183, 153, 138, 255], np.uint8)
ARMOR_HI = np.array([216, 193, 177, 255], np.uint8)
ARMOR_DARK = np.array([91, 80, 80, 255], np.uint8)
HAIR_LIGHT = np.array([237, 199, 167, 255], np.uint8)
HAIR_MID = np.array([210, 168, 139, 255], np.uint8)
HAIR_DARK = np.array([171, 133, 114, 255], np.uint8)
BROWN = np.array([110, 83, 74, 255], np.uint8)
BROWN_DARK = np.array([76, 58, 55, 255], np.uint8)
GOLD_HI = np.array([255, 236, 160, 255], np.uint8)
GOLD = np.array([243, 196, 74, 255], np.uint8)
GOLD_DARK = np.array([196, 134, 38, 255], np.uint8)
WHITE = np.array([255, 255, 255, 255], np.uint8)

FOOT_Y = 62          # 발바닥 행 (0-based, 64 캔버스)
HEAD_CX = 34         # 머리 중앙 x (64 캔버스)
HEAD_TOP = 3

def alpha(a):
    return a[..., 3] > 0

def blank(w=64, h=64):
    return np.zeros((h, w, 4), np.uint8)

def paste(dst, src, dx=0, dy=0, mask=None):
    """src(RGBA)를 dst에 (dx,dy) 오프셋으로 알파 합성(불투명 픽셀만 덮어씀)."""
    h, w = src.shape[:2]
    H, W = dst.shape[:2]
    m = alpha(src) if mask is None else (mask & alpha(src))
    ys, xs = np.where(m)
    ty, tx = ys + dy, xs + dx
    ok = (ty >= 0) & (ty < H) & (tx >= 0) & (tx < W)
    dst[ty[ok], tx[ok]] = src[ys[ok], xs[ok]]
    return dst

def extract(src, mask):
    out = blank(src.shape[1], src.shape[0])
    out[mask] = src[mask]
    return out

def shear_rows(img, pivot_y, top_shift, y_min=0):
    """pivot_y 행은 0, y_min 행은 top_shift만큼 x로 이동(전방 기울기)."""
    out = blank(img.shape[1], img.shape[0])
    H = img.shape[0]
    for y in range(H):
        if y > pivot_y:
            s = 0
        else:
            t = (pivot_y - y) / max(1, (pivot_y - y_min))
            s = int(round(top_shift * t))
        row = img[y]
        if s > 0:
            out[y, s:] = row[:-s] if s else row
        elif s < 0:
            out[y, :s] = row[-s:]
        else:
            out[y] = row
    return out

def shift(img, dx, dy):
    out = blank(img.shape[1], img.shape[0])
    return paste(out, img, dx, dy)

def hair_wave(img, hair_mask, phase, amp=1.6, y0=24):
    """뒷머리 파동: 아래로 갈수록 진폭이 커지는 행 단위 x 오프셋."""
    out = img.copy()
    out[hair_mask] = 0
    hair = extract(img, hair_mask)
    res = blank(img.shape[1], img.shape[0])
    H = img.shape[0]
    for y in range(H):
        if not hair[y].any():
            continue
        t = max(0.0, (y - y0) / 18.0)
        s = int(round(amp * t * np.sin(phase + (y - y0) * 0.45)))
        row = hair[y]
        if s > 0:
            res[y, s:] = row[:-s]
        elif s < 0:
            res[y, :s] = row[-s:]
        else:
            res[y] = row
    # 뒷머리는 몸 뒤에 있으므로 먼저 깔고 몸을 덮는다
    final = res
    paste(final, out)
    return final

# ---- 파츠 마스크 (기준 프레임 f0) ----
def masks(base=BASE):
    a = alpha(base)
    ys, xs = np.mgrid[0:64, 0:64]
    hair_back = a & (ys >= 22) & (ys <= 45) & (xs <= 29)
    legs = a & (ys >= 52)
    hips = a & (ys >= 42) & (ys < 52) & ~hair_back
    torso = a & (ys >= 30) & (ys < 42) & ~hair_back & (xs >= 28)
    head = a & ~hair_back & ~legs & ~hips & ~torso
    # 앞팔(견갑~손): 상체 안쪽 밝은 세로 띠 (x 28~35, y 31~42)
    arm = a & (ys >= 31) & (ys <= 42) & (xs >= 28) & (xs <= 35)
    return dict(hair_back=hair_back, legs=legs, hips=hips, torso=torso, head=head, arm=arm)

# ---- 저장 ----
def save_sheet(frames, name, gif_ms=90, scale_preview=4, bg=(51, 43, 47, 255), loop=True):
    h, w = frames[0].shape[:2]
    sheet = np.concatenate(frames, 1)
    p = os.path.join(OUT, f'{name}_시트_{w}x{h}x{len(frames)}.png')
    Image.fromarray(sheet).save(p)
    return p

def save_gif(frames, name, durations, scale=4, bg=(51, 43, 47, 255), ground=True):
    h, w = frames[0].shape[:2]
    ims = []
    for f in frames:
        im = Image.new('RGBA', (w, h), bg)
        fr = Image.fromarray(f)
        im.alpha_composite(fr)
        if ground:
            d = ImageDraw.Draw(im)
            gy = h - 1
            d.line([(0, gy), (w, gy)], fill=(120, 100, 96, 255))
        im = im.resize((w * scale, h * scale), Image.NEAREST).convert('RGB')
        ims.append(im)
    if isinstance(durations, int):
        durations = [durations] * len(frames)
    p = os.path.join(OUT, f'미리보기_{name}.gif')
    ims[0].save(p, save_all=True, append_images=ims[1:], duration=durations, loop=0, disposal=2)
    return p

def contact_sheet(frames, path, scale=4, bg=(40, 120, 90, 255), grid=8):
    h, w = frames[0].shape[:2]
    S = scale
    im = Image.new('RGBA', ((w * S + 4) * len(frames), h * S), bg)
    d = ImageDraw.Draw(im)
    for i, f in enumerate(frames):
        ox = i * (w * S + 4)
        im.alpha_composite(Image.fromarray(f).resize((w * S, h * S), Image.NEAREST), (ox, 0))
        for k in range(0, w + 1, grid):
            d.line([(ox + k * S, 0), (ox + k * S, h * S)], fill=(255, 255, 255, 70))
        for k in range(0, h + 1, grid):
            d.line([(ox, k * S), (ox + w * S, k * S)], fill=(255, 255, 255, 70))
        d.text((ox + 3, 3), str(i), fill=(255, 255, 0, 255))
    im.save(path)
    return path


def fill_gaps(img, max_gap=2, y_range=(0, 64)):
    """행 안에서 불투명 픽셀 사이의 짧은 투명 구간(<=max_gap)을 왼쪽 이웃 색으로 메운다(파츠 이동으로 생긴 틈 봉합)."""
    out = img.copy()
    H, W = img.shape[:2]
    for y in range(y_range[0], min(H, y_range[1])):
        row = out[y]
        a = row[:, 3] > 0
        x = 0
        while x < W:
            if a[x]:
                x += 1; continue
            x0 = x
            while x < W and not a[x]:
                x += 1
            if x0 > 0 and x < W and (x - x0) <= max_gap:
                row[x0:x] = row[x0 - 1]
        out[y] = row
    return out


def despeckle(img, min_size=3, y_from=0):
    """y_from 이하 영역에서 크기 < min_size 인 고립 픽셀 덩어리 제거(파츠 분리 부산물)."""
    from collections import deque
    out = img.copy()
    a = alpha(out)
    H, W = a.shape
    seen = np.zeros_like(a)
    for y in range(y_from, H):
        for x in range(W):
            if a[y, x] and not seen[y, x]:
                comp = [(y, x)]; seen[y, x] = True; q = deque(comp)
                while q:
                    cy, cx = q.popleft()
                    for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
                        ny, nx = cy+dy, cx+dx
                        if 0 <= ny < H and 0 <= nx < W and a[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True; q.append((ny, nx)); comp.append((ny, nx))
                if len(comp) < min_size:
                    for cy, cx in comp: out[cy, cx] = 0
    return out


def rotate_about(img, cx, cy, deg):
    """(cx,cy) 기준 NEAREST 회전. deg 양수 = 화면상 반시계(수학 좌표 기준 CCW). 팔레트 유지."""
    import math
    H, W = img.shape[:2]
    out = blank(W, H); a = alpha(img)
    th = math.radians(deg); c, s = math.cos(th), math.sin(th)
    ys_, xs_ = np.mgrid[0:H, 0:W]
    dx, dy = xs_ - cx, ys_ - cy
    # 화면 좌표(y 아래 +)에서 반시계 회전의 역매핑
    sx = np.rint(cx + c * dx - s * dy).astype(int)
    sy = np.rint(cy + s * dx + c * dy).astype(int)
    ok = (sx >= 0) & (sx < W) & (sy >= 0) & (sy < H)
    ok2 = ok.copy(); ok2[ok] = a[sy[ok], sx[ok]]
    out[ok2] = img[sy[ok2], sx[ok2]]
    return out

def rot_point(x, y, cx, cy, deg):
    import math
    th = math.radians(deg); c, s = math.cos(th), math.sin(th)
    dx, dy = x - cx, y - cy
    return cx + c * dx + s * dy, cy - s * dx + c * dy

def close_holes(img):
    """행/열 방향 1px 바늘구멍 메움(회전 부산물)."""
    out = img.copy(); H, W = img.shape[:2]
    for _ in range(2):
        a = alpha(out)
        for y in range(H):
            for x in range(1, W - 1):
                if not a[y, x] and a[y, x - 1] and a[y, x + 1]: out[y, x] = out[y, x - 1]
        a = alpha(out)
        for x in range(W):
            for y in range(1, H - 1):
                if not a[y, x] and a[y - 1, x] and a[y + 1, x]: out[y, x] = out[y - 1, x]
    return out
