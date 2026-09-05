# 3연격 공격: 1타 가로 베기(80x64) → 2타 올려 베기(80x64) → 3타 내려 찍기(96x80). 예비 → 스미어 → 접촉 → 홀드 → 팔로우스루 → 복귀 → 준비
import os, numpy as np
from PIL import Image
from kb import *
from armlib import *

M = masks(); ys, xs = np.mgrid[0:64, 0:64]
SHOULDER64 = (36, 33)
READY = ((42, 44), -50)       # 연격 사이 준비 자세: 검을 앞아래로 낮게

def body64(dy_upper=0, lean=0, legs_src=None, hair_phase=None):
    """기준 서기 몸(64): 상체 dy(스쿼시/스트레치) + 허리 축 기울기 + 다리 교체(런지)."""
    src = BASE
    hair = extract(src, M['hair_back']); upper = extract(src, alpha(src) & ~M['hair_back'] & ~M['legs'])
    legs = extract(src, M['legs']) if legs_src is None else extract(legs_src, alpha(legs_src) & (ys >= 52))
    if lean:
        upper = shear_rows(upper, 51, lean, 3); hair = shear_rows(hair, 51, lean, 3)
    b = blank(); paste(b, hair, 0, dy_upper); paste(b, legs, 0, 0); paste(b, upper, 0, dy_upper)
    if hair_phase is not None:
        hm = alpha(b) & (ys >= 22 + dy_upper) & (ys <= 45 + dy_upper) & (xs <= 29 + max(0, lean // 2))
        b = close_holes(hair_wave(b, hm, hair_phase, amp=1.0, y0=24 + dy_upper))
    return fill_gaps(b, 1, (16, 52))

def frame(W, H, off, dy_upper, lean, dx, hand, angle, smear_from=None, legs_src=None, hair_phase=None, sword=True, length=20):
    """캔버스 W×H, 몸 오프셋 off=(ox,oy). hand/angle은 64 좌표 기준(몸 dx 포함 전). smear_from=(hand, angle)."""
    ox, oy = off
    out = blank(W, H)
    b = body64(dy_upper, lean, legs_src, hair_phase)
    paste(out, b, ox + dx, oy)
    im = Image.fromarray(out)
    S = (SHOULDER64[0] + ox + dx + max(0, lean) // 3, SHOULDER64[1] + oy + dy_upper)   # 기울기에 따라 어깨도 앞으로
    Hd = (hand[0] + ox + dx, hand[1] + oy + dy_upper)
    lay = layer(W, H)
    if smear_from is not None:
        (h0, a0) = smear_from
        H0 = (h0[0] + ox + dx, h0[1] + oy + dy_upper)
        smear(lay, H0, a0, Hd, angle, length=length, inner=0.6)
    if sword:
        lay.alpha_composite(arm_and_sword(W, H, S, Hd, angle, length))
    im.alpha_composite(lay)
    a = np.array(im)
    a[H - 1, :] = 0 if H == 64 else a[H - 1, :]   # 64 캔버스: 63행 비움 규약
    return a

LUNGE = F[4]   # 걷기 접지 2: 가장 넓은 보폭(런지 다리)

# ---------- 1타: 가로 베기 (뒤에서 앞으로 수평) ----------
def hit1():
    W, H, off = 80, 64, (8, 0)
    P = [
        ("예비 — 검을 뒤로, 몸 뒤로 기울임",         0, -2, -1, (28, 36), 160, None, None),
        ("예비 홀드 — 1px 더 뒤",                    +1, -2, -2, (28, 37), 165, None, None),
        ("스미어 — 어깨 위로 넘어오는 궤적",          0, +1,  0, (40, 27),  65, ((28, 37), 165), None),
        ("접촉 — 수평 베기, 앞으로 3px",             0, +3, +2, (48, 36),   0, None, None),
        ("접촉 홀드",                                0, +3, +2, (48, 36),   0, None, None),
        ("팔로우스루 — 검이 조금 더 내려감",          0, +3, +2, (47, 41), -25, None, None),
        ("복귀 — 준비 자세로",                       0, +1, +1, (44, 44), -45, None, None),
        ("준비 — 검 낮게(다음 타로 연결)",            0,  0,  0, READY[0], READY[1], None, None),
    ]
    return [(n, frame(W, H, off, dyu, ln, dx, hd, ang, sm, lg)) for n, dyu, ln, dx, hd, ang, sm, lg in P], W, H

# ---------- 2타: 올려 베기 (앞아래에서 위로 대각선) ----------
def hit2():
    W, H, off = 80, 64, (8, 0)
    P = [
        ("예비 — 웅크리며 검을 아래로",               +2, +1,  0, (44, 46), -70, None, None),
        ("예비 홀드",                                +2, +1,  0, (44, 47), -72, None, None),
        ("스미어 — 아래에서 위로 궤적",               0, +2, +1, (49, 40), -15, ((44, 47), -72), None),
        ("접촉 — 앞위 대각선(스트레치), 앞으로 2px",  -2, +3, +2, (48, 36),  50, None, None),
        ("접촉 홀드",                                -2, +3, +2, (48, 36),  50, None, None),
        ("팔로우스루 — 검이 머리 위로 넘어감",         -1, +1, +1, (42, 26), 110, None, None),
        ("복귀 — 검을 다시 앞으로 내림",              0,  0,  0, (45, 36),  10, None, None),
        ("준비 — 검 낮게",                            0,  0,  0, READY[0], READY[1], None, None),
    ]
    return [(n, frame(W, H, off, dyu, ln, dx, hd, ang, sm, lg)) for n, dyu, ln, dx, hd, ang, sm, lg in P], W, H

# ---------- 3타: 내려 찍기 (머리 위에서 앞아래로, 런지) ----------
def hit3():
    W, H, off = 96, 80, (16, 16)
    P = [
        ("예비 1 — 검을 머리 뒤로 들어올림",            +1, -2,  0, (30, 22), 100, None, None),
        ("예비 2 — 더 뒤로 젖히고 웅크림",              +2, -3, -1, (27, 26), 125, None, None),
        ("예비 홀드 — 떨림",                            +2, -3, -2, (27, 27), 128, None, None),
        ("스미어 — 머리 위를 넘어오는 큰 궤적",          -1, +3, +1, (44, 18),  50, ((27, 27), 128), None),
        ("접촉 — 내려찍기 + 런지(앞으로 4px, 넓은 보폭)", +2, +5, +4, (52, 40), -45, None, LUNGE),
        ("접촉 홀드 — 충격(1px 더 앞)",                  +2, +5, +5, (52, 40), -45, None, LUNGE),
        ("팔로우스루 — 검끝이 땅 쪽으로",                +2, +4, +4, (50, 43), -50, None, LUNGE),
        ("복귀 — 몸을 세움",                            +1, +2, +2, (46, 43), -50, None, None),
        ("준비 — 검 낮게",                               0,  0,  0, READY[0], READY[1], None, None),
    ]
    return [(n, frame(W, H, off, dyu, ln, dx, hd, ang, sm, lg)) for n, dyu, ln, dx, hd, ang, sm, lg in P], W, H

DUR1 = [110, 70, 40, 90, 60, 80, 90, 120]
DUR2 = [110, 70, 40, 90, 60, 80, 90, 120]
DUR3 = [110, 100, 80, 40, 110, 70, 90, 100, 120]

if __name__ == "__main__":
    all_ = []
    for name, fn, dur in (("공격1타_가로베기", hit1, DUR1), ("공격2타_올려베기", hit2, DUR2), ("공격3타_내려찍기", hit3, DUR3)):
        frs, W, H = fn(); imgs = [f for _, f in frs]
        p = save_sheet(imgs, name); save_gif(imgs, name, dur)
        contact_sheet(imgs, os.path.join(SP, f"{name}_cs.png"), scale=5)
        print(p)
        for i, (n, f) in enumerate(frs):
            yy, xx = np.where(alpha(f)); print(f"  {i} {n}: top {yy.min()} bottom {yy.max()} x {xx.min()}-{xx.max()}")
        all_.append((imgs, W, H, dur))
    # 연격 미리보기: 3타를 96x80 캔버스로 통일해 이어 붙임
    chain = []; durs = []
    for imgs, W, H, dur in all_:
        for f, d in zip(imgs, dur):
            c = blank(96, 80); paste(c, f, (96 - W) // 2, 80 - H); chain.append(c); durs.append(d)
    save_gif(chain, "공격_3연격", durs)
