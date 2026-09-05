# -*- coding: utf-8 -*-
"""적 애니메이션 v2 빌드 — 스켈레톤 · 고블린 공용.
사용: python build_v2.py <스켈레톤|고블린> <원본시트.png> <v1폴더> <출력폴더>
v1 파이프라인(pipeline_v1.build)으로 64px 포즈를 얻은 뒤, v2tools 로 파츠를 편집해 새 프레임을 만든다.
"""
import sys, os, json
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pipeline_v1
from v2tools import *

NAME, SRC, V1DIR, OUT = sys.argv[1:5]
os.makedirs(OUT, exist_ok=True)
v1 = json.load(open(os.path.join(V1DIR, '_build.json'), encoding='utf-8'))
PAL_HEX = v1['palette']
PALETTE = np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in PAL_HEX])

if NAME == '스켈레톤':
    small, scale, _ = pipeline_v1.build(SRC, SHADOW_MAX=125, SHADOW_COOL=True, SMALL_MIN=0, palette_hex=PAL_HEX)
else:
    small, scale, _ = pipeline_v1.build(SRC, SHADOW_MAX=150, SHADOW_COOL=False, SMALL_MIN=120, palette_hex=PAL_HEX)

def get(k): return small[k][0].copy(), float(small[k][1])

PT, PL, PR = 22, 26, 10   # 편집용 여백(위 · 왼 · 오). 발(마지막 행)은 그대로
def padded(a, ax):
    h, w = a.shape[:2]
    out = np.zeros((h + PT, w + PL + PR, 4), np.uint8); out[PT:, PL:PL + w] = a
    return out, ax + PL
def pbox(b): return (b[0] + PL, b[1] + PT, b[2] + PL, b[3] + PT)
def ppiv(p): return (p[0] + PL, p[1] + PT)

def main_component(a):
    """몸에서 떨어진 조각(원본 이펙트 파편) 제거: 가장 큰 연결 성분만"""
    from scipy import ndimage
    m = a[..., 3] > 0
    lab, n = ndimage.label(ndimage.binary_dilation(m, iterations=2))
    if n <= 1: return a
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    keep = lab == (np.argmax(sizes) + 1)
    out = a.copy(); out[~keep] = 0
    return out

def finish(canvas, feet=True):
    c = canvas.copy()
    if feet: c = clean_feet(c, rows=CFG['feet_rows'])
    c[c[..., 3] == 0] = 0
    return c

# ---------------------------------------------------------------- 캐릭터 설정
if NAME == '스켈레톤':
    CFG = dict(feet_rows=4)
    idle, iax = get('idle')
    w1, w1ax = get('walk1'); w2, w2ax = get('walk2'); w3, w3ax = get('walk3'); w4, w4ax = get('walk4')
    atk, aax = get('attack'); hit, hax = get('hit')
    # 원본 3/4 뷰 셀은 두개골이 화면 왼쪽을 본다 → 두개골만 좌우 반전해 오른쪽(공격 방향)을 보게(v2c)
    idle = face_right(idle, 20); w1 = face_right(w1, 19); hit = face_right(hit, 20)
    HIP = 43
    SH_BOX = (27, 20, 45, 47)          # 방패 영역(walk1 기준, 패딩 없음)
    idleP, iaxP = padded(idle, iax)    # 편집용
    atkP, aaxP = padded(atk, aax)
    HIP_P = HIP + PT
    SW_BOX = pbox((0, 6, 12, 38)); SW_PIV = ppiv((9, 34))      # 대기 칼날+손, 손 축
    ASW_BOX = pbox((44, 4, 72, 27)); ASW_PIV = ppiv((49, 20))  # 공격 셀 칼날, 손 축
    HEAD_ROWS = 19 + PT
else:
    CFG = dict(feet_rows=3)
    idle, iax = get('idle')
    run, rax = get('run'); atk, aax = get('attack'); hit, hax = get('hit')
    atk = main_component(atk)
    # 공격 셀은 원본에서 크게 그려져(63px) 대기 키에 맞춰 0.9배
    atk_t, (ox, oy) = tight(atk)
    atk = resize_nn(atk_t, 0.9, 0.9); aax = (aax - ox) * 0.9
    HIP = 46
    SH_BOX = None
    idleP, iaxP = padded(idle, iax); atkP, aaxP = padded(atk, aax)
    HIP_P = HIP + PT
    SW_BOX = pbox((0, 0, 14, 27)); SW_PIV = ppiv((12, 24))
    ASW_BOX = None
    HEAD_ROWS = 32 + PT

