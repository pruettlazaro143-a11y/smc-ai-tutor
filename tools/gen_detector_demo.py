"""生成识别器网页的演示数据（虚构走势，MT5 导出格式），以及 README 用的效果图。

输出：
  detector/demo-mt5.csv            —— 虚构的 15 分钟 K 线，格式和 MT5 导出的历史数据一样
  docs/detector-example.png        —— tools/smc_detect.py 在这份数据上的识别结果
  detector/index.html 里的演示数据（"看示例"按钮）

在仓库根目录运行：python3 tools/gen_detector_demo.py
"""
import json
import os
import random
import re
import sys
from datetime import datetime, timedelta

sys.path.insert(0, 'tools')
import smc_detect as sd  # noqa: E402


def series(seed=7, n=300, start=1.08500):
    """带趋势切换和波动聚集的随机游走，四舍五入到 5 位小数。"""
    rnd = random.Random(seed)
    px, vol, drift = start, 0.0006, 0.0
    out = []
    for i in range(n):
        if i % 60 == 0:
            drift = rnd.choice([-1, 1]) * rnd.uniform(0.00005, 0.00018)
        vol = max(0.00025, min(0.0015, vol * rnd.uniform(0.85, 1.18)))
        o = px
        c = o + drift + rnd.gauss(0, vol)
        if rnd.random() < 0.04:  # 偶尔的位移 K 线
            c = o + (1 if drift >= 0 else -1) * vol * rnd.uniform(2.5, 4)
        h = max(o, c) + abs(rnd.gauss(0, vol * 0.6))
        l = min(o, c) - abs(rnd.gauss(0, vol * 0.6))
        out.append(tuple(round(x, 5) for x in (o, h, l, c)))
        px = c
    return out


def main():
    rows = series()
    t0 = datetime(2026, 3, 2, 0, 0)
    lines = ['<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>']
    for i, (o, h, l, c) in enumerate(rows):
        t = t0 + timedelta(minutes=15 * i)
        lines.append(f'{t:%Y.%m.%d}\t{t:%H:%M:%S}\t{o:.5f}\t{h:.5f}\t{l:.5f}\t{c:.5f}\t{100 + i % 37}\t0\t8')
    os.makedirs('detector', exist_ok=True)
    open('detector/demo-mt5.csv', 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    K, info = sd.parse('\n'.join(lines))
    R = sd.detect(K)
    sel = sd.select(K, R)
    os.makedirs('docs', exist_ok=True)
    sd.plot(K, R, sel, 'docs/detector-example.png', info, 'DEMO · 15m (synthetic)')
    html = open('detector/index.html', encoding='utf-8').read()
    html = re.sub(r'/\*DEMO\*/.*?/\*END\*/', lambda m: '/*DEMO*/' + json.dumps('\n'.join(lines)) + '/*END*/', html, count=1, flags=re.S)
    open('detector/index.html', 'w', encoding='utf-8').write(html)
    print(sd.report(K, R, sel, info))


if __name__ == '__main__':
    main()
