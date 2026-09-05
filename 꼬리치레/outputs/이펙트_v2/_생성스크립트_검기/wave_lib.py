# -*- coding: utf-8 -*-
# wave_lib.py — R-05 참격 파동(검기) 캐릭터 크기판 렌더러. 64x64, Pivot = Bottom Center.
import math
import numpy as np

W = H = 64
CX, CY = 29, 33          # 비행 크레센트 중심(픽셀 인덱스). y33 = 발(y63)에서 30px 위 = 몸 중심
R_FULL = 27              # 바깥 반지름 → 높이 2*27*sin75 ≈ 52 + 외곽선 = 약 55px
SPAN = 75                # 팔 벌림(도). 끝점 y = 33 ± 26

PAL = {                  # CB 크림 금 (이펙트_정렬표 2절)
    'core':    (255, 247, 230),   # #FFF7E6
    'light':   (255, 235, 194),   # #FFEBC2
    'base':    (243, 211, 154),   # #F3D39A
    'dark':    (217, 174, 124),   # #D9AE7C
    'outline': (141, 103,  88),   # #8D6758
}

def blank():
    return np.zeros((H, W, 4), np.uint8)

def put(img, x, y, name, a=255):
    if 0 <= x < W and 0 <= y < H:
        img[y, x, :3] = PAL[name]
        img[y, x, 3] = a

def thick(th, span, tmax, exp=0.8):
    """각도 th(라디안)에서의 두께. 중앙 tmax, 끝 1."""
    c = max(0.0, math.cos(th / span * math.pi / 2))
    return 1.0 + (tmax - 1.0) * (c ** exp)

def dilate4(m):
    d = m.copy()
    d[1:, :] |= m[:-1, :]; d[:-1, :] |= m[1:, :]
    d[:, 1:] |= m[:, :-1]; d[:, :-1] |= m[:, 1:]
    return d

def crescent_mask(cx, cy, R, tmax, span_deg, exp=0.8, dash=None):
    """초승달 마스크. 바깥 호 = 반지름 R 원호, 안쪽 = R - thick(th). dash=(period,on,phase) 호길이 기준."""
    m = np.zeros((H, W), bool)
    span = math.radians(span_deg)
    n = int(R * span * 2 * 6) + 8
    for i in range(n + 1):
        th = -span + 2 * span * i / n
        if dash:
            per, on, ph = dash
            s = R * (th + span)
            if (s + ph) % per >= on:
                continue
        t = thick(th, span, tmax, exp)
        rr = R - t
        while rr <= R + 1e-9:
            x = int(math.floor(cx + 0.5 + rr * math.cos(th)))
            y = int(math.floor(cy + 0.5 + rr * math.sin(th)))
            if 0 <= x < W and 0 <= y < H:
                m[y, x] = True
            rr += 0.2
    return m

def paint_crescent(img, cx, cy, R, tmax, span_deg, peak=False, light_gap=None,
                   outline=True, alpha=255, exp=0.8, dash=None, no_light=False):
    """본체. 램프: 앞날(바깥) light(피크는 core+light) → base → 안쪽 2px dark. 외곽선 1px(4방 팽창)."""
    m = crescent_mask(cx, cy, R, tmax, span_deg, exp, dash)
    span = math.radians(span_deg)
    if outline:
        o = dilate4(m) & ~m
        for y, x in zip(*np.nonzero(o)):
            put(img, x, y, 'outline', alpha)
    for y, x in zip(*np.nonzero(m)):
        dx, dy = x - cx, y - cy
        r = math.hypot(dx, dy)
        th = math.atan2(dy, dx)
        t = thick(th, span, tmax, exp)
        dout = R - r                     # 바깥 날에서 안쪽으로 들어온 거리
        if peak and dout < 0.75:
            name = 'core'
        elif (dout < 1.6) if peak else (dout < 0.9):
            name = 'base' if no_light else 'light'
        elif t >= 4.5 and (t - dout) < 1.9:
            name = 'dark'
        else:
            name = 'base'
        if light_gap and name == 'light' and not peak:
            per, on, ph = light_gap
            s = R * (th + span)
            if (s + ph) % per >= on:
                name = 'base'
        put(img, x, y, name, alpha)
    return m

def echo_arc(img, cx, cy, R, span_deg, name, alpha, period, on, phase, only_empty=True):
    """1px 잔상 호(점선). 본체보다 먼저 그린다."""
    span = math.radians(span_deg)
    n = int(R * span * 2 * 6) + 8
    for i in range(n + 1):
        th = -span + 2 * span * i / n
        s = R * (th + span)
        if (s + phase) % period >= on:
            continue
        x = int(math.floor(cx + 0.5 + R * math.cos(th)))
        y = int(math.floor(cy + 0.5 + R * math.sin(th)))
        if 0 <= x < W and 0 <= y < H and (not only_empty or img[y, x, 3] == 0):
            put(img, x, y, name, alpha)

def arc_points(cx, cy, R, span_deg, step, phase=0.0):
    """호 위에 step 간격으로 점 좌표를 돌려준다(소멸 점용)."""
    span = math.radians(span_deg)
    L = R * span * 2
    pts = []
    s = phase % step
    while s <= L:
        th = -span + s / R
        x = int(math.floor(cx + 0.5 + R * math.cos(th)))
        y = int(math.floor(cy + 0.5 + R * math.sin(th)))
        pts.append((x, y))
        s += step
    return pts

