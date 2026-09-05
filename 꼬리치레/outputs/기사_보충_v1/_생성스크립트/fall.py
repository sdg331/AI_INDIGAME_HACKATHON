# 낙사 복귀 시트 64x64: 낙하 시작 → 화면 밖 → 제자리 깜빡임 등장 → 착지 → 서기
import numpy as np, os
from kb import *

M = masks()
ys, xs = np.mgrid[0:64, 0:64]

def falling_body(dy_body, legs_src=F[3], hair_lift=4):
    """낙하 자세: 뒷머리가 위로 날리고(끝이 더 높이), 다리는 걷기 상승 프레임(한쪽 무릎 굽힘) 재사용."""
    hair = extract(BASE, M['hair_back'])
    upper = extract(BASE, alpha(BASE) & ~M['hair_back'] & ~M['legs'])
    legs = extract(legs_src, alpha(legs_src) & (ys >= 52))
    out = blank()
    # 뒷머리: 몸에서 멀수록(x 작을수록) 더 높이 들림
    hair_up = blank()
    for x in range(64):
        col = hair[:, x]
        if not (col[:, 3] > 0).any():
            continue
        d = -int(round(hair_lift * (30 - x) / 12.0))
        d = max(-hair_lift, min(0, d))
        if x >= 30: d = 0
        tmp = blank(); tmp[:, x] = col
        paste(hair_up, tmp, 0, d)
    paste(out, hair_up, 0, dy_body)
    paste(out, legs, 0, dy_body)
    paste(out, upper, 0, dy_body)
    out = fill_gaps(out, 1, (16, 52))
    # 뒤로 젖혀지며 떨어짐: 발 축으로 머리가 3px 뒤로
    out = shear_rows(out, 62 + dy_body, -3, 3 + dy_body)
    return out

def silhouette(img, color=WHITE):
    o = blank(); o[alpha(img)] = color; return o

def dither(img, offset=0):
    """50% 체커보드 디더로 '반투명' 표현(알파 없이)."""
    o = img.copy()
    m = ((ys + xs + offset) % 2 == 0)
    o[m] = 0
    return o

def squash(dy_upper):
    hair = extract(BASE, M['hair_back']); legs = extract(BASE, M['legs'])
    upper = extract(BASE, alpha(BASE) & ~M['hair_back'] & ~M['legs'])
    out = blank(); paste(out, hair, 0, dy_upper); paste(out, legs, 0, 0); paste(out, upper, 0, dy_upper)
    return fill_gaps(out, 1, (16, 52))

empty = blank()
frames = [
    ('낙하 시작 (머리 날림, 무릎 굽힘)',      falling_body(0, hair_lift=7)),
    ('낙하 중 (아래로 12px)',                  falling_body(12, hair_lift=8)),
    ('낙하 (아래로 30px, 머리만 보임)',        falling_body(30, hair_lift=9)),
    ('화면 밖 — 빈 프레임 (홀드용)',           empty),
    ('등장 깜빡임 1 — 흰 실루엣 (3px 위)',     shift(silhouette(BASE), 0, -3)),
    ('등장 깜빡임 2 — 빈 프레임',              empty),
    ('등장 깜빡임 3 — 50% 디더 (3px 위)',      shift(dither(BASE), 0, -3)),
    ('등장 깜빡임 4 — 흰 실루엣 (2px 위)',     shift(silhouette(BASE), 0, -2)),
    ('등장 완료 — 원본 (2px 위)',              shift(BASE, 0, -2)),
    ('착지 눌림 (상체 2px 아래)',              squash(2)),
    ('서기 (원본)',                            BASE.copy()),
]
names = [n for n, _ in frames]; imgs = [f for _, f in frames]
p = save_sheet(imgs, '낙사복귀')
dur = [80, 60, 60, 220, 60, 60, 60, 60, 90, 80, 300]
g = save_gif(imgs, '낙사복귀', dur)
contact_sheet(imgs[:6], os.path.join(SP, 'fall_a.png'), scale=4)
contact_sheet(imgs[6:], os.path.join(SP, 'fall_b.png'), scale=4)
print(p); print(g)
for i, (n, f) in enumerate(frames):
    a = alpha(f)
    if a.any():
        yy, xx = np.where(a); print(i, n, 'top', yy.min(), 'bottom', yy.max())
    else:
        print(i, n, 'EMPTY')
