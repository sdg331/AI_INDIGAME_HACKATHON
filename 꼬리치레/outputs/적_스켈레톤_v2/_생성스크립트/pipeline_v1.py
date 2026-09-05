"""v1 enemy_anim.py의 1~3절(셀 탐지 · 정리 · 64px 축소 · 24색 양자화)을 함수로 분리한 것. 로직은 v1과 같다."""
import sys, os, json
import numpy as np
from PIL import Image
from scipy import ndimage

def build(src, SHADOW_MAX=150, SHADOW_COOL=False, SMALL_MIN=120, palette_hex=None, extra=()):
 """원본 시트 → {이름: (RGBA ndarray, 앵커x)} 64px 밀도 스프라이트 + 팔레트. v1 enemy_anim.py 1~3절과 동일."""
 FOOT_Y = 62          # 발바닥 선 (0부터) — 주인공·A2 시트와 동일
 KEY_H = 58           # 대기 포즈 키(px). 주인공 60px보다 살짝 낮게
 im = Image.open(src).convert("RGB")
 A = np.asarray(im).astype(int)

 # ---------- 1. 셀 탐지 ----------
 lum = A.max(axis=2)
 m = ndimage.binary_dilation(ndimage.binary_opening(lum > 60, iterations=1), iterations=6)
 lab, _ = ndimage.label(m)
 boxes = []
 for sl in ndimage.find_objects(lab):
     y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
     if (y1 - y0) > 150 and (x1 - x0) > 40:
         boxes.append((x0, y0, x1, y1))
 boxes.sort(key=lambda b: (round(b[1] / 120), b[0]))
 names = ["front", "back", "left", "right"] + [f"walk{i}" for i in range(1, 9)] + ["idle", "run", "attack", "hit", "skill"]
 cells = dict(zip(names, boxes[:17]))

 # ---------- 2. 셀 정리 ----------
 def clean(box, pad=10, strip_light_fx=False):
     x0, y0, x1, y1 = box
     x0, y0 = max(0, x0 - pad), max(0, y0 - pad); x1, y1 = min(A.shape[1], x1 + pad), min(A.shape[0], y1 + pad)
     c = A[y0:y1, x0:x1].copy()
     l = c.max(axis=2); mn = c.min(axis=2); sat = l - mn
     # 배경: 가장자리와 이어진 어두운 영역
     lab2, _ = ndimage.label(l < 48)
     border = set(np.unique(np.concatenate([lab2[0], lab2[-1], lab2[:, 0], lab2[:, -1]]))) - {0}
     alpha = ~np.isin(lab2, list(border))
     # 다리 사이처럼 막힌 순수 검정(배경색) 영역: 면적 큰 것만 제거(눈구멍은 남김)
     lab_bk, _ = ndimage.label(l <= 15)
     for i, sl in enumerate(ndimage.find_objects(lab_bk), 1):
         comp = lab_bk == i
         if comp.sum() > 400:
             alpha &= ~comp
     # 세로 구분선(얇고 긴 회색) 제거
     lab3, _ = ndimage.label(alpha & (sat < 30))
     for i, sl in enumerate(ndimage.find_objects(lab3), 1):
         hh, ww = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
         if hh > 3 * ww and ww < 20 and hh > 120:
             alpha &= ~(lab3 == i)
     # 바닥 그림자: 스프라이트 아래 30% 띠 안의 저채도 중간 회색. 그림자 중심 x를 앵커로 기록
     ys = np.where(alpha.any(axis=1))[0]
     band_top = ys.min() + int((ys.max() - ys.min()) * 0.70)
     shadow = alpha & (sat < 30) & (l >= 35) & (l <= SHADOW_MAX)
     if SHADOW_COOL: shadow &= (c[..., 0] - c[..., 2]) < 12
     shadow[:band_top] = False
     sx = np.where(shadow.any(axis=0))[0]
     anchor = float((sx.min() + sx.max()) / 2) if len(sx) > 20 else None
     alpha &= ~shadow
     # 밝은 참격 이펙트(고블린 공격 셀): 크고 밝은 저채도 덩어리 제거
     if strip_light_fx:
         light = alpha & (sat < 45) & (l > 175)
         lab4, _ = ndimage.label(light)
         for i, sl in enumerate(ndimage.find_objects(lab4), 1):
             comp = (lab4 == i)
             hh = sl[0].stop - sl[0].start
             if comp.sum() > 800:   # 참격 호 조각(2570·1008px) 제거. 칼날(546px)은 남김
                 alpha &= ~ndimage.binary_dilation(comp, iterations=1)
         # 남은 세로로 긴 밝은 조각(호의 가장자리): 칼날은 대각선이라 bbox가 정방형에 가까움
         light2 = alpha & (sat < 75) & (l > 150)
         lab6, _ = ndimage.label(light2)
         for i, sl in enumerate(ndimage.find_objects(lab6), 1):
             comp = (lab6 == i); hh = sl[0].stop - sl[0].start; ww = sl[1].stop - sl[1].start
             if comp.sum() > 120 and hh > 2.2 * ww:
                 alpha &= ~ndimage.binary_dilation(comp, iterations=1)
     # 고립 조각 정리
     core = ndimage.binary_opening(alpha, iterations=2)
     alpha = alpha & ndimage.binary_dilation(core, iterations=4)
     # 몸에서 떨어진 작은 조각(이펙트 파편·충격선) 제거: 500px 미만 성분
     lab5, _ = ndimage.label(alpha)
     for i, sl in enumerate(ndimage.find_objects(lab5), 1):
         comp = lab5 == i
         if comp.sum() < (500 if strip_light_fx else SMALL_MIN):
             alpha &= ~comp
     ys, xs = np.where(alpha)
     y0c, y1c, x0c, x1c = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
     if anchor is None: anchor = (x0c + x1c) / 2
     rgba = np.dstack([c, alpha * 255]).astype(np.uint8)[y0c:y1c, x0c:x1c]
     return rgba, anchor - x0c

 raw = {}
 for k in ["walk1", "walk2", "walk3", "walk4", "walk5", "walk6", "walk7", "walk8", "idle", "run", "attack", "hit"] + list(extra):
     raw[k] = clean(cells[k], strip_light_fx=(k == "attack"))

 # ---------- 3. 64px 밀도로 축소 + 공통 팔레트 ----------
 scale = KEY_H / raw["idle"][0].shape[0]
 def shrink(rgba, ax):
     h, w = rgba.shape[:2]
     img = Image.fromarray(rgba, "RGBA")
     # 프리멀티플라이로 배경색 번짐 방지
     arr = np.asarray(img).astype(float); a = arr[..., 3:4] / 255
     pm = Image.fromarray(np.dstack([arr[..., :3] * a, arr[..., 3]]).astype(np.uint8), "RGBA")
     s = pm.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.BOX)
     sa = np.asarray(s).astype(float); al = sa[..., 3:4]
     rgb = np.where(al > 0, sa[..., :3] / np.maximum(al / 255, 1e-6), 0)
     keep = (al[..., 0] >= 110)
     out = np.dstack([np.clip(rgb, 0, 255), keep * 255]).astype(np.uint8)
     return out, ax * scale

 small = {k: shrink(*v) for k, v in raw.items()}
 # 팔레트 통일(모든 프레임 합쳐 24색)
 if palette_hex:
  palette = np.array([[int(h[i:i+2], 16) for i in (1, 3, 5)] for h in palette_hex])
 else:
  allpx = np.concatenate([s[0][s[0][..., 3] > 0][:, :3] for s in small.values()])
  pal_img = Image.fromarray(allpx.reshape(1, -1, 3), "RGB").quantize(colors=24, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
  palette = np.array(pal_img.getpalette()[:24 * 3]).reshape(-1, 3)
 def quantize(arr):
     px = arr[..., :3].reshape(-1, 3).astype(int)
     d = ((px[:, None, :] - palette[None, :, :]) ** 2).sum(-1)
     q = palette[d.argmin(1)].reshape(arr.shape[0], arr.shape[1], 3)
     return np.dstack([q, arr[..., 3]]).astype(np.uint8)
 small = {k: (quantize(v[0]), v[1]) for k, v in small.items()}

 return small, scale, palette
