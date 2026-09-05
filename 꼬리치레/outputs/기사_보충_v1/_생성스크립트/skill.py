# 스킬 발동(R) 시트 96x80: 예비 → 발동 → 유지 → 복귀. 몸만 / 소용돌이 포함 / 소용돌이만 3판 저장
import numpy as np, os, math
from PIL import Image, ImageDraw
from kb import *

W, H = 96, 80
OX, OY = 16, 16            # 64 캔버스 → 96x80 캔버스 오프셋 (Pivot Bottom Center 유지)
FOOT_Y96 = FOOT_Y + OY     # 78
HEAD_CX96 = HEAD_CX + OX   # 50

M = masks()
ys, xs = np.mgrid[0:64, 0:64]

BLADE = (214, 222, 230, 255)
BLADE_HI = (248, 250, 252, 255)
BLADE_SH = (150, 160, 176, 255)
GUARD = tuple(int(v) for v in GOLD)
GUARD_HI = tuple(int(v) for v in GOLD_HI)
GRIP = tuple(int(v) for v in BROWN_DARK)
OUT_DK = tuple(int(v) for v in DARK)
ARM_C = tuple(int(v) for v in ARMOR_MID)
ARM_HI = tuple(int(v) for v in ARMOR_HI)
ARM_LT = tuple(int(v) for v in ARMOR_LIGHT)
SKIN = tuple(int(v) for v in HAIR_LIGHT)

def layer():
    return Image.new('RGBA', (W, H), (0, 0, 0, 0))

def outline(im, color=OUT_DK):
    """불투명 픽셀의 4방 이웃 투명 픽셀을 외곽선 색으로."""
    a = np.array(im)
    m = a[..., 3] > 0
    d = np.zeros_like(m)
    d[1:, :] |= m[:-1, :]; d[:-1, :] |= m[1:, :]; d[:, 1:] |= m[:, :-1]; d[:, :-1] |= m[:, 1:]
    edge = d & ~m
    a[edge] = color
    return Image.fromarray(a)

def unit(angle_deg):
    r = math.radians(angle_deg)
    return math.cos(r), -math.sin(r)   # 화면 좌표(y 아래가 +). angle 0 = 오른쪽, 90 = 위

def draw_sword(im, hand, angle_deg, length=20):
    """hand(96캔버스 좌표)에서 angle 방향으로 검. 손잡이는 반대 방향."""
    d = ImageDraw.Draw(im)
    ux, uy = unit(angle_deg)
    px, py = -uy, ux            # 수직 방향
    hx, hy = hand
    # 손잡이(그립) 뒤쪽 3px, 폼멜
    gx, gy = hx - ux * 3, hy - uy * 3
    d.line([(hx, hy), (gx, gy)], fill=GRIP, width=2)
    d.point([(round(gx - ux), round(gy - uy))], fill=GUARD)
    # 날: 폭 3
    tx, ty = hx + ux * length, hy + uy * length
    d.line([(hx + ux * 2, hy + uy * 2), (tx, ty)], fill=BLADE, width=3)
    # 날 그림자(뒤쪽 1px) / 하이라이트(앞쪽 1px)
    d.line([(hx + ux * 2 + px, hy + uy * 2 + py), (tx - ux * 2 + px, ty - uy * 2 + py)], fill=BLADE_SH, width=1)
    d.line([(hx + ux * 3 - px, hy + uy * 3 - py), (tx - ux * 3 - px, ty - uy * 3 - py)], fill=BLADE_HI, width=1)
    # 검끝 1px
    d.point([(round(tx + ux), round(ty + uy))], fill=BLADE_HI)
    # 크로스가드: 수직 5px 금색
    cx, cy = hx + ux * 1.5, hy + uy * 1.5
    d.line([(cx - px * 2.5, cy - py * 2.5), (cx + px * 2.5, cy + py * 2.5)], fill=GUARD, width=2)
    d.point([(round(cx), round(cy))], fill=GUARD_HI)
    return im

