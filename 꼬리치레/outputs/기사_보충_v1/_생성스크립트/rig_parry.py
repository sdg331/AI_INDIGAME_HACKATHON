# 패링 · 방어(가드) — 파츠 리그: 파츠분할 7파츠(앞팔 밑 채움) + 검. 앞팔은 무손실 변환만. 팔을 그리지 않는다.
# 근거: 전체문서 5장 방어 — 패리(정해진 시간 안 성공, 피해 0) / 가드(시간 초과, 피해 80% 감소). 판정 시간은 플머.
import os
import numpy as np
from PIL import Image
from kb import *
from rig_combo import frame, hand_after, P, SX, SY

W, H, OFF = 96, 80, (16, 16)   # 파츠 리그 공격 · 방어 공통 캔버스(스킬과 동일). 발바닥 y 78

# 방어 자세 공통: 앞팔 90° 반시계(팔 앞으로 수평, 손 (51,34)) + 검 78°(날을 세워 얼굴 · 가슴 앞을 막음), 다리 벌려 버팀
GUARD = dict(arm='ccw', sword_deg=78, lean=-1, front=(+2, 0), back=(-2, 0))

PARRY = [
    ("준비 — 검 앞아래",                          dict(arm='id',    sword_deg=-35)),
    ("방어 진입 — 검을 앞으로 올림(예비)",          dict(arm='flipH', sword_deg=55,  lean=+1, front=(+1, 0))),
    ("방어 자세 — 날을 세움. 패리 판정 구간(홀드)",  dict(**GUARD)),
    ("패리 충격 — 검이 위로 튕겨 오름, 몸 뒤로 눌림", dict(arm='flipV', sword_deg=150, lean=-3, upper_dy=+1, hair_dx=+2, head_dx=-1, front=(+2, 0), back=(-2, 0))),
    ("반동 — 검이 앞으로 되돌아옴(오버슈트), 반격 준비", dict(arm='ccw', sword_deg=45, lean=+2, upper_dy=-1, hair_dx=-1, head_dx=+1, body_dx=+1, front=(+2, 0), back=(-2, 0))),
    ("정착 — 방어 자세로 되돌아옴",                 dict(arm='ccw',   sword_deg=70,  lean=0, front=(+2, 0), back=(-2, 0))),
    ("복귀 — 검 내림",                             dict(arm='flipH', sword_deg=-30, lean=+1)),
    ("준비 — 검 앞아래",                          dict(arm='id',    sword_deg=-35)),
]
GUARD_HIT = [
    ("준비",                                      dict(arm='id',    sword_deg=-35)),
    ("방어 진입",                                 dict(arm='flipH', sword_deg=55,  lean=+1, front=(+1, 0))),
    ("방어 자세 — 홀드(우클릭 유지 동안 루프)",      dict(**GUARD)),
    ("가드 피격 1 — 뒤로 1px 밀림, 검 조금 젖혀짐",  dict(arm='ccw',   sword_deg=88,  lean=-2, upper_dy=+1, hair_dx=+1, body_dx=-1, front=(+2, 0), back=(-2, 0))),
    ("가드 피격 2 — 버팀(복원 중)",                dict(arm='ccw',   sword_deg=82,  lean=-1, hair_dx=+1, front=(+2, 0), back=(-2, 0))),
    ("방어 자세 — 복원",                          dict(**GUARD)),
    ("해제 — 검 내림",                             dict(arm='flipH', sword_deg=-30, lean=+1)),
    ("준비",                                      dict(arm='id',    sword_deg=-35)),
]

def blade_info(spec):
    """접촉 좌표(96x80 캔버스): 손 픽셀, 날 중간, 날 끝 — 패리 섬광 이펙트 배치용."""
    import math
    hx, hy = hand_after(spec['arm']); lean = spec.get('lean', 0); sh = int(round(lean * (51 - SY) / 48))
    ox = OFF[0] + spec.get('body_dx', 0) + sh; oy = OFF[1] + spec.get('upper_dy', 0)
    hx, hy = hx + ox, hy + oy; a = math.radians(spec['sword_deg']); L = 20
    tip = (round(hx + math.cos(a) * L), round(hy - math.sin(a) * L)); mid = (round(hx + math.cos(a) * L * 0.55), round(hy - math.sin(a) * L * 0.55))
    return (hx, hy), mid, tip

if __name__ == "__main__":
    for name, frs, dur in (("패링_파츠리그", PARRY, [80, 50, 110, 60, 80, 90, 90, 120]), ("방어_파츠리그", GUARD_HIT, [80, 50, 120, 60, 70, 100, 90, 120])):
        imgs = [frame(W, H, OFF, sp) for _, sp in frs]
        save_sheet(imgs, name); save_gif(imgs, name, dur); contact_sheet(imgs, os.path.join(SP, name + "_cs.png"), scale=5)
        for (n, sp), f in zip(frs, imgs):
            yy, xx = np.where(alpha(f)); print(f"{name} | {n}: bottom {yy.max()} x {xx.min()}-{xx.max()} | 손·날중간·날끝 {blade_info(sp)}")
