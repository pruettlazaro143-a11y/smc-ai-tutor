"""生成标注器的示例截图和示例标注（全部是虚构数据，不是真实行情）。

输出：
  annotator/example-chart.png   —— 模拟的 K 线截图（带价格轴）
  annotator/example.json        —— 按 08 规范写的标注，坐标由数据精确算出
  docs/annotation-example.png   —— 用 tools/annotate.py 画好的效果图

在仓库根目录运行：python3 tools/gen_example.py
"""
import json
import os
import re
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

sys.path.insert(0, 'tools')
from annotate import draw  # noqa: E402

# ---------------- 虚构走势：下跌 → 等低 → 扫等低 → 位移破结构（留下 FVG）→ 回踩 OB ----------------
K = [
    (118.0, 118.4, 116.6, 116.9), (116.9, 117.2, 115.0, 115.3), (115.3, 115.6, 113.8, 114.1),
    (114.1, 114.3, 112.2, 112.5), (112.5, 113.9, 112.3, 113.6), (113.6, 114.8, 113.4, 114.5),
    (114.5, 114.7, 112.9, 113.2), (113.2, 113.4, 110.6, 111.6),                       # 7: 等低 1（110.6）
    (111.6, 113.0, 111.4, 112.8), (112.8, 114.1, 112.6, 113.9), (113.9, 114.4, 113.6, 114.0),  # 10: LH 114.4
    (114.0, 114.1, 113.4, 113.7), (113.7, 113.9, 111.9, 112.2), (112.2, 112.4, 110.6, 111.3),  # 13: 等低 2（110.6）
    (111.3, 112.6, 111.1, 112.3), (112.3, 112.5, 111.4, 111.7),
    (111.7, 111.9, 108.9, 110.9),                                                       # 16: 扫等低，收回
    (110.9, 111.1, 109.8, 110.7),                                                       # 17: 最后一根阴线 = OB（收盘仍在等低之上）
    (110.2, 113.6, 110.0, 113.3), (113.3, 116.6, 113.1, 116.3),                         # 18-19: 位移，19 收盘破 LH
    (116.3, 117.4, 115.8, 117.0), (117.0, 117.2, 115.2, 115.5), (115.5, 115.7, 113.4, 113.8),
    (113.8, 114.0, 110.4, 111.0),                                                       # 23: 回到 OB 实体
    (111.0, 113.6, 110.8, 113.3), (113.3, 115.2, 113.1, 114.9), (114.9, 116.8, 114.6, 116.5),
]
EQ = 110.6
OB, A, C = 17, 17, 19  # FVG：A = 17，B = 18，C = 19


def check(c, m):
    if not c:
        raise AssertionError('example check failed: ' + m)


for i, (o, h, l, c) in enumerate(K):
    check(h >= max(o, c) and l <= min(o, c), f'candle {i}')
check(K[7][2] == EQ == K[13][2], 'equal lows')
check(all(k[2] > EQ for i, k in enumerate(K[:16]) if i not in (7, 13)), 'lows intact before sweep')
check(K[16][2] < EQ < K[16][3], 'sweep: wick below, close back above')
check(K[OB][3] < K[OB][0] and K[OB + 1][3] > K[OB + 1][0], 'OB = last bearish candle before displacement')
check(all(k[3] >= EQ for k in K[13:]), 'no close below the equal lows (otherwise it would be a bearish BOS, not a sweep)')
lh = K[10][1]
check(K[0][1] > K[5][1] > lh, 'downtrend: candle 5 and candle 10 are successively lower highs')
check(K[3][2] > K[7][2], 'downtrend: lower low at candle 7')
check(all(k[1] < lh for k in K[11:19]), 'LH intact until displacement')
check(K[19][3] > lh, 'candle 19 closes above LH (CHoCH)')
check(K[C][2] > K[A][1], 'FVG: C.low above A.high')
ob_top, ob_bot = K[OB][0], K[OB][3]
first = next(i for i in range(20, len(K)) if K[i][2] <= ob_top)
check(first == 23 and K[23][2] >= K[16][2], 'first return to OB at 23, above the sweep low')
prior_high = max(k[1] for k in K[:3])

# ---------------- 画成"截图" ----------------
W, H, DPI = 1600, 900, 100
fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor='#131722')
ax = fig.add_axes([0.02, 0.05, 0.9, 0.9], facecolor='#131722')
for i, (o, h, l, c) in enumerate(K):
    col = '#26a69a' if c >= o else '#ef5350'
    ax.vlines(i, l, h, color=col, lw=1.4)
    ax.add_patch(Rectangle((i - .32, min(o, c)), .64, max(abs(c - o), .03), color=col))