def draw_arm(im, shoulder, hand):
    """2등신 비례의 짧고 두툼한 팔: 견갑(7×6 판) + 폭 5 상완/전완(밝은 쪽 하이라이트 · 어두운 쪽 그림자) + 5×5 건틀릿. 외곽선은 그림자 쪽만."""
    d = ImageDraw.Draw(im)
    sx, sy = shoulder; hx, hy = hand
    L = math.hypot(hx - sx, hy - sy); ux, uy = (hx - sx) / L, (hy - sy) / L
    px, py = -uy, ux                     # 수직 방향(px,py): 화면상 오른쪽-아래쪽이 그림자 쪽이 되도록 정렬
    if px + py < 0: px, py = -px, -py
    # 팔 본체 폭 5
    d.line([(sx, sy), (hx, hy)], fill=ARM_C, width=5)
    # 하이라이트(빛 쪽 1px) / 그림자(어두운 쪽 1px) / 그림자 쪽 외곽선
    d.line([(sx - px * 1.5, sy - py * 1.5), (hx - px * 1.5, hy - py * 1.5)], fill=ARM_LT, width=1)
    d.line([(sx + px * 1.5, sy + py * 1.5), (hx + px * 1.5, hy + py * 1.5)], fill=tuple(int(v) for v in ARMOR_DARK), width=1)
    d.line([(sx + px * 2.5, sy + py * 2.5), (hx + px * 2.5, hy + py * 2.5)], fill=OUT_DK, width=1)
    # 견갑: 7×6 둥근 판, 위쪽 하이라이트, 아래 외곽
    d.ellipse([sx - 3, sy - 3, sx + 3, sy + 2], fill=ARM_LT)
    d.ellipse([sx - 3, sy - 3, sx + 3, sy + 2], outline=OUT_DK)
    d.line([(sx - 2, sy - 2), (sx + 1, sy - 2)], fill=ARM_HI, width=1)
    d.point([(sx - 2, sy - 1)], fill=ARM_HI)
    # 건틀릿 5×5 + 손등 하이라이트 + 살색 손가락 2px
    d.ellipse([hx - 2, hy - 2, hx + 2, hy + 2], fill=ARM_C)
    d.ellipse([hx - 2, hy - 2, hx + 2, hy + 2], outline=OUT_DK)
    d.point([(hx - 1, hy - 1)], fill=ARM_LT)
    d.point([(hx + ux, hy + uy), (hx + ux + px, hy + uy + py)], fill=SKIN)
    return im

