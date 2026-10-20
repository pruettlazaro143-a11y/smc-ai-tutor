"""识别引擎的测试。在仓库根目录运行：python3 tools/test_detect.py

四类检查：
  1. 已知答案：示例图（tools/gen_example.py 的虚构走势）里人工确认过的结构、等低、清扫、OB、FVG，引擎必须原样识别出来
  2. 定义复核：在 60 组随机走势（360 个不同格式的数据文件）上，引擎报告的每一项都用教程定义重新独立核对一遍（FVG 缺口、实体收盘破位、影线清扫……）
  3. 两版一致：Python 版（tools/smc_detect.py）和网页版（detector/smc-detect.js）对同一份数据的读取、识别、挑选、报告逐项相同
     （需要 Node.js；没有就跳过并提示）
  4. 网页：用浏览器打开 detector/index.html，点"看示例"，报告必须和 Python 版一字不差、页面无报错（需要 playwright，没有就跳过）
"""
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, 'tools')
import smc_detect as sd  # noqa: E402
from gen_detector_demo import series  # noqa: E402

FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)


# ---------------------------------------------------------------- 1. 已知答案
def test_planted():
    src = open('tools/gen_example.py', encoding='utf-8').read()
    ns = {}
    exec(src[src.index('K = ['):src.index('EQ = 110.6')], ns)
    K = [{'t': '', 'o': o, 'h': h, 'l': l, 'c': c} for o, h, l, c in ns['K']]
    R = sd.detect(K, {'swing': 2})
    pools = [p for p in R['pools'] if p['type'] == 'low']
    check(len(pools) == 1 and pools[0]['members'] == [7, 13] and pools[0]['level'] == 110.6, 'planted: equal lows 7/13 @110.6')
    check(pools and pools[0]['state'] == 'swept' and pools[0]['at'] == 16, 'planted: equal lows swept at 16')
    ch = [e for e in R['events'] if e['dir'] == 1]
    check(len(ch) == 1 and ch[0]['type'] == 'CHoCH' and ch[0]['i'] == 18 and ch[0]['from'] == 10 and ch[0]['level'] == 114.4,
          'planted: CHoCH at 18 breaking LH 114.4 (candle 10)')
    check(ch and ch[0]['grade'] == 'strong', 'planted: the CHoCH is backed by displacement')
    check(not [e for e in R['events'] if e['dir'] == -1 and e['i'] > 13], 'planted: no bearish break after the equal lows')
    sw = [w for w in R['sweeps'] if w['i'] == 16 and w['pool']]
    check(sw and sw[0]['grade'] == 'strong', 'planted: the equal-low sweep is strong (real depth, clear reaction)')
    obs = [o for o in R['obs'] if o['valid']]
    check(len(obs) == 1 and obs[0]['i'] == 16 and (obs[0]['top'], obs[0]['bottom']) == (112.6, 110.8) and obs[0]['tapped'] == 22,
          'planted: bullish OB = candle 16 body 112.6–110.8, first return 22')
    check(obs and obs[0]['grade'] == 'strong' and ['ob_engulf'] in obs[0]['notes'], 'planted: textbook OB graded strong (full body, engulfed)')
    f = [x for x in R['fvgs'] if x['b'] == 17]
    check(f and f[0]['dir'] == 1 and (f[0]['top'], f[0]['bottom']) == (113.5, 112.7), 'planted: FVG A=16 C=18 113.5–112.7')
    # 反例：把 OB 那根改成十字星，引擎必须把它判为弱
    K2 = [dict(k) for k in K]
    K2[16].update(o=111.0, c=110.9)
    K2[17].update(o=110.9)
    R2 = sd.detect(K2, {'swing': 2})
    o2 = [o for o in R2['obs'] if o['i'] == 16]
    check(o2 and o2[0]['grade'] == 'weak' and o2[0]['notes'][0][0] == 'ob_doji', 'planted: doji OB graded weak with reason')


# ---------------------------------------------------------------- 2. 定义复核
def opp(K, i, d):
    return K[i]['c'] < K[i]['o'] if d == 1 else K[i]['c'] > K[i]['o']


