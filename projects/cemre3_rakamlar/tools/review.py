"""Contact sheet of a rendered reel: one frame every 0.5 s (each beat), timestamped,
plus a simple flag for dark/empty frames. usage: python tools/review.py <video> <out.jpg>"""

import sys

import cv2
import numpy as np

video, out = sys.argv[1], sys.argv[2]
cap = cv2.VideoCapture(video)
fps = cap.get(cv2.CAP_PROP_FPS) or 30
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
step = int(round(fps / 2))
tiles, flags = [], []
for i in range(0, n, step):
    cap.set(cv2.CAP_PROP_POS_FRAMES, i)
    ok, f = cap.read()
    if not ok:
        break
    t = i / fps
    small = cv2.resize(f, (180, 320))
    mean = small.mean()
    if mean < 25 or small.std() < 12:
        flags.append(f"{t:.1f}s dark/flat (mean {mean:.0f})")
        cv2.rectangle(small, (0, 0), (179, 319), (0, 0, 255), 4)
    cv2.rectangle(small, (0, 0), (64, 24), (0, 0, 0), -1)
    cv2.putText(small, f"{t:.1f}", (4, 18), cv2.FONT_HERSHEY_SIMPLEX, .55, (0, 255, 255), 2)
    tiles.append(small)
cols = 10
while len(tiles) % cols:
    tiles.append(np.zeros_like(tiles[0]))
sheet = np.vstack([np.hstack(tiles[k:k + cols]) for k in range(0, len(tiles), cols)])
cv2.imwrite(out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 85])
print(f"{len(tiles)} tiles -> {out}")
for fl in flags:
    print("FLAG", fl)