def body_frame(dy_upper=0, hair_phase=None, hair_amp=1.4, lean=0):
    """기준 서기(f0)를 96x80으로 옮기고 상체 오프셋/뒷머리 파동/기울기 적용. 반환: 96x80 RGBA numpy"""
    src = BASE
    hair = extract(src, M['hair_back'])
    legs = extract(src, M['legs'])
    upper = extract(src, alpha(src) & ~M['hair_back'] & ~M['legs'])
    if lean:
        upper = shear_rows(upper, 51, lean, 3)
        hair = shear_rows(hair, 51, lean, 3)
    body64 = blank()
    paste(body64, hair, 0, dy_upper)
    paste(body64, legs, 0, 0)
    paste(body64, upper, 0, dy_upper)
    if hair_phase is not None:
        hm = blank()[..., 0].astype(bool)
        # 이동 후 뒷머리 마스크 재계산
        hm = alpha(body64) & (ys >= 22 + dy_upper) & (ys <= 45 + dy_upper) & (xs <= 29 + max(0, lean // 2))
        body64 = close_holes(hair_wave(body64, hm, hair_phase, amp=hair_amp, y0=24 + dy_upper))
    body64 = fill_gaps(body64, 1, (20, 52))
    out = blank(W, H)
    paste(out, body64, OX, OY)
    return out

def swirl_layer(phase, radius=15, ry=4.5, cy=FOOT_Y96 - 2, cx=HEAD_CX96, n=3, rise=0, sparks=6, fade=1.0, turns=1.6, height=40):
    """금색 소용돌이: 발밑에서 몸을 감아 올라가는 나선(뒤쪽 어둡게·앞쪽 밝게) + 상승 불꽃."""
    im = layer(); d = ImageDraw.Draw(im)
    T = int(turns * 2 * math.pi * 6)
    prev = None
    for i in range(T + 1):
        t = i / 6.0
        r = radius * (1.0 - 0.45 * t / (turns * 2 * math.pi))
        a = t + phase
        x = cx + r * math.cos(a)
        y = cy - height * t / (turns * 2 * math.pi) + ry * 0.35 * math.sin(a)
        depth = math.sin(a)
        p = (round(x), round(y))
        if prev is not None:
            if depth > 0.15:
                col = (*GOLD_HI[:3], 255) if (i // 3) % 2 else (*GOLD[:3], 255)
            elif depth > -0.3:
                col = (*GOLD[:3], 255)
            else:
                col = (*GOLD_DARK[:3], 255)
            # 뒤쪽은 점선으로 끊어 깊이감
            if depth > -0.3 or (i % 3):
                d.line([prev, p], fill=col, width=1)
        prev = p
    # 상승 불꽃(작은 마름모/점)
    rng = np.random.RandomState(int(phase * 100) % 9973)
    for s in range(sparks):
        a = phase * 1.7 + s * 2 * math.pi / sparks
        x = cx + (radius - 3) * math.cos(a)
        yy = cy - 4 - (s * 7 + int(phase * 6)) % 34
        d.point([(round(x), round(yy))], fill=(*GOLD_HI[:3], 255))
        if s % 2 == 0:
            d.point([(round(x) + 1, round(yy)), (round(x) - 1, round(yy)), (round(x), round(yy) - 1), (round(x), round(yy) + 1)], fill=(*GOLD[:3], 255))
    return im

def blade_glow(im, hand, angle, length=20):
    d = ImageDraw.Draw(im)
    ux, uy = unit(angle); px, py = -uy, ux
    hx, hy = hand
    for k in (2, -2):
        d.line([(hx + ux * 4 + px * k, hy + uy * 4 + py * k), (hx + ux * (length - 1) + px * k, hy + uy * (length - 1) + py * k)], fill=(*GOLD_HI[:3], 255), width=1)
    d.point([(round(hx + ux * (length + 2)), round(hy + uy * (length + 2))), (round(hx + ux * (length + 3)), round(hy + uy * (length + 3)))], fill=(*GOLD_HI[:3], 255))
    return im

def smear(im, hand_from, ang_from, hand_to, ang_to, steps=14, length=20):
    """검끝이 지나간 궤적을 연속된 연한 선 하나로(점선·고립 픽셀 없이)."""
    d = ImageDraw.Draw(im)
    pts = []
    for i in range(steps + 1):
        t = i / steps
        hx = hand_from[0] + (hand_to[0] - hand_from[0]) * t
        hy = hand_from[1] + (hand_to[1] - hand_from[1]) * t
        ang = ang_from + (ang_to - ang_from) * t
        ux, uy = unit(ang)
        pts.append((hx + ux * length, hy + uy * length))
    d.line(pts, fill=(*ARMOR_HI[:3], 255), width=1)
    return im

# 어깨 위치(96캔버스): 기준 프레임 견갑 중심 (36,33) + 오프셋
SHOULDER = (36 + OX, 33 + OY)

# 팔 포즈: (손 위치 96캔버스, 검 각도)
A_LOW   = ((42 + OX, 42 + OY), -45)   # 예비: 검을 앞아래로 낮게 (어깨에서 11px)
A_LOW2  = ((40 + OX, 43 + OY), -50)   # 더 웅크림   # 더 웅크림
A_MID   = ((48 + OX, 34 + OY), 40)    # 발동 중간: 앞으로 뻗음, 가슴 높이 (12px)
A_MID2  = ((40 + OX, 22 + OY), 70)    # 발동 중간 2: 얼굴 앞을 지나 위로 (12px) — 스미어 1프레임
A_HIGH  = ((30 + OX, 21 + OY), 80)    # 정점: 머리 옆(뒷머리 앞)에서 하늘로 (13px)     # 정점: 머리 뒤 위로 하늘을 향해 치켜듦 (얼굴 비움)

# (이름, 상체 dy, 어깨 dy 보정, 팔 포즈, 뒷머리 위상, 소용돌이 위상 or None, 소용돌이 반지름, 옵션)
PLAN = [
    ('예비1 웅크림',      +2, A_LOW,  None, None, 0, {}),
    ('예비2 힘 모음',     +3, A_LOW2, None, 0.0, 9, {'sparks': 3}),
    ('발동 스미어',       -1, A_MID,  0.8,  1.3, 13, {'smear': (A_LOW2, A_MID), 'sparks': 5}),
    ('발동 스미어 2',     -2, A_MID2, 1.2,  2.0, 15, {'smear': (A_MID, A_MID2), 'sparks': 6}),
    ('발동 정점 · 섬광',  -2, A_HIGH, 1.6,  2.6, 16, {'glow': True, 'sparks': 8, 'smear': (A_MID2, A_HIGH)}),
    ('유지1',             -1, A_HIGH, 2.4,  3.9, 15, {'sparks': 6}),
    ('유지2',             -1, A_HIGH, 3.2,  5.2, 15, {'sparks': 6}),
    ('유지3',             -1, A_HIGH, 4.0,  6.5, 15, {'sparks': 6}),
    ('복귀1 내림',         0, A_MID,  4.8,  7.8, 12, {'sparks': 3}),
    ('복귀2 낮게',        +1, A_LOW,  None, None, 0, {}),
    ('서기(원본)',         0, None,   None, None, 0, {}),
]

body_frames, fx_frames, both_frames = [], [], []
for name, dyu, pose, hp, sp, rad, opt in PLAN:
    body = body_frame(dy_upper=dyu, hair_phase=hp, hair_amp=1.0)
    im = Image.fromarray(body)
    lay = layer()
    if pose is not None:
        hand, ang = pose
        sh = (SHOULDER[0], SHOULDER[1] + dyu)
        if 'smear' in opt:
            (h0, a0), (h1, a1) = opt['smear']
            smear(lay, h0, a0, h1, a1)
        arm = layer(); draw_arm(arm, sh, hand)
        sw = layer(); draw_sword(sw, hand, ang); sw = outline(sw)
        lay.alpha_composite(arm); lay.alpha_composite(sw)
    im.alpha_composite(lay)
    body_arr = np.array(im)
    body_frames.append(body_arr)
    # 이펙트
    fx = layer()
    if sp is not None:
        fx = swirl_layer(sp, radius=rad, sparks=opt.get('sparks', 6))
        if opt.get('glow') and pose is not None:
            blade_glow(fx, pose[0], pose[1])
    fx_arr = np.array(fx)
    fx_frames.append(fx_arr)
    # 소용돌이 뒤쪽(어두운 금색)은 몸 뒤, 앞쪽(밝은 금색)은 몸 앞
    both = body_arr.copy()
    fxm = alpha(fx_arr)
    is_back = fxm & (fx_arr[..., :3] == GOLD_DARK[:3]).all(-1)
    front = fxm & ~is_back
    back_only = is_back & ~alpha(body_arr)
    both[back_only] = fx_arr[back_only]
    both[front] = fx_arr[front]
    both_frames.append(both)

p1 = save_sheet(body_frames, '스킬발동')
p2 = save_sheet(both_frames, '스킬발동_소용돌이포함')
p3 = save_sheet(fx_frames, '스킬발동_소용돌이만')
dur = [70, 70, 50, 50, 90, 90, 90, 90, 70, 70, 120]
save_gif(both_frames, '스킬발동', dur)
save_gif(body_frames, '스킬발동_몸만', dur)
contact_sheet(both_frames[:6], os.path.join(SP, 'skill_a.png'), scale=6)
contact_sheet(both_frames[6:], os.path.join(SP, 'skill_b.png'), scale=6)
print(p1); print(p2); print(p3)
for i, f in enumerate(body_frames):
    yy, xx = np.where(alpha(f)); print(i, PLAN[i][0], 'top', yy.min(), 'bottom', yy.max(), 'x', xx.min(), xx.max())
