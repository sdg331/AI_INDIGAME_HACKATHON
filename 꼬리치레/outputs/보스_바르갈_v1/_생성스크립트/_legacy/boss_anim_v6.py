# -*- coding: utf-8 -*-
"""원본프레임/ (boss_cut.py 산출) → 애니메이션 시트 12종 + 미리보기 GIF + A4 참고 파일 + QA 시트.
프레임 구성은 보스_애니메이션_제작문서.md 4절 표를 그대로 따른다.
「신규」 프레임은 절단본의 변형(기울임 · 늘림 · 이동 · 눈 색)으로 근사했다 → README에 손보정 목록으로 적는다.
실행: 프로젝트 루트에서  python outputs/보스_바르갈_v1/_생성스크립트/boss_anim.py
"""
import os, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
import boss_cut as bc
import time

def save_retry(im, path, **kw):
    """OneDrive 동기화 잠금으로 간헐적 OSError(Invalid argument)가 나서 5회 재시도."""
    for k in range(5):
        try:
            im.save(path, **kw); return
        except OSError:
            time.sleep(0.6)
    im.save(path, **kw)

ROOT = bc.ROOT
DIR = os.path.join(ROOT, 'outputs', '보스_바르갈_v1')
RAW = os.path.join(DIR, '원본프레임')
PAL = bc.PAL
FOOT_Y = 62
IDX = {i: c for i, c in enumerate(bc.PALETTE)}
PINK = np.array(IDX[2]); WHITE0 = np.array(IDX[0]); LIGHT1 = np.array(IDX[1]); DARK7 = np.array(IDX[7]); EYE6 = np.array(IDX[6])

# ---------------------------------------------------------------- 로드
def load(name):
    return np.asarray(Image.open(os.path.join(RAW, name + '.png')).convert('RGBA')).copy()

F = {k: load(k + '_64x64') for k in ['정면', '후면', '좌측', '우측', '대기', '달리기', '피격'] + [f'이동{i}' for i in range(1, 9)]}

# ---------------------------------------------------------------- 공격 · 스킬 몸/이펙트 분리 (원본 해상도)
def split_attack():
    """공격 셀: 손끝 오른쪽(원본 x ≥ SPLIT)은 전부 궤적·마력 → 몸에서 뺀다."""
    c, alpha, (cw, ch, flip) = bc.cell('공격')
    x0 = bc.REGIONS['공격'][0]
    SPLIT = 623 - x0            # 손끝 바로 뒤 (실측)
    body = alpha.copy(); body[:, SPLIT:] = False
    fx = alpha.copy(); fx[:, :SPLIT] = False
    return c, body, fx

def split_skill():
    """스킬 셀: 자주 발광(R-G>40) + 머리카락 영역 밖의 밝은 핑크 코어 = 고리. 나머지 = 몸."""
    c, alpha, _ = bc.cell('스킬')
    x0, y0 = bc.REGIONS['스킬'][:2]
    R, G, B = c[..., 0], c[..., 1], c[..., 2]
    lum = c.max(axis=2); sat = lum - c.min(axis=2)
    # 몸 상자(원본 x 1005~1160 · y 985~1161) 밖: 자주 발광 + 밝은 코어 전부 고리.
    # 몸 상자 안: 강한 자주 발광(R-G>60, B>G+20)만 고리 → 머리카락(R-G≈19) · 피부(R-G≈39)는 몸으로 남는다.
    body_box = np.zeros_like(alpha); body_box[985 - y0:1161 - y0, 1005 - x0:1160 - x0] = True
    glow_strong = (R - G > 60) & (B - G > 20) & (lum > 100)
    glow = (R - G > 40) & (lum > 100)
    core = (lum > 215) & (sat < 45)
    ring = alpha & ((~body_box & (glow | core)) | (body_box & glow_strong))
    ring = ndimage.binary_closing(ring, iterations=2) & alpha
    body = alpha & ~ring
    # 고리 조각이 몸에 가늘게 붙어 남는다 → 열기(3px)로 끊고 가장 큰 성분만 남긴 뒤 원래 두께로 복원
    core_b = ndimage.binary_opening(body, iterations=3)
    lab, n = ndimage.label(core_b)
    sizes = ndimage.sum(core_b, lab, range(1, n + 1))
    main = (lab == (int(np.argmax(sizes)) + 1)) if n else core_b
    body = ndimage.binary_dilation(main, iterations=4) & body
    ring = ring | (alpha & ~body)
    return c, body, ring

def to64(c, mask, body_h_rows, cw, ch, flip=False):
    """원본 셀 + 마스크 → 60px 몸 높이로 축소한 캔버스 (bc.shrink/quantize/place 재사용)."""
    ys, xs = np.where(mask)
    y0, y1 = body_h_rows
    x0, x1 = xs.min(), xs.max() + 1
    scale = bc.BODY_H / (y1 - y0)
    rgb, keep = bc.shrink(c[y0:y1, x0:x1], mask[y0:y1, x0:x1], scale)
    q = bc.quantize(rgb, keep)
    if flip: q = q[:, ::-1]
    foot = q[-6:, :, 3] > 0
    fxs = np.where(foot.any(axis=0))[0]
    anchor = (fxs.min() + fxs.max()) / 2 if len(fxs) else q.shape[1] / 2
    return bc.place(q, cw, ch, anchor), scale

