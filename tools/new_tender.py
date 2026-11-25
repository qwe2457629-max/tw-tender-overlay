"""開新標案：解壓招標包 → 抓招標單關鍵資料 → 算疑義期限 → 複製表單套印範本 → 產準備清單初稿。

用法：
  python new_tender.py 招標包.zip 輸出資料夾 --kit 套印範本資料夾 [--announce YYYY-MM-DD] [--entity 主體.tex]

參數：
  招標包.zip     機關的招標文件壓縮檔（也可以是已經解壓好的資料夾）
  輸出資料夾      會建 招標文件/、表單套印/ 和準備清單初稿。已存在也可以，不會刪東西
  --kit          表單套印範本資料夾（例如 example/），裡面要有 kit.json，見下方
  --announce     招標公告日（西元），用來算疑義期限（等標期的四分之一，進位）
  --entity       投標主體資料檔（.tex），會複製進 表單套印/entity/ 並設為使用中的主體

kit.json 範例：
  {
    "template_case_no": "EX-2026-001",
    "template_name": "範例資訊系統維護案（虛構）",
    "forms": {
      "sample_form.pdf": {"keys": ["投標單"], "exclude": ["須知", "美金"]},
      "sample_form_usd.pdf": {"keys": ["投標單", "美金"], "optional": true}
    },
    "checklist_pdf": "資格審查單"
  }
  forms：src/ 底下每個檔名，對應招標包裡「檔名同時含有 keys、且不含 exclude」的第一份 PDF。
  optional：招標包沒有這份就把範本裡的刪掉（例如有些標案才附外幣投標單）。

產出的全部是草稿：聲明書、勾選等已確認的值會被加回「?」，並切回 \\drafttrue。
需要 pypdf（pip install pypdf）。編譯需要 tectonic 或 xelatex（找不到就略過）。
"""
import sys, os, re, json, math, shutil, zipfile, argparse, datetime, subprocess
import pypdf

B = chr(92)


def fix_name(info):
    """Windows 中文壓縮檔常用 Big5（cp950）存檔名，沒有 UTF-8 旗標時轉回來。"""
    n = info.filename
    if info.flag_bits & 0x800:
        return n
    try:
        return n.encode('cp437').decode('cp950')
    except Exception:
        return n


def unpack(src, dst):
    os.makedirs(dst, exist_ok=True)
    if os.path.isdir(src):
        shutil.copytree(src, dst, dirs_exist_ok=True)
        return
    with zipfile.ZipFile(src) as z:
        for info in z.infolist():
            name = fix_name(info)
            target = os.path.normpath(os.path.join(dst, name))
            if not target.startswith(os.path.normpath(dst)):
                continue  # 防止 zip slip
            if info.is_dir():
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(info) as s, open(target, 'wb') as d:
                shutil.copyfileobj(s, d)
            if target.lower().endswith('.zip'):
                try:
                    unpack(target, os.path.splitext(target)[0])
                except Exception as e:
                    print('  ! 內層壓縮檔解壓失敗', name, e)


def find_pdfs(root):
    return sorted(os.path.join(r, f) for r, _d, fs in os.walk(root) for f in fs if f.lower().endswith('.pdf'))


def pdf_text(path, pages=None):
    r = pypdf.PdfReader(path)
    rng = range(len(r.pages)) if pages is None else range(min(pages, len(r.pages)))
    return '\n'.join((r.pages[i].extract_text() or '') for i in rng)


def pick(pdfs, keys, exclude=()):
    for p in pdfs:
        n = os.path.basename(p)
        if all(k in n for k in keys) and not any(x in n for x in exclude):
            return p
    return None


def parse_sheet(text):
    """讀招標單常見欄位。各機關格式略有差異，讀不到的欄位會是 None，請人工補。"""
    t = re.sub(r'[ 　\t]+', '', text)
    g = lambda pat, flags=0: (re.search(pat, t, flags) or [None, None])[1]
    d = {'案號': g(r'案號[:：]([A-Za-z0-9\-_]+)'), '名稱': g(r'標案名稱[:：]([^\n]+)')}
    for key, label in (('截標', '截止投標(?:期限|時間)'), ('開標', '開標時間')):
        m = re.search(label + r'[:：](\d{2,4})年(\d{1,2})月(\d{1,2})日(\d{1,2})時(\d{1,2})分', t)
        if m:
            y = int(m.group(1))
            y = y + 1911 if y < 1911 else y   # 民國年也接受
            d[key] = datetime.datetime(y, *map(int, m.groups()[1:]))
        else:
            d[key] = None
    d['預算'] = g(r'預算金額[:：]新臺幣([\d,]+)元')
    for key, label in (('招標方式', '招標方式'), ('決標原則', '決標原則'), ('押標金', '押標金'),
                       ('履約保證金', '履約保證金'), ('收件處所', '投標文件收件處所'), ('開標地點', '開標地點'),
                       ('文字', '投標文件使用文字'), ('共同投標', '允許共同投標'), ('招標機關', '招標機關')):
        d[key] = g(label + r'[:：]([^\n]+)')
    return d