def verify(K, R):
    n, N = len(K), R['params']['swing']
    H = [k['h'] for k in K]
    L = [k['l'] for k in K]
    C = [k['c'] for k in K]
    sw = {(s['type'], s['i']): s for s in R['swings']}
    for s in R['swings']:
        i = s['i']
        if s['type'] == 'high':
            check(all(H[i] > H[j] for j in range(i - N, i)) and all(H[i] >= H[j] for j in range(i + 1, i + N + 1)), f'swing high {i}')
        else:
            check(all(L[i] < L[j] for j in range(i - N, i)) and all(L[i] <= L[j] for j in range(i + 1, i + N + 1)), f'swing low {i}')
    prev_dir = 0
    for e in R['events']:
        s = sw.get(('high' if e['dir'] == 1 else 'low', e['from']))
        check(s is not None and s['price'] == e['level'] and s['confirmed'] < e['i'], f'event {e["i"]} refers to a confirmed swing')
        check(C[e['i']] > e['level'] if e['dir'] == 1 else C[e['i']] < e['level'], f'event {e["i"]}: body close beyond the level')
        check((e['type'] == 'CHoCH') == (prev_dir == -e['dir']), f'event {e["i"]}: CHoCH only against the prior direction')
        prev_dir = e['dir']
    for w in R['sweeps']:
        k = K[w['i']]
        if w['side'] == 'high':
            check(k['h'] > w['level'] and k['c'] <= w['level'], f'sweep {w["i"]}: wick above, close back inside')
        else:
            check(k['l'] < w['level'] and k['c'] >= w['level'], f'sweep {w["i"]}: wick below, close back inside')
        check(w['from'] < w['i'], f'sweep {w["i"]} after its level')
    for p in R['pools']:
        px = [H[i] if p['type'] == 'high' else L[i] for i in p['members']]
        check(p['level'] == (max(px) if p['type'] == 'high' else min(px)), 'pool level is the extreme member')
        for a, b in zip(p['members'], p['members'][1:]):
            tol = R['params']['eq_tol_atr'] * max(1e-12, sd_atr(K, b, R['params']['atr_len']))
            check(abs(px[p['members'].index(a)] - px[p['members'].index(b)]) <= tol + 1e-12, 'pool members within tolerance')
            mid = range(a + 1, b)
            if p['type'] == 'low':
                check(all(L[j] >= p['level'] for j in mid), 'pool: nothing below the level between members')
            else:
                check(all(H[j] <= p['level'] for j in mid), 'pool: nothing above the level between members')
    for f in R['fvgs']:
        a, b, c = f['a'], f['b'], f['c']
        check(a == b - 1 and c == b + 1, 'fvg: consecutive A B C')
        if f['dir'] == 1:
            check(L[c] > H[a] and f['top'] == L[c] and f['bottom'] == H[a], f'fvg {b}: bull gap = A high → C low')
            if f['filled'] is not None:
                check(L[f['filled']] <= f['bottom'] and all(L[j] > f['bottom'] for j in range(c + 1, f['filled'])), f'fvg {b} fill index')
            else:
                check(all(L[j] > f['bottom'] for j in range(c + 1, n)), f'fvg {b} unfilled')
        else:
            check(H[c] < L[a] and f['top'] == L[a] and f['bottom'] == H[c], f'fvg {b}: bear gap = C high → A low')
            if f['filled'] is not None:
                check(H[f['filled']] >= f['top'] and all(H[j] < f['top'] for j in range(c + 1, f['filled'])), f'fvg {b} fill index')
            else:
                check(all(H[j] < f['top'] for j in range(c + 1, n)), f'fvg {b} unfilled')
    fv = {(f['dir'], f['b']) for f in R['fvgs']}
    swp = {(w['side'], w['i']) for w in R['sweeps']}
    for ob in R['obs']:
        j, d, k = ob['i'], ob['dir'], ob['break']
        check(opp(K, j, d), f'ob {j}: opposite-colour candle')
        check(ob['top'] == max(K[j]['o'], K[j]['c']) and ob['bottom'] == min(K[j]['o'], K[j]['c']), f'ob {j}: body only')
        check(j < k, f'ob {j} before the break')
        check(j + 1 >= k or not opp(K, j + 1, d), f'ob {j}: last opposite candle before displacement')
        check(all((d, b) in fv and j < b <= k for b in ob['fvg']), f'ob {j}: FVG refs valid')
        check(all((('low' if d == 1 else 'high'), i) in swp for i in ob['sweep']), f'ob {j}: sweep refs valid')
        check(ob['valid'] == bool(ob['fvg'] and ob['sweep']), f'ob {j}: valid = all three conditions')
        if ob['invalidated'] is not None:
            x = ob['invalidated']
            check(C[x] < ob['bottom'] if d == 1 else C[x] > ob['top'], f'ob {j} invalidation is a close through the body')
    verify_grades(K, R)
    r = R['range']
    if r:
        check(r['eq'] == (r['high'] + r['low']) / 2, 'range eq midpoint')
        if r['dir'] == 1:
            check(r['high'] >= r['ote'][0] >= r['ote'][1] >= r['ote'][2] >= r['low'], 'bull OTE inside range, measured from the high')
            check(r['low'] == L[r['low_i']] and r['high'] == max(H[r['low_i']:]), 'bull range extremes')
        else:
            check(r['low'] <= r['ote'][0] <= r['ote'][1] <= r['ote'][2] <= r['high'], 'bear OTE inside range, measured from the low')
            check(r['high'] == H[r['high_i']] and r['low'] == min(L[r['high_i']:]), 'bear range extremes')


