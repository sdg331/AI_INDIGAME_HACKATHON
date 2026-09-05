# 기사_보충_v1 자동 QA: 규격(발바닥·캔버스·알파), 고립 픽셀, 팔레트 밖 색, 몸 안 구멍, 프레임 간 머리 중앙 편차 + 1x/2x 확인용 스트립
import os, glob, sys
import numpy as np
from PIL import Image, ImageDraw
from collections import deque
from kb import *

BODY_PAL = {tuple(int(v) for v in c) for c in np.unique(BASE[alpha(BASE)][:, :3], axis=0)}
for f in F:
    for c in np.unique(f[alpha(f)][:, :3], axis=0): BODY_PAL.add(tuple(int(v) for v in c))
EXTRA_OK = {(214, 222, 230), (248, 250, 252), (150, 160, 176), (243, 196, 74), (255, 236, 160), (196, 134, 38), (255, 255, 255),
            (76, 58, 55), (51, 43, 47), (137, 117, 111), (216, 193, 177), (183, 153, 138), (91, 80, 80), (237, 199, 167), (62, 54, 55)}

def components(mask):
    H, W = mask.shape; seen = np.zeros_like(mask); comps = []
    for y in range(H):
        for x in range(W):
            if mask[y, x] and not seen[y, x]:
                comp = [(y, x)]; seen[y, x] = True; q = deque(comp)
                while q:
                    cy, cx = q.popleft()
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):   # 8방향(대각선 1px 선은 이어진 것으로 본다)
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < H and 0 <= nx < W and mask[ny, nx] and not seen[ny, nx]:
                                seen[ny, nx] = True; q.append((ny, nx)); comp.append((ny, nx))
                comps.append(comp)
    return comps

def holes(img):
    """몸 안에 갇힌 투명 픽셀 덩어리(외부와 연결되지 않은 투명 영역)."""
    a = ~alpha(img); H, W = a.shape
    out = np.zeros_like(a); q = deque()
    for k in range(H):
        for p in ((k, 0), (k, W - 1)):
            if a[p] and not out[p]: out[p] = True; q.append(p)
    for k in range(W):
        for p in ((0, k), (H - 1, k)):
            if a[p] and not out[p]: out[p] = True; q.append(p)
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and a[ny, nx] and not out[ny, nx]: out[ny, nx] = True; q.append((ny, nx))
    enclosed = a & ~out
    return components(enclosed)

def check_sheet(path, w, h, foot_y, grounded_frames=None, allow_empty=()):
    s = np.array(Image.open(path).convert("RGBA")); n = s.shape[1] // w
    report = []
    for i in range(n):
        f = s[:, i * w:(i + 1) * w]
        issues = []
        al = f[..., 3]
        if ((al > 0) & (al < 255)).any(): issues.append("반투명 알파")
        if not alpha(f).any():
            if i not in allow_empty: issues.append("빈 프레임")
            report.append((i, issues)); continue
        yy, xx = np.where(alpha(f))
        if yy.max() > foot_y: issues.append(f"바닥 넘침 y{yy.max()}")
        if grounded_frames is None or i in grounded_frames:
            if yy.max() != foot_y: issues.append(f"발바닥 y{yy.max()}≠{foot_y}")
        small = [c for c in components(alpha(f)) if len(c) < 3]
        if small: issues.append(f"고립픽셀 {len(small)}개 {[(c[0][1], c[0][0]) for c in small[:3]]}")
        hs = [c for c in holes(f) if len(c) <= 3]
        if len(hs) > 2: issues.append(f"몸 안 바늘구멍 {len(hs)}개")
        cols = {tuple(int(v) for v in c) for c in np.unique(f[alpha(f)][:, :3], axis=0)}
        bad = [c for c in cols if c not in BODY_PAL and c not in EXTRA_OK]
        if bad: issues.append(f"팔레트 밖 색 {len(bad)} {bad[:3]}")
        report.append((i, issues))
    return report

