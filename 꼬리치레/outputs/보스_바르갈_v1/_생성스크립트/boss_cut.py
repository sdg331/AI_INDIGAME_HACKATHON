# -*- coding: utf-8 -*-
"""보스2.png → 원본프레임/ (손질 전 64px 프레임 17장 + 확인용 4배 시트).
보스_애니메이션_제작문서.md 부록 스크립트를 바탕으로, 배경 분리를 연결성 기반으로 바꾸고
프리멀티플라이 BOX 축소(적 파이프라인 enemy_anim.py 방식)로 배경색 번짐을 막았다.
실행: 프로젝트 루트에서  python outputs/보스_바르갈_v1/_생성스크립트/boss_cut.py
"""
import os, json
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SRC = os.path.join(ROOT, '보스2.png')
OUT = os.path.join(ROOT, 'outputs', '보스_바르갈_v1', '원본프레임')
os.makedirs(OUT, exist_ok=True)

# 이름: (영역 x0,y0,x1,y1, 캔버스 폭, 캔버스 높이, 반전 여부)  — 제작문서 1절
REGIONS = {
    '정면':  (300, 90, 540, 450, 64, 64, False),
    '후면':  (560, 90, 790, 450, 64, 64, False),
    '좌측':  (810, 90, 1020, 450, 64, 64, True),
    '우측':  (1040, 90, 1240, 450, 64, 64, False),
    '이동1': (40, 640, 190, 820, 64, 64, True),
    '이동2': (190, 640, 340, 820, 64, 64, True),
    '이동3': (340, 640, 490, 820, 64, 64, True),
    '이동4': (490, 640, 640, 820, 64, 64, True),
    '이동5': (640, 640, 790, 820, 64, 64, True),
    '이동6': (790, 640, 940, 820, 64, 64, True),
    '이동7': (940, 640, 1090, 820, 64, 64, True),
    '이동8': (1090, 640, 1240, 820, 64, 64, True),
    '대기':  (40, 945, 200, 1180, 64, 64, False),
    '달리기': (240, 945, 440, 1180, 64, 64, False),
    '공격':  (455, 945, 700, 1180, 80, 64, False),
    '피격':  (730, 945, 920, 1180, 64, 64, False),
    '스킬':  (940, 940, 1245, 1180, 96, 80, False),
}
PALETTE = [(0xFC,0xE8,0xDF),(0xF6,0xCF,0xC5),(0xE7,0xA1,0xAC),(0x6D,0x32,0x5B),
           (0xEA,0xD7,0xD5),(0xBD,0x96,0xA4),(0x96,0x56,0x7B),(0x28,0x1F,0x2B),
           (0x61,0x31,0x53),(0x4D,0x32,0x45),(0x2F,0x22,0x30),(0x43,0x2B,0x36)]
PAL = np.array(PALETTE)
BODY_H = 60
FOOT_Y = 62

im = Image.open(SRC).convert('RGB')
A = np.asarray(im).astype(int)
BG = A[600, 20]

def cell(name):
    x0, y0, x1, y1, cw, ch, flip = REGIONS[name]
    c = A[y0:y1, x0:x1]
    diff = np.abs(c - BG).sum(axis=2)
    lum = c.max(axis=2); sat = lum - c.min(axis=2)
    # 배경 #000101 과 거의 같은(차이 12 이하) 픽셀 중 가장자리와 이어진 성분만 배경으로.
    # 부츠·드레스 최암부는 차이 10~60이라 60 기준으로는 빠진다(실측).
    fg = diff > 12
    lab, _ = ndimage.label(~fg)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    alpha = ~np.isin(lab, list(border))
    alpha = ndimage.binary_closing(alpha, iterations=2) | alpha
    # 바닥 그림자: 아래 30% 띠의 저채도 회색
    ys = np.where(alpha.any(axis=1))[0]
    band_top = ys.min() + int((ys.max() - ys.min()) * 0.70)
    # 실측: 그림자 본체 ≈ (170,158,152) 채도 20 미만 · 밝기 120~200, 가장자리는 회색 (60,56,54)~(105,94,94) 채도 12 미만.
    # 부츠는 자주색(채도 13 이상)이라 남는다. 발이 그림자 타원 안에 겹쳐 있으므로 행으로 자르지 않고 색으로 뺀다.
    # v3: 그림자 본체(회색, 밝기 90~200 · 채도 22 미만) + 어두운 테두리(채도 8 미만 · 밝기 25~90).
    #     부츠는 채도 13 이상 또는 밝기 90 미만이라 남고, 머리카락 밝음(밝기 234)은 상한에 걸려 남는다.
    gray = alpha & (((sat < 22) & (lum >= 90) & (lum <= 200)) | ((sat < 8) & (lum >= 25) & (lum < 90)))
    gray[:band_top] = False
    lab_s, ns = ndimage.label(gray)
    big = np.zeros_like(gray)
    for i, sz in enumerate(ndimage.sum(gray, lab_s, range(1, ns + 1)), 1):
        if sz >= 150: big |= (lab_s == i)
    shadow = big | (ndimage.binary_dilation(big, iterations=2) & alpha & (sat < 30) & (lum >= 25) & (lum <= 205))
    shadow[:band_top] = False
    alpha &= ~shadow
    # v3: 그림자가 다리 사이 · 드레스 아래의 검은 배경을 둘러싸 「막힌 영역」으로 만들었다 → 그림자를 뺀 뒤 배경 연결성을 다시 검사
    bgpix = (diff <= 12) | ~alpha
    lab_b, _ = ndimage.label(bgpix)
    border_b = set(np.unique(np.concatenate([lab_b[0], lab_b[-1], lab_b[:, 0], lab_b[:, -1]]))) - {0}
    alpha &= ~np.isin(lab_b, list(border_b))
    # 그래도 남는 큰 순수 검정 덩어리(400px 이상)는 배경으로 본다 (눈동자 같은 작은 검정은 남김)
    lab_k, nk = ndimage.label(alpha & (lum <= 15))
    for i, sz in enumerate(ndimage.sum(alpha & (lum <= 15), lab_k, range(1, nk + 1)), 1):
        if sz >= 400: alpha &= ~(lab_k == i)
    # 얇은 세로 구분선 · 라벨 조각 제거: 몸에서 떨어진 작은 성분
    lab2, n = ndimage.label(alpha)
    sizes = ndimage.sum(alpha, lab2, range(1, n + 1))
    keep = np.zeros_like(alpha)
    for i, s in enumerate(sizes, 1):
        if s >= 400: keep |= (lab2 == i)
    alpha = keep
    return c, alpha, (cw, ch, flip)