def verify_grades(K, R):
    """强弱判断：按 09 第五节的标准独立重算，必须和引擎给的强 / 弱一致。"""
    p = R['params']
    n = len(K)
    O = [k['o'] for k in K]
    C = [k['c'] for k in K]

    def A(x):  # 前一根的 ATR
        return sd_atr(K, max(0, x - 1), p['atr_len'])

    def near(a, b):
        return abs(a - b) <= 1e-9 * max(1.0, abs(b))

    for ob in R['obs']:
        j, d = ob['i'], ob['dir']
        body, full = abs(C[j] - O[j]), K[j]['h'] - K[j]['l']
        ratio = body / full if full > 0 else 0
        a = A(j)
        weak_body = ratio < p['full_body_ratio'] or body < p['full_body_atr'] * a
        nxt = [x for x in range(j + 1, min(j + 3, n)) if (C[x] - O[x]) * d > 0]
        big = max([abs(C[x] - O[x]) for x in nxt] or [0])
        eng = j + 1 < n and (C[j + 1] - O[j + 1]) * d > 0 and min(O[j + 1], C[j + 1]) <= ob['bottom'] + 1e-12 and max(O[j + 1], C[j + 1]) >= ob['top'] - 1e-12
        strong = (not weak_body) and (eng or big >= p['disp_atr'] * a)
        check((ob['grade'] == 'strong') == strong, f'ob {j}: grade (body {ratio:.2f}, {body / a:.2f} ATR)')
        if ratio < 0.3 and ob['grade'] == 'strong':
            check(False, f'ob {j}: doji-like OB must never be strong')
    for f in R['fvgs']:
        a = A(f['b'])
        small = f['top'] - f['bottom'] < p['fvg_weak_atr'] * a
        withbrk = any(e['dir'] == f['dir'] and e.get('origin', e['from'] + 1) <= f['b'] <= e['i'] for e in R['events'])
        check((f['grade'] == 'strong') == (not small and withbrk), f'fvg {f["b"]}: grade')
    for w in R['sweeps']:
        i, a = w['i'], A(w['i'])
        depth = w['level'] - K[i]['l'] if w['side'] == 'low' else K[i]['h'] - w['level']
        cl = C[i:min(i + p['react_bars'], n - 1) + 1]
        best = (max(cl) - w['level']) if w['side'] == 'low' else (w['level'] - min(cl))
        check((w['grade'] == 'strong') == (depth >= p['sweep_min_atr'] * a and best >= p['react_atr'] * a), f'sweep {i}: grade')
    for e in R['events']:
        i, a = e['i'], A(e['i'])
        margin = (C[i] - e['level']) * e['dir']
        st = e.get('origin', e['from'] + 1)
        disp = any(f['dir'] == e['dir'] and st <= f['b'] <= i for f in R['fvgs']) or (C[i] - O[i]) * e['dir'] >= p['break_body_atr'] * a
        check((e['grade'] == 'strong') == (margin >= p['break_min_atr'] * a and disp), f'event {i}: grade')


