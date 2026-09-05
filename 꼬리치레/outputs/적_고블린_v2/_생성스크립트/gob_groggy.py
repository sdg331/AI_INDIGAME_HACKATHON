# 고블린 v2 그로기 64x64: 진입 3(v1) → 멈춤(직접 그림: 무릎 굽힘 + 고개 숙임 + 단검 늘어짐) → 유지 2. 명도 조정 없음(팔레트 24색 유지)
import os
import numpy as np
from gob_lib import *

SP = os.path.dirname(os.path.abspath(__file__))
G1 = [snap(f) for f in load_sheet("고블린_그로기_시트_64x64x6.png", 64, 6)]
H1 = [snap(f) for f in load_sheet("고블린_피격_시트_64x64x4.png", 64, 4)]
I1 = [snap(f) for f in load_sheet("고블린_대기_시트_64x64x4.png", 64, 4)]
ys, xs = np.mgrid[0:64, 0:64]

HIT = shift(H1[2], 1, 0)          # v1 피격 3번 = 피격 포즈 dx -1 → 원위치
IDLE = I1[0]
ai = alpha(IDLE)
DAGGER = extract(IDLE, ai & (xs <= 19) & (ys <= 33))       # 대기 포즈의 단검(날+손잡이)

def stopped(sag=0):
    m = alpha(HIT)
    head = m & (ys <= 38)
    upper = m & (ys <= 50)
    legs = extract(HIT, m & (ys >= 51))
    body = extract(HIT, upper & ~head)
    hd = extract(HIT, head)
    out = blank()
    paste(out, legs, 0, 0)
    # 무릎 굽힘: 상체 3px 내려앉음(다리 윗부분이 허리 밑으로 들어감)
    paste(out, body, 0, 3)
    # 고개 숙임: 머리 2px 더 내려가고 앞으로 2px 기울임
    hd = shear_rows(hd, 38, 2, 8)
    paste(out, hd, 0, 5)
    out = fill_gaps(out, 1, (8, 52))
    # 단검 든 손이 늘어짐: 단검을 180° 돌려 칼끝이 아래로, 왼손(x 5~9, y 40~47) 아래에 매달림
    dag = rotate_about(DAGGER, 14, 24, 180)
    dag = close_holes(dag)
    e = extents(dag)
    # 손잡이(회전 후 위쪽)를 손 위치 (8, 47+3)에 맞춤
    paste(out, dag, 7 - (e[2] + e[3]) // 2, 44 - e[0] + sag)
    out[63, :] = 0
    return snap(out)

S0 = stopped(0); S1 = stopped(1)
FRAMES = [
    ("진입1 — 앞으로 쏠림 (v1)", G1[0]),
    ("진입2 — 뒤로 젖힘 (v1)", G1[1]),
    ("진입3 — 가라앉음 (v1)", G1[2]),
    ("멈춤 — 무릎 굽힘·고개 숙임·단검 늘어짐 (직접)", S0),
    ("유지1", S0),
    ("유지2 — 단검 손 1px 더 늘어짐", S1),
]

if __name__ == "__main__":
    frames = [f for _, f in FRAMES]
    fn = save_sheet(frames, "그로기"); save_gif(frames, "그로기", [120, 120, 150, 400, 400, 400])
    contact_sheet(frames, os.path.join(SP, "gg.png"), scale=5)
    for i, (n, f) in enumerate(FRAMES): print(i, n, extents(f), "extra:", len(palette_check(f)))
    print(fn)
