# 3연격을 파츠 리그로: 파츠분할 7파츠(앞팔 밑 채움 포함) + 검. 앞팔은 무손실 변환(id/cw/ccw/180/flipH/flipV + 이동)만. 팔을 그리지 않는다.
import os
import numpy as np
from PIL import Image
from kb import *
from armlib import draw_sword, outline, layer

PD = os.path.join(OUT, "파츠분할")
def load_part(name):
    return np.array(Image.open(os.path.join(PD, name + ".png")).convert("RGBA"))
P = {k: load_part(k) for k in ["01_뒷머리", "02_뒷다리", "03_앞다리", "04_허리치마", "05_몸통", "06_앞팔", "07_머리"]}
SX, SY = 33, 31; HAND = (30, 49); ARM_PX = int(alpha(P["06_앞팔"]).sum())
LEG_TOP, LEG_BOT = 52, 62

def rigid(img, op):
    out = blank(); ys_, xs_ = np.where(alpha(img)); dx, dy = xs_ - SX, ys_ - SY
    nx, ny = {'id': (dx, dy), 'ccw': (dy, -dx), 'cw': (-dy, dx), '180': (-dx, -dy), 'flipH': (-dx, dy), 'flipV': (dx, -dy)}[op]
    out[ny + SY, nx + SX] = img[ys_, xs_]; return out
def hand_after(op):
    dx, dy = HAND[0] - SX, HAND[1] - SY
    m = {'id': (dx, dy), 'ccw': (dy, -dx), 'cw': (-dy, dx), '180': (-dx, -dy), 'flipH': (-dx, dy), 'flipV': (dx, -dy)}[op]
    return SX + m[0], SY + m[1]
def tilt(img, top_y, bottom_y, k):
    out = blank(); a = alpha(img)
    for y in range(64):
        if not a[y].any(): continue
        t = (y - top_y) / max(1, bottom_y - top_y); s = int(round(k * max(0.0, min(1.0, t)))); row = img[y]
        if s > 0: out[y, s:] = row[:-s]
        elif s < 0: out[y, :s] = row[-s:]
        else: out[y] = row
    return out

def frame(W, H, off, spec):
    s = dict(arm='id', arm_dx=0, arm_dy=0, sword_deg=-50, body_dx=0, lean=0, upper_dy=0, hair_dx=0, head_dx=0, front=(0, 0), back=(0, 0), sword_len=20)
    s.update(spec); ox, oy = off
    c = blank(); lean, dyu = s["lean"], s["upper_dy"]
    def up(img): return shear_rows(img, 51, lean, 3) if lean else img
    paste(c, up(P["01_뒷머리"]), s["hair_dx"], dyu)
    paste(c, tilt(P["02_뒷다리"], LEG_TOP, LEG_BOT, s["back"][0]), 0, s["back"][1])
    paste(c, tilt(P["03_앞다리"], LEG_TOP, LEG_BOT, s["front"][0]), 0, s["front"][1])
    paste(c, up(P["04_허리치마"]), 0, dyu); paste(c, up(P["05_몸통"]), 0, dyu); paste(c, up(P["07_머리"]), s["head_dx"], dyu)
    sh = int(round(lean * (51 - SY) / 48)); arm = rigid(P["06_앞팔"], s["arm"]); adx, ady = sh + s["arm_dx"], dyu + s["arm_dy"]
    paste(c, arm, adx, ady); c = fill_gaps(c, 1, (16, 52))
    out = blank(W, H); paste(out, c, ox + s["body_dx"], oy)
    hx, hy = hand_after(s["arm"]); Hd = (hx + adx + ox + s["body_dx"], hy + ady + oy)
    # 검끝 · 손잡이가 캔버스(외곽선 1px 여유) 안에 있는지 검사
    import math
    ang = math.radians(s["sword_deg"]); L = s["sword_len"]
    tip = (Hd[0] + math.cos(ang) * (L + 1), Hd[1] - math.sin(ang) * (L + 1)); pom = (Hd[0] - math.cos(ang) * 4, Hd[1] + math.sin(ang) * 4)
    for px_, py_ in (tip, pom):
        if not (1 <= px_ <= W - 2 and 1 <= py_ <= (62 if H == 64 else 78)):
            print(f"  !! 검이 캔버스를 벗어남: 손 {Hd} 각도 {s['sword_deg']} 끝 ({px_:.0f},{py_:.0f})")
    im = Image.fromarray(out); sw = layer(W, H); draw_sword(sw, Hd, s["sword_deg"], s["sword_len"]); im.alpha_composite(outline(sw))
    a = np.array(im)
    if H == 64: a[63, :] = 0
    else: a[79, :] = 0
    return a