def roc(dt):
    return dt.year - 1911, dt.month, dt.day


def set_def(text, name, value):
    """把 \\def\\Name{...} 的值換掉，保留後面的註解。找不到回傳 None。"""
    pre = B + 'def' + B + name + '{'
    out, hit = [], False
    for line in text.split('\n'):
        i = line.find(pre)
        if i >= 0 and '}' in line[i + len(pre):]:
            end = line.index('}', i + len(pre))
            line = line[:i] + pre + value + line[end:]
            hit = True
        out.append(line)
    return '\n'.join(out) if hit else None


def to_draft(text, prefixes=('Decl', 'Chk', 'SMEItem', 'SMEAmt', 'SMETotal', 'Tax')):
    """已確認的聲明書、勾選等值加回「?」，並切回草稿模式：每個新標案都要重新確認。"""
    out = []
    for line in text.split('\n'):
        if line.strip() == B + 'draftfalse':
            line = B + 'drafttrue'
        else:
            for k in prefixes:
                pre = B + 'def' + B + k
                if line.startswith(pre) and '{' in line:
                    a = line.index('{')
                    b = line.index('}', a)
                    val = line[a + 1:b]
                    if val and not val.endswith('?'):
                        line = line[:b] + '?' + line[b:]
                    break
        out.append(line)
    return '\n'.join(out)


