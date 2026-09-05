# 고블린 v2.1 흉부 보정: v1 배경 키잉이 지워 버린 짙은 가죽 조끼를 대기 포즈(64 캔버스, 대기 1번 좌표)에 다시 그린다.
# 원본 `적 2.png` 정면·대기 셀: 어깨끈 아래 가슴~배는 거의 검은 가죽 조끼. v1은 명도 < 48 영역을 배경으로 보고 통째로 지웠다.
# 채움 색은 24색 팔레트 안. v2.1은 원본대로 검은 조끼(M/N/L)였으나 어두운 배경에서 여전히 「빈 것」처럼 읽혀 v2.2에서 **갈색 가죽 조끼**로 바꿨다
# (허리천 · 부츠와 같은 갈색 계열): E(#75513C) 면 · D(#81553D) 왼쪽 림 라이트(광원 = 왼쪽 위, 얼굴 하이라이트와 동일) · G(#694635) 턱 그림자 · J(#5B3E30) 팔 밑 그림자 · M(#372B21) 외곽선.
# 어깨끈(K/L/M)은 그 위에 그대로 남아 어두운 띠로 읽힌다.
import numpy as np
from gob_lib import PAL, alpha, blank, remove_component_of_color, rect

D, E, G, J, L, M, N = PAL[13], PAL[14], PAL[16], PAL[19], PAL[21], PAL[22], PAL[23]
FACE, RIM, SHADE_CHIN, SHADE_ARM, OUTLINE, PIN_COL = E, D, G, J, M, J

# 행별 조끼 범위 (x0, x1 포함). 투명 픽셀만 채운다 — 어깨끈·팔·턱·주머니·벨트는 그대로 위에 남는다.
TORSO = {
    32: [(18, 20)],
    34: [(26, 27), (36, 37)],
    35: [(27, 35)],
    36: [(24, 35)],
    37: [(23, 33)],
    38: [(21, 32), (39, 40)],
    39: [(17, 41)],
    40: [(18, 41)],
    41: [(20, 41)],
    42: [(21, 41)],
    43: [(23, 41)],
    44: [(24, 41)],
}
# 전완과 어깨끈 사이 바늘구멍(y 35~38, x 8~27, 폭 ≤ 4): 팔 밑 그림자 N
PIN_ROWS, PIN_X, PIN_GAP = (35, 38), (8, 27), 4
LEG_HOLE = (26, 39, 50, 62)   # 다리 사이 배경 구멍(#1A120F 큰 덩어리) — x0, x1, y0, y1


def fix_chest(frame, dx=0, close_leg_hole=True):
    """대기 1번 포즈 프레임(64 또는 80 캔버스, 몸이 dx만큼 오른쪽으로 옮겨진 상태)의 흉부를 채운다.
    반환: (수정 프레임, 조끼 면 마스크 — 팔 회전에서 제외할 픽셀)."""
    out = frame.copy()
    a = alpha(out)
    H, W = a.shape
    fill = np.zeros((H, W), bool)
    for y, spans in TORSO.items():
        for x0, x1 in spans:
            xs = np.arange(x0 + dx, x1 + dx + 1)
            xs = xs[(xs >= 0) & (xs < W)]
            fill[y, xs] |= ~a[y, xs]
    pin = np.zeros((H, W), bool)
    for y in range(PIN_ROWS[0], PIN_ROWS[1] + 1):
        x = PIN_X[0] + dx
        while x <= PIN_X[1] + dx and x < W:
            if not a[y, x]:
                x0 = x
                while x < W and not a[y, x]: x += 1
                if x0 > 0 and x < W and a[y, x0 - 1] and a[y, x] and (x - x0) <= PIN_GAP and x0 >= PIN_X[0] + dx:
                    pin[y, x0:x] = True
            else:
                x += 1
    fill &= ~pin
    # ---- 색 ----
    out[fill, :3] = FACE; out[fill, 3] = 255
    out[pin, :3] = PIN_COL; out[pin, 3] = 255
    a2 = alpha(out)
    # 외곽선: 채운 픽셀 중 상하좌우에 투명이 있으면 N
    edge = np.zeros_like(fill)
    for dy, dxx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        s = np.zeros_like(a2); 
        ys0, ys1 = max(0, dy), H + min(0, dy); xs0, xs1 = max(0, dxx), W + min(0, dxx)
        s[ys0:ys1, xs0:xs1] = a2[ys0 - dy:ys1 - dy, xs0 - dxx:xs1 - dxx]
        edge |= fill & ~s
    out[edge, :3] = OUTLINE
    # 턱 그림자: y 34~35 채움 전부, y 36 은 오른쪽 절반
    ys, xs = np.mgrid[0:H, 0:W]
    shade = fill & (((ys <= 35)) | ((ys == 36) & (xs >= 30 + dx)))
    out[shade & ~edge, :3] = SHADE_CHIN
    # 오른팔(주먹 든 팔) 밑 그림자: x 40~41, y 39~43
    arm_sh = fill & (xs >= 40 + dx) & (xs <= 41 + dx) & (ys >= 39) & (ys <= 43)
    out[arm_sh & ~edge, :3] = SHADE_ARM
    # 림 라이트: y 39~43 왼쪽 외곽선 바로 안쪽 1px
    for y in range(39, 44):
        row = np.where(fill[y] & ~edge[y])[0]
        if len(row): out[y, row.min(), :3] = RIM
    if close_leg_hole:
        x0, x1, y0, y1 = LEG_HOLE
        out = remove_component_of_color(out, N, rect(out, x0 + dx, x1 + dx, y0, y1), 30)
    # 반환 마스크는 조끼 면(fill)만. 바늘구멍(pin)은 전완 밑 그림자라 공격 예고에서 팔과 함께 돌아가야 자연스럽다.
    return out, fill
