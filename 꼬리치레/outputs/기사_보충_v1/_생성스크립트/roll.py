# 구르기 시트 64x64: 예비 웅크림 → 말기 → 회전(90° 단위, 무손실) → 착지 웅크림 → 복귀 → 서기
import numpy as np, os
from kb import *

M = masks()
ys, xs = np.mgrid[0:64, 0:64]
a = alpha(BASE)

HEAD = extract(BASE, a & (ys <= 30) & ~((ys >= 22) & (xs <= 29)))   # 머리(뒷머리 제외)
HAIR = extract(BASE, a & (ys >= 22) & (ys <= 40) & (xs <= 29))        # 뒷머리(끝단 y 41~45는 접어 넣음)
TORSO = extract(BASE, a & (ys >= 31) & (ys <= 51) & ~M['hair_back'])
LEGS = extract(BASE, a & (ys >= 52))
UPPER = extract(BASE, a & ~M['legs'])

def crouch(dy_upper, lean, hair_lift=0):
    """웅크림: 상체 dy만큼 내려앉음(다리 윗부분이 허리 밑으로), 허리 축 전방 기울기, 뒷머리 위로 들림."""
    out = blank()
    up = shear_rows(UPPER, 51, lean, 3)
    if hair_lift:
        hm = alpha(up) & (ys >= 22) & (ys <= 45) & (xs <= 29 + lean // 2)
        hair = extract(up, hm); up[hm] = 0
        lifted = blank()
        for x in range(64):
            col = hair[:, x]
            if not (col[:, 3] > 0).any(): continue
            d = -int(round(hair_lift * max(0, (31 - x)) / 12.0)); d = max(-hair_lift, min(0, d))
            tmp = blank(); tmp[:, x] = col; paste(lifted, tmp, 0, d)
        paste(up, lifted)
    paste(out, LEGS, 0, 0)
    paste(out, up, 0, dy_upper)
    return fill_gaps(out, 1, (16, 52))

def ball():
    """말린 자세: 몸통을 중심에, 다리를 90° 접어 앞으로, 머리를 앞아래로 숙여 몸통을 덮음. 지름 약 34px."""
    b = blank()
    paste(b, TORSO, -4, 6, mask=(ys >= 40))                  # 몸통은 허리 아래만 머리 뒤에 살짝(등 실루엣)
    lg = close_holes(rotate_about(LEGS, 36, 57, 90))         # 다리 접힘: 머리 뒤에서 부츠 끝만 앞아래로 보임
    paste(b, lg, 6, -8)
    paste(b, HAIR, 4, 20)                                    # 뒷머리는 머리와 함께 아래로
    paste(b, HEAD, 4, 22)                                    # 머리 중심 (38,39) — 머리가 몸을 덮어 공 실루엣
    return b

BALL = ball()
BCX, BCY = 34, 44   # 회전 중심

def ball_rot(deg, dx=0):
    """구르는 방향(오른쪽)으로 회전 = 화면상 시계 방향 = deg 음수. 90° 단위는 무손실."""
    r = rotate_about(BALL, BCX, BCY, -deg)
    yy, xx = np.where(alpha(r))
    return shift(r, dx, 62 - yy.max())                      # 공의 최하단을 땅(y 62)에

FRAMES = [
    ("예비 — 웅크림 (상체 3px 아래, 앞으로 3px)", crouch(3, 3)),
    ("말기 — 공 0°, 뒷머리가 위로 (공중 1px)", shift(ball_rot(0), 1, -1)),
    ("구르기 90°", ball_rot(90, 1)),
    ("구르기 180° (머리가 위로)", ball_rot(180, 1)),
    ("구르기 270°", ball_rot(270, 1)),
    ("착지 — 웅크림, 뒷머리 위로 날림 (상체 3px 아래, 앞으로 4px)", crouch(3, 4, hair_lift=5)),
    ("복귀 — 상체 1px 아래", crouch(1, 1)),
    ("서기 (원본)", BASE.copy()),
]

if __name__ == "__main__":
    imgs = [f for _, f in FRAMES]
    p = save_sheet(imgs, '구르기')
    save_gif(imgs, '구르기', [70, 60, 60, 60, 60, 80, 70, 150])
    contact_sheet(imgs, os.path.join(SP, 'roll_contact.png'), scale=4)
    for i, (n, f) in enumerate(FRAMES):
        yy, xx = np.where(alpha(f)); print(i, n, 'top', yy.min(), 'bottom', yy.max(), 'x', xx.min(), xx.max())
    print(p)
