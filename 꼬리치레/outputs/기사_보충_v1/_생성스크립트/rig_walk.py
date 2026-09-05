# 파츠 리그 걷기 v1: 파츠분할/01~07 PNG만 사용, 무손실 변환(이동 · 행 이동 기울이기)만. SLYNYRD Pixelblog 50 8프레임 구성
# 접지(가장 낮음) → 눌림 → 교차(가장 높음) → 상승 × 좌우. 팔은 반대쪽 다리와 함께 흔들리고 뒷머리는 1프레임 늦게 따라온다.
import os
import numpy as np
from PIL import Image
from kb import *

PD = os.path.join(OUT, "파츠분할")
def load_part(name):
    return np.array(Image.open(os.path.join(PD, name + ".png")).convert("RGBA"))
P = {k: load_part(k) for k in ["01_뒷머리", "02_뒷다리", "03_앞다리", "04_허리치마", "05_몸통", "06_앞팔", "07_머리"]}
PX = {k: int(alpha(v).sum()) for k, v in P.items()}

def tilt(img, top_y, bottom_y, k):
    """top_y 행은 0, bottom_y 행은 k px 이동하는 행 단위 기울이기(픽셀 보존). 다리 · 팔 스윙용."""
    out = blank(); a = alpha(img)
    for y in range(64):
        if not a[y].any(): continue
        t = (y - top_y) / max(1, bottom_y - top_y); s = int(round(k * max(0.0, min(1.0, t))))
        row = img[y]
        if s > 0: out[y, s:] = row[:-s]
        elif s < 0: out[y, :s] = row[-s:]
        else: out[y] = row
    return out

LEG_TOP, LEG_BOT = 52, 62
ARM_TOP, ARM_BOT = 31, 49

def frame(s):
    """s: body_dy, back=(k, dy), front=(k, dy), arm_k, hair_dx, hair_dy, head_dx. k = 발/손이 이동하는 px(+앞)."""
    c = blank(); bdy = s["body_dy"]
    paste(c, P["01_뒷머리"], s.get("hair_dx", 0), bdy + s.get("hair_dy", 0))
    bk, bdy_leg = s["back"]; fk, fdy_leg = s["front"]
    paste(c, tilt(P["02_뒷다리"], LEG_TOP, LEG_BOT, bk), 0, bdy_leg)
    paste(c, tilt(P["03_앞다리"], LEG_TOP, LEG_BOT, fk), 0, fdy_leg)
    paste(c, P["04_허리치마"], 0, bdy)
    paste(c, P["05_몸통"], 0, bdy)
    paste(c, P["07_머리"], s.get("head_dx", 0), bdy)
    paste(c, tilt(P["06_앞팔"], ARM_TOP, ARM_BOT, s["arm_k"]), 0, bdy)
    c = fill_gaps(c, 1, (16, 52))
    c[63, :] = 0
    return c

# 근다리(앞다리)가 앞으로 나가는 접지 A부터. 뒷다리는 뒤에서 앞으로 스윙. 팔(근팔)은 앞다리와 반대.
FRAMES = [
    ("접지 A — 앞다리 앞(뒤꿈치), 뒷다리 뒤(발끝). 가장 낮음", dict(body_dy=+1, front=(+4, 0), back=(-4, 0), arm_k=-3, hair_dx=0, hair_dy=0, head_dx=0)),
    ("눌림 A — 앞다리 평발, 뒷다리 뒤꿈치 들림",              dict(body_dy=+1, front=(+2, 0), back=(-3, -1), arm_k=-2, hair_dx=0, hair_dy=0)),
    ("교차 A — 뒷다리가 들려 지나감. 가장 높음",              dict(body_dy=-1, front=(0, 0), back=(0, -3), arm_k=0, hair_dx=-1, hair_dy=0)),
    ("상승 A — 뒷다리가 앞으로 뻗어 내려옴",                  dict(body_dy=0, front=(-2, 0), back=(+3, -1), arm_k=+2, hair_dx=-1, hair_dy=0)),
    ("접지 B — 뒷다리 앞(뒤꿈치), 앞다리 뒤(발끝). 가장 낮음", dict(body_dy=+1, front=(-4, 0), back=(+4, +1), arm_k=+3, hair_dx=0, hair_dy=0)),
    ("눌림 B — 뒷다리 평발, 앞다리 뒤꿈치 들림",              dict(body_dy=+1, front=(-3, -1), back=(+2, +1), arm_k=+2, hair_dx=0, hair_dy=0)),
    ("교차 B — 앞다리가 들려 지나감. 가장 높음",              dict(body_dy=-1, front=(0, -3), back=(0, +1), arm_k=0, hair_dx=-1, hair_dy=0)),
    ("상승 B — 앞다리가 앞으로 뻗어 내려옴",                  dict(body_dy=0, front=(+3, -1), back=(-2, +1), arm_k=-2, hair_dx=-1, hair_dy=0)),
]

if __name__ == "__main__":
    imgs = []
    for n, s in FRAMES:
        f = frame(s); imgs.append(f)
        # 파츠 픽셀 보존 검사(전체 픽셀 수 = 파츠 합, 겹침으로 줄 수는 있음)
        yy, xx = np.where(alpha(f)); print(n, "| top", yy.min(), "bottom", yy.max(), "px", int(alpha(f).sum()))
    save_sheet(imgs, "걷기_파츠리그"); save_gif(imgs, "걷기_파츠리그", 110)
    contact_sheet(imgs, os.path.join(SP, "rigwalk_cs.png"), scale=5)
    # 1x · 2x 스트립
    from PIL import ImageDraw
    rows = []
    for sc in (1, 2, 3):
        st = Image.new("RGBA", (64 * 8 * sc, 64 * sc), (51, 43, 47, 255))
        for i, f in enumerate(imgs): st.alpha_composite(Image.fromarray(f).resize((64 * sc, 64 * sc), Image.NEAREST), (i * 64 * sc, 0))
        rows.append(st)
    Wm = max(r.width for r in rows); Hm = sum(r.height + 4 for r in rows); big = Image.new("RGBA", (Wm, Hm), (30, 30, 30, 255)); y = 0
    for r in rows: big.alpha_composite(r, (0, y)); y += r.height + 4
    big.save(os.path.join(SP, "rigwalk_1x.png"))