def hline(img, x0, x1, y, name, a):
    for x in range(x0, x1 + 1):
        if img[y, x, 3] == 0:
            put(img, x, y, name, a)

# ---------------------------------------------------------------- 프레임
T_FLY, T_PEAK, EXP = 6, 7, 1.0          # 두께(중앙) · 끝은 1px로 빠르게 좁아짐
SPAN = 78

def tip_xy():
    """비행 크레센트 위 · 아래 끝점(픽셀)."""
    s = math.radians(SPAN)
    x = int(math.floor(CX + 0.5 + R_FULL * math.cos(s)))
    return x, int(math.floor(CY + 0.5 - R_FULL * math.sin(s))), int(math.floor(CY + 0.5 + R_FULL * math.sin(s)))

def tip_streaks(img, k, lens=(8, 6, 10, 7)):
    """끝점에서 뒤(왼쪽)로 흐르는 1px 잔상선. 본체보다 먼저 그린다."""
    tx, ty0, ty1 = tip_xy()
    L = lens[k % 4]
    for y in (ty0 + 1, ty1 - 1):
        for i in range(L):
            x = tx - 1 - i
            name, a = ('base', 160) if i < 2 else ('dark', 110)
            if 0 <= x < W and img[y, x, 3] == 0:
                put(img, x, y, name, a)

def frame_emerge1():
    """F1 발생: 검끝을 감싸는 작은 호. 앞날 x49(주인공 64캔버스 x73 = 검끝 71 바로 앞)."""
    img = blank()
    paint_crescent(img, 32, 33, 17, tmax=3.5, span_deg=70, exp=EXP)
    return img

def frame_emerge2():
    """F2 피크: 최대 크기 + 코어 앞날. 유일한 코어 프레임."""
    img = blank()
    paint_crescent(img, CX, CY, R_FULL, tmax=T_PEAK, span_deg=SPAN, peak=True, exp=EXP)
    for (x, y) in [(40, 3), (40, 62)]:
        put(img, x, y, 'light')
    for (x, y) in [(61, 21), (61, 45)]:
        put(img, x, y, 'core')
    return img

def frame_fly(k):
    """F3~F6 비행 루프 k=0..3. 본체 고정, 잔상 · 꼬리 · 불티만 움직인다."""
    img = blank()
    # 끝점 잔상선 · 중앙 꼬리(안쪽 날에서 뒤로)
    tip_streaks(img, k)
    # 잔상 호 2개(본체를 뒤로 12 · 20px 옮긴 사본의 앞날): 1번은 거의 이어진 그림자 호, 2번은 점
    echo_arc(img, CX - 12, CY, R_FULL, 62, 'dark', 150, 12, 10, k * 3.0)
    echo_arc(img, CX - 20, CY, R_FULL, 44, 'dark', 90, 4, 1, k * 1.0)
    # 본체
    paint_crescent(img, CX, CY, R_FULL, tmax=T_FLY, span_deg=SPAN, light_gap=(9, 8, k * 2.0), exp=EXP)
    # 불티
    sp_light = [(58, 18), (59, 46), (57, 50), (58, 14)][k]
    sp_base = [(52, 8), (52, 58), (50, 6), (51, 60)][k]
    put(img, *sp_light, 'light')
    put(img, *sp_base, 'base')
    return img

def frame_dissolve1():
    """F7 소멸 1: 본체가 토막으로 끊긴다. 앞날 하이라이트 없음."""
    img = blank()
    tip_streaks(img, 1, lens=(3, 3, 3, 3))
    echo_arc(img, CX - 12, CY, R_FULL, 56, 'dark', 110, 6, 3, 1.0)
    paint_crescent(img, CX, CY, R_FULL, tmax=3.0, span_deg=SPAN, dash=(11, 7, 2.0), no_light=True, exp=EXP)
    for (x, y) in [(61, 24), (61, 42)]:
        put(img, x, y, 'base', 180)
    return img

def frame_dissolve2():
    """F8 소멸 2: 흩어진 점. 외곽선 없음, 알파 낮음."""
    img = blank()
    for (x, y) in arc_points(CX, CY, R_FULL + 2, 72, 5.0, 1.0):
        put(img, x, y, 'base', 150)
    for (x, y) in arc_points(CX, CY, R_FULL - 4, 58, 5.0, 3.0):
        put(img, x, y, 'dark', 100)
    for (x, y) in [(60, 16), (61, 33), (60, 50)]:
        put(img, x, y, 'light', 120)
    return img

FRAME_MS = [50, 60, 60, 60, 60, 60, 70, 90]
FRAME_NAMES = ['F1 발생', 'F2 피크', 'F3 비행', 'F4 비행', 'F5 비행', 'F6 비행', 'F7 소멸', 'F8 소멸']

def render_all():
    return [frame_emerge1(), frame_emerge2(),
            frame_fly(0), frame_fly(1), frame_fly(2), frame_fly(3),
            frame_dissolve1(), frame_dissolve2()]

def sheet(frames):
    s = np.zeros((H, W * len(frames), 4), np.uint8)
    for i, f in enumerate(frames):
        s[:, i * W:(i + 1) * W] = f
    return s
