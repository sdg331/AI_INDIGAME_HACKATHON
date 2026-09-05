# 주인공 팔 · 검 그리기 공통(2등신 비례). skill.py / attack_combo.py 공용
import math
import numpy as np
from PIL import Image, ImageDraw
from kb import *

BLADE = (214, 222, 230, 255); BLADE_HI = (248, 250, 252, 255); BLADE_SH = (150, 160, 176, 255)
GUARD = tuple(int(v) for v in GOLD); GUARD_HI = tuple(int(v) for v in GOLD_HI)
GRIP = tuple(int(v) for v in BROWN_DARK); OUT_DK = tuple(int(v) for v in DARK)
ARM_C = tuple(int(v) for v in ARMOR_MID); ARM_HI = tuple(int(v) for v in ARMOR_HI); ARM_LT = tuple(int(v) for v in ARMOR_LIGHT)
ARM_DK = tuple(int(v) for v in ARMOR_DARK); SKIN = tuple(int(v) for v in HAIR_LIGHT)
SMEAR_C = (*ARMOR_HI[:3], 255)

def layer(w, h):
    return Image.new('RGBA', (w, h), (0, 0, 0, 0))

def outline(im, color=OUT_DK):
    a = np.array(im); m = a[..., 3] > 0
    d = np.zeros_like(m)
    d[1:, :] |= m[:-1, :]; d[:-1, :] |= m[1:, :]; d[:, 1:] |= m[:, :-1]; d[:, :-1] |= m[:, 1:]
    a[d & ~m] = color
    return Image.fromarray(a)

def unit(angle_deg):
    r = math.radians(angle_deg); return math.cos(r), -math.sin(r)   # 0° = 오른쪽, 90° = 위

def draw_sword(im, hand, angle_deg, length=20):
    d = ImageDraw.Draw(im); ux, uy = unit(angle_deg); px, py = -uy, ux; hx, hy = hand
    gx, gy = hx - ux * 3, hy - uy * 3
    d.line([(hx, hy), (gx, gy)], fill=GRIP, width=2)
    d.point([(round(gx - ux), round(gy - uy))], fill=GUARD)
    tx, ty = hx + ux * length, hy + uy * length
    d.line([(hx + ux * 2, hy + uy * 2), (tx, ty)], fill=BLADE, width=3)
    d.line([(hx + ux * 2 + px, hy + uy * 2 + py), (tx - ux * 2 + px, ty - uy * 2 + py)], fill=BLADE_SH, width=1)
    d.line([(hx + ux * 3 - px, hy + uy * 3 - py), (tx - ux * 3 - px, ty - uy * 3 - py)], fill=BLADE_HI, width=1)
    d.point([(round(tx + ux), round(ty + uy))], fill=BLADE_HI)
    cx, cy = hx + ux * 1.5, hy + uy * 1.5
    d.line([(cx - px * 2.5, cy - py * 2.5), (cx + px * 2.5, cy + py * 2.5)], fill=GUARD, width=2)
    d.point([(round(cx), round(cy))], fill=GUARD_HI)
    return im

def draw_arm(im, shoulder, hand):
    """견갑 7×6 + 폭 5 팔 + 5×5 건틀릿. 외곽선은 그림자 쪽만."""
    d = ImageDraw.Draw(im); sx, sy = shoulder; hx, hy = hand
    L = max(1e-6, math.hypot(hx - sx, hy - sy)); ux, uy = (hx - sx) / L, (hy - sy) / L
    px, py = -uy, ux
    if px + py < 0: px, py = -px, -py
    d.line([(sx, sy), (hx, hy)], fill=ARM_C, width=5)
    d.line([(sx - px * 1.5, sy - py * 1.5), (hx - px * 1.5, hy - py * 1.5)], fill=ARM_LT, width=1)
    d.line([(sx + px * 1.5, sy + py * 1.5), (hx + px * 1.5, hy + py * 1.5)], fill=ARM_DK, width=1)
    d.line([(sx + px * 2.5, sy + py * 2.5), (hx + px * 2.5, hy + py * 2.5)], fill=OUT_DK, width=1)
    d.ellipse([sx - 3, sy - 3, sx + 3, sy + 2], fill=ARM_LT); d.ellipse([sx - 3, sy - 3, sx + 3, sy + 2], outline=OUT_DK)
    d.line([(sx - 2, sy - 2), (sx + 1, sy - 2)], fill=ARM_HI, width=1); d.point([(sx - 2, sy - 1)], fill=ARM_HI)
    d.ellipse([hx - 2, hy - 2, hx + 2, hy + 2], fill=ARM_C); d.ellipse([hx - 2, hy - 2, hx + 2, hy + 2], outline=OUT_DK)
    d.point([(hx - 1, hy - 1)], fill=ARM_LT)
    d.point([(hx + ux, hy + uy), (hx + ux + px, hy + uy + py)], fill=SKIN)
    return im

def smear(im, hand_from, ang_from, hand_to, ang_to, steps=14, length=20, width=1, color=SMEAR_C, inner=0.0):
    """검끝(및 선택적으로 날 중간)이 지나간 궤적을 연속선으로."""
    d = ImageDraw.Draw(im); pts = []; pts2 = []
    for i in range(steps + 1):
        t = i / steps
        hx = hand_from[0] + (hand_to[0] - hand_from[0]) * t; hy = hand_from[1] + (hand_to[1] - hand_from[1]) * t
        ang = ang_from + (ang_to - ang_from) * t; ux, uy = unit(ang)
        pts.append((hx + ux * length, hy + uy * length))
        if inner: pts2.append((hx + ux * length * inner, hy + uy * length * inner))
    d.line(pts, fill=color, width=width)
    if inner: d.line(pts2, fill=color, width=1)
    return im

def arm_and_sword(w, h, shoulder, hand, angle, length=20):
    """팔(외곽 없음) + 검(외곽 있음) 레이어."""
    lay = layer(w, h)
    arm = layer(w, h); draw_arm(arm, shoulder, hand)
    sw = layer(w, h); draw_sword(sw, hand, angle, length); sw = outline(sw)
    lay.alpha_composite(arm); lay.alpha_composite(sw)
    return lay