def save_ref(c, mask, name, scale):
    """A4 참고: 원본 해상도 + 64 밀도 축소본."""
    ys, xs = np.where(mask)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    sub = np.dstack([c[y0:y1, x0:x1], mask[y0:y1, x0:x1] * 255]).astype(np.uint8)
    save_retry(Image.fromarray(sub, 'RGBA'), os.path.join(DIR, f'{name}_원본해상도.png'))
    rgb, keep = bc.shrink(c[y0:y1, x0:x1], mask[y0:y1, x0:x1], scale)
    small = np.dstack([np.clip(rgb, 0, 255).astype(np.uint8), keep.astype(np.uint8) * 255])
    save_retry(Image.fromarray(small, 'RGBA'), os.path.join(DIR, f'{name}_64밀도.png'))

c_at, body_at, fx_at = split_attack()
ys = np.where(body_at.any(axis=1))[0]
ATTACK, at_scale = to64(c_at, body_at, (ys.min(), ys.max() + 1), 80, 64)
save_ref(c_at, fx_at, '참고_궤적_원본', at_scale)

def keep_main(fr):
    """64px에서 몸과 떨어진 조각(고리 부스러기 · 잡티) 제거: 가장 큰 연결 성분만 남긴다."""
    a = fr[..., 3] > 0
    lab, n = ndimage.label(a)
    if n <= 1: return fr
    sizes = ndimage.sum(a, lab, range(1, n + 1))
    keep = lab == (int(np.argmax(sizes)) + 1)
    out = fr.copy(); out[~keep] = 0
    return out

c_sk, body_sk, ring_sk = split_skill()
ys_sk = np.where(body_sk.any(axis=1))[0]
SKILL_RAW, sk_scale = to64(c_sk, body_sk, (ys_sk.min(), ys_sk.max() + 1), 96, 80)   # v3: 다른 프레임과 같은 「마스크 전체 높이 = 60」 기준
save_ref(c_sk, ring_sk, '참고_고리_원본', sk_scale)
SKILL_RAW = keep_main(SKILL_RAW)
ATTACK = keep_main(ATTACK)

# ---------------------------------------------------------------- 프레임 유틸 (모두 64×64 기준, 발 y62)
def crop_sprite(fr):
    a = fr[..., 3] > 0
    ys, xs = np.where(a)
    return fr[ys.min():ys.max() + 1, xs.min():xs.max() + 1], (xs.min() + xs.max()) / 2

def canvas(w=64, h=64):
    return np.zeros((h, w, 4), np.uint8)

def put(fr, dx=0, dy=0, w=64, h=64):
    """64 프레임을 w×h 캔버스에. 넓은 캔버스는 규약 오프셋(80: x+8 / 96×80: x+16,y+16) + dx,dy."""
    out = canvas(w, h)
    ox = (w - 64) // 2 + dx; oy = (h - 64) + dy
    sy0, sy1 = max(0, -oy), min(64, h - oy); sx0, sx1 = max(0, -ox), min(64, w - ox)
    out[oy + sy0:oy + sy1, ox + sx0:ox + sx1] = fr[sy0:sy1, sx0:sx1]
    return out

def shear(fr, px):
    """상체 기울임: 맨 위 행이 px만큼, 발(y62)은 0."""
    out = np.zeros_like(fr)
    for y in range(fr.shape[0]):
        off = int(round(px * (1 - y / FOOT_Y))) if y <= FOOT_Y else 0
        out[y] = np.roll(fr[y], off, axis=0)
        if off > 0: out[y, :off] = 0
        elif off < 0: out[y, off:] = 0
    return out

def stretch(fr, dh=0, dw=0):
    """발 고정 세로 늘림(dh) · 중심 고정 가로 늘림(dw). NEAREST."""
    sp, cx = crop_sprite(fr)
    h, w = sp.shape[:2]
    img = Image.fromarray(sp, 'RGBA').resize((max(1, w + dw), max(1, h + dh)), Image.NEAREST)
    s = np.asarray(img)
    out = canvas(fr.shape[1], fr.shape[0])
    ys, xs = np.where(fr[..., 3] > 0)
    x0 = int(round(cx - s.shape[1] / 2)); y0 = ys.max() + 1 - s.shape[0]
    sx0 = max(0, -x0); sy0 = max(0, -y0)   # 위로 넘치면 윗부분을 잘라 발을 고정
    ex = min(out.shape[1], x0 + s.shape[1]); ey = min(out.shape[0], y0 + s.shape[0])
    out[max(0, y0):ey, max(0, x0):ex] = s[sy0:sy0 + ey - max(0, y0), sx0:sx0 + ex - max(0, x0)]
    return out

def eyes_pink(fr, rows=(26, 33)):
    """예고 신호: 눈 흰자(#FCE8DF)를 밝은 분홍으로. 눈은 26~32행에만 흰색이 있다(실측)."""
    out = fr.copy()
    r0, r1 = rows
    m = np.all(out[r0:r1, :, :3] == WHITE0, axis=2) & (out[r0:r1, :, 3] > 0)
    out[r0:r1][m] = np.array([*PINK, 255])
    return out

def eyes_closed(fr, rows=(27, 32)):
    """눈 감음: 눈 흰자 행을 피부색으로 덮고 가운데 행에 어두운 선."""
    out = fr.copy()
    r0, r1 = rows
    m = np.all(out[r0:r1, :, :3] == WHITE0, axis=2) & (out[r0:r1, :, 3] > 0)
    out[r0:r1][m] = np.array([*LIGHT1, 255])
    mid = (r0 + r1) // 2
    cols = np.where(m.any(axis=0))[0]
    if len(cols):
        out[mid, cols.min():cols.max() + 1] = np.where(out[mid, cols.min():cols.max() + 1, 3:4] > 0, np.array([*EYE6, 255]), 0)
    return out

