# 고블린 v2.1 대기(4) · 피격(4): v1 프레임에 흉부 보정(gob_chest)만 적용. 포즈·타이밍은 v1과 동일.
# 대기: 1 기본 → 2 상체(y ≤ 32) 1px 위로 늘림 → 3 동일 → 4 기본.  피격: 1 플래시(v1) → 2 · 3 피격 포즈(v1) → 4 대기 기본.
import os
import numpy as np
from gob_lib import *
from gob_chest import fix_chest

SP = os.path.dirname(os.path.abspath(__file__))
I1 = [snap(f) for f in load_sheet("고블린_대기_시트_64x64x4.png", 64, 4)]
H1 = [f for f in load_sheet("고블린_피격_시트_64x64x4.png", 64, 4)]   # 플래시 프레임은 팔레트 밖 2색(v1 그대로)이라 snap 하지 않는다

BASE, CHEST_MASK = fix_chest(I1[0])

def stretch(f):
    """v1 대기 2·3번과 같은 변환: y ≤ 32 행을 1px 위로(33행 유지 = 1px 늘림)."""
    out = f.copy(); out[0:33] = f[1:34]; return out

IDLE = [BASE, stretch(BASE), stretch(BASE), BASE]
HIT = [H1[0], snap(H1[1]), snap(H1[2]), BASE]

if __name__ == "__main__":
    # v1 파생 관계 검증(입력이 바뀌면 여기서 멈춘다)
    assert (I1[1] == stretch(I1[0])).all() and (I1[3] == I1[0]).all(), "v1 대기 파생 관계가 다르다"
    assert (snap(H1[3]) == I1[0]).all(), "v1 피격 4번이 대기 1번과 다르다"
    fn1 = save_sheet(IDLE, "대기"); save_gif(IDLE, "대기", 180)
    fn2 = save_sheet(HIT, "피격"); save_gif(HIT, "피격", 100)
    contact_sheet(IDLE + HIT, os.path.join(SP, "gih.png"), scale=5)
    print("흉부 채움 픽셀:", int(CHEST_MASK.sum()), "extra:", len(palette_check(BASE)))
    print(fn1, fn2)
