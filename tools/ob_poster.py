import sys
src = open('tools/gen_diagrams.py', encoding='utf-8').read()
src = src[:src.index('for fn in (d00')]
sys.argv = ['x', '/tmp/_smc_unused']
exec(src)

W, H = 1080, 1440
cs = mk(113, [112.0, 110.8, 111.4, 110.0, 108.8, (107.4, None, 106.2),     # 0-5, idx5 prior low
              108.0, 109.1, (109.7, 110.2, None),                         # 6-8, idx8 LH
              108.8, 107.9, 107.2, (106.9, None, None),                   # 9-12
              (105.6, 107.1, 104.9),                                      # 13 OB: bearish, sweeps prior low
              (108.6, None, 105.5), (111.0, None, 108.4),                 # 14-15 displacement, breaks LH
              111.8, 111.0, 109.9, 108.6, (106.8, None, 106.2),           # 16-20 first return into OB
              (108.8, None, 106.6), 110.2, 111.6, 112.5, 113.8, 115.0, 116.2], seed=91, wick=(0.15, 0.4))

class Dummy: pass
p = Panel(Dummy(), cs, 40, 230, 1040, 830, pad=1.5)
A = 13
ao, ac = p.O(A), p.Cl(A)
low = p.L(5)
check(is_swing_low(p, 5) and all(p.L(j) > low for j in range(6, A)), "poster: prior low intact until the OB candle")
check(p.L(A) < low and ac < ao and p.Cl(A + 1) > p.O(A + 1), "poster: OB = bearish candle that sweeps the prior low, followed by displacement")
check(is_swing_high(p, 8) and all(p.H(j) < p.H(8) for j in range(9, A + 1)), "poster: structure high")
ret = next(j for j in range(A + 3, p.n) if p.L(j) <= max(ao, ac))
check(ret == 20 and p.L(20) >= min(ao, ac) - 0.6, f"poster: first return expected at 20, got {ret}")
check(p.Cl(21) > p.O(21) and p.O(21) <= min(p.O(20), p.Cl(20)) and p.Cl(21) >= max(p.O(20), p.Cl(20)), "poster: candle 21 engulfs 20")
check(p.H(A) < p.L(A + 2), "poster: displacement leaves an FVG")
p.hline(low, 5, A + 1, C["liq"], "前低：多头止损聚集", lpos="start", above=False)
p.ob(A, p.n - 1, None, C["ob"], opacity=0.2)
p.tag(p.x(p.n - 1), p.y((ao + ac) / 2) + 8, "OB = 这根阴线的实体", C["ob"], anchor="end", fs=22)
p.tag(p.x(p.n - 1), p.y(p.H(A)) - 10, "虚线 = 影线，只作缓冲", C["muted"], anchor="end", fs=17)
p.badge(A, p.L(A) - 1.0, "1", C["liq"])
p.tag(p.x(A) + 18, p.y(p.L(A) - 1.0) + 7, "扫掉前低", C["liq"], fs=20)
ym = p.y(p.O(15)) + 30
p.over.append(f'<circle cx="{p.x(15) + 30:.1f}" cy="{ym:.1f}" r="11" fill="{C["warn"]}"/><text x="{p.x(15) + 30:.1f}" y="{ym + 4.5:.1f}" font-size="13" font-weight="700" text-anchor="middle" fill="{C["bg"]}">2</text>')
p.tag(p.x(15) + 48, ym + 7, "强力位移", C["warn"], fs=20)
lh = p.H(8)
k = p.first_close_above(lh, A)
check(k in (A + 1, A + 2), "poster: displacement must break the structure high")
p.hline(lh, 8, k + 1, C["tp"], None)
p.badge(8, lh + 0.75, "3", C["tp"])
p.tag(p.x(8) + 18, p.y(lh + 0.75) + 7, "收盘突破前高 = 打破结构", C["tp"], fs=20)
p.tag(p.x(20) - 20, p.y((ao + ac) / 2) + 7, "第一次回到 OB", C["text"], anchor="end", fs=19)
p.tag(p.x(20) - 8, p.y(p.L(A)) + 34, "↑ 出现吞没反应，才考虑进", C["tp"], fs=19)

F = "'Noto Sans CJK SC','PingFang SC','Microsoft YaHei',sans-serif"
out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{F}">',
       f'<rect width="{W}" height="{H}" fill="{C["bg"]}"/>',
       f'<text x="40" y="100" font-size="60" font-weight="800" fill="{C["text"]}">订单区 <tspan fill="{C["ob"]}">OB</tspan> 是什么？</text>',
       f'<text x="40" y="160" font-size="28" fill="{C["muted"]}">大资金发动行情之前，最后一次反向建仓的位置</text>',
       f'<text x="48" y="262" font-size="20" font-weight="700" fill="{C["muted"]}">示例：看涨 OB</text>']
out += p.render()

cards = [
    ("1", "怎么找", ["上涨前的最后一根阴线 = 看涨 OB", "下跌前的最后一根阳线 = 看跌 OB", "区域只取实体：开盘价 → 收盘价"], C["ob"]),
    ("2", "怎么算真", ["之前扫过前高 / 前低的流动性", "之后有强力位移，一口气拉开", "并且打破了结构"], C["warn"]),
    ("3", "怎么用", ["回到 OB 先看反应（拒绝、吞没）再进", "第一次回测最强，测得越多越弱", "止损放在影线极端之外"], C["tp"]),
]
y = 860
for n, title, lines, col in cards:
    h = 150
    out.append(f'<rect x="40" y="{y}" width="1000" height="{h}" rx="14" fill="{C["panel"]}" stroke="{col}" stroke-opacity="0.6" stroke-width="2"/>')
    out.append(f'<rect x="40" y="{y}" width="8" height="{h}" rx="4" fill="{col}"/>')
    out.append(f'<circle cx="100" cy="{y + 48}" r="24" fill="{col}"/>')
    out.append(f'<text x="100" y="{y + 57}" font-size="26" font-weight="800" text-anchor="middle" fill="{C["bg"]}">{n}</text>')
    out.append(f'<text x="140" y="{y + 58}" font-size="32" font-weight="800" fill="{C["text"]}">{title}</text>')
    for k, ln in enumerate(lines):
        cx = 320 if k else 320
        out.append(f'<text x="330" y="{y + 44 + k * 40}" font-size="24" fill="{C["text"]}">· {esc(ln)}</text>')
    y += h + 16
out.append(f'<text x="540" y="{H - 40}" font-size="18" text-anchor="middle" fill="{C["muted"]}">示意图，非真实行情 · 仅供学习交流，不构成投资建议</text>')
out.append('</svg>')
import os
os.makedirs('diagrams/svg', exist_ok=True)
open('diagrams/svg/11-OB一图看懂.svg', 'w', encoding='utf-8').write('\n'.join(out))
print('ok')