def compile_tex(folder, names):
    tec = shutil.which('tectonic') or os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'tectonic', 'tectonic.exe')
    cmd = [tec, '-X', 'compile'] if os.path.exists(tec) else ([shutil.which('xelatex')] if shutil.which('xelatex') else None)
    if not cmd:
        print('   找不到 tectonic 或 xelatex，略過編譯')
        return
    for tex in names:
        subprocess.run(cmd + [tex], cwd=folder, capture_output=True)
        ok = os.path.exists(os.path.join(folder, tex.replace('.tex', '.pdf')))
        print(f'   編譯 {tex}：', '成功' if ok else '失敗，請手動編譯看錯誤訊息')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(description='開新標案')
    ap.add_argument('package')
    ap.add_argument('out')
    ap.add_argument('--kit', required=True)
    ap.add_argument('--announce')
    ap.add_argument('--entity')
    a = ap.parse_args()

    kit_dir = os.path.abspath(a.kit)
    cfg = json.load(open(os.path.join(kit_dir, 'kit.json'), encoding='utf-8'))
    out = os.path.abspath(a.out)
    ex = os.path.join(out, '招標文件', '解壓縮')
    print('1. 解壓招標包 →', ex)
    unpack(a.package, ex)
    pdfs = find_pdfs(ex)
    print(f'   找到 {len(pdfs)} 份 PDF')

    sheet = pick(pdfs, ['招標單']) or pick(pdfs, ['投標須知'])
    d = parse_sheet(pdf_text(sheet, 3)) if sheet else {}
    print('2. 招標單關鍵資料', f'（{os.path.basename(sheet)}）' if sheet else '（找不到招標單，請手動整理）')
    for k, v in d.items():
        print(f'   {k}：{v if v else "（沒讀到）"}')

    due = None
    if a.announce and d.get('截標'):
        ann = datetime.date.fromisoformat(a.announce)
        days = (d['截標'].date() - ann).days
        due = ann + datetime.timedelta(days=math.ceil(days / 4))
        print(f'3. 等標期 {days} 天 → 疑義期限約 {due}（四分之一進位；以招標公告為準）')

    dest = os.path.join(out, '表單套印')
    print('4. 複製套印範本 →', dest)
    shutil.copytree(kit_dir, dest, dirs_exist_ok=True, ignore=shutil.ignore_patterns('*.pdf', 'sample-forms'))
    os.makedirs(os.path.join(dest, 'src'), exist_ok=True)
    core_src = os.path.join(os.path.dirname(kit_dir), 'core')
    if os.path.isdir(core_src):
        shutil.copytree(core_src, os.path.join(out, 'core'), dirs_exist_ok=True)
    for name, rule in cfg.get('forms', {}).items():
        src = pick(pdfs, rule['keys'], rule.get('exclude', ()))
        if src:
            shutil.copy2(src, os.path.join(dest, 'src', name))
            print(f'   src/{name} ← {os.path.basename(src)}')
        elif rule.get('optional'):
            print(f'   招標包沒有 {name}（選用），略過')
        else:
            print(f'   ! 找不到 {name} 對應的表單，請手動放進 src/')

    vp = os.path.join(dest, 'vendor.tex')
    v = to_draft(open(vp, encoding='utf-8').read())
    if d.get('截標'):
        y, m, dd = roc(d['截標'])
        for name, val in (('SignY', f'{y}?'), ('SignM', f'{m}?'), ('SignD', f'{dd}?')):
            v = set_def(v, name, val) or v
    for k in ('PriceUnitA', 'PriceAmtA', 'PriceUnitB', 'PriceAmtB', 'PriceUnitC', 'PriceAmtC',
              'PriceUnitD', 'PriceAmtD', 'PriceTotal', 'PriceTotalCn'):
        v = set_def(v, k, '') or v
    if a.entity:
        os.makedirs(os.path.join(dest, 'entity'), exist_ok=True)
        shutil.copy2(a.entity, os.path.join(dest, 'entity'))
        v = re.sub(re.escape(B) + r'input\{entity/[^}]+\}',
                   lambda _m: B + 'input{entity/' + os.path.basename(a.entity) + '}', v)
    if d.get('案號'):
        v = v.replace(cfg.get('template_case_no', '\0'), d['案號'])
    if d.get('名稱'):
        v = v.replace(cfg.get('template_name', '\0'), d['名稱'])
    open(vp, 'w', encoding='utf-8', newline='\n').write(v)

    zige = pick(pdfs, [cfg['checklist_pdf']]) if cfg.get('checklist_pdf') else None
    zt = pdf_text(zige) if zige else '（招標包裡找不到資格審查單，請手動整理）'
    f = lambda x: x if x else '（沒讀到，請手動確認）'
    md = [f'# {d.get("案號") or "（案號）"} 投標文件準備清單（初稿）', '',
          f'{d.get("名稱") or ""}　整理日期：{datetime.date.today()}　由 new_tender.py 產生，**請人工核對招標單**', '',
          '## 1. 重點日期與條件', '', '| 項目 | 內容 |', '|---|---|',
          f'| 截止投標 | {d["截標"]:%Y/%m/%d %H:%M} |' if d.get('截標') else '| 截止投標 | （沒讀到） |',
          f'| 開標 | {d["開標"]:%Y/%m/%d %H:%M} |' if d.get('開標') else '| 開標 | （沒讀到） |',
          f'| 疑義期限 | {due or "請給 --announce 公告日"}（以招標公告為準） |',
          f'| 預算 | 新臺幣 {f(d.get("預算"))} 元；標價超過預算為不合格標 |']
    for k in ('招標方式', '決標原則', '押標金', '履約保證金', '收件處所', '開標地點', '文字', '共同投標', '招標機關'):
        md.append(f'| {k} | {f(d.get(k))} |')
    md += ['', '## 2. 要交的文件（資格審查單原文，請整理成表）', '', '```', zt.strip(), '```', '',
           '## 3. 下一步', '',
           '1. 投標須知和上一案比對：`tools/itbdiff.py`。',
           '2. 表單版面和範本不同時，用 `tools/coords.py`、`tools/lines.py` 重新量座標，改 `forms.tex`。',
           '3. 打開 `表單套印/vendor.tex` 補資料；確認過的值把「?」刪掉。',
           '4. 截止前重新下載招標包比對一次（招標文件可能更正或改版）。']
    mp = os.path.join(out, f'{d.get("案號") or "新標案"}_投標文件準備清單_初稿.md')
    open(mp, 'w', encoding='utf-8', newline='\n').write('\n'.join(md))
    print('5. 準備清單初稿 →', mp)

    print('6. 編譯')
    compile_tex(dest, ('forms.tex', 'preview.tex'))
    print('完成。產出都是草稿（紅字＝未確認）。先看 preview.pdf，再逐頁核對座標。')


if __name__ == '__main__':
    main()