def region_mask(a, box):
    m = np.zeros(a.shape[:2], bool); x0, y0, x1, y1 = box; m[y0:y1, x0:x1] = True
    return m & (a[..., 3] > 0)

# ---------------------------------------------------------------- 대기 (v1 동일)
def stretch_top(a, px):
    """몸을 위로 px 늘림(발 고정): 상단을 그대로 두고 아래를 NEAREST 로 재샘플 대신 v1 방식 sy 스케일"""
    h = a.shape[0]
    return resize_nn(a, 1.0, (h + px) / h)

frames_idle = [place(idle, iax), place(stretch_top(idle, 1), iax), place(stretch_top(idle, 1), iax), place(idle, iax)]
frames_idle = [finish(f) for f in frames_idle]

# ---------------------------------------------------------------- 이동 — 진짜 걷기 사이클 6
def compose_walk(torso, tax, legs, W=64, body_dy=0, arm=None, hip=None):
    """legs: [(blob, dx, dy[, plant])] 뒤→앞 순서. torso 는 다리 위에 덮는다(들린 다리의 윗부분 숨김).
    hip 을 주면 다리 블롭의 hip 행을 몸통의 hip 행에 맞추고, plant=True 인 다리는 발바닥이 y=62 에 닿도록 세로로 늘린다."""
    c = blank(W)
    x0 = int(round(W / 2 - tax)); ty = FOOT_Y - torso.shape[0] + 1
    for leg in legs:
        blob, dx, dy = leg[:3]; plant = leg[3] if len(leg) > 3 else False
        if hip is None:
            paste(c, shift(blob, dx, dy), x0, FOOT_Y - blob.shape[0] + 1); continue
        tb, (bx, by) = tight(blob)                       # by = 블롭 위 행(=hip 부근)
        top = ty + by                                    # 몸통 기준 같은 행
        if plant:
            need = FOOT_Y - top + 1
            if need != tb.shape[0]: tb = resize_nn(tb, 1.0, need / tb.shape[0])
        paste(c, tb, x0 + bx + dx, top + dy)
    t = torso
    if arm is not None and SH_BOX is not None:
        m = region_mask(t, SH_BOX); t = t.copy()
        armpart = crop_mask(t, m); t[m] = 0
        t = paste(t, shift(armpart, arm, 0), 0, 0)
    paste(c, t, int(round(W / 2 - tax)), FOOT_Y - torso.shape[0] + 1 + body_dy)
    return c

if NAME == '스켈레톤':
    # 원본 walk1 = 접지(양발 벌림), walk4 = 뒷발 들림(통과). 두 장의 다리로 6프레임을 만든다.
    t1, _ = split_rows(w1, HIP)
    b1, f1 = split_legs(w1, HIP)              # 접지: 뒤 · 앞
    b4, f4 = split_legs(w4, HIP)              # 통과: 뒤(들림) · 앞(딛음)
    # walk4 는 앵커가 다르므로 walk1 앵커 기준으로 정렬
    d4 = int(round(w1ax - w4ax))
    b4, f4 = shift(b4, d4, 0), shift(f4, d4, 0)
    # 앞다리가 들리는 통과 프레임: walk4 의 딛는 앞다리를 뒤로, 들린 뒷다리를 앞으로
    bb4, fb4 = bbox(b4), bbox(f4)
    gap = int(round(((fb4[0] + fb4[2]) - (bb4[0] + bb4[2])) / 2))   # 두 다리 중심 거리
    walk = [
        compose_walk(t1, w1ax, [(b1, 0, 0), (f1, 0, 0)], body_dy=0, arm=0),                      # 1 접지 A
        compose_walk(t1, w1ax, [(b1, 1, 0), (f1, -1, 0)], body_dy=1, arm=0),                     # 2 눌림(몸 1px 내려감)
        compose_walk(t1, w1ax, [(b4, 0, -3), (f4, 0, 0, True)], body_dy=-1, arm=1, hip=HIP),     # 3 통과: 뒷발 들림(앞다리 딛음)
        compose_walk(t1, w1ax, [(f1, 0, 0), (b1, 0, 0)], body_dy=0, arm=1),                      # 4 접지 B(다리 겹침 순서 교대)
        compose_walk(t1, w1ax, [(f1, -1, 0), (b1, 1, 0)], body_dy=1, arm=1),                     # 5 눌림
        compose_walk(t1, w1ax, [(f4, -gap, 0, True), (b4, gap, -3)], body_dy=-1, arm=0, hip=HIP), # 6 통과: 앞발 들림(뒷다리 딛음)
    ]
