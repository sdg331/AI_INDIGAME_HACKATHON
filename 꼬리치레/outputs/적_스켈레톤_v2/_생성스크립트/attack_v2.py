# -*- coding: utf-8 -*-
"""스켈레톤 공격 모션 v2b — 대기 몸 한 벌에서 검 팔을 다시 그려 머리 위 내려치기 10프레임.
build_v2.py 에서 import 해 frames_attack 을 대체한다."""
import math
import numpy as np
from PIL import Image, ImageDraw
from v2tools import *

def seg_mask(shape, p0, p1, r):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    x0, y0 = p0; x1, y1 = p1
    vx, vy = x1 - x0, y1 - y0
    t = np.clip(((xx - x0) * vx + (yy - y0) * vy) / max(1e-6, vx * vx + vy * vy), 0, 1)
    d = np.hypot(xx - (x0 + t * vx), yy - (y0 + t * vy))
    return d <= r

def build_attack(idle, iax, palette, W=80):
    """idle: 대기 RGBA(58x45, 검이 왼쪽). 반환: 80x64 프레임 10장"""
    H0, W0 = idle.shape[:2]
    pal = [tuple(p) for p in palette]
    # 팔레트에서 뼈 색 고르기(밝기 순)
    lum = sorted(pal, key=lambda c: sum(c))
    OUTL = lum[1]; DARK = lum[4]; MID = lum[13]; LIGHT = lum[20]
    # 1) 검 블롭: 칼날 축 (1,8)-(9,31) 반경 3 + 손 상자
    sw_m = seg_mask((H0, W0), (1, 8), (9, 31), 3.2)
    sw_m[30:38, 6:13] = True
    sw_m &= idle[..., 3] > 0
    sword0 = crop_mask(idle, sw_m)
    P = 32                                            # 회전용 여백(칼날이 원본 캔버스 밖으로 나가도 잘리지 않게)
    sword = np.zeros((H0 + 2 * P, W0 + 2 * P, 4), np.uint8); sword[P:P + H0, P:P + W0] = sword0
    PIV = (9 + P, 34 + P)
    # 2) 팔+검 지운 몸
    body0 = idle.copy(); body0[6:38, 0:14] = 0
    SHOULDER = (15, 19)

    def draw_arm(c, S, E, Hd):
        m = np.zeros(c.shape[:2], bool)
        for a, b in ((S, E), (E, Hd)):
            m |= seg_mask(c.shape[:2], a, b, 2.0)
        m |= seg_mask(c.shape[:2], S, S, 2.6)          # 어깨 관절
        ring = m & ~ndimage_erode(m)
        c[m] = (*MID, 255); c[ring] = (*OUTL, 255)
        # 뼈 하이라이트: 팔 축을 따라 1px
        hl = np.zeros_like(m)
        for a, b in ((S, E), (E, Hd)):
            hl |= seg_mask(c.shape[:2], (a[0] - 1, a[1] - 1), (b[0] - 1, b[1] - 1), 0.6)
        c[hl & m & ~ring] = (*LIGHT, 255)
        # 관절 어둠
        c[seg_mask(c.shape[:2], E, E, 1.2) & m & ~ring] = (*DARK, 255)
        return c

    def ghost(sw_rot, f):
        a = sw_rot.astype(float); a[..., :3] *= f
        return quantize(np.clip(a, 0, 255).astype(np.uint8), palette)

    def frame(dx=0, sy=1.0, shear=0, hand=(-6, 15), bend=0, angle=0, behind=False, smear=(), front_leg=0, back_leg=0):
        body = body0
        if front_leg or back_leg:
            torso, legs = split_rows(body, 43)
            bl, fl = split_legs(body, 43)
            body = blank(W0, H0)[:, :, :] if False else np.zeros_like(body)
            paste(body, shift(bl, back_leg, 0), 0, 0); paste(body, shift(fl, front_leg, 0), 0, 0); paste(body, torso, 0, 0)
        if sy != 1.0: body = resize_nn(body, 1.0, sy)
        h = body.shape[0]
        X0 = int(round(W / 2 - iax + dx)); Y0 = FOOT_Y - h + 1
        c = blank(W)
        # 어깨 캔버스 좌표(압축 · 전단 반영)
        sy_ = SHOULDER[1] * sy
        S = (X0 + SHOULDER[0], int(round(Y0 + sy_)))
        def sh_off(y): return int(round(shear * (FOOT_Y - 6 - y) / (FOOT_Y - 6))) if shear else 0
        S = (S[0] + sh_off(S[1]), S[1])
        Hd = (S[0] + hand[0], S[1] + hand[1])
        # 팔꿈치
        mx, my = (S[0] + Hd[0]) / 2, (S[1] + Hd[1]) / 2
        vx, vy = Hd[0] - S[0], Hd[1] - S[1]; L = max(1e-6, math.hypot(vx, vy))
        nx, ny = -vy / L, vx / L
        E = (int(round(mx + nx * bend)), int(round(my + ny * bend)))
        # 검(회전 → 손 위치)
        sw = rotate_about(sword, angle, PIV)
        swt, (ox, oy) = tight(sw)
        # 회전 후 pivot 좌표
        px, py = PIV[0] - ox, PIV[1] - oy
        layer_w = blank(W)
        for ga, gf in smear:
            g = rotate_about(sword, ga, PIV); gt, (gox, goy) = tight(g)
            paste(layer_w, ghost(gt, gf), Hd[0] - (PIV[0] - gox), Hd[1] - (PIV[1] - goy))
        paste(layer_w, swt, Hd[0] - px, Hd[1] - py)
        layer_a = blank(W); draw_arm(layer_a, S, E, Hd)
        bodyc = paste(blank(W), body, X0, Y0)
        if shear: bodyc = shear_rows(bodyc, shear, 0, FOOT_Y - 6)
        if behind:
            paste(c, layer_w, 0, 0); paste(c, layer_a, 0, 0); paste(c, bodyc, 0, 0)
        else:
            paste(c, bodyc, 0, 0); paste(c, layer_a, 0, 0); paste(c, layer_w, 0, 0)
        return c

    F = [
        frame(),                                                                             # 1 서기
        frame(dx=0, shear=-2, hand=(-9, -2), bend=-3, angle=-25, behind=True),               # 2 예고: 검을 뒤로 들어올림
        frame(dx=2, sy=0.92, shear=-3, hand=(-6, -12), bend=-4, angle=-50, behind=True),      # 3 예고: 최대 — 웅크리고 검이 머리 뒤 위
        frame(dx=2, sy=0.92, shear=-3, hand=(-6, -12), bend=-4, angle=-50, behind=True),      # 4 홀드
        frame(dx=2, sy=0.92, shear=-3, hand=(-6, -13), bend=-4, angle=-53, behind=True),      # 5 홀드 떨림
        frame(dx=0, sy=1.03, shear=3, hand=(13, -7), bend=3, angle=100,                       # 6 휘두름: 검이 머리 위를 지나 앞으로 + 뒤따르는 잔상 2(스미어)
              smear=((60, 0.62), (80, 0.8)), front_leg=2),
        frame(dx=2, sy=0.96, shear=5, hand=(16, 4), bend=4, angle=140, front_leg=4, back_leg=-1),   # 7 접촉: 45° 내려침, 칼끝이 주인공 가슴 높이(y≈43)
        frame(dx=2, sy=0.95, shear=4, hand=(14, 10), bend=4, angle=165, front_leg=4, back_leg=-1),  # 8 팔로우스루: 칼끝 바닥 근처
        frame(dx=1, sy=0.98, shear=1, hand=(2, 12), bend=2, angle=60, front_leg=2),            # 9 회수
        frame(),                                                                             # 10 서기
    ]
    return F

def ndimage_erode(m):
    from scipy import ndimage
    return ndimage.binary_erosion(m, iterations=1)
