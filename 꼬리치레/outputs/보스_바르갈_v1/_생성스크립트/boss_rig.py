# -*- coding: utf-8 -*-
"""보스 바르갈 — 파츠 리그 v8. 기준 몸 두 벌로 12개 애니메이션 전부를 조립한다.
  STAND = 파츠분할_걷기/ (이동1 절단본: 3/4 측면 · 오른쪽 보기 · 똑바로 선 자세) → 대기 · 걷기 · 예고 · 하트탄 · 피격 · 페이즈 전환 · 마력 고리 · 마력 폭주 · 그로기
  LUNGE = 파츠분할_공격/ (캡쳐 2 = 하트 참격 타격 프레임: 런지) → 타격 · 돌진 · 달리기
둘 다 오른쪽 보기 3/4라 예고(STAND) → 타격(LUNGE) 전환이 「몸을 던지는」 동작으로 읽힌다.

포즈 파라미터(64 캔버스):
  arm_f   앞팔 회전(도). STAND: 0 = 늘어뜨림, +90 = 앞으로 수평, +170 = 머리 위, 음수 = 뒤로. LUNGE: 0 = 앞으로 뻗음(기준), -90 = 아래
  arm_b   뒷팔 x 기울임(px, 어깨 축)
  leg_f, leg_b  앞다리 · 뒷다리 발끝 x 변위(px, 엉덩이 축 기울임)
  lift_f, lift_b  다리 들림(px, +위)
  toe_f, toe_b  발끝 앞세움(px)
  upper_dy  상체 세로 이동(+아래 웅크림 / -위 솟음. 솟음 때 다리 윗부분을 늘려 틈을 막는다)
  lean      상체 기울임(px, 엉덩이 축, +앞)
  body_dx   몸 전체 x
  hair_up · hair_dx  머리카락 떠오름 · 흔들림
  drape     (LUNGE만) 머리카락 드리움 0~1
  head_bow  고개 숙임(px)
  eyes      'open' | 'pink' | 'closed'
  smear     가로 스미어(px)
  tail_dx   (STAND만) 꼬리 흔들림

실행: 프로젝트 루트에서 python outputs/보스_바르갈_v1/_생성스크립트/boss_rig.py
산출: 시트 12종 · 미리보기 GIF · _build.json · _QA_필름/*.png · _QA_자동검사.md · QA_주인공비교_4x.png
"""
import os, json, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DIR = os.path.join(ROOT, 'outputs', '보스_바르갈_v1')
RAW = os.path.join(DIR, '원본프레임')
QA_DIR = os.path.join(DIR, '_QA_필름'); os.makedirs(QA_DIR, exist_ok=True)
FONT = 'C:/Windows/Fonts/malgun.ttf'
FOOT_Y = 62
PALETTE = [(0xFC,0xE8,0xDF),(0xF6,0xCF,0xC5),(0xE7,0xA1,0xAC),(0x6D,0x32,0x5B),
           (0xEA,0xD7,0xD5),(0xBD,0x96,0xA4),(0x96,0x56,0x7B),(0x28,0x1F,0x2B),
           (0x61,0x31,0x53),(0x4D,0x32,0x45),(0x2F,0x22,0x30),(0x43,0x2B,0x36)]
PAL = np.array(PALETTE)
WHITE0, SKIN1, PINK2, EYE6, DARK7 = [np.array(PALETTE[i]) for i in (0, 1, 2, 6, 7)]

def save_retry(im, path, **kw):
    for _ in range(5):
        try:
            im.save(path, **kw); return
        except OSError:
            time.sleep(0.6)
    im.save(path, **kw)

def load_parts(sub, names):
    d = os.path.join(DIR, sub)
    return {n[3:]: np.asarray(Image.open(os.path.join(d, n + '.png')).convert('RGBA')).copy() for n in names}

FRONT = np.asarray(Image.open(os.path.join(RAW, '정면_64x64.png')).convert('RGBA')).copy()

# ---------------------------------------------------------------- 기본 변환
def canvas(w=64, h=64): return np.zeros((h, w, 4), np.uint8)
def compose(dst, src):
    out = dst.copy(); m = src[..., 3] > 0; out[m] = src[m]; return out
