"""QA 합성: 전체 시트 3배, 주인공 비교 4배, 팔레트 출력."""
import glob, json
import numpy as np
from PIL import Image
import os
os.chdir(r"C:\Users\jahy0\OneDrive\바탕 화면\꼬리치레")
for d in ["적_스켈레톤_v1", "적_고블린_v1"]:
    files = sorted(glob.glob(f"outputs/{d}/*_시트_*.png"))
    ims = [Image.open(f) for f in files]
    W = max(i.width for i in ims); H = sum(i.height + 6 for i in ims)
    out = Image.new("RGBA", (W, H), (40, 30, 30, 255)); y = 0
    for i in ims: out.alpha_composite(i, (0, y)); y += i.height + 6
    out.resize((out.width * 3, out.height * 3), Image.NEAREST).save(f"outputs/{d}/_QA_전체시트_x3.png")
k = Image.open("미리보기_걷기8.gif").convert("RGBA").resize((64, 64), Image.NEAREST)
arr = np.asarray(k).copy(); bgc = arr[0, 0, :3].astype(int)
mask = (np.abs(arr[..., :3].astype(int) - bgc).sum(2) < 24); arr[mask, 3] = 0
k = Image.fromarray(arr, "RGBA")
cells = [k]
for d, n in [("적_스켈레톤_v1", "스켈레톤"), ("적_고블린_v1", "고블린")]:
    cells.append(Image.open(f"outputs/{d}/{n}_대기_시트_64x64x4.png").crop((0, 0, 64, 64)))
    cells.append(Image.open(f"outputs/{d}/{n}_공격_시트_80x64x10.png").crop((80 * 6, 0, 80 * 7, 64)))
    cells.append(Image.open(f"outputs/{d}/{n}_그로기_시트_64x64x6.png").crop((64 * 3, 0, 64 * 4, 64)))
W = sum(c.width + 4 for c in cells); out = Image.new("RGBA", (W, 64), (40, 30, 30, 255)); x = 0
for c in cells: out.alpha_composite(c, (x, 0)); x += c.width + 4
px = out.load()
for xx in range(0, out.width, 4): px[xx, 63] = (255, 120, 120, 255)
out = out.resize((out.width * 4, 256), Image.NEAREST)
for d in ["적_스켈레톤_v1", "적_고블린_v1"]: out.save(f"outputs/{d}/QA_주인공비교_4x.png")
for d in ["적_스켈레톤_v1", "적_고블린_v1"]:
    b = json.load(open(f"outputs/{d}/_build.json", encoding="utf-8")); print(d, b["idle_size"], " ".join(b["palette"]))
