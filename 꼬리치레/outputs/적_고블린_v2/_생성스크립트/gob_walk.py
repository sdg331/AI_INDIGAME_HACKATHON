# 고블린 v2 걷기: v1 이동 2번(원본 2) 상체 + 다리 3형(직립·뒤로 뻗음·들림) 재조합. 접지·눌림·교차·상승 × 좌우 = 8프레임
import os, sys
import numpy as np
from gob_lib import *

SP = os.path.dirname(os.path.abspath(__file__))
walk_v1 = load_sheet("고블린_이동_시트_64x64x8.png", 64, 8)
idle_v1 = load_sheet("고블린_대기_시트_64x64x4.png", 64, 4)
BASE = snap(walk_v1[1])          # 원본 2: 배경 구멍 없음, 근다리 들린 자세
IDLE = snap(idle_v1[0])
ys, xs = np.mgrid[0:64, 0:64]

# ---- 파츠 ----
a = alpha(BASE)
UPPER = extract(BASE, a & (ys <= 50))                       # 머리·상체·팔·허리천(y<=50)
L_BACK = extract(BASE, a & (ys >= 51) & (xs <= 31))         # 원다리: 뒤로 뻗은 다리 + 발 (x 16~30, y 51~61)
L_LIFT = extract(BASE, a & (ys >= 51) & (xs >= 32))         # 근다리: 들린 다리 (x 33~44, y 51~56)
ai = alpha(IDLE)
hole = remove_component_of_color(IDLE, PAL[23], rect(IDLE, 26, 39, 50, 62), 30)   # 대기 다리 사이 배경 구멍 제거
L_STRAIGHT = extract(hole, alpha(hole) & (ys >= 48) & (xs >= 33))                 # 직립 다리 (x 34~46, y 48~62)

# 상체 안의 부위(어깨축 회전·팔로우스루용)
DAGGER = a & (ys <= 33) & (xs <= 18)                        # 단검 날 + 손 (어깨축 회전: 위아래 1px)
FIST_L = a & (ys >= 38) & (ys <= 50) & (xs <= 17)           # 근팔 주먹(늘어진 팔)
FIST_R = a & (ys >= 39) & (ys <= 50) & (xs >= 41)           # 원팔 주먹
EAR_R = a & (ys >= 26) & (ys <= 31) & (xs >= 45)            # 오른귀 끝
EAR_L = a & (ys >= 21) & (ys <= 27) & (xs >= 18) & (xs <= 20)

# ---- 다리를 픽셀 단위로 직접 그린다 (팔레트 인덱스: 3 밝은 초록, 6 중간, 9 어두운 초록, K 초록 외곽 / D·E·J 갈색 부츠, M 외곽) ----
C = {k: PAL[i] for k, i in dict(g3=3, g6=6, g9=9, gK=20, bD=13, bE=14, bJ=19, bM=22).items()}

def put(canvas, x, y, col):
    if 0 <= x < 64 and 0 <= y < 64:
        canvas[y, x, :3] = col; canvas[y, x, 3] = 255

def draw_leg(canvas, hip, knee, ankle, boot="flat", boot_y=None):
    """hip→knee→ankle 폴리라인을 폭 5 초록 다리로, 그 아래 8×4 갈색 부츠. boot: flat / toe(뒤꿈치 들림) / heel(발끝 들림). boot_y = 부츠 윗행(기본 ankle.y+1)."""
    (hx, hy), (kx, ky), (ax, ay) = hip, knee, ankle
    for y in range(hy, ay + 1):
        if y <= ky:
            t = (y - hy) / max(1, ky - hy); cx = hx + (kx - hx) * t
        else:
            t = (y - ky) / max(1, ay - ky); cx = kx + (ax - kx) * t
        c = int(round(cx))
        put(canvas, c - 2, y, C["g3"]); put(canvas, c - 1, y, C["g3"]); put(canvas, c, y, C["g6"]); put(canvas, c + 1, y, C["g9"]); put(canvas, c + 2, y, C["gK"])
        if y == ky:  # 무릎 하이라이트
            put(canvas, c - 1, y, C["g6"])
    by = ay + 1 if boot_y is None else boot_y
    c = ax
    if boot == "flat":
        rows = [(c - 3, c + 4), (c - 3, c + 4), (c - 2, c + 4)]
    elif boot == "toe":      # 뒤꿈치 들려 발끝만 땅
        rows = [(c - 1, c + 3), (c - 2, c + 4), (c, c + 4)]
    else:                    # heel: 뒤꿈치 먼저 닿음, 발끝 들림
        rows = [(c - 3, c + 2), (c - 3, c + 4), (c - 3, c + 2)]
    cols = [C["bD"], C["bE"], C["bJ"]]
    for r, ((x0, x1), col) in enumerate(zip(rows, cols)):
        y = by + r
        for x in range(x0, x1 + 1):
            put(canvas, x, y, col)
        put(canvas, x1 + 1, y, C["bM"]); put(canvas, x0 - 1, y, C["bM"])
    # 밑창 외곽
    x0, x1 = rows[-1]
    for x in range(x0 - 1, x1 + 2): put(canvas, x, by + 3, C["bM"])
    return canvas