def flash(fr):
    a = fr[..., 3] > 0
    inner = ndimage.binary_erosion(a, iterations=1)
    out = fr.copy(); out[a] = (255, 241, 236, 255); out[inner] = (255, 255, 255, 255)
    return out

def swap_legs(fr, hip_row=48):
    """하반신을 몸 중심 기준으로 좌우 반전 → 반대 다리 접지 (제작문서 4.3 「반전 다리」)."""
    out = fr.copy()
    sp, cx = crop_sprite(fr)
    low = fr[hip_row:]
    a = low[..., 3] > 0
    xs = np.where(a.any(axis=0))[0]
    if not len(xs): return out
    x0, x1 = xs.min(), xs.max() + 1
    seg = low[:, x0:x1][:, ::-1]
    out[hip_row:, x0:x1] = seg
    return out

def hair_lift(fr, px=1):
    """옆머리(어깨 아래로 흘러내린 머리카락)가 떠오르는 표현. v4: 픽셀을 복사하지 않고
    머리카락이 주인 열(側 기둥)의 34행 아래를 통째로 px만큼 위로 「이동」한다 → 잔상 없음."""
    if px <= 0: return fr.copy()
    out = fr.copy()
    h, w = fr.shape[:2]
    hair_cls = np.all(fr[..., :3] == np.array(IDX[4]), axis=2) | np.all(fr[..., :3] == np.array(IDX[5]), axis=2)
    hair_cls &= fr[..., 3] > 0
    a = fr[..., 3] > 0
    ys = np.where(a.any(axis=1))[0]
    top_row = 34 if h == 64 else 34 + (h - 64)
    for x in range(w):
        col = hair_cls[top_row:, x]
        seg = a[top_row:, x]
        if seg.sum() == 0: continue
        if col.sum() < seg.sum() * 0.35: continue     # 머리카락이 주인 열만
        src = fr[top_row:, x].copy()
        out[top_row:, x] = 0
        out[top_row - px:h - px, x] = src
    return out

def compose(fr, over):
    """over의 불투명 픽셀을 fr 위에."""
    out = fr.copy(); m = over[..., 3] > 0; out[m] = over[m]; return out

# ---------------------------------------------------------------- 기본 프레임
IDLE = F['대기']
HIT = F['피격']
RUN = F['달리기']
WALK = [F[f'이동{i}'] for i in range(1, 9)]
# 스킬 몸: 고리를 뺀 자리를 대기 프레임으로 메운다 (96×80 캔버스 안에서 64 위치 정렬)
sk = SKILL_RAW.copy()
idle_on_96 = put(IDLE, w=96, h=80)
holes = (sk[..., 3] == 0) & (idle_on_96[..., 3] > 0)
sk[holes] = idle_on_96[holes]
SKILL_CUT = sk[16:80, 16:80].copy()   # 64 기준 절단본 (고리 잔재가 머리 뒤에 남는다 — 참고용)

def splice_skill_arms(idle, skill_cut, box=(18, 41, 35, 48)):
    """v5: 스킬 절단본에서 「가슴 앞에 모은 양팔」 영역(box)만 대기 프레임 위에 얹는다.
    머리 · 머리카락 · 치마 · 다리는 대기 프레임 → 머리 뒤 고리 잔상이 원천적으로 사라진다.
    정렬: 발바닥은 둘 다 y62, x는 머리 중심으로 맞춘다."""
    a = idle[..., 3] > 0; b = skill_cut[..., 3] > 0
    def hx(m):
        ys = np.where(m.any(axis=1))[0]; rows = m[ys.min():ys.min() + 30]; xs = np.where(rows.any(axis=0))[0]
        return (xs.min() + xs.max()) / 2
    dx = int(round(hx(a) - hx(b)))
    sk_al = np.zeros_like(skill_cut)
    x0s, x1s = max(0, dx), min(64, 64 + dx)
    sk_al[:, x0s:x1s] = skill_cut[:, x0s - dx:x1s - dx]
    out = idle.copy()
    bx0, bx1, by0, by1 = box
    out[by0:by1 + 1, bx0:bx1 + 1] = 0
    src = sk_al[by0:by1 + 1, bx0:bx1 + 1]
    m = src[..., 3] > 0
    out[by0:by1 + 1, bx0:bx1 + 1][m] = src[m]
    # 상자 안에서 비어버린 곳(스킬 절단본에 픽셀이 없는 곳)은 대기 원본으로 되메움
    hole = (out[by0:by1 + 1, bx0:bx1 + 1][..., 3] == 0) & (idle[by0:by1 + 1, bx0:bx1 + 1][..., 3] > 0)
    out[by0:by1 + 1, bx0:bx1 + 1][hole] = idle[by0:by1 + 1, bx0:bx1 + 1][hole]
    return out

SKILL = splice_skill_arms(IDLE, SKILL_CUT)
ATK = ATTACK[:, 8:72].copy()      # 80 → 64 기준 (몸이 64 안에 들어오는지 확인: 손끝 x)