ax.set_xlim(-1, len(K) + 3)
ax.set_ylim(107.5, 119.5)
ax.yaxis.tick_right()
ax.tick_params(axis='y', colors='#b2b5be', labelsize=12)
ax.tick_params(axis='x', bottom=False, labelbottom=False)
ax.grid(color='#2a2e39', lw=.6)
for sp in ax.spines.values():
    sp.set_visible(False)
ax.text(0, 119.1, 'DEMO / USD · 15m   (illustration, not real data)', color='#b2b5be', fontsize=12)
os.makedirs('annotator', exist_ok=True)
fig.savefig('annotator/example-chart.png', dpi=DPI, facecolor=fig.get_facecolor())
fig.canvas.draw()


def fx(i):
    return round(float(ax.transData.transform((i, 0))[0]) / W, 4)


def fy(p):
    return round(1 - float(ax.transData.transform((0, p))[1]) / H, 4)


plt.close(fig)

# ---------------- 标注（坐标由数据精确算出，价格用 calibration 换算） ----------------
spec = {
    'version': 1,
    'note': '示例：虚构走势，只用来演示标注格式。',
    'calibration': {'price_a': 118.0, 'y_a': fy(118.0), 'price_b': 108.0, 'y_b': fy(108.0)},
    'items': [
        {'type': 'hline', 'price': EQ, 'x1': fx(6.5), 'x2': fx(16.5), 'kind': 'liquidity',
         'label': '等低 SSL', 'label_en': 'Equal lows (SSL)', 'confidence': 'high',
         'why': '第 8、14 根的低点同为 110.6，中间有明显反弹'},
        {'type': 'marker', 'x': fx(16), 'price': K[16][2], 'text': '扫等低，收回', 'text_en': 'sweep',
         'kind': 'liquidity', 'place': 'below', 'confidence': 'high',
         'why': '下影线刺穿 110.6 到 108.9，实体收在 110.9'},
        {'type': 'hline', 'price': lh, 'x1': fx(9.5), 'x2': fx(19.5), 'kind': 'structure',
         'label': 'CHoCH：收盘突破 LH', 'label_en': 'CHoCH: close above LH', 'confidence': 'high',
         'why': '第 20 根收盘 116.3，高于最后一个 LH 114.4'},
        {'type': 'box', 'x1': fx(OB - .5), 'x2': fx(len(K) + 2), 'price_top': ob_top, 'price_bottom': ob_bot,
         'kind': 'ob', 'label': '看涨 OB（只取实体）', 'label_en': 'Bullish OB (body)', 'confidence': 'high',
         'why': f'扫等低后、位移前最后一根阴线，实体 {ob_top}–{ob_bot}'},
        {'type': 'box', 'x1': fx(A + .5), 'x2': fx(len(K) + 2), 'price_top': K[C][2], 'price_bottom': K[A][1],
         'kind': 'fvg', 'label': 'FVG', 'confidence': 'high', 'fvg_check': {'a_high': K[A][1], 'c_low': K[C][2]},
         'why': 'A（第 18 根）最高 111.1，C（第 20 根）最低 113.1，中间没有重叠'},
        {'type': 'marker', 'x': fx(first), 'price': K[first][2], 'text': '首次回到 OB', 'text_en': 'first return',
         'kind': 'note', 'place': 'below', 'confidence': 'high', 'why': '第 24 根低点 110.4 进入 OB 实体'},
        {'type': 'hline', 'price': prior_high, 'x1': fx(0), 'x2': fx(len(K) + 2), 'kind': 'tp',
         'label': '对侧流动性：前高 BSL', 'label_en': 'Opposite liquidity: prior high (BSL)', 'confidence': 'medium',
         'why': '左侧前高 118.4 尚未被扫'},
    ],
}
json.dump(spec, open('annotator/example.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
os.makedirs('docs', exist_ok=True)
draw('annotator/example-chart.png', spec, 'docs/annotation-example.png')
html = open('annotator/index.html', encoding='utf-8').read()
html = re.sub(r'/\*SAMPLE\*/.*?/\*END\*/', lambda m: '/*SAMPLE*/' + json.dumps(spec, ensure_ascii=False) + '/*END*/', html, count=1, flags=re.S)
open('annotator/index.html', 'w', encoding='utf-8').write(html)
print('example ok')
