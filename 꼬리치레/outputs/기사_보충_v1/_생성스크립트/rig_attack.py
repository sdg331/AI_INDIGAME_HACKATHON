# 파츠 리그 옆베기(1타 원형): 파츠분할 7파츠(앞팔 밑 채움) + 검. 앞팔 무손실 변환만. 캔버스 96x80(오프셋 +16,+16), 발바닥 y 78
import os
import numpy as np
from PIL import Image
from kb import *
from rig_combo import frame, rigid, P, ARM_PX

W, H, OFF = 96, 80, (16, 16)
FRAMES = [
    ("준비 — 원본 팔, 검 앞아래",                dict(arm='id',    sword_deg=-35)),
    ("예비 — 팔 90° 시계(뒤로 수평), 몸 뒤로",     dict(arm='cw',    sword_deg=165, lean=-2, upper_dy=1, hair_dx=1, head_dx=-1)),
    ("예비 홀드 — 몸 1px 더 뒤",                  dict(arm='cw',    sword_deg=170, lean=-2, upper_dy=1, hair_dx=1, head_dx=-1, body_dx=-1)),
    ("휘두름 — 팔 상하 반전(위로), 검 머리 위",    dict(arm='flipV', sword_deg=80,  lean=1)),
    ("접촉 — 팔 90° 반시계(앞으로 수평), 검 수평", dict(arm='ccw',   sword_deg=0,   lean=3, body_dx=2, hair_dx=-2, head_dx=1, front=(+1, 0))),
    ("접촉 홀드",                                 dict(arm='ccw',   sword_deg=0,   lean=3, body_dx=2, hair_dx=-1, head_dx=1, front=(+1, 0))),
    ("팔로우스루 — 팔 좌우 반전(손 앞·아래)",       dict(arm='flipH', sword_deg=-30, lean=3, body_dx=2, head_dx=1, front=(+1, 0))),
    ("복귀 — 좌우 반전 유지, 검 낮게",              dict(arm='flipH', sword_deg=-35, lean=1, body_dx=1, hair_dx=1)),
    ("준비 — 원본 팔",                             dict(arm='id',    sword_deg=-35)),
]

if __name__ == "__main__":
    imgs, arms = [], []
    for n, sp in FRAMES:
        f = frame(W, H, OFF, sp); imgs.append(f)
        ao = blank(W, H); paste(ao, rigid(P["06_앞팔"], sp["arm"]), OFF[0], OFF[1]); arms.append(ao)
        assert int(alpha(ao).sum()) == ARM_PX
        yy, xx = np.where(alpha(f)); print(n, "| bottom", yy.max(), "x", xx.min(), xx.max())
    save_sheet(imgs, "공격_파츠리그"); save_gif(imgs, "공격_파츠리그", [120, 110, 70, 40, 100, 60, 80, 90, 120])
    save_sheet(arms, "공격_파츠리그_앞팔만")
    contact_sheet(imgs, os.path.join(SP, "rig_cs.png"), scale=5)
    print("앞팔 픽셀", ARM_PX, "— 모든 프레임 동일")
