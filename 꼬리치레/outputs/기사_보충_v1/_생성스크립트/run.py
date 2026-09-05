# 달리기 v4 방식 재제작: 걷기 v4 프레임(접지·교차·상승 ×2) 파생 + 전방 기울기 + 보폭 확대 + 상하 바운스
import numpy as np, os
from kb import *

M = masks()
ys, xs = np.mgrid[0:64, 0:64]

def split_legs(legs_img):
    """다리 영역(y>=52)을 뒷다리/앞다리로 분리. 두 다리 사이 빈 열을 기준으로 나눈다."""
    a = alpha(legs_img)
    cols = a[54:63].sum(0)
    # 중앙 부근(x 28~40)에서 비어 있는 열을 찾는다
    gap = [x for x in range(26, 42) if cols[x] == 0]
    if not gap:
        return None, None
    cut = (gap[0] + gap[-1]) // 2
    back = despeckle(extract(legs_img, a & (xs <= cut)), 8)
    front = despeckle(extract(legs_img, a & (xs > cut)), 8)
    return back, front

# (걷기 프레임 index, 역할, 몸 상하 오프셋, 뒷다리 dx, 뒷다리 dy, 앞다리 dx, 기울기 픽셀)
PLAN = [
    (0, 'contact', 0, -3, -2, +2, 6),
    (2, 'pass',   -1,  0,  0,  0, 6),
    (3, 'up',     -3, -3, -2, +2, 7),
    (4, 'contact', 0, -3, 0, +2, 6),   # f4는 뒷발이 땅에 붙은 접지 → 들지 않음
    (6, 'pass',   -1,  0,  0,  0, 6),
    (7, 'up',     -3, -3, -2, +2, 7),
]

frames = []
for wi, role, dy, bdx, bdy, fdx, lean in PLAN:
    src = F[wi]
    a = alpha(src)
    hair_m = a & (ys >= 22) & (ys <= 45) & (xs <= 29)
    legs_m = a & (ys >= 52)
    upper_m = a & ~hair_m & ~legs_m
    hair = extract(src, hair_m)
    legs = extract(src, legs_m)
    upper = extract(src, upper_m)

    # 상체 전방 기울기: 허리(y 51) 고정, 머리 꼭대기(y 3)가 lean px 앞으로
    upper_s = shear_rows(upper, pivot_y=51, top_shift=lean, y_min=3)
    # 뒷머리: 머리와 붙는 윗부분은 같이 가고, 끝(y 41)은 남아 뒤로 흘림
    head_shift_at22 = int(round(lean * (51 - 22) / 48))
    hair_s = shear_rows(hair, pivot_y=51, top_shift=lean, y_min=3)
    # 머리끝 뒤로 흘림: y 34 이하 행을 1px 뒤로
    tail = extract(hair_s, alpha(hair_s) & (ys >= 34))
    hair_s[alpha(hair_s) & (ys >= 34)] = 0
    paste(hair_s, tail, -1, 0)

    # 다리 보폭 확대 (contact/up)
    out = blank()
    if role == 'pass':
        legs_o = legs
    else:
        back, front = split_legs(legs)
        if back is None:
            legs_o = legs
        else:
            legs_o = blank()
            paste(legs_o, back, bdx, bdy)
            paste(legs_o, front, fdx, 0)
    # 합성 순서: 뒷머리 → 다리 → 상체(허리/치마가 다리 윗부분을 덮음)
    paste(out, hair_s, 0, dy)
    paste(out, legs_o, 0, dy)
    paste(out, upper_s, 0, dy)
    out = fill_gaps(out, 2, (20, 44))
    out = despeckle(out, 3, 50)
    frames.append(out)

p = save_sheet(frames, '달리기')
g = save_gif(frames, '달리기', 70)
contact_sheet(frames, os.path.join(SP, 'run_contact.png'), scale=5)
print(p); print(g)
for i, f in enumerate(frames):
    yy, xx = np.where(alpha(f)); print(i, 'top', yy.min(), 'bottom', yy.max(), 'x', xx.min(), xx.max())