def strip(paths_ws, out, scales=(1, 2)):
    rows = []
    for path, w in paths_ws:
        s = Image.open(path).convert("RGBA")
        for sc in scales:
            bg = Image.new("RGBA", (s.width * sc, s.height * sc), (51, 43, 47, 255))
            bg.alpha_composite(s.resize((s.width * sc, s.height * sc), Image.NEAREST)); rows.append(bg)
    W = max(r.width for r in rows); H = sum(r.height + 4 for r in rows)
    im = Image.new("RGBA", (W, H), (30, 30, 30, 255)); y = 0
    for r in rows: im.alpha_composite(r, (0, y)); y += r.height + 4
    im.save(out)

if __name__ == "__main__":
    sheets = [("달리기_시트_64x64x6.png", 64, 64, 62, [0, 3]), ("스킬발동_시트_96x80x11.png", 96, 80, 78, range(11)),
              ("스킬발동_소용돌이포함_시트_96x80x11.png", 96, 80, 78, None, "fx"), ("낙사복귀_시트_64x64x11.png", 64, 64, 62, [0, 9, 10], (1, 2, 6)),
              ("구르기_시트_64x64x8.png", 64, 64, 62, [0, 2, 3, 4, 5, 6, 7]),
              ("공격1타_가로베기_파츠리그_시트_96x80x8.png", 96, 80, 78, range(8)), ("공격2타_올려베기_파츠리그_시트_96x80x8.png", 96, 80, 78, range(8)),
              ("공격3타_내려찍기_파츠리그_시트_96x80x9.png", 96, 80, 78, range(9)), ("공격_파츠리그_시트_96x80x9.png", 96, 80, 78, range(9)), ("걷기_파츠리그_시트_64x64x8.png", 64, 64, 62, range(8)), ("패링_파츠리그_시트_96x80x8.png", 96, 80, 78, range(8)), ("방어_파츠리그_시트_96x80x8.png", 96, 80, 78, range(8))]
    total = 0
    for row in sheets:
        name, w, h, fy, gf = row[:5]; skip = row[5] if len(row) > 5 else ()
        p = os.path.join(OUT, name)
        if not os.path.exists(p): print("없음", name); continue
        rep = check_sheet(p, w, h, fy, gf, allow_empty=(3, 5) if "낙사" in name else ())
        if skip == "fx":   # 이펙트 판: 불꽃(의도된 1~5px)은 고립 검사 제외
            rep = [(i, [x for x in iss if not (x.startswith("고립") or x.startswith("몸 안"))]) for i, iss in rep]
        elif skip:         # 의도된 프레임(낙하 클리핑 · 디더) 제외
            rep = [(i, [] if i in skip else iss) for i, iss in rep]
        bad = [(i, iss) for i, iss in rep if iss]
        print(f"== {name}: 문제 프레임 {len(bad)}/{len(rep)}")
        for i, iss in bad: print("   ", i, "; ".join(iss)); total += len(iss)
    print("총 지적", total)
    strip([(os.path.join(OUT, "달리기_시트_64x64x6.png"), 64), (os.path.join(OUT, "구르기_시트_64x64x8.png"), 64)], os.path.join(SP, "qa_1x_a.png"))
    strip([(os.path.join(OUT, "스킬발동_소용돌이포함_시트_96x80x11.png"), 96), (os.path.join(OUT, "낙사복귀_시트_64x64x11.png"), 64)], os.path.join(SP, "qa_1x_b.png"))
    strip([(os.path.join(OUT, "공격1타_가로베기_파츠리그_시트_96x80x8.png"), 96), (os.path.join(OUT, "공격2타_올려베기_파츠리그_시트_96x80x8.png"), 96), (os.path.join(OUT, "공격3타_내려찍기_파츠리그_시트_96x80x9.png"), 96), (os.path.join(OUT, "패링_파츠리그_시트_96x80x8.png"), 96)], os.path.join(SP, "qa_1x_c.png"))