def shift(fr, dx=0, dy=0):
    out = np.zeros_like(fr); h, w = fr.shape[:2]
    ys0, ys1 = max(0, dy), min(h, h + dy); xs0, xs1 = max(0, dx), min(w, w + dx)
    if ys1 > ys0 and xs1 > xs0: out[ys0:ys1, xs0:xs1] = fr[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
    return out
def shear_about(fr, px, pivot_y):
    if px == 0: return fr.copy()
    out = np.zeros_like(fr)
    for y in range(fr.shape[0]):
        off = int(round(px * (pivot_y - y) / pivot_y)) if y < pivot_y else 0
        row = np.roll(fr[y], off, axis=0)
        if off > 0: row[:off] = 0
        elif off < 0: row[off:] = 0
        out[y] = row
    return out
def rotate_part(part, pivot, deg):
    if deg == 0: return part.copy()
    im = Image.fromarray(part, 'RGBA')
    return np.asarray(im.rotate(deg, resample=Image.NEAREST, center=(pivot[0] + 0.5, pivot[1] + 0.5), expand=False)).copy()
def limb_swing(part, pivot, dx, lift=0, toe=0):
    out = np.zeros_like(part); py = pivot[1]
    a = part[..., 3] > 0; ys = np.where(a.any(axis=1))[0]
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
def extend_top(part, px):
    if px <= 0: return part
    out = part.copy(); a = part[..., 3] > 0
    for x in range(part.shape[1]):
        ys = np.where(a[:, x])[0]
        if not len(ys): continue
        y0 = ys.min()
        for k in range(1, px + 1):
            if y0 - k >= 0 and out[y0 - k, x, 3] == 0: out[y0 - k, x] = part[y0, x]
    return out
def drape_hair(part, f, root_x=30):
    if f <= 0: return part.copy()
    out = np.zeros_like(part)
    for x in range(part.shape[1]):
        dy = int(round(f * max(0, root_x - x) * 0.55)); col = part[:, x]
        if dy: out[dy:, x] = col[:-dy]
        else: out[:, x] = col
    return out
def eyes(part, mode, rows=(26, 36)):
    if mode == 'open': return part
    out = part.copy(); r0, r1 = rows
    m = np.all(out[r0:r1, :, :3] == WHITE0, axis=2) & (out[r0:r1, :, 3] > 0)
    if mode == 'pink':
        out[r0:r1][m] = np.array([*PINK2, 255])
    else:
        out[r0:r1][m] = np.array([*SKIN1, 255])
        # 눈마다(열 덩어리마다) 가운데 행에 감은 선
        cols = m.any(axis=0); lab, n = ndimage.label(cols)
        for k in range(1, n + 1):
            xs = np.where(lab == k)[0]; rws = np.where(m[:, xs].any(axis=1))[0]
            mid = r0 + int(np.median(rws))
            seg = out[mid, xs.min():xs.max() + 1]
            seg[seg[..., 3] > 0] = np.array([*EYE6, 255]); out[mid, xs.min():xs.max() + 1] = seg
    return out
def smear_x(fr, dw):
    if dw == 0: return fr
    a = fr[..., 3] > 0; ys, xs = np.where(a)
    sp = fr[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    s = np.asarray(Image.fromarray(sp, 'RGBA').resize((sp.shape[1] + dw, sp.shape[0]), Image.NEAREST))
    out = np.zeros_like(fr); x0 = max(0, min(xs.min() - dw // 2, fr.shape[1] - s.shape[1])); y0 = ys.min()
    out[y0:y0 + s.shape[0], x0:x0 + s.shape[1]] = s
    return out
def flash(fr):
    a = fr[..., 3] > 0; inner = ndimage.binary_erosion(a, iterations=1)
    out = fr.copy(); out[a] = (*DARK7, 255); out[inner] = (255, 244, 240, 255); return out
def flip_in_place(fr):
    a = fr[..., 3] > 0; ys = np.where(a.any(axis=1))[0]
    def ax(m):
        rows = m[ys.max() - 5:ys.max() + 1]; xs = np.where(rows.any(axis=0))[0]; return (xs.min() + xs.max()) / 2
    m = fr[:, ::-1].copy()
    return shift(m, int(round(ax(a) - ax(m[..., 3] > 0))))
def put(fr, w=64, h=64, dx=0, dy=0):
    out = canvas(w, h); ox = (w - 64) // 2 + dx; oy = (h - 64) + dy
    sy0, sy1 = max(0, -oy), min(64, h - oy); sx0, sx1 = max(0, -ox), min(64, w - ox)
    out[oy + sy0:oy + sy1, ox + sx0:ox + sx1] = fr[sy0:sy1, sx0:sx1]
    return out
def mirror_move(part, dx, dy=0):
    """파츠를 자기 bbox 안에서 좌우 반전한 뒤 dx 이동(꼬리를 등 뒤로)."""
    a = part[..., 3] > 0; ys, xs = np.where(a)
    x0, x1 = xs.min(), xs.max() + 1
    out = np.zeros_like(part); out[:, x0:x1] = part[:, x0:x1][:, ::-1]
    return shift(out, dx, dy)

# ---------------------------------------------------------------- 리그
class Rig:
    def __init__(self, parts, piv, hip_row, arm_front_over_head_deg, eye_rows, tail_dx=None, tail_dy=0, front_foot_ground=0):
        self.P, self.piv, self.hip, self.over, self.eye_rows = parts, piv, hip_row, arm_front_over_head_deg, eye_rows
        self.tail = mirror_move(parts['꼬리'], tail_dx, tail_dy) if ('꼬리' in parts and tail_dx is not None) else None
        self.ffg = front_foot_ground   # 앞다리 기본 접지 보정(px, +아래)

    def pose(self, arm_f=0, arm_b=0, leg_f=0, leg_b=0, lift_f=0, lift_b=0, toe_f=0, toe_b=0, upper_dy=0, lean=0, body_dx=0,
             drape=0.0, hair_up=0, hair_dx=0, head_bow=0, eyes_mode='open', smear=0, tail_dx=0, only=None):
        P, piv = self.P, self.piv
        sel = lambda name, layer: layer if (only is None or name in only) else np.zeros_like(layer)
        legF = limb_swing(P['앞다리'], piv['앞다리'], leg_f, lift_f - self.ffg, toe_f)
        legB = limb_swing(P['뒷다리'], piv['뒷다리'], leg_b, lift_b, toe_b)
        if upper_dy < 0:
            legF = extend_top(legF, -upper_dy); legB = extend_top(legB, -upper_dy)
        hair = drape_hair(P['뒷머리'], drape) if drape else P['뒷머리']
        hair = shift(hair, hair_dx, -hair_up)
        armB = limb_swing(P['뒷팔'], piv['뒷팔'], arm_b)
        armF = rotate_part(P['앞팔'], piv['앞팔'], arm_f)
        head = shift(eyes(P['머리'], eyes_mode, self.eye_rows), head_bow, head_bow)
        upper = canvas()
        if self.tail is not None: upper = compose(upper, sel('꼬리', shift(self.tail, tail_dx, 0)))
        upper = compose(upper, sel('뒷머리', hair)); upper = compose(upper, sel('뒷팔', armB))
        f = compose(canvas(), shift(upper, 0, upper_dy))
        f = compose(f, sel('뒷다리', legB)); f = compose(f, sel('앞다리', legF))
        up2 = compose(canvas(), sel('치마', P['치마'])); up2 = compose(up2, sel('몸통', P['몸통']))
        arm_over = arm_f >= self.over
        if not arm_over: up2 = compose(up2, sel('앞팔', armF))
        up2 = compose(up2, sel('머리', head))
        if arm_over: up2 = compose(up2, sel('앞팔', armF))     # 머리 위로 든 팔은 얼굴 앞을 지난다
        f = compose(f, shift(up2, 0, upper_dy))
        if lean: f = shear_about(f, lean, self.hip)
        if body_dx: f = shift(f, body_dx, 0)
        if smear: f = smear_x(f, smear)
        return f

STAND = Rig(load_parts('파츠분할_걷기', ['01_꼬리', '02_뒷머리', '03_뒷팔', '04_뒷다리', '05_앞다리', '06_치마', '07_몸통', '08_앞팔', '09_머리']),
            {'뒷팔': (22, 37), '뒷다리': (24, 50), '앞다리': (34, 50), '앞팔': (38, 40)}, hip_row=50, arm_front_over_head_deg=120,
            eye_rows=(26, 36), tail_dx=-27, tail_dy=-3, front_foot_ground=1)
LUNGE = Rig(load_parts('파츠분할_공격', ['01_뒷머리', '02_뒷팔', '03_뒷다리', '04_앞다리', '05_치마', '06_몸통', '07_앞팔', '08_머리']),
            {'뒷팔': (22, 38), '뒷다리': (20, 47), '앞다리': (30, 49), '앞팔': (37, 38)}, hip_row=47, arm_front_over_head_deg=95,
            eye_rows=(26, 34))
S = STAND.pose
L = LUNGE.pose

# ---------------------------------------------------------------- 보행
def gait_stand(n, amp, lift, arm_amp, bob, tail_wag=1):
    """STAND 보행: 앞다리 dx = amp·cos, 뒷다리 반대. 앞으로 가는 다리를 들고 발끝을 앞세운다. 앞팔은 앞다리와 반대 위상."""
    frames = []
    for i in range(n):
        ph = 2 * np.pi * i / n; c = np.cos(ph); v = -np.sin(ph)
        dxf, dxb = int(round(amp * c)), int(round(-amp * c))
        f_sw, b_sw = v > 0.2, v < -0.2
        passing = abs(c) < 0.45
        frames.append(S(arm_f=int(round(-arm_amp * c)), arm_b=int(round(2 * c)), leg_f=dxf, leg_b=dxb,
                        lift_f=lift if f_sw else 0, lift_b=lift if b_sw else 0, toe_f=1 if f_sw else 0, toe_b=1 if b_sw else 0,
                        upper_dy=-(bob if passing else 0), hair_up=1 if passing else 0, tail_dx=int(round(tail_wag * c))))
    return frames

def gait_lunge(n, front, back, arm_deg, arm_amp, air, lean):
    frames = []
    for i in range(n):
        ph = 2 * np.pi * i / n; c = np.cos(ph); v = -np.sin(ph)
        dxf = int(round(front[0] + front[1] * c)); dxb = int(round(back[0] - back[1] * c))
        f_sw, b_sw = v > 0.2, v < -0.2
        fr = L(arm_f=arm_deg + arm_amp * c, arm_b=int(round(-2 * c)), leg_f=dxf, leg_b=dxb, lift_f=4 if f_sw else 0, lift_b=1 if b_sw else -4,
               toe_f=1 if f_sw else 0, toe_b=1 if b_sw else 0, hair_up=1 if abs(c) < 0.45 else 0, lean=lean)
        if air[i]: fr = shift(fr, 0, -air[i])
        frames.append(fr)
    return frames

# ---------------------------------------------------------------- 애니메이션 정의 (w, h, frames, ms, notes, cuts=의도된 큰 변화 프레임 쌍)
A = {}
A['대기'] = dict(w=64, h=64, ms=[180] * 4, cuts=[],
    frames=[S(), S(upper_dy=-1, tail_dx=1), S(hair_up=1), S(upper_dy=1, tail_dx=-1)],
    notes=['서기', '들숨 · 상체 1px 위 · 꼬리 +1', '머리카락 1px(따라 옴)', '날숨 · 상체 1px 아래 · 꼬리 −1'])
A['걷기'] = dict(w=64, h=64, ms=[110] * 8, cuts=[], frames=gait_stand(8, amp=5, lift=3, arm_amp=25, bob=1),
    notes=['접지(앞다리 앞 · 앞팔 뒤)', '앞다리 스탠스 · 뒷다리 들고 앞으로', '지나감 · 바운스 1', '뒷다리 착지 직전', '접지(뒷다리 앞 · 앞팔 앞)', '뒷다리 스탠스 · 앞다리 들고 앞으로', '지나감 · 바운스 1', '앞다리 착지 직전'])
A['달리기'] = dict(w=64, h=64, ms=[80] * 6, cuts=[], frames=gait_lunge(6, front=(-11, 11), back=(10, 10), arm_deg=-50, arm_amp=20, air=[0, 1, 2, 0, 1, 2], lean=2),
    notes=['접지(런지)', '밀기 · 1px 위', '공중 2px · 다리 교차', '접지(다리 바뀜)', '밀기 · 1px 위', '공중 2px'])

pre = [S(eyes_mode='pink', arm_f=-45, arm_b=-2, lean=-2, leg_b=2),
       S(eyes_mode='pink', arm_f=-80, arm_b=-4, lean=-4, upper_dy=1, leg_b=3, hair_dx=-1),
       S(eyes_mode='pink', arm_f=-95, arm_b=-4, lean=-4, upper_dy=1, leg_b=3, hair_dx=-1, hair_up=1)]
hit1 = L(arm_f=0, lean=3, body_dx=2, eyes_mode='pink')
hit2 = L(arm_f=4, lean=3, body_dx=3, eyes_mode='pink', smear=2)
post = [L(arm_f=0, lean=2, body_dx=2), L(arm_f=-25, lean=1, body_dx=1, leg_f=-4, leg_b=2, lift_b=-2),
        S(arm_f=35, lean=1, leg_f=3, leg_b=-3), S()]
A['하트참격'] = dict(w=80, h=64, ms=[100, 100, 120, 70, 70, 100, 100, 100, 100], cuts=[(3, 4), (7, 8)],
    frames=[put(x, 80) for x in pre + [hit1, hit2] + post],
    notes=['예고1 · 눈 분홍 · 양팔 뒤로 · 상체 뒤 2', '예고2 · 양팔 더 뒤로 · 상체 뒤 4 · 웅크림 1', '예고3 · 팔 95° 장전 · 머리카락', '타격1 · 런지 · 팔 앞으로 (손끝 = A4 정렬점)', '타격2 · 스미어 2 · 3px 앞', '후딜1 홀드', '후딜2 · 팔 내리는 중 · 다리 모으기', '후딜3 · 서기 자세로 · 팔 앞 35°', '후딜4 서기'])

pre2 = [S(eyes_mode='pink', arm_f=-45, arm_b=-3, lean=-2, leg_b=2),
        S(eyes_mode='pink', arm_f=-80, arm_b=-4, lean=-4, upper_dy=1, leg_b=3, hair_dx=-1, hair_up=1),
        S(eyes_mode='pink', arm_f=-95, arm_b=-4, lean=-4, upper_dy=1, leg_b=3, hair_dx=-1, hair_up=2)]
turn = eyes(FRONT, 'pink', (26, 34))
A['이단참격'] = dict(w=80, h=64, ms=[100, 100, 120, 70, 60, 70, 70, 100, 100, 100, 100], cuts=[(3, 4), (4, 5), (5, 6), (9, 10), (10, 11)],
    frames=[put(x, 80) for x in pre2 + [hit1, turn, flip_in_place(hit1), flip_in_place(hit2), flip_in_place(post[0]), flip_in_place(post[1]), flip_in_place(post[2]), S()]],
    notes=['예고1 · 양팔 뒤로', '예고2 · 머리카락 1', '예고3 · 머리카락 2(양손 신호)', '타격1', '전환 = 정면 절단(몸을 돌리는 중간)', '타격2 · 발 기준 반전(왼쪽 보기)', '타격2 스미어', '후딜1 반전 홀드', '후딜2 반전 · 팔 내리는 중', '후딜3 반전 · 서기 자세로', '서기(오른쪽 보기)'])

pre3 = [S(eyes_mode='pink', arm_f=40), S(eyes_mode='pink', arm_f=80, lean=1), S(eyes_mode='pink', arm_f=100, lean=1, hair_up=1)]
fire = [S(eyes_mode='pink', arm_f=90, lean=-2, body_dx=-1, hair_dx=1), S(eyes_mode='pink', arm_f=90, lean=-3, body_dx=-2, hair_dx=1)]
post3 = [S(arm_f=90, lean=-1), S(arm_f=60), S(arm_f=30), S()]
A['하트탄'] = dict(w=80, h=64, ms=[100, 100, 120, 70, 70, 100, 100, 100, 100], cuts=[],
    frames=[put(x, 80) for x in pre3 + fire + post3],
    notes=['예고1 · 눈 분홍 · 팔 앞으로 40°', '예고2 · 팔 80°', '예고3 · 팔 100° 손끝 위(하트 맺힘 = A4 정렬점)', '발사1 · 반동 상체 뒤 2 · 1px 뒤', '발사2 · 반동 3 · 2px 뒤', '후딜1 · 팔 뻗은 채', '후딜2 · 팔 60°', '후딜3 · 팔 30°', '후딜4 서기'])

hitpose = S(eyes_mode='closed', lean=-3, upper_dy=1, body_dx=-2, hair_dx=1)
A['피격'] = dict(w=64, h=64, ms=[50, 120, 100], cuts=[(1, 2)],
    frames=[flash(hitpose), hitpose, S()],
    notes=['흰 플래시(윤곽 유지)', '움찔 · 뒤로 2px · 상체 뒤 3 · 웅크림 1 · 눈 감음', '복귀 = 서기'])

t2 = S(body_dx=-2, arm_f=55, arm_b=2, head_bow=1, eyes_mode='closed', upper_dy=1)
A['페이즈전환'] = dict(w=64, h=64, ms=[120, 120, 200, 120, 120, 120, 120, 120], cuts=[],
    frames=[S(body_dx=-2), t2, t2, S(body_dx=-2, arm_f=55, arm_b=2, head_bow=1, eyes_mode='closed', upper_dy=1, hair_up=1),
            S(body_dx=-2, arm_f=30, eyes_mode='closed', hair_up=1), S(body_dx=-2, arm_f=10, eyes_mode='pink', hair_up=1),
            S(body_dx=-2, eyes_mode='pink', hair_up=2), S(body_dx=-2, eyes_mode='pink', hair_up=2)],
    notes=['뒤로 반 걸음', '고개 숙임 · 양손 가슴 앞(팔 55°) · 눈 감음 · 웅크림 1', '홀드 — A4 고리 퍼짐', '머리카락 1px 떠오름', '고개 든다 · 팔 내리는 중', '눈 뜸 · 밝은 분홍', '머리카락 2px 떠오름', '2페이즈 대기(= 7)'])

g = [S(eyes_mode='pink', arm_f=20), S(eyes_mode='pink', arm_f=50, arm_b=1, upper_dy=1), S(eyes_mode='pink', arm_f=55, arm_b=2, upper_dy=2, hair_up=1),
     S(eyes_mode='pink', arm_f=95, arm_b=-2, upper_dy=-2, hair_up=3), S(eyes_mode='pink', arm_f=100, arm_b=-2, upper_dy=-1, hair_up=3),
     S(eyes_mode='pink', arm_f=70, hair_up=2), S(arm_f=30, upper_dy=1, hair_up=1), S()]
A['마력고리'] = dict(w=96, h=80, ms=[100, 100, 120, 70, 70, 100, 100, 100], cuts=[],
    frames=[put(x, 96, 80) for x in g],
    notes=['예고1 · 눈 분홍 · 팔 올리기 20°', '예고2 · 양손 가슴 앞 50° · 웅크림 1', '예고3 · 웅크림 2 · 머리카락(충전)', '접촉1 · 양손 앞으로 편다 95° · 솟음 2 · 머리카락 3(A4 고리)', '접촉2 · 100° · 솟음 1', '후딜1 · 팔 70° · 머리카락 내려옴', '후딜2 · 팔 30° · 가라앉음 1', '후딜3 서기'])

d = [S(eyes_mode='pink', arm_f=-45, arm_b=-2, lean=-2, upper_dy=2, leg_b=2), S(eyes_mode='pink', arm_f=-70, arm_b=-4, lean=-3, upper_dy=3, leg_b=3, hair_up=1),
     S(eyes_mode='pink', arm_f=-80, arm_b=-4, lean=-4, upper_dy=4, leg_b=3, hair_up=1),
     L(eyes_mode='pink', arm_f=-110, lean=4, body_dx=3, smear=8, lift_b=1), L(eyes_mode='pink', arm_f=-60, lean=4, body_dx=6, smear=4, lift_b=1),
     shift(hit1, 4, 0), shift(post[0], 4, 0), shift(post[1], 3, 0), shift(S(arm_f=35, lean=1, leg_f=3, leg_b=-3), 2, 0)]
A['돌진참격'] = dict(w=80, h=64, ms=[100, 100, 120, 50, 50, 70, 100, 100, 100], cuts=[(3, 4), (8, 9)],
    frames=[put(x, 80) for x in d],
    notes=['예고1 · 뒤로 2 · 웅크림 2 · 양팔 뒤로', '예고2 · 웅크림 3', '예고3 · 웅크림 4 · 머리카락', '돌진1 · 스미어 8 · 앞기울임 4 · 팔 뒤로 끌림(화면 이동은 게임)', '돌진2 · 스미어 4 · 6px 앞', '타격 = 하트 참격 타격1(+4px)', '후딜1 홀드', '후딜2 · 팔 내리는 중', '후딜3 · 서기 자세(지나친 자리에서 멈춤)'])

w_ = [S(eyes_mode='pink', arm_f=30, arm_b=-1), S(eyes_mode='pink', arm_f=70, arm_b=-3, upper_dy=1), S(eyes_mode='pink', arm_f=95, arm_b=-4, upper_dy=1, hair_up=1),
      S(eyes_mode='pink', arm_f=95, arm_b=-4, upper_dy=-1, hair_up=2), S(eyes_mode='pink', arm_f=100, arm_b=-4, hair_up=2), S(eyes_mode='pink', arm_f=95, arm_b=-4, upper_dy=-1, hair_up=3),
      S(eyes_mode='pink', arm_f=140, arm_b=-2, hair_up=3), S(eyes_mode='pink', arm_f=170, arm_b=-1, upper_dy=1, hair_up=3), S(eyes_mode='pink', arm_f=175, upper_dy=-3, hair_up=4),
      S(arm_f=10, arm_b=1, upper_dy=2, head_bow=1), S(arm_f=0, upper_dy=1), S()]
A['마력폭주'] = dict(w=96, h=80, ms=[100, 100, 120, 80, 80, 80, 100, 120, 70, 120, 100, 100], cuts=[],
    frames=[put(x, 96, 80) for x in w_],
    notes=['예고1 · 눈 분홍 · 팔 30°', '예고2 · 양손 벌림 70° · 뒷팔 뒤로 · 웅크림 1', '예고3 · 팔 95° 수평 · 머리카락 1', '고리1 · 솟음 1 · 머리카락 2 (A4 반지름 1)', '고리2', '고리3 · 솟음 1 · 머리카락 3', '마지막 예고1 · 팔 140° 위로', '마지막 예고2 · 팔 170° 머리 위 · 웅크림 1(모음)', '폭발 · 팔 175° · 솟음 3 · 머리카락 최대', '후딜1 · 양팔 늘어짐 · 웅크림 2 · 고개 숙임', '후딜2 · 웅크림 1', '후딜3 서기'])

k = [S(eyes_mode='closed', lean=-2), S(eyes_mode='closed', lean=-3, body_dx=-2, arm_f=-5, upper_dy=1),
     S(eyes_mode='closed', lean=2, body_dx=-1, upper_dy=2), S(eyes_mode='closed', body_dx=-1, upper_dy=2, head_bow=1)]
A['그로기'] = dict(w=64, h=64, ms=[120, 120, 120, 150, 600], cuts=[], frames=k + [k[3]],
    notes=['움찔 · 눈 감음 · 상체 뒤 2', '뒤로 반 걸음 · 양팔 늘어짐 · 웅크림 1', '앞으로 기울며 비틀거림 · 웅크림 2', '다시 서며 고개 숙임', '멈춤 포즈 = 4 · 이 프레임에서 정지 · 색 변화 없음 · 서 있음'])

# ---------------------------------------------------------------- 저장 · QA
def frames_to_sheet(frames, w, h):
    sheet = Image.new('RGBA', (w * len(frames), h), (0, 0, 0, 0))
    for i, f in enumerate(frames): sheet.alpha_composite(Image.fromarray(f, 'RGBA'), (i * w, 0))
    return sheet
def save_gif(frames, durs, path, scale=4):
    rgb = []
    for f in frames:
        im = Image.fromarray(f, 'RGBA').resize((f.shape[1] * scale, f.shape[0] * scale), Image.NEAREST)
        bg = Image.new('RGBA', im.size, (51, 43, 47, 255)); bg.alpha_composite(im); rgb.append(bg.convert('RGB'))
    strip = Image.new('RGB', (rgb[0].width, rgb[0].height * len(rgb)))
    for i, im in enumerate(rgb): strip.paste(im, (0, i * im.height))
    master = strip.quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = [im.quantize(palette=master, dither=Image.Dither.NONE) for im in rgb]
    save_retry(pal[0], path, save_all=True, append_images=pal[1:], duration=list(durs), loop=0, optimize=False)

AIR_OK = {'달리기': {1: 1, 2: 2, 4: 1, 5: 2}}
def qa_check(key, w, h, frames, cuts):
    issues = []; foot_target = FOOT_Y + (h - 64)
    for i, f in enumerate(frames):
        a = f[..., 3] > 0
        if not a.any(): issues.append(f'{i+1}: 빈 프레임'); continue
        ys = np.where(a.any(axis=1))[0]; xs = np.where(a.any(axis=0))[0]
        expect = foot_target - AIR_OK.get(key, {}).get(i, 0)
        if int(ys.max()) != expect: issues.append(f'{i+1}: 발바닥 y{int(ys.max())} (기대 {expect})')
        if ys.min() <= 0: issues.append(f'{i+1}: 위 잘림')
        if xs.min() <= 0 or xs.max() >= w - 1: issues.append(f'{i+1}: 좌우 잘림')
        al = f[..., 3]
        if ((al > 0) & (al < 255)).any(): issues.append(f'{i+1}: 반투명')
        lab, n = ndimage.label(a, structure=np.ones((3, 3)))
        if n > 1:
            sizes = sorted(ndimage.sum(a, lab, range(1, n + 1)), reverse=True)
            if sizes[1] >= 3: issues.append(f'{i+1}: 떨어진 조각 {int(sizes[1])}px')
        uniq = np.unique(f[a][:, :3], axis=0)
        extra = [c for c in uniq if not any(np.array_equal(c, p) for p in PAL)]
        if extra and not (key == '피격' and i == 0): issues.append(f'{i+1}: 팔레트 밖 색 {len(extra)}종')
    # 연속성: 실루엣 IoU
    for i in range(len(frames) - 1):
        a, b = frames[i][..., 3] > 0, frames[i + 1][..., 3] > 0
        iou = (a & b).sum() / max(1, (a | b).sum())
        if iou < 0.6 and (i + 1, i + 2) not in cuts: issues.append(f'{i+1}→{i+2}: 실루엣 변화 큼 (IoU {iou:.2f})')
    return issues

font = ImageFont.truetype(FONT, 14)
report = {}
for key, spec in A.items():
    w, h, frames, durs, notes, cuts = spec['w'], spec['h'], spec['frames'], spec['ms'], spec['notes'], spec['cuts']
    assert len(frames) == len(durs) == len(notes), key
    for f in frames: assert f.shape[:2] == (h, w), (key, f.shape)
    fn = f'보스_{key}_시트_{w}x{h}x{len(frames)}.png'
    save_retry(frames_to_sheet(frames, w, h), os.path.join(DIR, fn))
    save_gif(frames, durs, os.path.join(DIR, f'미리보기_{key}.gif'))
    issues = qa_check(key, w, h, frames, cuts)
    report[key] = dict(file=fn, frames=len(frames), canvas=[w, h], durations_ms=durs, notes=notes, qa_issues=issues)
    Sx, per = 8, 4
    rows_n = (len(frames) + per - 1) // per
    film = Image.new('RGBA', ((w * Sx + 12) * per + 12, (h * Sx + 44) * rows_n + 40), (51, 43, 47, 255)); dr = ImageDraw.Draw(film)
    for i, f in enumerate(frames):
        r, c_ = divmod(i, per); x = 12 + c_ * (w * Sx + 12); y = 30 + r * (h * Sx + 44)
        film.alpha_composite(Image.fromarray(f, 'RGBA').resize((w * Sx, h * Sx), Image.NEAREST), (x, y))
        gy = y + (FOOT_Y + (h - 64)) * Sx + Sx
        dr.line([(x, gy), (x + w * Sx, gy)], fill=(90, 140, 110, 255))
        dr.text((x, y - 18), f'{i+1}. {notes[i][:40]}', font=font, fill=(230, 220, 220))
    dr.text((12, film.height - 22), f'{key} {w}×{h}×{len(frames)} · ' + ('자동검사 통과' if not issues else '자동검사: ' + '; '.join(issues)), font=font, fill=(230, 220, 220))
    save_retry(film, os.path.join(QA_DIR, f'{key}.png'))
    print(key, 'issues:', issues if issues else 'none')

def hand_tip(fr):
    a = fr[..., 3] > 0; xs = np.where(a.any(axis=0))[0]; x = int(xs.max()); ys = np.where(a[:, x])[0]; return [x, int(ys.mean())]
def head_center(fr):
    a = fr[..., 3] > 0; ys = np.where(a.any(axis=1))[0]; rows = a[ys.min():ys.min() + 30]; xs = np.where(rows.any(axis=0))[0]
    return [int((xs.min() + xs.max()) / 2), int(ys.min() + 15)]
HIT1_ARM = put(L(arm_f=0, lean=3, body_dx=2, only={'앞팔'}), 80)
BULLET_ARM = put(S(arm_f=100, lean=1, only={'앞팔'}), 80)
RING_ARM = put(S(arm_f=95, arm_b=-2, upper_dy=-2, only={'앞팔'}), 96, 80)
pts = {'발바닥 y(64 캔버스)': FOOT_Y, '머리 중앙 (대기, 64)': head_center(A['대기']['frames'][0]), '가슴 중앙 (대기, 64)': [head_center(A['대기']['frames'][0])[0], 40],
       '손끝 (하트참격 타격1, 80)': hand_tip(HIT1_ARM), '손끝 (하트탄 예고3, 80)': hand_tip(BULLET_ARM), '손끝 (마력고리 접촉1, 96×80)': hand_tip(RING_ARM),
       '머리 중앙 (마력고리 접촉1, 96×80)': head_center(A['마력고리']['frames'][3])}
json.dump(dict(sheets=report, points=pts, rig='boss_rig.py v8 · STAND=파츠분할_걷기 · LUNGE=파츠분할_공격'), open(os.path.join(DIR, '_build.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(pts)
lines = ['# 자동 QA 결과 (boss_rig.py v8)', '', '검사: 캔버스 · 발바닥 y62(공중 프레임 제외) · 위/좌우 잘림 · 반투명 · 팔레트 12색 · 떨어진 조각(8방향 연결, 3px 이상) · 연속 프레임 실루엣 IoU ≥ 0.6(의도된 컷 제외)', '',
         '| 시트 | 프레임 | 결과 | 문제 |', '|---|---|---|---|']
for key, v in report.items():
    lines.append(f"| {key} | {v['frames']} | {'통과' if not v['qa_issues'] else '실패'} | {'; '.join(v['qa_issues']) if v['qa_issues'] else '—'} |")
open(os.path.join(DIR, '_QA_자동검사.md'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')

rows = list(A.items()); S3 = 3
W3 = max(spec['w'] * len(spec['frames']) for _, spec in rows) * S3 + 20; H3 = sum((spec['h'] + 14) * S3 for _, spec in rows) + 20
ov = Image.new('RGBA', (W3, H3), (51, 43, 47, 255)); d3 = ImageDraw.Draw(ov); y3 = 10
for key, spec in rows:
    d3.text((10, y3), f"{key} {spec['w']}×{spec['h']}×{len(spec['frames'])}", font=font, fill=(230, 220, 220)); y3 += 14 * S3
    ov.alpha_composite(frames_to_sheet(spec['frames'], spec['w'], spec['h']).resize((spec['w'] * len(spec['frames']) * S3, spec['h'] * S3), Image.NEAREST), (10, y3)); y3 += spec['h'] * S3
save_retry(ov, os.path.join(DIR, '_QA_전체시트_x3.png'))

hero = np.asarray(Image.open(os.path.join(ROOT, '미리보기_걷기8.gif')).convert('RGBA'))[::4, ::4].copy()
bgc = hero[0, 0, :3]; hero[np.all(hero[..., :3] == bgc, axis=2), 3] = 0
cmp_ = Image.new('RGBA', ((64 * 3 + 80) * 4 + 50, 64 * 4 + 40), (51, 43, 47, 255)); xx = 10
for fr in [hero, A['대기']['frames'][0], A['걷기']['frames'][0], A['하트참격']['frames'][3]]:
    im = Image.fromarray(fr, 'RGBA').resize((fr.shape[1] * 4, fr.shape[0] * 4), Image.NEAREST); cmp_.alpha_composite(im, (xx, 20)); xx += im.width + 10
ImageDraw.Draw(cmp_).text((10, 2), '주인공 64 · 보스 대기 · 걷기1 · 하트참격 타격(80) — 같은 바닥선, 4배', font=font, fill=(230, 220, 220))
save_retry(cmp_, os.path.join(DIR, 'QA_주인공비교_4x.png'))
print('done')