# 1타 가로 베기 (96x80, 오프셋 +16,+16 — 팔 18px + 검 20px가 80x64에 안 들어감): 뒤로 수평 → 머리 위 → 앞으로 수평
HIT1 = [
    ("준비 — 검 앞아래",                 dict(arm='id',    sword_deg=-35)),
    ("예비 — 팔 뒤로 수평, 몸 뒤로",      dict(arm='cw',    sword_deg=165, lean=-2, upper_dy=1, hair_dx=1, head_dx=-1)),
    ("예비 홀드",                        dict(arm='cw',    sword_deg=170, lean=-2, upper_dy=1, hair_dx=1, head_dx=-1, body_dx=-1)),
    ("휘두름 — 팔 위로, 검 머리 위",      dict(arm='flipV', sword_deg=80,  lean=1)),
    ("접촉 — 팔 앞으로 수평, 검 수평",    dict(arm='ccw',   sword_deg=0,   lean=3, body_dx=2, hair_dx=-2, head_dx=1, front=(+1, 0))),
    ("접촉 홀드",                        dict(arm='ccw',   sword_deg=0,   lean=3, body_dx=2, hair_dx=-1, head_dx=1, front=(+1, 0))),
    ("팔로우스루 — 손 앞아래",            dict(arm='flipH', sword_deg=-30, lean=3, body_dx=2, head_dx=1, front=(+1, 0))),
    ("준비 — 손 앞아래, 검 낮게",         dict(arm='flipH', sword_deg=-35, lean=1, body_dx=1)),
]
# 2타 올려 베기 (96x80): 앞아래에서 위로. 1타의 마지막(flipH)에서 시작
HIT2 = [
    ("준비 — 손 앞아래",                  dict(arm='flipH', sword_deg=-35, lean=1)),
    ("예비 — 웅크리며 검을 뒤아래로 내림",  dict(arm='id',    sword_deg=200, lean=1, upper_dy=2, hair_dx=1)),
    ("예비 홀드",                         dict(arm='id',    sword_deg=205, lean=1, upper_dy=2, hair_dx=1)),
    ("휘두름 — 팔 앞으로, 검 앞위",        dict(arm='ccw',   sword_deg=25,  lean=2, upper_dy=0, body_dx=1)),
    ("접촉 — 팔 위로(스트레치), 검 앞위",  dict(arm='flipV', sword_deg=60,  lean=3, upper_dy=-2, body_dx=2, hair_dx=-2, head_dx=1, front=(+1, 0))),
    ("접촉 홀드",                         dict(arm='flipV', sword_deg=60,  lean=3, upper_dy=-2, body_dx=2, hair_dx=-1, head_dx=1, front=(+1, 0))),
    ("팔로우스루 — 검 머리 뒤로 넘어감",   dict(arm='flipV', sword_deg=110, lean=1, upper_dy=-1, body_dx=1)),
    ("복귀 — 팔 앞으로, 검 앞",            dict(arm='ccw',   sword_deg=10,  lean=1, body_dx=1)),
]
# 3타 내려찍기 (96x80, 오프셋 +16,+16): 머리 뒤에서 앞아래로 + 런지
HIT3 = [
    ("예비 1 — 팔 위로, 검 머리 뒤로",     dict(arm='flipV', sword_deg=110, lean=-2, upper_dy=1, hair_dx=1, head_dx=-1)),
    ("예비 2 — 더 젖히고 웅크림",          dict(arm='flipV', sword_deg=125, lean=-3, upper_dy=2, hair_dx=2, head_dx=-1, body_dx=-1)),
    ("예비 홀드 — 떨림",                   dict(arm='flipV', sword_deg=128, lean=-3, upper_dy=2, hair_dx=2, head_dx=-1, body_dx=-2)),
    ("휘두름 — 팔 앞으로, 검 앞위",         dict(arm='ccw',   sword_deg=35,  lean=3, upper_dy=-1, body_dx=1)),
    ("접촉 — 팔 앞으로 뻗고 검 앞아래로 내려찍음 + 런지", dict(arm='ccw', sword_deg=-50, lean=5, upper_dy=2, body_dx=4, hair_dx=-3, head_dx=1, front=(+5, 0), back=(-4, 0))),
    ("접촉 홀드 — 충격",                   dict(arm='ccw',   sword_deg=-50, lean=5, upper_dy=2, body_dx=5, hair_dx=-2, head_dx=1, front=(+5, 0), back=(-4, 0))),
    ("팔로우스루 — 손 앞아래, 검끝 땅 쪽",   dict(arm='flipH', sword_deg=-30, lean=4, upper_dy=2, body_dx=4, hair_dx=-1, front=(+5, 0), back=(-4, 0))),
    ("복귀 — 몸 세움",                     dict(arm='flipH', sword_deg=-25, lean=2, upper_dy=1, body_dx=2, front=(+2, 0), back=(-2, 0))),
    ("준비 — 검 앞아래",                   dict(arm='id',    sword_deg=-35)),
]
DUR = {"1": [120, 110, 70, 40, 100, 60, 80, 120], "2": [110, 110, 70, 40, 100, 60, 80, 120], "3": [110, 100, 80, 40, 110, 70, 90, 100, 120]}

if __name__ == "__main__":
    sets = [("공격1타_가로베기_파츠리그", HIT1, 96, 80, (16, 16), DUR["1"]), ("공격2타_올려베기_파츠리그", HIT2, 96, 80, (16, 16), DUR["2"]), ("공격3타_내려찍기_파츠리그", HIT3, 96, 80, (16, 16), DUR["3"])]
    chain, durs = [], []
    for name, frs, W, H, off, dur in sets:
        imgs = [frame(W, H, off, sp) for _, sp in frs]
        fn = save_sheet(imgs, name); save_gif(imgs, name, dur); contact_sheet(imgs, os.path.join(SP, name + "_cs.png"), scale=5)
        for (n, sp), f in zip(frs, imgs):
            yy, xx = np.where(alpha(f)); print(f"{name} | {n}: bottom {yy.max()} x {xx.min()}-{xx.max()}")
        for f, d in zip(imgs, dur):
            c = blank(96, 80); paste(c, f, (96 - W) // 2, 80 - H); chain.append(c); durs.append(d)
    save_gif(chain, "공격_3연격_파츠리그", durs)