def sd_atr(K, i, ln):
    tr = []
    for x in range(max(0, i - ln + 1), i + 1):
        k = K[x]
        tr.append(k['h'] - k['l'] if x == 0 else max(k['h'] - k['l'], abs(k['h'] - K[x - 1]['c']), abs(k['l'] - K[x - 1]['c'])))
    return sum(tr) / len(tr)


def verify_select(K, R, sel):
    for it in sel['items']:
        kind, idx = it['ref']
        if kind == 'event':
            check(it['price'] == R['events'][idx]['level'], 'select: structure price')
        elif kind == 'pool':
            check(R['pools'][idx]['state'] == 'active' and it['price'] == R['pools'][idx]['level'], 'select: pool active')
        elif kind == 'ob':
            ob = R['obs'][idx]
            check(ob['valid'] and ob['invalidated'] is None and (it['top'], it['bottom']) == (ob['top'], ob['bottom']), 'select: only valid live OBs')
        elif kind == 'fvg':
            f = R['fvgs'][idx]
            check(f['filled'] is None and (it['top'], it['bottom']) == (f['top'], f['bottom']) and it['i1'] == f['b'], 'select: FVG drawn from B')
        elif kind == 'level':
            check(R['levels'][idx]['state'] == 'active', 'select: target untaken')
    for kind, lst, ok in (('ob', R['obs'], lambda o: o['valid'] and o['invalidated'] is None and o['i'] >= sel['from']),
                          ('fvg', R['fvgs'], lambda f: f['filled'] is None and f['b'] >= sel['from'])):
        shown = [R[kind + 's'][it['ref'][1]] for it in sel['items'] if it['ref'][0] == kind]
        strong_all = [x for x in lst if ok(x) and x['grade'] == 'strong']
        check(sum(x['grade'] == 'strong' for x in shown) == min(2, len(strong_all)), f'select: {kind} slots go to strong items first')


# ---------------------------------------------------------------- 3. 数据文件（多种格式）
def write_formats(rows, d, tmp, tag):
    from datetime import datetime, timedelta, timezone
    t0 = datetime(2026, 1, 5, tzinfo=timezone.utc)
    ts = [t0 + timedelta(minutes=15 * i) for i in range(len(rows))]
    f = lambda x: f'{x:.{d}f}'  # noqa: E731
    files = {}
    p = os.path.join(tmp, tag + '_mt5.csv')
    open(p, 'w').write('\n'.join(['<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>'] +
                                 [f'{t:%Y.%m.%d}\t{t:%H:%M:%S}\t' + '\t'.join(map(f, r)) + '\t10' for t, r in zip(ts, rows)]))
    files['mt5'] = p
    p = os.path.join(tmp, tag + '_tv.csv')
    open(p, 'w').write('\n'.join(['time,open,high,low,close,Volume'] +
                                 [f'{int(t.timestamp())},' + ','.join(map(f, r)) + ',5' for t, r in zip(ts, rows)]))
    files['tv'] = p
    p = os.path.join(tmp, tag + '_mt4.csv')
    open(p, 'w').write('\n'.join([f'{t:%Y.%m.%d},{t:%H:%M},' + ','.join(map(f, r)) + ',7' for t, r in zip(ts, rows)]))
    files['mt4'] = p
    p = os.path.join(tmp, tag + '_desc_semicolon.csv')
    open(p, 'w').write('\n'.join(['Datum;Open;High;Low;Close'] +
                                 [f'{t:%Y-%m-%d %H:%M};' + ';'.join(f(x).replace('.', ',') for x in r) for t, r in reversed(list(zip(ts, rows)))]))
    files['desc'] = p  # 表头里没有认识的时间列名 → 只认开高低收；倒序但时间列不认识，所以不翻转（测试读取一致即可）
    p = os.path.join(tmp, tag + '_binance.json')
    json.dump([[int(t.timestamp() * 1000)] + [f(x) for x in r] + ['1.0', 0] for t, r in zip(ts, rows)], open(p, 'w'))
    files['binance'] = p
    p = os.path.join(tmp, tag + '_cn.csv')
    open(p, 'w').write('\n'.join(['日期,开盘,最高,最低,收盘,成交量'] +
                                 [f'{t0 + timedelta(days=i):%Y-%m-%d},' + ','.join(map(f, r)) + ',100' for i, r in reversed(list(enumerate(rows)))]))
    files['cn_desc'] = p  # 日线、倒序（国内软件常见），读取时应自动翻转
    return files


