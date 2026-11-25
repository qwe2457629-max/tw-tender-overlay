"""比對兩份投標須知（或任何兩份 PDF）的文字差異。

用法：
  python itbdiff.py 舊.pdf 新.pdf [舊檔頁碼範圍] [新檔頁碼範圍]
  頁碼範圍寫成 起-迄（從 1 開始），省略就是整份。
例：
  python itbdiff.py 舊版投標須知.pdf 新版招標單與投標須知.pdf 2-22 10-30

會忽略空白和頁首頁尾（「投標須知 1234567」版本號、「第n頁，共n頁」），以句子為單位列出不同的地方。
沒有列出差異，就表示兩份內容相同，舊的整理和翻譯可以直接沿用。
需要 pypdf（pip install pypdf）。只讀不寫。
"""
import sys, re, difflib, pypdf
sys.stdout.reconfigure(encoding='utf-8')


def load(path, rng):
    r = pypdf.PdfReader(path)
    a, b = (1, len(r.pages)) if not rng else [int(x) for x in rng.split('-')]
    txt = ''.join(r.pages[i].extract_text() or '' for i in range(a - 1, b))
    txt = re.sub(r'投標須知 \d{7}|第\d+頁，共 ?\d+ ?頁', '', txt)
    txt = re.sub(r'\s+', '', txt)
    return re.split(r'(?<=[。；：])', txt)


if len(sys.argv) < 3:
    print(__doc__)
    sys.exit(1)
old = load(sys.argv[1], sys.argv[3] if len(sys.argv) > 3 else None)
new = load(sys.argv[2], sys.argv[4] if len(sys.argv) > 4 else None)
n = 0
for line in difflib.unified_diff(old, new, '舊', '新', lineterm='', n=0):
    print(line[:400])
    n += 1
print(f'\n舊 {len(old)} 句、新 {len(new)} 句；' + ('沒有差異' if n == 0 else '以上為差異'))
