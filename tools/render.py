"""把 PDF 的某幾頁轉成 PNG，用來檢查套印位置。

用法：python render.py 檔案.pdf 頁碼[,頁碼...] 輸出檔名前綴 [dpi] [x0,y0,x1,y1]
例：
  python render.py forms.pdf 1,2 check 80                    → check_p1.png、check_p2.png
  python render.py forms.pdf 4 zoom 200 240,540,430,620      → 只截這個範圍（bp，原點在左下角）

需要 PyMuPDF（pip install pymupdf）。
"""
import sys, pymupdf
if len(sys.argv) < 4:
    print(__doc__)
    sys.exit(1)
doc = pymupdf.open(sys.argv[1])
out = sys.argv[3]
dpi = int(sys.argv[4]) if len(sys.argv) > 4 else 80
for pn in [int(x) for x in sys.argv[2].split(',')]:
    pg = doc[pn - 1]
    clip = None
    if len(sys.argv) > 5:
        x0, y0, x1, y1 = [float(v) for v in sys.argv[5].split(',')]
        H = pg.rect.height
        clip = pymupdf.Rect(x0, H - y1, x1, H - y0)
    pg.get_pixmap(dpi=dpi, clip=clip).save(f'{out}_p{pn}.png')
