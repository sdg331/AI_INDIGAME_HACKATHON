# -*- coding: utf-8 -*-
"""
보스 바르갈 1단계 러프 생성기.
- 파라메트릭(키 K 기준 설계 좌표)으로 2등신 치비 보스를 그린다.
- 산출물: 캔버스 규격 비교 · 실루엣 후보 3종(단색 + 채색) · 마족 피부 색 실험.
실행: python draw_vargal.py   (작업 폴더 = 꼬리치레 루트)
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUT = os.path.join(ROOT, 'outputs', '보스_바르갈_v1')
os.makedirs(OUT, exist_ok=True)
FONT = 'C:/Windows/Fonts/malgun.ttf'
BG = (51, 43, 47, 255)  # 미리보기 배경 (주인공 GIF와 동일)

# ---------------------------------------------------------------- 색 유틸
def mix(a, b, t):
    return tuple(int(round(a[i] * (1 - t) + b[i] * t)) for i in range(3))

WARM_WHITE = (255, 240, 220)
COOL_DARK = (58, 40, 72)
LINE_DARK = (44, 32, 48)

def tone(base):
    """base → (light, dark, outline). 따뜻한 하이라이트 · 차가운 그림자 · 부드러운 외곽선."""
    return mix(base, WARM_WHITE, 0.30), mix(base, COOL_DARK, 0.38), mix(base, LINE_DARK, 0.68)

# ---------------------------------------------------------------- 레이어 셰이딩
def _shift(mp, pad, dy, dx, H, W):
    return mp[pad + dy:pad + dy + H, pad + dx:pad + dx + W]

def shade_and_outline(layer, base, mode='rim', hl=1, sh=2, outline_col=None, light=None, dark=None):
    a = np.array(layer)
    m = a[:, :, 3] > 0
    if not m.any():
        return layer
    H, W = m.shape
    light_c, dark_c, out_c = tone(base)
    if light is not None: light_c = light
    if dark is not None: dark_c = dark
    if outline_col is not None: out_c = outline_col
    pad = 6
    mp = np.pad(m, pad)
    rgb = a[:, :, :3].copy()
    if mode == 'rim':
        shadow = np.zeros_like(m)
        for k in range(1, sh + 1):
            shadow |= ~_shift(mp, pad, k, k, H, W) | ~_shift(mp, pad, k, 0, H, W) | ~_shift(mp, pad, 0, k, H, W)
        high = np.zeros_like(m)
        for k in range(1, hl + 1):
            high |= ~_shift(mp, pad, -k, -k, H, W) | ~_shift(mp, pad, -k, 0, H, W) | ~_shift(mp, pad, 0, -k, H, W)
        rgb[m & shadow] = dark_c
        rgb[m & high & ~shadow] = light_c
    elif mode == 'band':
        ys = np.where(m.any(axis=1))[0]
        y0, y1 = ys.min(), ys.max()
        rows = np.arange(H)[:, None]
        shadow = m & (rows > y0 + (y1 - y0) * 0.62)
        high = m & (rows < y0 + (y1 - y0) * 0.18)
        # 오른쪽 가장자리 2px도 그림자
        for k in range(1, 3):
            shadow |= m & ~_shift(mp, pad, 0, k, H, W)
        rgb[shadow] = dark_c
        rgb[high & ~shadow] = light_c
    a[:, :, :3] = rgb
    # outline (바깥 1px)
    ring = np.zeros_like(m)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ring |= _shift(mp, pad, dy, dx, H, W)
    ring &= ~m
    a[ring, :3] = out_c
    a[ring, 3] = 255
    return Image.fromarray(a, 'RGBA')

# ---------------------------------------------------------------- 스프라이트
class Sprite:
    """설계 좌표: 원점 = 발 중앙(바닥), x = 바라보는 방향(+), y = 위(+). K=112 기준 설계."""
    def __init__(self, W, H, K, facing=1, bottom_margin=0):
        self.W, self.H, self.K = W, H, K
        self.s = K / 112.0
        self.f = facing
        self.cx = W // 2
        self.y0 = H - 1 - bottom_margin
        self.img = Image.new('RGBA', (W, H), (0, 0, 0, 0))

    # 좌표 변환
    def P(self, x, y):
        return (self.cx + self.f * x * self.s, self.y0 - y * self.s)

    def bbox(self, x0, x1, ylo, yhi):
        a = self.P(x0, yhi); b = self.P(x1, ylo)
        return [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])]

    def poly(self, pts):
        return [self.P(x, y) for x, y in pts]

    def part(self, fn, base, mode='rim', hl=1, sh=2, outline=None, light=None, dark=None):
        layer = Image.new('RGBA', (self.W, self.H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        fn(d, base + (255,))
        layer = shade_and_outline(layer, base, mode, hl, sh, outline, light, dark)
        self.img.alpha_composite(layer)

    def flat(self, fn, col):
        """외곽선·셰이딩 없이 바로 그린다 (눈·트림 등)."""
        d = ImageDraw.Draw(self.img)
        fn(d, col + (255,))

    def silhouette(self, col=(70, 56, 68)):
        a = np.array(self.img)
        m = a[:, :, 3] > 0
        out = np.zeros_like(a)
        out[m] = col + (255,)
        return Image.fromarray(out, 'RGBA')

# ---------------------------------------------------------------- 팔레트
PAL = {
    'skin':   (150, 132, 158),   # 마족 피부 · 재보라(ash violet) — 색 실험 1안
    'skin_hl': (188, 172, 192),
    'plate':  (74, 66, 84),      # 흑철 판금
    'plate_hl': (112, 104, 124),
    'gold':   (206, 164, 92),    # 금 트림
    'cape':   (132, 52, 58),     # 찢긴 망토 · 어두운 적색
    'hair':   (52, 40, 60),      # 머리카락 · 검보라
    'horn':   (216, 196, 168),   # 뿔 · 뼈색
    'eye':    (255, 196, 72),    # 발광 눈 · 호박색
    'eye_core': (120, 40, 30),
    'steel':  (176, 182, 196),   # 검신
    'steel_hl': (226, 230, 238),
    'grip':   (96, 62, 48),
    'fur':    (128, 118, 112),   # 늑대 털 · 회갈색
    'fur_dk': (88, 78, 76),
    'fang':   (240, 232, 214),
    'claw':   (222, 206, 176),
    'nose':   (48, 34, 40),
    'leather': (110, 74, 58),
}

# ---------------------------------------------------------------- 공통 부위
def draw_cape(sp, col, top_y=62, x_back=-34, x_front=10, bottom=10, fur=False):
    def fn(d, c):
        pts = [(x_front - 2, top_y), (x_back + 10, top_y - 2), (x_back, top_y - 26), (x_back - 2, bottom + 14),
               (x_back + 6, bottom), (x_back + 12, bottom + 10), (x_back + 18, bottom + 2), (x_back + 24, bottom + 12),
               (x_back + 30, bottom + 4), (x_front, bottom + 16), (x_front + 2, top_y - 20)]
        d.polygon(sp.poly(pts), fill=c)
    sp.part(fn, col, mode='band', sh=3)

def draw_back_leg(sp, plate, x=-15):
    def fn(d, c):
        d.rounded_rectangle(sp.bbox(x, x + 14, 6, 30), radius=3 * sp.s, fill=c)
        d.rounded_rectangle(sp.bbox(x - 2, x + 16, 0, 9), radius=2 * sp.s, fill=c)
    sp.part(fn, mix(plate, COOL_DARK, 0.25))

def draw_front_leg(sp, plate, x=1):
    def fn(d, c):
        d.rounded_rectangle(sp.bbox(x, x + 15, 6, 30), radius=3 * sp.s, fill=c)
        d.rounded_rectangle(sp.bbox(x - 1, x + 20, 0, 9), radius=2 * sp.s, fill=c)  # 사바톤
    sp.part(fn, plate)

def draw_torso(sp, plate, w=22, ylo=22, yhi=60):
    def fn(d, c):
        d.rounded_rectangle(sp.bbox(-w, w, ylo, yhi), radius=6 * sp.s, fill=c)
    sp.part(fn, plate, sh=3)

def draw_belt(sp, ylo=24, yhi=30, w=21):
    sp.part(lambda d, c: d.rectangle(sp.bbox(-w, w, ylo, yhi), fill=c), PAL['leather'], sh=1)
    sp.flat(lambda d, c: d.rectangle(sp.bbox(-3, 4, ylo + 1, yhi - 1), fill=c), PAL['gold'])

def draw_pauldron(sp, plate, cx=25, cy=58, rx=13, ry=9, spikes=True, back=False):
    col = mix(plate, COOL_DARK, 0.25) if back else plate
    def fn(d, c):
        d.ellipse(sp.bbox(cx - rx, cx + rx, cy - ry, cy + ry), fill=c)
        if spikes:
            d.polygon(sp.poly([(cx - 6, cy + ry - 2), (cx - 2, cy + ry + 8), (cx + 3, cy + ry - 2)]), fill=c)
            d.polygon(sp.poly([(cx + 4, cy + ry - 3), (cx + 10, cy + ry + 5), (cx + 12, cy + ry - 5)]), fill=c)
    sp.part(fn, col, sh=3)
    if not back:
        sp.flat(lambda d, c: d.line(sp.poly([(cx - rx + 3, cy - 2), (cx + rx - 3, cy - 2)]), fill=c, width=max(1, int(2 * sp.s))), PAL['gold'])

def draw_front_arm(sp, plate, shoulder=(22, 54), hand=(31, 32), w=10):
    def fn(d, c):
        d.line([sp.P(*shoulder), sp.P(*hand)], fill=c, width=int(w * sp.s))
        d.ellipse(sp.bbox(shoulder[0] - w / 2, shoulder[0] + w / 2, shoulder[1] - w / 2, shoulder[1] + w / 2), fill=c)
        d.rounded_rectangle(sp.bbox(hand[0] - 7, hand[0] + 7, hand[1] - 7, hand[1] + 6), radius=2 * sp.s, fill=c)  # 건틀릿
    sp.part(fn, plate)

def draw_greatsword(sp, hand=(31, 30), tip=(66, -1), pommel=(22, 44), blade_w=9, jagged=False):
    hx, hy = hand
    tx, ty = tip
    dx, dy = tx - hx, ty - hy
    L = (dx * dx + dy * dy) ** 0.5
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux  # 법선
    # 손잡이
    def grip(d, c):
        d.line([sp.P(*pommel), sp.P(hx, hy)], fill=c, width=int(6 * sp.s))
        d.ellipse(sp.bbox(pommel[0] - 4, pommel[0] + 4, pommel[1] - 4, pommel[1] + 4), fill=c)
    sp.part(grip, PAL['grip'], sh=1)
    # 날
    def blade(d, c):
        g = 6  # 가드에서 시작
        bx, by = hx + ux * g, hy + uy * g
        pts = [(bx + nx * blade_w / 2, by + ny * blade_w / 2), (bx - nx * blade_w / 2, by - ny * blade_w / 2),
               (tx - ux * 6 - nx * blade_w * 0.35, ty - uy * 6 - ny * blade_w * 0.35), (tx, ty),
               (tx - ux * 6 + nx * blade_w * 0.35, ty - uy * 6 + ny * blade_w * 0.35)]
        if jagged:
            pts = [pts[0]] + [(bx + ux * t * L * 0.8 + nx * blade_w * (0.5 + (0.35 if i % 2 else 0)),
                               by + uy * t * L * 0.8 + ny * blade_w * (0.5 + (0.35 if i % 2 else 0)))
                              for i, t in enumerate(np.linspace(0.15, 0.85, 6))] + [(tx, ty)] + pts[2:3][::-1] + [pts[1]]
        d.polygon(sp.poly(pts), fill=c)
    sp.part(blade, PAL['steel'], sh=2, hl=1)
    # 풀러(혈조) 라인
    def fuller(d, c):
        d.line([sp.P(hx + ux * 10, hy + uy * 10), sp.P(hx + ux * (L - 12), hy + uy * (L - 12))], fill=c, width=max(1, int(1.5 * sp.s)))
    sp.flat(fuller, mix(PAL['steel'], COOL_DARK, 0.3))
    # 가드
    def guard(d, c):
        gx, gy = hx + ux * 5, hy + uy * 5
        pts = [(gx + nx * 11, gy + ny * 11), (gx - nx * 11, gy - ny * 11), (gx - nx * 11 + ux * 4, gy - ny * 11 + uy * 4), (gx + nx * 11 + ux * 4, gy + ny * 11 + uy * 4)]
        d.polygon(sp.poly(pts), fill=c)
    sp.part(guard, PAL['gold'], sh=1)

def draw_head_skin(sp, skin, cx=0, cy=84, rx=26, ry=28):
    sp.part(lambda d, c: d.ellipse(sp.bbox(cx - rx, cx + rx, cy - ry, cy + ry), fill=c), skin, sh=3, hl=2)

def draw_hair_back(sp, col):
    def fn(d, c):
        d.ellipse(sp.bbox(-30, 6, 78, 114), fill=c)                       # 정수리~뒤통수
        d.polygon(sp.poly([(-6, 113), (4, 112), (12, 106), (16, 96), (2, 100), (-4, 108)]), fill=c)  # 앞머리 쓸어넘김
        d.polygon(sp.poly([(-24, 98), (-40, 90), (-30, 82), (-42, 74), (-26, 72), (-22, 80)]), fill=c)  # 뒤로 뻗친 머리
    sp.part(fn, col, sh=3)

def draw_horn(sp, col, base=(-8, 104), tip=(-26, 128), back=False, ctrl=None, r0=5.0, r1=1.5):
    bx, by = base; tx, ty = tip
    cx_, cy_ = ctrl if ctrl else (bx + 4, ty + 2)
    def fn(d, c):
        for t in np.linspace(0, 1, 28):
            x = (1 - t) ** 2 * bx + 2 * (1 - t) * t * cx_ + t * t * tx
            y = (1 - t) ** 2 * by + 2 * (1 - t) * t * cy_ + t * t * ty
            r = r0 * (1 - t) + r1 * t
            d.ellipse(sp.bbox(x - r, x + r, y - r, y + r), fill=c)
    sp.part(fn, mix(col, COOL_DARK, 0.3) if back else col, sh=1, hl=1)

def draw_face(sp, eye=(13, 86), brow=True, mouth=True):
    ex, ey = eye
    # 눈 : 발광 호박색 + 어두운 동공
    sp.flat(lambda d, c: d.ellipse(sp.bbox(ex - 3, ex + 4, ey - 4, ey + 3), fill=c), PAL['eye'])
    sp.flat(lambda d, c: d.rectangle(sp.bbox(ex + 1, ex + 3, ey - 3, ey + 1), fill=c), PAL['eye_core'])
    sp.flat(lambda d, c: d.rectangle(sp.bbox(ex - 2, ex - 1, ey + 1, ey + 2), fill=c), (255, 250, 230))
    if brow:
        sp.flat(lambda d, c: d.line(sp.poly([(ex - 6, ey + 8), (ex + 7, ey + 5)]), fill=c, width=max(1, int(2 * sp.s))), PAL['hair'])
    if mouth:
        sp.flat(lambda d, c: d.line(sp.poly([(ex + 2, ey - 14), (ex + 9, ey - 13)]), fill=c, width=max(1, int(1.5 * sp.s))), mix(PAL['skin'], COOL_DARK, 0.5))

def draw_gorget(sp, plate):
    sp.part(lambda d, c: d.rounded_rectangle(sp.bbox(-17, 19, 54, 63), radius=4 * sp.s, fill=c), mix(plate, WARM_WHITE, 0.08), sh=2)

def draw_chest_trim(sp):
    sp.flat(lambda d, c: d.line(sp.poly([(0, 30), (0, 54)]), fill=c, width=max(1, int(2 * sp.s))), mix(PAL['plate'], COOL_DARK, 0.4))
    sp.flat(lambda d, c: d.line(sp.poly([(-16, 44), (16, 44)]), fill=c, width=max(1, int(1.5 * sp.s))), PAL['gold'])

# ---------------------------------------------------------------- 후보 A · 늑대 요소 없음
def candidate_A(sp, skin=None):
    skin = skin or PAL['skin']
    plate = PAL['plate']
    draw_cape(sp, PAL['cape'])
    draw_pauldron(sp, plate, cx=-24, cy=57, back=True)
    draw_back_leg(sp, plate)
    draw_front_leg(sp, plate)
    draw_torso(sp, plate)
    draw_chest_trim(sp)
    draw_belt(sp)
    draw_gorget(sp, plate)
    draw_greatsword(sp)
    draw_front_arm(sp, plate)
    draw_pauldron(sp, plate)
    draw_horn(sp, PAL['horn'], base=(6, 104), tip=(-8, 124), ctrl=(14, 120), back=True)
    draw_head_skin(sp, skin)
    draw_hair_back(sp, PAL['hair'])
    draw_horn(sp, PAL['horn'], base=(-8, 104), tip=(-26, 123), ctrl=(-2, 122))
    draw_face(sp)

# ---------------------------------------------------------------- 후보 B · 갑주 장식 정도 (늑대 가죽 후드 + 늑대 머리 견갑 + 이빨 목걸이)
def draw_wolf_pelt_cape(sp):
    draw_cape(sp, PAL['fur'], top_y=64, x_back=-36, x_front=8, bottom=12)

def draw_wolf_hood(sp):
    fur = PAL['fur']
    def fn(d, c):
        d.ellipse(sp.bbox(-32, 12, 82, 122), fill=c)              # 두개골 부분 (정수리~뒤통수)
        d.ellipse(sp.bbox(2, 38, 96, 116), fill=c)                # 주둥이 (이마 위로 나옴)
        d.polygon(sp.poly([(-24, 110), (-16, 124), (-6, 114)]), fill=c)   # 귀 뒤
        d.polygon(sp.poly([(-8, 116), (2, 126), (10, 116)]), fill=c)      # 귀 앞
    sp.part(fn, fur, sh=3, hl=2)
    # 가죽의 늑대 눈(빈 눈구멍)·코
    sp.flat(lambda d, c: d.ellipse(sp.bbox(33, 38, 106, 111), fill=c), PAL['nose'])
    sp.flat(lambda d, c: d.rectangle(sp.bbox(14, 19, 108, 112), fill=c), PAL['fur_dk'])
    # 가죽 이빨 (주둥이 아래)
    for x in (12, 19, 26):
        sp.flat(lambda d, c, x=x: d.polygon(sp.poly([(x, 97), (x + 3, 90), (x + 6, 97)]), fill=c), PAL['fang'])

def draw_wolf_pauldron(sp, plate):
    def fn(d, c):
        d.ellipse(sp.bbox(12, 38, 48, 68), fill=c)                # 늑대 머리 형태 견갑
        d.ellipse(sp.bbox(30, 46, 46, 58), fill=c)                # 주둥이
        d.polygon(sp.poly([(16, 66), (22, 78), (28, 66)]), fill=c) # 귀
    sp.part(fn, plate, sh=3)
    sp.flat(lambda d, c: d.ellipse(sp.bbox(26, 31, 58, 63), fill=c), PAL['eye'])
    sp.flat(lambda d, c: d.ellipse(sp.bbox(42, 46, 50, 54), fill=c), PAL['nose'])

def draw_fang_necklace(sp):
    for i, x in enumerate((-10, -3, 4, 11)):
        y = 52 + (0 if i in (1, 2) else 2)
        sp.flat(lambda d, c, x=x, y=y: d.polygon(sp.poly([(x, y + 2), (x + 3, y - 6), (x + 6, y + 2)]), fill=c), PAL['fang'])

def candidate_B(sp, skin=None):
    skin = skin or PAL['skin']
    plate = PAL['plate']
    draw_wolf_pelt_cape(sp)
    draw_pauldron(sp, plate, cx=-24, cy=57, back=True, spikes=False)
    draw_back_leg(sp, plate)
    draw_front_leg(sp, plate)
    draw_torso(sp, plate)
    draw_chest_trim(sp)
    draw_belt(sp)
    draw_gorget(sp, plate)
    draw_fang_necklace(sp)
    draw_greatsword(sp)
    draw_front_arm(sp, plate)
    draw_wolf_pauldron(sp, plate)
    draw_head_skin(sp, skin)
    draw_wolf_hood(sp)
    draw_horn(sp, PAL['horn'], base=(-20, 100), tip=(-36, 118), ctrl=(-24, 116), r0=4, r1=1.5)  # 후드 밖으로 삐져나온 작은 뿔
    draw_face(sp, eye=(14, 82))

# ---------------------------------------------------------------- 후보 C · 수인형
def draw_tail(sp):
    def fn(d, c):
        d.polygon(sp.poly([(-18, 26), (-34, 22), (-48, 34), (-56, 52), (-50, 60), (-44, 46), (-34, 34), (-20, 34)]), fill=c)
    sp.part(fn, PAL['fur'], sh=2)

def draw_beast_leg(sp, x, back=False):
    col = mix(PAL['fur'], COOL_DARK, 0.25) if back else PAL['fur']
    def fn(d, c):
        d.ellipse(sp.bbox(x - 9, x + 9, 16, 34), fill=c)              # 허벅지
        d.line([sp.P(x + 2, 24), sp.P(x - 4, 10)], fill=c, width=int(9 * sp.s))  # 정강이(뒤로 꺾임)
        d.polygon(sp.poly([(x - 10, 0), (x - 10, 9), (x - 2, 11), (x + 14, 7), (x + 16, 0)]), fill=c)  # 발
    sp.part(fn, col, sh=2)
    for cx in (x + 4, x + 9, x + 14):
        sp.flat(lambda d, c, cx=cx: d.polygon(sp.poly([(cx, 3), (cx + 3, -1), (cx + 5, 4)]), fill=c), PAL['claw'])

def draw_beast_arm(sp, shoulder=(20, 52), hand=(31, 30)):
    def fn(d, c):
        d.line([sp.P(*shoulder), sp.P(*hand)], fill=c, width=int(11 * sp.s))
        d.ellipse(sp.bbox(shoulder[0] - 6, shoulder[0] + 6, shoulder[1] - 6, shoulder[1] + 6), fill=c)
        d.ellipse(sp.bbox(hand[0] - 8, hand[0] + 8, hand[1] - 8, hand[1] + 7), fill=c)
    sp.part(fn, PAL['fur'], sh=2)
    for i, (cx, cy) in enumerate(((hand[0] + 4, hand[1] - 8), (hand[0] + 8, hand[1] - 5), (hand[0] + 9, hand[1] + 1))):
        sp.flat(lambda d, c, cx=cx, cy=cy: d.polygon(sp.poly([(cx, cy), (cx + 6, cy - 3), (cx + 1, cy - 4)]), fill=c), PAL['claw'])

def draw_wolf_head(sp, skin):
    fur = PAL['fur']
    def fn(d, c):
        d.ellipse(sp.bbox(-26, 22, 58, 112), fill=c)                       # 두개골
        d.ellipse(sp.bbox(8, 42, 66, 92), fill=c)                          # 주둥이
        d.polygon(sp.poly([(-20, 104), (-14, 124), (-2, 108)]), fill=c)    # 귀 뒤
        d.polygon(sp.poly([(-4, 108), (6, 126), (14, 108)]), fill=c)       # 귀 앞
        d.ellipse(sp.bbox(-30, 8, 50, 76), fill=c)                         # 목 털 (러프)
    sp.part(fn, fur, sh=3, hl=2)
    # 주둥이 아래쪽·귀 안쪽은 피부색(마족 피부 노출)
    sp.flat(lambda d, c: d.ellipse(sp.bbox(12, 40, 66, 78), fill=c), mix(skin, WARM_WHITE, 0.1))
    sp.flat(lambda d, c: d.polygon(sp.poly([(0, 110), (6, 126), (11, 110)]), fill=c), skin)
    # 코 · 입선 · 이빨
    sp.flat(lambda d, c: d.ellipse(sp.bbox(37, 43, 84, 90), fill=c), PAL['nose'])
    sp.flat(lambda d, c: d.line(sp.poly([(14, 74), (40, 78)]), fill=c, width=max(1, int(1.5 * sp.s))), PAL['nose'])
    for x in (18, 26, 33):
        sp.flat(lambda d, c, x=x: d.polygon(sp.poly([(x, 76), (x + 2, 69), (x + 5, 76)]), fill=c), PAL['fang'])
    # 눈 (사납게 기울인 눈)
    sp.flat(lambda d, c: d.polygon(sp.poly([(2, 88), (16, 93), (16, 98), (4, 96)]), fill=c), PAL['eye'])
    sp.flat(lambda d, c: d.rectangle(sp.bbox(10, 13, 92, 96), fill=c), PAL['eye_core'])
    # 작은 뿔 (마족 공통 표식)
    draw_horn(sp, PAL['horn'], base=(-14, 104), tip=(-30, 122), ctrl=(-14, 120), r0=4, r1=1.5)

def candidate_C(sp, skin=None):
    skin = skin or PAL['skin']
    plate = PAL['plate']
    draw_tail(sp)
    draw_beast_leg(sp, -12, back=True)
    draw_pauldron(sp, plate, cx=-22, cy=56, back=True, spikes=False)
    draw_beast_leg(sp, 4)
    # 털 몸통 + 흉갑(부분 갑주)
    sp.part(lambda d, c: d.rounded_rectangle(sp.bbox(-22, 22, 20, 60), radius=8 * sp.s, fill=c), PAL['fur'], sh=3)
    sp.part(lambda d, c: d.rounded_rectangle(sp.bbox(-16, 18, 30, 56), radius=5 * sp.s, fill=c), plate, sh=2)
    draw_belt(sp, ylo=22, yhi=28, w=20)
    draw_greatsword(sp, jagged=True, blade_w=11)
    draw_beast_arm(sp)
    draw_pauldron(sp, plate, cx=24, cy=57, rx=12, ry=8)
    draw_wolf_head(sp, skin)

CANDS = [
    ('A', '늑대없음', candidate_A, '마족 기사 — 늑대 요소 없음'),
    ('B', '갑주장식', candidate_B, '갑주 장식 정도 — 늑대 가죽 후드 · 늑대 머리 견갑 · 이빨 목걸이'),
    ('C', '수인형',   candidate_C, '수인형 — 늑대 머리 · 짐승 다리 · 꼬리 · 발톱'),
]

# ---------------------------------------------------------------- 주인공 64×64 추출
def load_hero():
    im = Image.open(os.path.join(ROOT, '미리보기_걷기8.gif')); im.seek(0)
    a = np.array(im.convert('RGBA'))[::4, ::4].copy()
    bg = a[0, 0, :3]
    m = np.all(a[:, :, :3] == bg, axis=2)
    a[m, 3] = 0
    return Image.fromarray(a, 'RGBA')

# ---------------------------------------------------------------- 출력 유틸
def up(img, n):
    return img.resize((img.width * n, img.height * n), Image.NEAREST)

def canvas_frame(img, col=(120, 100, 110, 255)):
    """캔버스 테두리 1px 표시용."""
    fr = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(fr)
    d.rectangle([0, 0, img.width - 1, img.height - 1], outline=col)
    fr.alpha_composite(img)
    return fr

def label(draw, xy, text, size=14, col=(235, 225, 220)):
    draw.text(xy, text, font=ImageFont.truetype(FONT, size), fill=col)

# ---------------------------------------------------------------- 1. 캔버스 규격 비교
SPECS = [
    ('1안', 128, 128, 104, '키 104px · 주인공 1.73배'),
    ('2안', 160, 128, 112, '키 112px · 주인공 1.87배 · 추천'),
    ('3안', 192, 160, 140, '키 140px · 주인공 2.33배'),
]

def make_size_compare(hero):
    S = 3
    gap = 24
    total_w = sum(w for _, w, _, _, _ in SPECS) + 64 * len(SPECS) + gap * (len(SPECS) + 1) + 8 * len(SPECS)
    total_h = 160 + 40
    sheet = Image.new('RGBA', (total_w * S, total_h * S + 60), BG)
    d = ImageDraw.Draw(sheet)
    x = gap
    ground = 160 + 8  # 바닥선 (1x 좌표)
    for name, W, H, K, desc in SPECS:
        sp = Sprite(W, H, K, facing=-1)
        candidate_A(sp)
        boss = canvas_frame(sp.img)
        hero_f = canvas_frame(hero)
        # 주인공 왼쪽, 보스 오른쪽, 바닥선 맞춤
        hx, hy = x, ground - 64
        bx, by = x + 64 + 8, ground - H
        sheet.alpha_composite(up(hero_f, S), (hx * S, hy * S))
        sheet.alpha_composite(up(boss, S), (bx * S, by * S))
        d.line([(x * S, ground * S), ((bx + W) * S, ground * S)], fill=(150, 120, 130, 255), width=2)
        label(d, (x * S, (ground + 4) * S), f'{name}  {W}×{H}', 22)
        label(d, (x * S, (ground + 4) * S + 30), desc, 16, (200, 190, 190))
        label(d, (hx * S, (hy - 8) * S), '주인공 64×64 · 키 60', 14, (200, 190, 190))
        x = bx + W + gap
    label(d, (gap * S, 8), '보스 캔버스 규격 초안 — 후보 A 실루엣으로 비교 · Pivot = Bottom Center · 같은 PPU · 3배 확대', 20)
    sheet.save(os.path.join(OUT, '캔버스규격_크기비교.png'))

# ---------------------------------------------------------------- 2. 실루엣 후보 3종
def make_candidates(hero):
    W, H, K = 160, 128, 112
    S = 4
    for key, name, fn, desc in CANDS:
        sp = Sprite(W, H, K, facing=1)
        fn(sp)
        sp.img.save(os.path.join(OUT, f'실루엣후보_{key}_{name}_1x_{W}x{H}.png'))
        sil = sp.silhouette()
        # 미리보기: 실루엣 | 채색 | 주인공 대비
        sheet = Image.new('RGBA', ((W * 2 + 64 + 40) * S, (H + 36) * S), BG)
        d = ImageDraw.Draw(sheet)
        sheet.alpha_composite(up(canvas_frame(sil), S), (8 * S, 30 * S))
        sheet.alpha_composite(up(canvas_frame(sp.img), S), ((W + 16) * S, 30 * S))
        sheet.alpha_composite(up(canvas_frame(hero), S), ((W * 2 + 24) * S, (30 + H - 64) * S))
        label(d, (8 * S, 6 * S), f'후보 {key} · {desc}', 28)
        label(d, (8 * S, 16 * S), '단색 실루엣', 18, (200, 190, 190))
        label(d, ((W + 16) * S, 16 * S), f'채색 러프 · {W}×{H} · 키 {K}', 18, (200, 190, 190))
        label(d, ((W * 2 + 24) * S, (30 + H - 64 - 10) * S), '주인공', 18, (200, 190, 190))
        sheet.save(os.path.join(OUT, f'실루엣후보_{key}_{name}.png'))
    # 3종 한 장 (1x, 가로 배치 — 시트 형식)
    sheet = Image.new('RGBA', (W * 3, H), (0, 0, 0, 0))
    for i, (key, name, fn, desc) in enumerate(CANDS):
        sp = Sprite(W, H, K, facing=1); fn(sp)
        sheet.alpha_composite(sp.img, (i * W, 0))
    sheet.save(os.path.join(OUT, f'실루엣후보_3종_시트_{W}x{H}x3.png'))
    # 3종 나란히 미리보기 (주인공 포함, 마주보게)
    S = 3
    pv = Image.new('RGBA', ((64 + 16 + W * 3 + 32) * S, (H + 44) * S), BG)
    d = ImageDraw.Draw(pv)
    pv.alpha_composite(up(hero, S), (8 * S, (36 + H - 64) * S))
    for i, (key, name, fn, desc) in enumerate(CANDS):
        sp = Sprite(W, H, K, facing=-1); fn(sp)
        x = 64 + 16 + i * W + 8
        pv.alpha_composite(up(sp.img, S), (x * S, 36 * S))
        label(d, (x * S, 20 * S), f'{key} · {name}', 22)
    label(d, (8 * S, 6 * S), '실루엣 후보 3종 · 주인공과 같은 바닥선 · 3배 확대', 22)
    d.line([(0, (36 + H) * S), (pv.width, (36 + H) * S)], fill=(150, 120, 130, 255), width=2)
    pv.save(os.path.join(OUT, '실루엣후보_3종_나란히.png'))

# ---------------------------------------------------------------- 3. 마족 피부 색 실험
SKINS = [
    ('S1 재보라',  (150, 132, 158), '회색에 보라 한 방울. 주인공 살구색과 보색 관계라 한눈에 다른 종족'),
    ('S2 청회',    (128, 140, 160), '차가운 돌빛. 단단한 피부 = 돌·강철 연상. 배경 보라 하늘과 겹칠 위험'),
    ('S3 적갈',    (166, 118, 112), '주인공과 같은 난색 계열. 가장 따뜻하지만 주인공과 구분이 약함'),
    ('S4 뼈회',    (176, 168, 150), '탈색된 뼈빛. 가장 밝아 실루엣 대비 큼. 창백해서 언데드로 읽힐 위험'),
]

def make_skin_test(hero):
    S = 4
    W, H, K = 96, 96, 72   # 흉상만 보이도록 작은 키
    cell_w = W + 8
    sheet = Image.new('RGBA', ((64 + 16 + cell_w * len(SKINS) + 16) * S, (H + 90) * S), BG)
    d = ImageDraw.Draw(sheet)
    sheet.alpha_composite(up(hero, S), (8 * S, (60 + H - 64) * S))
    label(d, (8 * S, (60 + H + 4) * S), '주인공', 18, (200, 190, 190))
    # 주인공 피부 스와치
    hero_skin = (237, 199, 167)
    d.rectangle([8 * S, (60 + H + 14) * S, (8 + 12) * S, (60 + H + 26) * S], fill=hero_skin + (255,))
    label(d, ((8 + 14) * S, (60 + H + 14) * S), '#%02X%02X%02X' % hero_skin, 16, (200, 190, 190))
    for i, (name, skin, note) in enumerate(SKINS):
        x = 64 + 16 + i * cell_w + 8
        sp = Sprite(W, H, K, facing=-1, bottom_margin=0)
        PAL['skin'] = skin
        # 흉상: 후보 A의 머리·견갑·고짓만
        plate = PAL['plate']
        draw_pauldron(sp, plate, cx=-24, cy=57, back=True)
        draw_torso(sp, plate)
        draw_gorget(sp, plate)
        draw_pauldron(sp, plate)
        draw_horn(sp, PAL['horn'], base=(6, 104), tip=(-8, 124), ctrl=(14, 120), back=True)
        draw_head_skin(sp, skin)
        draw_hair_back(sp, PAL['hair'])
        draw_horn(sp, PAL['horn'], base=(-8, 104), tip=(-26, 123), ctrl=(-2, 122))
        draw_face(sp)
        sheet.alpha_composite(up(sp.img, S), (x * S, 60 * S))
        light, dark, out = tone(skin)
        label(d, (x * S, 40 * S), name, 20)
        for j, (c, t) in enumerate(((light, '밝음'), (skin, '기본'), (dark, '그늘'), (out, '선'))):
            sx = x + j * 22
            d.rectangle([sx * S, (60 + H + 4) * S, (sx + 20) * S, (60 + H + 16) * S], fill=c + (255,))
            label(d, (sx * S, (60 + H + 17) * S), '#%02X%02X%02X' % c, 11, (200, 190, 190))
    PAL['skin'] = SKINS[0][1]
    label(d, (8 * S, 6 * S), '마족 피부 색 실험 — 4안 · A2(근접 유닛) 팔레트가 나오면 그쪽에 맞춘다', 24)
    label(d, (8 * S, 18 * S), '기준: 주인공 살구색(#EDC7A7)과 같은 화면에서 종족이 다르게 읽히되, 따뜻하고 부드러운 톤을 벗어나지 않을 것', 16, (200, 190, 190))
    sheet.save(os.path.join(OUT, '색실험_마족피부_4안.png'))

# ---------------------------------------------------------------- 팔레트 기록
def dump_palette():
    lines = []
    for k, v in PAL.items():
        lines.append(f'| {k} | #%02X%02X%02X | {v} |' % v)
    with open(os.path.join(OUT, '_작업파일', 'palette.md'), 'w', encoding='utf-8') as f:
        f.write('| 키 | HEX | RGB |\n|---|---|---|\n' + '\n'.join(lines) + '\n')

def report_coords():
    print('| 규격 | 키 K | 발 바닥 행(y) | 머리 중앙 (x, y) | 머리 꼭대기 y | 점유 영역 x0..x1, y0..y1 (후보 A/B/C) |')
    for name, W, H, K, desc in SPECS:
        sp = Sprite(W, H, K)
        hc = sp.P(0, 84); ht = sp.P(0, 112)
        ext = []
        for key, nm, fn, _ in CANDS:
            s2 = Sprite(W, H, K); fn(s2)
            a = np.array(s2.img)[:, :, 3] > 0
            ys, xs = np.where(a)
            ext.append(f'{key}: {xs.min()}..{xs.max()}, {ys.min()}..{ys.max()}')
        print(f'| {name} {W}×{H} | {K} | {sp.y0} | ({int(hc[0])}, {int(round(hc[1]))}) | {int(round(ht[1]))} | ' + ' / '.join(ext) + ' |')

if __name__ == '__main__':
    hero = load_hero()
    report_coords()
    make_size_compare(hero)
    make_candidates(hero)
    make_skin_test(hero)
    dump_palette()
    print('done →', OUT)