def frames_to_sheet(frames, w, h):
    sheet = Image.new('RGBA', (w * len(frames), h), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        sheet.alpha_composite(Image.fromarray(f, 'RGBA'), (i * w, 0))
    return sheet

# ---------------------------------------------------------------- 추가 유틸 (v2 — 애니메이션 원칙 반영)
def shift(fr, dx=0, dy=0):
    """캔버스 안에서 스프라이트 평행 이동."""
    out = np.zeros_like(fr)
    h, w = fr.shape[:2]
    ys0, ys1 = max(0, dy), min(h, h + dy); xs0, xs1 = max(0, dx), min(w, w + dx)
    out[ys0:ys1, xs0:xs1] = fr[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
    return out

def foot_anchor_x(fr):
    a = fr[..., 3] > 0
    ys = np.where(a.any(axis=1))[0]
    rows = a[ys.max() - 5:ys.max() + 1]
    xs = np.where(rows.any(axis=0))[0]
    return (xs.min() + xs.max()) / 2

def head_x(fr):
    a = fr[..., 3] > 0
    ys = np.where(a.any(axis=1))[0]
    rows = a[ys.min():ys.min() + 30]
    xs = np.where(rows.any(axis=0))[0]
    return (xs.min() + xs.max()) / 2

def flip_in_place(fr):
    """좌우 반전하되 발 위치(앵커 x)를 유지 — 캔버스 중심 반전으로 몸이 점프하는 것을 막는다."""
    ax = foot_anchor_x(fr)
    m = fr[:, ::-1].copy()
    return shift(m, int(round(ax - foot_anchor_x(m))))

def stabilize(frames, ref_x=None):
    """상체(머리 30행) 중심 x를 맞춰 프레임 간 떨림 제거. 걷기용."""
    if ref_x is None: ref_x = float(np.mean([head_x(f) for f in frames]))
    return [shift(f, int(round(ref_x - head_x(f)))) for f in frames]

def squash(fr, dh):
    """발 고정 세로 스쿼시/스트레치. 폭은 유지(머리 왜곡 방지)."""
    return stretch(fr, dh=dh, dw=0)

def smear(fr, dw):
    """가로 스미어: 폭만 늘린다. 돌진 · 빠른 이동 프레임에만."""
    return stretch(fr, dh=0, dw=dw)

def flash_keep_outline(fr):
    """피격 플래시: 몸은 흰색, 윤곽 1px은 최암부 색으로 남겨 실루엣이 읽히게."""
    a = fr[..., 3] > 0
    inner = ndimage.binary_erosion(a, iterations=1)
    out = fr.copy(); out[a] = (*DARK7, 255); out[inner] = (255, 244, 240, 255)
    return out

IDLE_P = eyes_pink(IDLE)
SKILL_P = eyes_pink(SKILL)
FRONT = F['정면']
P = lambda fr: put(fr, w=96, h=80)

# ---------------------------------------------------------------- 애니메이션 정의 (제작문서 4절 · v2)
A = {}
# 4.1 대기 ×4 — 호흡
A['대기'] = (64, 64, [IDLE, squash(IDLE, 1), IDLE, squash(IDLE, -1)], [180, 180, 180, 180],
             ['기본(대기 절단)', '들숨 · 몸 1px 위', '복귀', '날숨 · 몸 1px 아래'])
# ---- 파츠 기반 보행 (v4): 파츠분할/NN_이름.png 를 읽어 다리 · 팔 · 뒷머리 · 몸을 따로 움직인다
PARTS_DIR = os.path.join(DIR, '파츠분할')
PART_FILES = ['01_뒷머리', '02_꼬리', '03_왼다리', '04_오른다리', '05_치마', '06_몸통', '07_왼팔', '08_오른팔', '09_머리']
PARTS = {n[3:]: np.asarray(Image.open(os.path.join(PARTS_DIR, n + '.png')).convert('RGBA')).copy() for n in PART_FILES}
PIV = {'왼다리': (23, 53), '오른다리': (32, 53), '왼팔': (22, 38), '오른팔': (36, 38)}

def limb_swing(part, pivot, dx, lift=0, toe=0, top_dir=1):
    """관절 피벗 아래(top_dir=1) 행을 엉덩이/어깨 기준으로 기울여 dx만큼 흔든다. lift = 전체 들림, toe = 맨 아래 2행 추가 전진."""
    out = np.zeros_like(part)
    px_, py = pivot
    a = part[..., 3] > 0
    ys = np.where(a.any(axis=1))[0]
    if not len(ys): return out
    y_end = ys.max()
    for y in range(ys.min(), y_end + 1):
        t = 0 if y <= py else (y - py) / max(1, y_end - py)
        off = int(round(dx * t)) + (toe if (toe and y >= y_end - 1) else 0)
        row = np.roll(part[y], off, axis=0)
        if off > 0: row[:off] = 0
        elif off < 0: row[off:] = 0
        ty = y - lift
        if 0 <= ty < part.shape[0]:
            m = row[..., 3] > 0; out[ty][m] = row[m]
    return out

def parts_gait(n=8, amp=4, lift=3, lean=1, bob=1, arm_amp=2, hair_back=0, air=None, fps_note=''):
    """보행 사이클. 오른다리(화면 오른쪽)를 앞다리로: dx = amp·cos(ph). 앞으로 가는 다리(속도 +)는 들고 발끝을 앞세운다.
    팔은 같은 쪽 다리와 반대. 지나감(다리 교차)에서 몸 bob px 위. air = 프레임별 전체 띄움(달리기 공중)."""
    frames = []
    for i in range(n):
        ph = 2 * np.pi * i / n
        d = amp * np.cos(ph); v = -np.sin(ph)
        dR, dL = int(round(d)), int(round(-d))
        liftR = lift if v > 0.25 else 0; liftL = lift if v < -0.25 else 0
        toeR = 1 if liftR else 0; toeL = 1 if liftL else 0
        passing = abs(d) < amp * 0.45
        dy_body = -(bob if passing else 0) - (air[i] if air else 0)
        legR = limb_swing(PARTS['오른다리'], PIV['오른다리'], dR, liftR, toeR)
        legL = limb_swing(PARTS['왼다리'], PIV['왼다리'], dL, liftL, toeL)
        armR = limb_swing(PARTS['오른팔'], PIV['오른팔'], -int(round(arm_amp * np.cos(ph))))
        armL = limb_swing(PARTS['왼팔'], PIV['왼팔'], int(round(arm_amp * np.cos(ph))))
        hair = shift(PARTS['뒷머리'], -hair_back, 0)
        upper = [hair, PARTS['꼬리']]
        f = canvas()
        for pimg in upper: f = compose(f, shift(pimg, 0, dy_body))
        if air: legR = shift(legR, 0, -air[i]); legL = shift(legL, 0, -air[i])
        f = compose(f, legL); f = compose(f, legR)
        for name in ('치마', '몸통'):
            f = compose(f, shift(PARTS[name], 0, dy_body))
        f = compose(f, shift(armL, 0, dy_body)); f = compose(f, shift(armR, 0, dy_body))
        f = compose(f, shift(PARTS['머리'], 0, dy_body))
        if lean: f = shear(f, lean)
        frames.append(f)
    return frames

# ---- 측면 파츠 보행 (v6): 파츠분할_공격/ (캡쳐 2 = 하트 참격 타격 프레임, 측면 런지) 을 기준 몸으로
PARTS_ATK_DIR = os.path.join(DIR, '파츠분할_공격')
PARTS_ATK_FILES = ['01_뒷머리', '02_뒷팔', '03_뒷다리', '04_앞다리', '05_치마', '06_몸통', '07_앞팔', '08_머리']
PA = {n[3:]: np.asarray(Image.open(os.path.join(PARTS_ATK_DIR, n + '.png')).convert('RGBA')).copy() for n in PARTS_ATK_FILES}
PIV_A = {'뒷팔': (22, 38), '뒷다리': (20, 47), '앞다리': (30, 49), '앞팔': (37, 38), '머리': (36, 36), '뒷머리': (30, 22)}

def rotate_part(part, pivot, deg):
    """관절 피벗을 중심으로 회전(NEAREST, 팔레트 유지). deg > 0 = 시계 반대(화면 기준 위로)."""
    if deg == 0: return part.copy()
    im = Image.fromarray(part, 'RGBA')
    px_, py = pivot
    out = im.rotate(deg, resample=Image.NEAREST, center=(px_ + 0.5, py + 0.5), expand=False)
    return np.asarray(out).copy()

def side_gait(n, front, back, arm_deg, arm_amp, lean_hair, bob, air=None, run=False):
    """front/back = (중심 dx, 진폭): 다리 발끝 x 변위 범위. 앞다리는 기준 포즈에서 이미 22px 앞에 있으므로 음수로 끌어온다.
    스탠스(뒤로 가는) 다리는 발을 땅(y62)에, 스윙(앞으로 가는) 다리는 든다. 뒷다리 기준 발은 y58이라 스탠스 때 4px 내린다."""
    frames = []
    for i in range(n):
        ph = 2 * np.pi * i / n
        c = np.cos(ph); v = -np.sin(ph)          # v > 0: 앞다리가 앞으로 가는 중
        dxf = int(round(front[0] + front[1] * c)); dxb = int(round(back[0] - back[1] * c))
        f_swing = v > 0.2; b_swing = v < -0.2
        lift_f = (4 if run else 3) if f_swing else 0
        lift_b = (0 if b_swing else -4)             # 뒷다리: 스윙이면 기준(y58) 유지, 스탠스면 땅까지 내림
        if b_swing and run: lift_b = 1
        toe_f = 1 if f_swing else 0; toe_b = 1 if b_swing else 0
        legF = limb_swing(PA['앞다리'], PIV_A['앞다리'], dxf, lift_f, toe_f)
        legB = limb_swing(PA['뒷다리'], PIV_A['뒷다리'], dxb, lift_b, toe_b)
        passing = abs(c) < 0.45
        dy = -(bob if passing else 0) - (air[i] if air else 0)
        if air:
            legF = shift(legF, 0, -air[i]); legB = shift(legB, 0, -air[i])
        armF = rotate_part(PA['앞팔'], PIV_A['앞팔'], arm_deg + arm_amp * c)      # 앞팔: 같은 쪽(앞) 다리와 반대 위상
        armB = limb_swing(PA['뒷팔'], PIV_A['뒷팔'], int(round(-2 * c)))
        hair = shift(PA['뒷머리'], 0, int(round(lean_hair * (1 if passing else 0))))
        f = canvas()
        f = compose(f, shift(hair, 0, dy))
        f = compose(f, shift(armB, 0, dy))
        f = compose(f, legB); f = compose(f, legF)
        for name in ('치마', '몸통'):
            f = compose(f, shift(PA[name], 0, dy))
        f = compose(f, shift(armF, 0, dy))
        f = compose(f, shift(PA['머리'], 0, dy))
        frames.append(f)
    return frames

# 4.2 걷기 ×8 — 측면 파츠. 앞다리 발끝 x 32~44 · 뒷다리 발끝 x 16~28(보폭 12) · 스윙 다리 3px 들고 발끝 앞세움 · 앞팔 −75°±10° · 지나감 1px 바운스
A['걷기'] = (64, 64, side_gait(8, front=(-14, 6), back=(12, 6), arm_deg=-75, arm_amp=10, lean_hair=1, bob=1), [110] * 8,
             ['접지(앞다리 앞)', '앞다리 뒤로(스탠스) · 뒷다리 들며 앞으로', '지나감 · 바운스', '뒷다리 앞 착지 직전', '접지(뒷다리 앞)', '뒷다리 뒤로 · 앞다리 들며 앞으로', '지나감 · 바운스', '앞다리 착지 직전'])
# 4.3 달리기 ×6 — 측면 파츠. 앞다리 발끝 x 30~52(기준 런지 그대로가 최대 보폭) · 뒷다리 x 10~30 · 공중 2 · 앞팔 −50°±20°
A['달리기'] = (64, 64, side_gait(6, front=(-11, 11), back=(10, 10), arm_deg=-50, arm_amp=20, lean_hair=1, bob=0, air=[0, 1, 3, 0, 1, 3], run=True), [80] * 6,
               ['접지(기준 런지)', '밀기 · 1px 위', '공중 3px · 다리 교차', '접지(다리 바뀜)', '밀기', '공중 3px'])
# 4.4 하트 참격 B1-1 ×9 (80×64) — 예고 3(뒤로 젖힘 · 웅크림) · 타격 2 · 후딜 4
pre1 = shear(IDLE_P, -1)
pre2 = shear(squash(IDLE_P, -1), -3)
pre3 = hair_lift(shear(squash(IDLE_P, -1), -4), 1)
hit1 = ATTACK
hit2 = put(shift(ATK, 1), w=80)
post1 = ATTACK
post2 = put(shear(ATK, 1), w=80)
post3 = put(shear(IDLE, 1), w=80)
A['하트참격'] = (80, 64, [put(pre1, dx=-1, w=80), put(pre2, dx=-2, w=80), put(pre3, dx=-3, w=80), hit1, hit2, post1, post2, post3, put(IDLE, w=80)],
                 [100, 100, 120, 70, 70, 100, 100, 100, 100],
                 ['예고1 · 눈 분홍 · 뒤로 1', '예고2 · 뒤로 젖힘 3 · 웅크림 1', '예고3 · 장전 4 · 머리카락', '타격1 = 공격 절단(궤적 제거) · 손끝 (60,41)', '타격2 · 1px 앞', '후딜1 홀드', '후딜2 · 상체 앞 1', '후딜3 · 복귀 중', '후딜4 서기'])
# 4.5 이단 참격 B1-2 ×11 — 전환은 정면 프레임, 반전은 발 기준
pre3b = hair_lift(pre3, 2)
turn = put(eyes_pink(FRONT), w=80)
hitR = put(flip_in_place(ATK), w=80)
postR = put(shear(flip_in_place(ATK), -1), w=80)
A['이단참격'] = (80, 64, [put(pre1, dx=-1, w=80), put(pre2, dx=-2, w=80), put(pre3b, dx=-3, w=80), hit1, turn, hitR, hitR, postR, put(shear(IDLE, -1), w=80), put(IDLE, w=80), put(IDLE, w=80)],
                 [100, 100, 120, 70, 60, 70, 100, 100, 100, 100, 100],
                 ['예고1', '예고2', '예고3 · 머리카락 2px(꼬리 신호 대용)', '타격1', '전환 = 정면 절단(몸을 돌리는 중간)', '타격2 = 타격1 발 기준 반전(꼬리 앞, 손보정)', '후딜1 반전 홀드', '후딜2 반전 · 상체 뒤 1', '후딜3 복귀', '후딜4 서기', '서기'])
# 4.6 하트 탄 B1-3 ×9 — 예고는 앞으로 기울임(참격의 뒤로 젖힘과 반대)
p1 = IDLE_P
p2 = shear(IDLE_P, 1)
p3 = hair_lift(shear(IDLE_P, 2), 1)
fire1 = put(shear(ATK, -1), w=80); fire2 = put(shear(ATK, -2), w=80)
A['하트탄'] = (80, 64, [put(p1, w=80), put(p2, dx=1, w=80), put(p3, dx=2, w=80), fire1, fire2, post1, post2, post3, put(IDLE, w=80)],
               [100, 100, 120, 70, 70, 100, 100, 100, 100],
               ['예고1 · 눈 분홍', '예고2 · 앞기울임 1', '예고3 · 앞기울임 2', '발사1 · 반동(상체 뒤 1)', '발사2 · 반동 2', '후딜1', '후딜2', '후딜3', '후딜4'])
# 4.7 피격 ×4 — 플래시(윤곽 유지) · 뒤로 2px 스쿼시 · 복귀 중 · 대기  (문서 3 → 4: 복귀 중간 추가)
A['피격'] = (64, 64, [flash_keep_outline(HIT), shift(squash(HIT, -1), -2), shift(HIT, -1), IDLE], [50, 110, 80, 100],
             ['피격 절단 + 흰 플래시(윤곽 유지)', '움찔 · 뒤로 2px · 스쿼시 1', '복귀 중 · 뒤로 1px', '대기 복귀'])
# 4.8 페이즈 전환 ×8
t1 = shift(IDLE, -2)
t2 = squash(HIT, -2)
t4 = hair_lift(t2, 1)
t5 = hair_lift(squash(HIT, -1), 1)
t6 = IDLE_P
t7 = hair_lift(IDLE_P, 2)
A['페이즈전환'] = (64, 64, [t1, t2, t2, t4, t5, t6, t7, t7], [120, 120, 200, 120, 120, 120, 120, 120],
                  ['뒤로 반 걸음', '고개 숙임 · 양손 모음(근사: 피격 웅크림 2)', '홀드 — A4 고리 퍼짐', '머리카락 1px 떠오름', '고개 든다 · 눈 감음', '눈 뜸 · 밝은 분홍', '머리카락 2px 떠오름', '2페이즈 대기 1'])
# 4.9 마력 고리 B2-1 ×8 (96×80) — 스킬 몸(양손 가슴 앞)을 예고부터 쓴다. 웅크림(충전) → 솟음(해방) → 가라앉음
A['마력고리'] = (96, 80, [P(IDLE_P), P(SKILL_P), P(hair_lift(squash(SKILL_P, -1), 1)), P(hair_lift(squash(SKILL_P, 1), 2)),
                          P(hair_lift(SKILL_P, 2)), P(hair_lift(SKILL, 1)), P(SKILL), P(IDLE)],
                [100, 100, 120, 70, 70, 100, 100, 100],
                ['예고1 · 눈 분홍', '예고2 · 양손 모음(스킬 몸) · 웅크림 1', '예고3 · 웅크림 2 · 머리카락(충전)', '접촉 · 솟음 2 · 머리카락 2(해방)', '접촉2 · 솟음 1', '후딜1 · 머리카락 내려옴', '후딜2 · 가라앉음 1', '후딜3 서기'])
# 4.10 돌진 참격 B2-2 ×9 (80×64) — 예고 3(뒤로 젖히며 웅크림) · 돌진 2(가로 스미어 + 앞기울임) · 타격 · 후딜
d1 = eyes_pink(shear(squash(RUN, -1), -2)); d2 = eyes_pink(shear(squash(RUN, -2), -3)); d3 = hair_lift(eyes_pink(shear(squash(RUN, -2), -4)), 1)
d4 = hair_lift(shear(smear(RUN, 8), 4), 2)
d5 = hair_lift(shear(smear(RUN, 4), 4), 1)
A['돌진참격'] = (80, 64, [put(d1, dx=-1, w=80), put(d2, dx=-2, w=80), put(d3, dx=-3, w=80), put(d4, dx=4, w=80), put(d5, dx=8, w=80), hit1, post1, post2, put(IDLE, w=80)],
                [100, 100, 120, 50, 50, 70, 100, 100, 100],
                ['예고1 · 뒤로 2 · 웅크림 1', '예고2 · 뒤로 3 · 웅크림 2', '예고3 · 뒤로 4 · 머리카락', '돌진1 · 가로 스미어 8 · 앞기울임 4 · 4px 앞(화면 이동은 게임)', '돌진2 · 스미어 4 · 8px 앞', '타격 = 하트 참격 4', '후딜1', '후딜2', '서기'])
# 4.11 마력 폭주 B2-3 ×12 (96×80) — 충전(웅크림) → 고리 3회(바운스) → 솟음(양손 위 대용) → 폭발(최대 스트레치) → 탈진(가라앉음)
A['마력폭주'] = (96, 80, [P(IDLE_P), P(SKILL_P), P(hair_lift(squash(SKILL_P, -1), 1)),
                          P(hair_lift(SKILL_P, 1)), P(hair_lift(squash(SKILL_P, 1), 2)), P(hair_lift(SKILL_P, 2)),
                          P(hair_lift(squash(SKILL_P, 1), 3)), P(hair_lift(squash(SKILL_P, 1), 3)), P(hair_lift(squash(SKILL_P, 2), 3)),
                          P(squash(SKILL, -1)), P(SKILL), P(IDLE)],
                [100, 100, 120, 80, 80, 80, 100, 120, 70, 120, 100, 100],
                ['예고1 · 눈 분홍', '예고2 · 양손 모음 · 웅크림 1', '예고3 · 웅크림 2(충전)', '고리1 · 솟음 1 (A4 반지름 1)', '고리2', '고리3 · 솟음 1', '마지막 예고1 · 솟음 2(양손 위 대용)', '마지막 예고2 · 솟음 3', '폭발 · 솟음 4 · 머리카락 최대', '후딜1 · 탈진 가라앉음 2', '후딜2 · 가라앉음 1', '후딜3 서기'])
# 4.12 그로기 ×(4+1)
k1 = shear(HIT, -2)
k2 = shift(shear(squash(HIT, -1), -3), -2)
k3 = shear(squash(HIT, -2), 2)
k4 = squash(HIT, -3)
A['그로기'] = (64, 64, [k1, k2, k3, k4, k4], [120, 120, 120, 150, 600],
              ['움찔 (피격 · 눈 감음)', '뒤로 반 걸음 · 양팔 늘어짐(근사)', '앞으로 기울며 비틀거림', '다시 서며 고개 숙임', '멈춤 포즈 — 이 프레임에서 정지 · 색 변화 없음 · 서 있음'])

# ---------------------------------------------------------------- 저장
def save_gif(frames, durs, path, scale=4):
    """배경 합성 → RGB → 전체 프레임 공통 팔레트로 양자화. (RGBA를 바로 P로 바꾸면 팔레트가 깨진다)"""
    rgb = []
    for f in frames:
        im = Image.fromarray(f, 'RGBA').resize((f.shape[1] * scale, f.shape[0] * scale), Image.NEAREST)
        bg = Image.new('RGBA', im.size, (51, 43, 47, 255)); bg.alpha_composite(im)
        rgb.append(bg.convert('RGB'))
    strip = Image.new('RGB', (rgb[0].width, rgb[0].height * len(rgb)))
    for i, im in enumerate(rgb): strip.paste(im, (0, i * im.height))
    master = strip.quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = [im.quantize(palette=master, dither=Image.Dither.NONE) for im in rgb]
    save_retry(pal[0], path, save_all=True, append_images=pal[1:], duration=list(durs), loop=0, optimize=False)

def color_count(frames):
    px = np.concatenate([f[f[..., 3] > 0][:, :3] for f in frames])
    return len(np.unique(px, axis=0))

report = {}
for key, (w, h, frames, durs, notes) in A.items():
    for f in frames:
        assert f.shape[:2] == (h, w), (key, f.shape)
    fn = f'보스_{key}_시트_{w}x{h}x{len(frames)}.png'
    save_retry(frames_to_sheet(frames, w, h), os.path.join(DIR, fn))
    save_gif(frames, durs, os.path.join(DIR, f'미리보기_{key}.gif'))
    # 발바닥 검사
    feet = []
    for f in frames:
        ys = np.where((f[..., 3] > 0).any(axis=1))[0]
        feet.append(int(ys.max()) if len(ys) else -1)
    report[key] = dict(file=fn, frames=len(frames), canvas=[w, h], durations_ms=durs, notes=notes, foot_rows=feet, colors=int(color_count(frames)))
    print(key, fn, 'feet', feet, 'colors', report[key]['colors'])

# ---------------------------------------------------------------- 기준점 실측
def head_center(fr):
    a = fr[..., 3] > 0
    ys = np.where(a.any(axis=1))[0]
    top = ys.min()
    # 머리 = 위에서 30행 (2등신, 몸 60의 절반)
    rows = a[top:top + 30]
    xs = np.where(rows.any(axis=0))[0]
    return [int((xs.min() + xs.max()) / 2), int(top + 15)]

def hand_tip(fr80):
    a = fr80[..., 3] > 0
    xs = np.where(a.any(axis=0))[0]
    x = int(xs.max())
    ys = np.where(a[:, x])[0]
    return [x, int(ys.mean())]

pts = {
    '발바닥 y(64 캔버스)': FOOT_Y,
    '머리 중앙 (대기, 64)': head_center(IDLE),
    '가슴 중앙 (대기, 64)': [head_center(IDLE)[0], 40],
    '손끝 (하트참격 타격1, 80 캔버스)': hand_tip(ATTACK),
    '머리 중앙 (하트참격 타격1, 80)': head_center(ATTACK),
    '머리 중앙 (마력고리 접촉, 96×80)': head_center(put(SKILL, w=96, h=80)),
}
print(pts)
json.dump(dict(sheets=report, points=pts, attack_scale=at_scale, skill_scale=sk_scale),
          open(os.path.join(DIR, '_build.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- QA 시트 (주인공 비교 · 전체 시트 3배)
hero = np.asarray(Image.open(os.path.join(ROOT, '미리보기_걷기8.gif')).convert('RGBA'))[::4, ::4].copy()
bgc = hero[0, 0, :3]; hero[np.all(hero[..., :3] == bgc, axis=2), 3] = 0
font = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 18)
S = 3
rows = list(A.items())
W = max(w * len(fr) for _, (w, h, fr, _, _) in rows) * S + 40
H = sum((h + 14) * S for _, (w, h, fr, _, _) in rows) + 20
qa = Image.new('RGBA', (W, H), (51, 43, 47, 255)); d = ImageDraw.Draw(qa); y = 10
for key, (w, h, frames, durs, notes) in rows:
    d.text((10, y), f'{key} {w}×{h}×{len(frames)}', font=font, fill=(230, 220, 220))
    y += 14 * S
    sheet = frames_to_sheet(frames, w, h).resize((w * len(frames) * S, h * S), Image.NEAREST)
    qa.alpha_composite(sheet, (10, y)); y += h * S
save_retry(qa, os.path.join(DIR, '_QA_전체시트_x3.png'))
# 주인공 나란히 (대기 · 걷기1 · 하트참격 타격)
cmp = Image.new('RGBA', ((64 + 64 + 64 + 80) * 4 + 50, 64 * 4 + 40), (51, 43, 47, 255))
xx = 10
for fr in [hero, IDLE, WALK[0], ATTACK]:
    im = Image.fromarray(fr, 'RGBA').resize((fr.shape[1] * 4, fr.shape[0] * 4), Image.NEAREST)
    cmp.alpha_composite(im, (xx, 20)); xx += im.width + 10
ImageDraw.Draw(cmp).text((10, 2), '주인공 64 · 보스 대기 · 걷기1 · 하트참격 타격(80) — 같은 바닥선, 4배', font=font, fill=(230, 220, 220))
save_retry(cmp, os.path.join(DIR, 'QA_주인공비교_4x.png'))
print('done')