else:
    ti, _ = split_rows(idle, HIP)
    bl, fl = split_legs(idle, HIP)
    walk = [
        compose_walk(ti, iax, [(bl, -3, 0), (fl, 3, 0)], body_dy=0),          # 1 접지 A
        compose_walk(ti, iax, [(bl, -2, 0), (fl, 2, 0)], body_dy=1),          # 2 눌림
        compose_walk(ti, iax, [(fl, 0, 0), (bl, 1, -3)], body_dy=-1),         # 3 통과: 뒷발 들림(앞으로 나오는 중)
        compose_walk(ti, iax, [(fl, -3, 0), (bl, 3, 0)], body_dy=0),          # 4 접지 B (다리 교대)
        compose_walk(ti, iax, [(fl, -2, 0), (bl, 2, 0)], body_dy=1),          # 5 눌림
        compose_walk(ti, iax, [(bl, 0, 0), (fl, 1, -3)], body_dy=-1),         # 6 통과: 앞발 들림
    ]
frames_walk = [finish(f) for f in walk]

# ---------------------------------------------------------------- 공격 10
def swing_weapon(base, box, piv, angle, dx=0, dy=0):
    """base 의 box 안 무기 블롭을 piv 기준 angle 회전 + 이동해 다시 붙인다. 무기는 몸 뒤에 둔다(뒤로 빼는 예고용)."""
    m = region_mask(base, box)
    wpn = crop_mask(base, m); body = base.copy(); body[m] = 0
    wpn = shift(rotate_about(wpn, angle, piv), dx, dy)
    out = wpn.copy(); paste(out, body, 0, 0)
    return out

def shear_body(canvas, amount):
    h = canvas.shape[0]
    return shear_rows(canvas, amount, 0, FOOT_Y - 6)

def squash(a, sy):
    """바닥 고정 세로 압축(v1 sy)"""
    return resize_nn(a, 1.0, sy)

if NAME == '스켈레톤':
    # v2b: 공격은 attack_v2.build_attack — 대기 몸에서 검 팔을 지우고 어깨 축 2마디 뼈 팔을 다시 그려 검을 손에 붙인다(10프레임 한 몸).
    from attack_v2 import build_attack
    W = 80
    attack = build_attack(idle, iax, PALETTE, W=W)
else:
    W = 80
    anti1 = swing_weapon(idleP, SW_BOX, SW_PIV, -35, 0, 1)
    anti2 = swing_weapon(idleP, SW_BOX, SW_PIV, -105, -2, 5)            # 단검을 뒤로 빼 허리 뒤에
    anti2s = squash(anti2, 0.86)
    ASW = (34, 30, 60, 52)
    aw_piv = None
    attack = [
        place(idle, iax, W),                                            # 1 서기
        shear_body(place(squash(anti1, 0.94), iaxP, W, dx=-2), -2),     # 2 예고: 웅크리기 시작
        shear_body(place(anti2s, iaxP, W, dx=-4), -3),                  # 3 예고: 최대 웅크림 + 단검 뒤로
        shear_body(place(anti2s, iaxP, W, dx=-4), -3),                  # 4 홀드
        shear_body(place(squash(anti2, 0.85), iaxP, W, dx=-4), -3),     # 5 홀드 떨림
        place(resize_nn(run, 1.15, 0.98), rax * 1.15, W, dx=2),         # 6 스미어: 튀어나감(원본 달리기 셀 늘림)
        place(atk, aax, W, dx=4),                                       # 7 접촉(낮은 베기)
        None, None,
        place(idle, iax, W),                                            # 10 서기
    ]
    # 팔로우스루: 접촉 프레임의 칼날 블롭을 손 축으로 더 아래로
    ab = bbox(atk)
    # 칼날은 접촉 셀 오른쪽 아래의 밝은 부분: 밝은(크림) 색 픽셀만 찾아 박스로
    lum = atk[..., :3].astype(int).sum(-1); bright = (lum > 500) & (atk[..., 3] > 0)
    ys, xs = np.where(bright); bx = (xs.min() - 1, ys.min() - 1, xs.max() + 2, ys.max() + 2)
    piv = (xs.min(), ys.min())
    attack[7] = place(swing_weapon(atk, bx, piv, 22, 0, 0), aax, W, dx=5)
    attack[8] = place(resize_nn(swing_weapon(atk, bx, piv, 10, 0, 0), 0.96, 1.0), aax * 0.96, W, dx=1)
