"""把金額轉成投標單「中文大寫」格子要填的字串。

投標單的大寫欄通常是固定格數，每格一個數字（例如：佰萬、拾萬、萬、仟、佰、拾、元 共 7 格），
沒有用到的高位補「零」。

用法：python cn_amount.py 金額 格數
例：
  python cn_amount.py 720000 7      → 零柒貳零零零零
  python cn_amount.py 23,500 6      → 零貳參伍零零

輸出可直接貼進 vendor.tex 的 \\def\\PriceTotalCn{...}。
"""
import sys

DIGITS = '零壹貳參肆伍陸柒捌玖'


def to_cells(amount, cells):
    n = int(str(amount).replace(',', '').strip())
    if n < 0:
        raise ValueError('金額不能是負數')
    s = str(n)
    if len(s) > cells:
        raise ValueError(f'金額 {n:,} 超過 {cells} 格能表示的範圍')
    return ''.join(DIGITS[int(c)] for c in s.zfill(cells))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    print(to_cells(sys.argv[1], int(sys.argv[2])))