HIP_FAR, HIP_NEAR, HIP_Y = 28, 37, 51
# (역할, 상체 dy, 원다리(hip,knee,ankle,boot,boot_y), 근다리(...))
PLAN = [
    ("접지A", 0, ((HIP_FAR, HIP_Y), (24, 55), (21, 58), "toe", None),   ((HIP_NEAR, HIP_Y), (40, 55), (43, 58), "flat", None)),
    ("눌림A", +1, ((HIP_FAR, HIP_Y), (26, 55), (25, 58), "flat", None),  ((HIP_NEAR, HIP_Y), (39, 55), (40, 58), "flat", None)),
    ("교차A", 0, ((HIP_FAR, HIP_Y), (31, 54), (30, 55), "flat", 56),     ((HIP_NEAR, HIP_Y), (37, 55), (37, 58), "flat", None)),
    ("상승A", -1, ((HIP_FAR, HIP_Y), (32, 54), (35, 57), "heel", 57),    ((HIP_NEAR, HIP_Y), (36, 55), (35, 58), "toe", None)),
    ("접지B", 0, ((HIP_FAR, HIP_Y), (32, 55), (35, 58), "flat", None),   ((HIP_NEAR, HIP_Y), (34, 55), (31, 58), "toe", None)),
    ("눌림B", +1, ((HIP_FAR, HIP_Y), (30, 55), (31, 58), "flat", None),  ((HIP_NEAR, HIP_Y), (35, 55), (34, 58), "flat", None)),
    ("교차B", 0, ((HIP_FAR, HIP_Y), (28, 55), (28, 58), "flat", None),   ((HIP_NEAR, HIP_Y), (39, 54), (38, 55), "flat", 56)),
    ("상승B", -1, ((HIP_FAR, HIP_Y), (27, 55), (26, 58), "toe", None),   ((HIP_NEAR, HIP_Y), (41, 54), (44, 57), "heel", 57)),
]

def build():
    frames = []; prev_dy = 0
    for i, (name, dy, far, near) in enumerate(PLAN):
        out = blank()
        # 다리: 원다리 먼저(뒤), 근다리 위(앞). 발은 땅(y 62)에 고정, 상체만 바운스
        draw_leg(out, *far); draw_leg(out, *near)
        # 상체: 바운스 dy
        up = UPPER.copy()
        # 어깨축 팔 회전: 단검(근팔) ↕1, 원팔 주먹 반대
        arm = -1 if i in (0, 7) else (+1 if i in (3, 4) else 0)
        dag = extract(up, DAGGER); up[DAGGER] = 0; paste(up, dag, 0, arm)
        fl = extract(up, FIST_L); up[FIST_L] = 0; paste(up, fl, 0, arm)
        fr = extract(up, FIST_R); up[FIST_R] = 0; paste(up, fr, 0, -arm)
        # 귀 팔로우스루: 머리 dy 변화의 반대로 1프레임 늦게
        ear_dy = prev_dy - dy
        for em in (EAR_R, EAR_L):
            e = extract(up, em); up[em] = 0; paste(up, e, 0, ear_dy)
        up = fill_gaps(up, 1, (10, 51))
        paste(out, up, 0, dy)
        out = snap(out)
        frames.append(out); prev_dy = dy
    return frames

if __name__ == "__main__":
    frames = build()
    fn = save_sheet(frames, "이동"); g = save_gif(frames, "이동", 110)
    contact_sheet(frames[:4], os.path.join(SP, "gw_a.png"), scale=6); contact_sheet(frames[4:], os.path.join(SP, "gw_b.png"), scale=6)
    for i, f in enumerate(frames): print(i, PLAN[i][0], extents(f), "extra colors:", len(palette_check(f)))
    print(fn)