frames_attack = [finish(f) for f in attack]

# ---------------------------------------------------------------- 피격 4 (v1 동일 + 발 정리)
hitf = [flash(place(hit, hax)), shear_body(place(hit, hax, dx=-3), -2), place(hit, hax, dx=-1), place(idle, iax)]
frames_hit = [finish(f) for f in hitf]

# ---------------------------------------------------------------- 그로기 6 — 멈춤 포즈 직접 구성
def groggy_pose(head_dy, leg_sy, wpn_angle, wpn_dxy, shear=0):
    base = swing_weapon(idleP, SW_BOX, SW_PIV, wpn_angle, *wpn_dxy)
    # 다리 압축(무릎 굽힘): HIP 아래를 leg_sy 배
    base = squash_rows(base, HIP_P, leg_sy)
    # 고개 숙임: 머리 행을 아래로
    head, body = split_rows(base, HEAD_ROWS + int(round((1 - leg_sy) * (base.shape[0] - HIP_P))))
    out = body.copy(); paste(out, shift(head, 0, head_dy), 0, 0)
    c = place(out, iaxP)
    return shear_body(c, shear) if shear else c

if NAME == '스켈레톤':
    G_ANG, G_DXY = 215, (0, 0)
else:
    G_ANG, G_DXY = 150, (0, 2)
stop = groggy_pose(2, 0.70, G_ANG, G_DXY, shear=2)
stop2 = groggy_pose(3, 0.68, G_ANG, G_DXY, shear=2)
groggy = [
    shear_body(place(hit, hax, dx=2), 3),                           # 1 앞으로 쏠림
    shear_body(place(hit, hax, dx=-2), -3),                         # 2 뒤로 젖힘
    groggy_pose(1, 0.85, G_ANG // 2, (0, 0), shear=-1),             # 3 가라앉음(무기 내려가는 중)
    dim_to_palette(stop, PALETTE),                                  # 4 멈춤
    dim_to_palette(stop, PALETTE),                                  # 5 유지
    dim_to_palette(stop2, PALETTE),                                 # 6 유지(1px 호흡)
]
frames_groggy = [finish(f) for f in groggy]

# ---------------------------------------------------------------- 저장
speed = {'대기': 180, '이동': 110, '공격': 110, '피격': 100, '그로기': 150}
sets = {'대기': (64, frames_idle), '이동': (64, frames_walk), '공격': (80, frames_attack), '피격': (64, frames_hit), '그로기': (64, frames_groggy)}
report = {}; qa_rows = []
for key, (Wd, fr) in sets.items():
    fn = f'{NAME}_{key}_시트_{Wd}x64x{len(fr)}.png'
    save_sheet(fr, os.path.join(OUT, fn), Wd)
    save_gif(fr, os.path.join(OUT, f'미리보기_{key}.gif'), Wd, speed[key])
    qa_rows.append(strip(fr, Wd, scale=3))
    bad = check_palette(fr, PALETTE, extra=[(255, 241, 230), (216, 200, 192)])
    report[key] = fn
    print(key, fn, '팔레트 밖 색:', len(bad))
qa = Image.new('RGBA', (max(r.width for r in qa_rows), sum(r.height + 6 for r in qa_rows)), (40, 30, 30, 255)); y = 0
for r in qa_rows: qa.paste(r, (0, y)); y += r.height + 6
qa.save(os.path.join(OUT, '_QA_전체시트_x3.png'))
json.dump({'scale': scale, 'palette': PAL_HEX, 'files': report, 'idle_size': [int(idle.shape[1]), int(idle.shape[0])]},
          open(os.path.join(OUT, '_build.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('done', NAME)
