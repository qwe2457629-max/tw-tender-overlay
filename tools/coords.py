"""列出表單 PDF 每段文字的座標，用來決定套印位置。

用法：python coords.py 表單.pdf 頁碼[,頁碼...]
例：  python coords.py src/sample_form.pdf 1

輸出的 x、y 單位是 bp（PDF 點），原點在頁面左下角，y 是文字基線，
可以直接填進 forms.tex 的 putl{x,y}{...}。fs 是字級。
需要 pypdf（pip install pypdf）。只讀不寫，可以安全執行。
"""
import sys, pypdf
sys.stdout.reconfigure(encoding='utf-8')
if len(sys.argv) < 3:
    print(__doc__)
    sys.exit(1)
r = pypdf.PdfReader(sys.argv[1])
for pn in [int(x) for x in sys.argv[2].split(',')]:
    p = r.pages[pn - 1]
    print(f"===== p{pn} mediabox={[round(float(v), 1) for v in p.mediabox]} rotate={p.get('/Rotate', 0)}")
    out = []

    def vis(text, cm, tm, fd, fs):
        t = text.strip()
        if not t:
            return
        x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
        y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
        out.append((round(y, 1), round(x, 1), round(fs * (tm[3] or 1) * (cm[3] or 1), 1), t[:46]))

    p.extract_text(visitor_text=vis)
    for y, x, fs, t in sorted(out, key=lambda z: (-z[0], z[1])):
        print(f"y={y:7.1f} x={x:7.1f} fs={fs:5.1f} | {t}")