def datasets():
    out = []
    for seed in range(60):
        rnd = random.Random(seed)
        n = rnd.choice([40, 120, 300, 600])
        rows = series(seed, n, 1.1 + seed * 0.01)
        d = rnd.choice([5, 5, 3, 2])
        if d < 5:  # 少位小数 → 大量同价高低点，专门测并列的处理
            rows = [tuple(round(x * (10 if d == 3 else 100), d) for x in r) for r in rows]
            rows = [(o, max(o, h, l, c), min(o, h, l, c), c) for o, h, l, c in rows]
        out.append((f'set{seed}', rows, d, {'swing': rnd.choice([2, 3, 4, 5]), 'last': rnd.choice([60, 120, 200])}))
    return out


def test_page():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('SKIP page test: playwright not installed')
        return
    K, info = sd.parse(open('detector/demo-mt5.csv', encoding='utf-8').read())
    R = sd.detect(K)
    want = sd.report(K, R, sd.select(K, R), info, 'zh')
    with sync_playwright() as p:
        b = p.chromium.launch()
        for w in (1400, 390):
            pg = b.new_page(viewport={'width': w, 'height': 900})
            errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.goto('file://' + os.path.abspath('detector/index.html'))
            pg.click('#demoBtn')
            got = pg.input_value('#report').split('\n', 1)[-1]
            check(not errs, f'page {w}px: JS errors {errs}')
            check(got == want, f'page {w}px: report differs from Python')
            check(pg.evaluate("getComputedStyle(document.getElementById('empty')).display") == 'none', f'page {w}px: chart drawn')
            check(pg.evaluate('document.documentElement.scrollWidth') <= w, f'page {w}px: no horizontal scroll')
        b.close()
    print('page test done')


def main():
    test_planted()
    test_page()
    tmp = tempfile.mkdtemp(prefix='smcdet_')
    jobs, py = [], []
    count = 0
    for tag, rows, d, params in datasets():
        for fmt, path in write_formats(rows, d, tmp, tag).items():
            K, info = sd.parse(open(path, encoding='utf-8').read())
            check(len(K) == len(rows), f'{tag}/{fmt}: all rows read')
            if fmt in ('mt5', 'tv', 'mt4', 'binance', 'cn_desc'):
                check([(k['o'], k['h'], k['l'], k['c']) for k in K] == [tuple(round(x, d) for x in r) for r in rows], f'{tag}/{fmt}: values and order')
            R = sd.detect(K, params)
            sel = sd.select(K, R, params['last'])
            if fmt == 'mt5':
                verify(K, R)
                verify_select(K, R, sel)
                count += len(R['fvgs']) + len(R['obs']) + len(R['events']) + len(R['sweeps']) + len(R['pools'])
            jobs.append({'file': path, 'params': params})
            py.append({'K': K, 'info': info, 'R': R, 'sel': sel, 'zh': sd.report(K, R, sel, info, 'zh'), 'en': sd.report(K, R, sel, info, 'en')})
    print(f'checked {count} detected items across {len(jobs) // 6} datasets')
    node = shutil.which('node')
    if not node:
        print('SKIP parity: Node.js not found')
    else:
        jp, op = os.path.join(tmp, 'jobs.json'), os.path.join(tmp, 'out.json')
        json.dump(jobs, open(jp, 'w'))
        subprocess.run([node, 'tools/detect_node_runner.js', jp, op], check=True)
        js = json.load(open(op, encoding='utf-8'))
        same = 0
        for job, a, b in zip(jobs, py, js):
            a = json.loads(json.dumps(a))
            if 'error' in b:
                check(False, f'JS error on {job["file"]}: {b["error"]}')
                continue
            for key in ('K', 'info', 'R', 'sel', 'zh', 'en'):
                if a[key] != b[key]:
                    check(False, f'parity {key} differs on {os.path.basename(job["file"])}')
                    break
            else:
                same += 1
        print(f'parity: {same}/{len(jobs)} files identical between Python and JS')
    shutil.rmtree(tmp, ignore_errors=True)
    if FAILS:
        print('FAILED:')
        for m in sorted(set(FAILS))[:40]:
            print('  -', m)
        sys.exit(1)
    print('all detector tests passed')


if __name__ == '__main__':
    main()
