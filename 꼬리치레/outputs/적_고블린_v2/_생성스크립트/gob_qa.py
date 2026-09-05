# 고블린 v2 마무리: 대기·피격 v1 복사, _build.json, QA_주인공비교_4x.png, _QA_전체시트_x3.png, 스크립트 복사
import os, json, shutil, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from gob_lib import *

SP = os.path.dirname(os.path.abspath(__file__))
# 1. 대기 · 피격은 gob_idle_hit.py 가 만든다(v2.1: 흉부 보정)

# 2. _build.json (팔레트 동일, 파일명 갱신)
b = dict(BUILD)
b["files"] = {"대기": "고블린_대기_시트_64x64x4.png", "이동": "고블린_이동_시트_64x64x8.png", "공격": "고블린_공격_시트_80x64x11.png",
              "피격": "고블린_피격_시트_64x64x4.png", "그로기": "고블린_그로기_시트_64x64x6.png"}
b["version"] = "v2.3"; b["base_frames"] = {"이동 상체": "v1 이동 2번(원본 2)", "공격 서기": "v1 공격 1번(대기 포즈, 흉부 조끼 채움 + 다리 사이 구멍 제거)", "대기·피격4": "v1 대기 1번(흉부 조끼 채움 + 다리 사이 구멍 제거)", "공격 접촉": "원본 적 2.png 공격 셀 재추출(v2.3, 문턱값 14 · 조끼 갈색화)", "그로기 멈춤": "v1 피격 3번(피격 포즈)"}
b.pop("walk_order", None)
json.dump(b, open(os.path.join(OUT, "_build.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# 3. 팔레트 검사 (전 시트)
for fn in sorted(glob.glob(os.path.join(OUT, "*_시트_*.png"))):
    a = np.array(Image.open(fn).convert("RGBA")); ex = palette_check(a)
    print(os.path.basename(fn), "팔레트 외 색:", len(ex), ex[:3])

# 4. QA_주인공비교_4x: 주인공 걷기 f0(기사_보충_v1 기준 프레임) · 고블린 대기 · 이동 접지 · 공격 접촉 · 백스윙 · 그로기 멈춤
knight = np.load(os.path.join(ROOT, "outputs", "기사_보충_v1", "_생성스크립트", "frames_snap.npy"))[0]
idle = load_sheet("고블린_대기_시트_64x64x4.png", 64, 4, OUT)[0]
walk = load_sheet("고블린_이동_시트_64x64x8.png", 64, 8, OUT)
atk = load_sheet("고블린_공격_시트_80x64x11.png", 80, 11, OUT)
gro = load_sheet("고블린_그로기_시트_64x64x6.png", 64, 6, OUT)
cells = [knight, idle, walk[0], walk[3], atk[2], atk[6], atk[8], gro[3]]
labels = ["주인공 걷기", "대기", "이동 접지", "이동 상승", "공격 백스윙", "공격 접촉", "팔로우스루", "그로기 멈춤"]
W = sum(c.shape[1] + 4 for c in cells)
out = Image.new("RGBA", (W, 64), (40, 30, 30, 255)); x = 0; xsl = []
for c in cells:
    out.alpha_composite(Image.fromarray(c), (x, 0)); xsl.append(x); x += c.shape[1] + 4
px = out.load()
for xx in range(0, out.width, 4): px[xx, FOOT_Y + 1] = (255, 120, 120, 255)   # 발바닥 선 바로 아래 행(y 63)에 점선
out = out.resize((out.width * 4, 256), Image.NEAREST)
d = ImageDraw.Draw(out)
try: font = ImageFont.truetype(r"C:\Windows\Fonts\malgun.ttf", 14)
except Exception: font = None
for xx, lb in zip(xsl, labels): d.text((xx * 4 + 4, 4), lb, fill=(255, 230, 120, 255), font=font)
out.save(os.path.join(OUT, "QA_주인공비교_4x.png"))

# 5. 전체 시트 x3
files = sorted(glob.glob(os.path.join(OUT, "*_시트_*.png")))
ims = [Image.open(f).convert("RGBA") for f in files]
Wm = max(i.width for i in ims); H = sum(i.height + 6 for i in ims)
sheet = Image.new("RGBA", (Wm, H), (40, 30, 30, 255)); y = 0
for i in ims: sheet.alpha_composite(i, (0, y)); y += i.height + 6
sheet.resize((Wm * 3, H * 3), Image.NEAREST).save(os.path.join(OUT, "_QA_전체시트_x3.png"))

# 6. 스크립트 복사
sd = os.path.join(OUT, "_생성스크립트"); os.makedirs(sd, exist_ok=True)
for fn in ["gob_lib.py", "gob_chest.py", "gob_idle_hit.py", "gob_walk.py", "gob_attack_src.py", "gob_attack.py", "gob_groggy.py", "gob_qa.py"]:
    if os.path.abspath(os.path.join(SP, fn)) != os.path.abspath(os.path.join(sd, fn)): shutil.copy2(os.path.join(SP, fn), os.path.join(sd, fn))
open(os.path.join(sd, "실행방법.txt"), "w", encoding="utf-8").write(
    "필요: Python 3, pillow, numpy, scipy. outputs/적_고블린_v1/ (v1 시트) 과 프로젝트 폴더의 적 2.png (공격 접촉 포즈 원본) 이 있어야 한다. 콘솔 인코딩: PYTHONIOENCODING=utf-8.\n"
    "순서대로 실행:\n  python gob_idle_hit.py\n  python gob_walk.py\n  python gob_attack.py\n  python gob_groggy.py\n  python gob_qa.py\n"
    "gob_lib.py 의 ROOT 경로를 프로젝트 폴더로 맞춘다. 모든 출력은 outputs/적_고블린_v2/ 에 쓴다.\n")
print("done", len(files), "sheets")
