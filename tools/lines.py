"""列出表單 PDF 的表格格線和每個字的位置，用來算勾選欄、儲存格、填空底線的位置。

用法：
  python lines.py 表單.pdf 頁碼[,頁碼...]              → 格線
  python lines.py 表單.pdf 頁碼 chars y下限 y上限      → 這個高度範圍內每個字的 x 範圍
例：
  python lines.py src/sample_form.pdf 1,2
  python lines.py src/sample_form.pdf 1 chars 510 518

格線輸出：V x 是直線的 x 座標和它的 y 範圍；H y 是橫線的 y 座標和它的 x 範圍。
單位 bp，原點在頁面左下角。需要 PyMuPDF（pip install pymupdf）。只讀不寫。
"""
import sys, pymupdf
sys.stdout.reconfigure(encoding='utf-8')
if len(sys.argv) < 3:
    print(__doc__)
    sys.exit(1)
doc = pymupdf.open(sys.argv[1])
pages = [int(x) for x in sys.argv[2].split(',')]

if len(sys.argv) > 3 and sys.argv[3] == 'chars':
    ylo, yhi = float(sys.argv[4]), float(sys.argv[5])
    pg = doc[pages[0] - 1]
    H = pg.rect.height
    for b in pg.get_text('rawdict')['blocks']:
        for line in b.get('lines', []):
            for s in line['spans']:
                for c in s['chars']:
                    y = H - c['origin'][1]
                    if ylo <= y <= yhi and c['c'].strip():
                        print(f"{c['c']} x={c['bbox'][0]:.1f}-{c['bbox'][2]:.1f} y={y:.1f}")
    sys.exit(0)

for pn in pages:
    pg = doc[pn - 1]
    H = pg.rect.height
    vs, hs = {}, {}
    for d in pg.get_drawings():
        for it in d['items']:
            if it[0] == 'l':
                a, b = it[1], it[2]
                segs = [(a.x, a.y, b.x, b.y)]
            elif it[0] == 're':
                r = it[1]
                segs = [(r.x0, r.y0, r.x1, r.y0), (r.x0, r.y1, r.x1, r.y1),
                        (r.x0, r.y0, r.x0, r.y1), (r.x1, r.y0, r.x1, r.y1)]
            else:
                continue
            for x0, y0, x1, y1 in segs:
                if abs(x0 - x1) < 1.2 and abs(y0 - y1) > 8:
                    vs.setdefault(round((x0 + x1) / 2), []).append((round(H - max(y0, y1)), round(H - min(y0, y1))))
                elif abs(y0 - y1) < 1.2 and abs(x0 - x1) > 8:
                    hs.setdefault(round(H - (y0 + y1) / 2), []).append((round(min(x0, x1)), round(max(x0, x1))))
    print(f'== p{pn} size {pg.rect.width:.1f}x{H:.1f} rot={pg.rotation}')
    print(' V x:', {x: (min(a for a, b in v), max(b for a, b in v)) for x, v in sorted(vs.items())})
    print(' H y:', {y: (min(a for a, b in v), max(b for a, b in v)) for y, v in sorted(hs.items(), reverse=True)})
