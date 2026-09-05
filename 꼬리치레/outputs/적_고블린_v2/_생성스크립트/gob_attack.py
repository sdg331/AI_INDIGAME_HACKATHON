# 고블린 v2 공격 80x64: 서기 → 예고(실제 백스윙 3장, 직접 그림) → 스미어 → 접촉 → 홀드 → 팔로우스루(직접 그림) → 회수 → 서기 = 11프레임
import os
import numpy as np
from gob_lib import *
from gob_chest import fix_chest
from gob_attack_src import attack_sprite, place

SP = os.path.dirname(os.path.abspath(__file__))
A1 = [snap(f) for f in load_sheet("고블린_공격_시트_80x64x10.png", 80, 10)]
ys, xs = np.mgrid[0:64, 0:80]
BLACK = PAL[23]

# 서기 = v1 대기 1번을 x+8 옮긴 것. 흉부 조끼 채움 + 다리 사이 배경 구멍 제거(gob_chest)
IDLE, CHEST_MASK = fix_chest(A1[0], dx=8)
# v2.3: 접촉 포즈는 v1 시트 대신 원본 「공격」 셀에서 다시 추출(gob_attack_src — 조끼·몸통이 살아 있음). 변형 값은 v1 과 동일(스미어 가로 1.12 · 기울임 3, 회수 가로 0.96), 위치만 2px 왼쪽(칼끝 캔버스 밖 방지)
_SP, _AX = attack_sprite()
SMEAR   = place(_SP, _AX, dx=-1, sx=1.12, shear=3)
CONTACT = place(_SP, _AX, dx=2)
HOLD    = CONTACT
RECOVER = place(_SP, _AX, dx=-1, sx=0.96)

# ---- 참격 호 흔적 제거: 접촉·홀드·스미어 칼끝 부근의 고립 검은 점 ----
def clean_blade_tip(f):
    out = f.copy()
    m = alpha(out)
    # 칼날(크림 #DDD0AC) 영역의 오른쪽 끝에서 칼날에 붙은 최암색 1~2px 제거
    cream = (out[..., :3] == PAL[0]).all(-1) & m
    yy, xx = np.where(cream & (xs >= 50))
    if len(xx):
        tip_x = xx.max()
        region = m & (xs >= tip_x - 2) & (xs <= 79) & (ys >= 30) & (ys <= 60)
        dark = region & (out[..., :3] == BLACK).all(-1)
        out[dark] = 0
    return out

CONTACT_C, HOLD_C, SMEAR_C = clean_blade_tip(CONTACT), clean_blade_tip(HOLD), clean_blade_tip(SMEAR)

# ---- 예고: 웅크림 + 단검 뒤로 빼기 ----
ai = alpha(IDLE)
UPPER = extract(IDLE, ai & (ys <= 50))
LEGS = extract(IDLE, ai & (ys >= 51))
DAG_ARM = ai & (xs <= 27) & (ys <= 37) & ~CHEST_MASK   # 단검 + 손 + 전완 (80캔버스, 대기 포즈). 새로 채운 조끼는 팔과 함께 돌리지 않는다
SHOULDER = (30, 37)

def anticipation(crouch, deg, dx_body, tremble=0):
    up = UPPER.copy()
    arm = extract(up, DAG_ARM); up[DAG_ARM] = 0
    arm_r = close_holes(rotate_about(arm, SHOULDER[0], SHOULDER[1], deg))
    out = blank(80, 64)
    # 다리는 제자리(무릎 굽힘 = 상체가 내려와 다리 윗부분을 덮음)
    paste(out, LEGS, dx_body // 2, 0)
    body = blank(80, 64)
    paste(body, up, 0, 0)
    paste(body, arm_r, 0, 0)
    body = fill_gaps(body, 1, (10, 51))
    # 상체를 뒤로 살짝 기울임(허리 고정) + 웅크림
    body = shear_rows(body, 50, -2, 10)
    paste(out, body, dx_body, crouch + tremble)
    return snap(out)

# ---- 팔로우스루: 접촉 포즈에서 칼날이 더 아래로 지나가고 몸이 앞으로 쏠림 ----
def follow_through(f):
    m = alpha(f)
    blade = m & (xs >= 55) & (ys >= 34) & (ys <= 52)
    body = f.copy(); body[blade] = 0
    bl = extract(f, blade)
    bl_r = close_holes(rotate_about(bl, 55, 39, +30))
    out = blank(80, 64)
    body = shear_rows(body, 50, +2, 0)
    paste(out, body, 1, 1)
    paste(out, bl_r, 1, 1)
    # 발은 땅: 이동으로 y 62를 넘은 픽셀 제거
    out[63, :] = 0
    return snap(out)

FT = follow_through(CONTACT_C)

FRAMES = [
    ("서기",                IDLE),
    ("예고1 — 웅크리기 시작, 단검 뒤로", anticipation(1, -35, -1)),
    ("예고2 — 최대 백스윙",  anticipation(3, -80, -3)),
    ("예고3 — 홀드",          anticipation(3, -80, -3)),
    ("예고4 — 홀드 떨림",     anticipation(3, -84, -2)),
    ("스미어",              SMEAR_C),
    ("접촉",                CONTACT_C),
    ("접촉 홀드",           HOLD_C),
    ("팔로우스루",          FT),
    ("회수",                RECOVER),
    ("서기",                IDLE),
]

if __name__ == "__main__":
    frames = [f for _, f in FRAMES]
    fn = save_sheet(frames, "공격"); save_gif(frames, "공격", [110, 90, 110, 110, 110, 60, 90, 90, 80, 110, 110])
    contact_sheet(frames[:6], os.path.join(SP, "ga_a.png"), scale=5); contact_sheet(frames[6:], os.path.join(SP, "ga_b.png"), scale=5)
    for i, (n, f) in enumerate(FRAMES): print(i, n, extents(f), "extra:", len(palette_check(f)))
    # 칼끝 확인용 확대
    contact_sheet([CONTACT[28:60, 40:80], CONTACT_C[28:60, 40:80]], os.path.join(SP, "ga_tip.png"), scale=12, grid=4, labels=["v1", "v2"])
    print(fn)