def shrink(rgb, alpha, scale):
    h, w = alpha.shape
    a = alpha[..., None].astype(float)
    pm = np.dstack([rgb * a, alpha * 255]).astype(np.uint8)
    img = Image.fromarray(pm, 'RGBA').resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.BOX)
    s = np.asarray(img).astype(float); al = s[..., 3:4]
    col = np.where(al > 0, s[..., :3] / np.maximum(al / 255, 1e-6), 0)
    keep = al[..., 0] >= 110
    return np.clip(col, 0, 255), keep

def quantize(rgb, keep):
    px = rgb.reshape(-1, 3)
    d = ((px[:, None, :] - PAL[None, :, :]) ** 2).sum(-1)
    q = PAL[d.argmin(1)].reshape(rgb.shape).astype(np.uint8)
    return np.dstack([q, keep.astype(np.uint8) * 255])

def place(rgba, cw, ch, anchor_x=None):
    h, w = rgba.shape[:2]
    canvas = np.zeros((ch, cw, 4), np.uint8)
    ax = w / 2 if anchor_x is None else anchor_x
    ox = int(round(cw / 2 - ax)); oy = (FOOT_Y + (ch - 64)) - h + 1
    x0, y0 = max(ox, 0), max(oy, 0)
    x1, y1 = min(ox + w, cw), min(oy + h, ch)
    canvas[y0:y1, x0:x1] = rgba[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
    return canvas

if __name__ == '__main__':
    info = {}
    previews = []
    for name in REGIONS:
        c, alpha, (cw, ch, flip) = cell(name)
        ys, xs = np.where(alpha)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        body_h = y1 - y0
        if name == '스킬':
            # 고리가 머리 위·발 아래로 퍼진다 → 몸 높이는 손으로 (문서: 발 y≈1160, 머리 y≈985)
            gy0 = REGIONS[name][1]
            y0, y1 = 985 - gy0, 1161 - gy0
            body_h = y1 - y0
        scale = BODY_H / body_h
        rgb, keep = shrink(c[y0:y1, x0:x1], alpha[y0:y1, x0:x1], scale)
        q = quantize(rgb, keep)
        if flip: q = q[:, ::-1]
        # 발 위치 앵커: 아래 6행에서 불투명 픽셀의 x 중심
        foot = q[-6:, :, 3] > 0
        fx = np.where(foot.any(axis=0))[0]
        anchor = (fx.min() + fx.max()) / 2 if len(fx) else q.shape[1] / 2
        canvas = place(q, cw, ch, anchor)
        Image.fromarray(canvas, 'RGBA').save(os.path.join(OUT, f'{name}_{cw}x{ch}.png'))
        info[name] = dict(bbox=[int(x0 + REGIONS[name][0]), int(y0 + REGIONS[name][1]), int(x1 + REGIONS[name][0]), int(y1 + REGIONS[name][1])],
                          body_h=int(body_h), scale=round(scale, 4), small=[int(q.shape[1]), int(q.shape[0])], flip=flip, anchor=float(anchor))
        previews.append(Image.fromarray(canvas, 'RGBA').resize((cw * 4, ch * 4), Image.NEAREST))
        print(name, info[name])
    W = sum(p.width for p in previews); H = max(p.height for p in previews)
    sheet = Image.new('RGBA', (W, H), (40, 30, 30, 255)); x = 0
    for p in previews:
        sheet.alpha_composite(p, (x, H - p.height)); x += p.width
    sheet.save(os.path.join(OUT, '_확인용_4배.png'))
    json.dump(info, open(os.path.join(OUT, '_절단정보.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
