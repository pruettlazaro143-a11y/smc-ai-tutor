"""SMC 识别引擎（Python 版）：从 K 线数据里按教程规则精确识别结构、流动性、FVG、OB、区间。

用法：
  python3 smc_detect.py 数据.csv                 # 打印识别报告
  python3 smc_detect.py 数据.csv --png 图.png    # 同时画出标注图（需要 matplotlib）
  python3 smc_detect.py 数据.csv --json 结果.json --swing 3 --last 120 --lang en

支持的数据：
  - MT5 / MT4 导出的历史数据（<DATE> <TIME> <OPEN> ... 或无表头的 日期,时间,开,高,低,收,量）
  - 通用 CSV：表头含 open/high/low/close（或 开盘/最高/最低/收盘），可选 time/date 列
  - 币安 K 线 JSON（[[开盘时间, 开, 高, 低, 收, ...], ...]）

识别规则和网页版 detector/smc-detect.js 完全一致（tools/test_detect.py 会逐项比对），
规则说明见 skills/smc-learning/references/09-数据识别引擎.md。
这个文件刻意写成单文件、只用标准库（画图才需要 matplotlib），方便 AI 在自带的代码环境里直接运行。
"""
import json
import math
import re
import sys
from datetime import datetime, timezone

VERSION = 1
WEAK = ('ob_doji', 'ob_thin', 'ob_slow', 'fvg_small', 'fvg_nobreak', 'sw_shallow', 'sw_noreact', 'sw_pending', 'br_thin', 'br_nodisp')
DEFAULTS = {'swing': 3, 'atr_len': 14, 'eq_tol_atr': 0.1, 'eq_bounce_atr': 0.5, 'fvg_min_atr': 0.0, 'last': 120,
            # 强弱判断（见 09 第五节）：ATR 一律取该 K 线之前一根的 ATR，避免被它自己放大
            'full_body_ratio': 0.5, 'full_body_atr': 0.5,   # OB 实体饱满：实体 ≥ 全长 50% 且 ≥ 0.5 倍 ATR
            'doji_ratio': 0.3, 'doji_atr': 0.25,            # 接近十字星：实体 < 全长 30% 或 < 0.25 倍 ATR
            'disp_atr': 1.5,                                # 暴力推动：OB 后 2 根内有实体 ≥ 1.5 倍 ATR（或下一根直接吞没 OB 实体）
            'fvg_weak_atr': 0.3,                            # FVG 宽度 < 0.3 倍 ATR 算小
            'sweep_min_atr': 0.1, 'react_atr': 0.5, 'react_bars': 3,  # 清扫越过 < 0.1 倍 ATR 算浅；3 根内收盘反向离开 ≥ 0.5 倍 ATR 算有反应
            'break_min_atr': 0.1, 'break_body_atr': 1.0}    # 结构突破收盘越过 < 0.1 倍 ATR 算勉强；突破 K 线实体 ≥ 1 倍 ATR 算有位移
OTE = (0.62, 0.705, 0.79)


def fx(x, d):
    """四舍五入到 d 位小数（两版用同一种舍入，保证报告一字不差）。"""
    m = math.floor(abs(x) * 10 ** d + 0.5)
    t = str(m)
    if d > 0:
        t = t.rjust(d + 1, '0')
        t = t[:-d] + '.' + t[-d:]
    return ('-' if x < 0 and m > 0 else '') + t


# ============================== 1. 读数据 ==============================
NAMES = {
    'open': ('open', 'o', '开盘', '开盘价', '开'),
    'high': ('high', 'h', '最高', '最高价', '高'),
    'low': ('low', 'l', '最低', '最低价', '低'),
    'close': ('close', 'c', '收盘', '收盘价', '收', 'close/last', 'last', 'price'),
    'time': ('time', 'date', 'datetime', 'timestamp', 'opentime', 'open time', 'gmt time', 'local time', '日期', '时间', '交易日期'),
}


def _norm(cell):
    return cell.strip().strip('"\'').strip().strip('<>').strip().lower()


def _num(s):
    s = s.strip().strip('"\'').strip()
    if not re.fullmatch(r'[+-]?([0-9]+\.?[0-9]*|\.[0-9]+)([eE][+-]?[0-9]+)?', s):
        return None
    v = float(s)
    return v if math.isfinite(v) else None


def _decimals(s):
    s = s.strip().strip('"\'').strip()
    if 'e' in s.lower() or '.' not in s:
        return 0
    frac = s.split('.', 1)[1].rstrip('0')
    return len(frac)


def _fmt_unix(v):
    if v > 1e11:
        v = v / 1000.0
    return datetime.fromtimestamp(int(v), tz=timezone.utc).strftime('%Y-%m-%d %H:%M')


def _time_label(raw):
    raw = raw.strip().strip('"\'').strip()
    if re.fullmatch(r'[0-9]{9,13}(\.[0-9]+)?', raw):
        return _fmt_unix(float(raw)), float(raw)
    return raw, None


def parse(text):
    """把文本解析成 K 线。返回 (candles, info)。candles: [{'t','o','h','l','c'}]。"""
    text = text.lstrip('﻿').strip()
    rows, warn, dec = [], [], 0
    if text.startswith('['):
        data = json.loads(text)
        for r in data:
            vals = [str(x) for x in r[1:5]]
            nums = [_num(x) for x in vals]
            if None in nums:
                continue
            dec = max([dec] + [_decimals(x) for x in vals])
            t = r[0]
            rows.append([_fmt_unix(float(t)) if isinstance(t, (int, float)) or re.fullmatch(r'[0-9]+', str(t)) else str(t),
                         float(t) if isinstance(t, (int, float)) or re.fullmatch(r'[0-9]+', str(t)) else None] + nums)
        src = 'json'
    else:
        lines = [ln for ln in re.split(r'\r?\n', text) if ln.strip()]
        first = lines[0]
        if '\t' in first:
            sep = '\t'
        elif first.count(';') > first.count(','):
            sep = ';'
        else:
            sep = ','
        comma_dec = sep == ';' and ',' in text and '.' not in text
        cells0 = [_norm(x) for x in first.split(sep)]
        idx = {}
        for key, names in NAMES.items():
            for k, cell in enumerate(cells0):
                if cell in names and key not in idx and k not in idx.values():
                    idx[key] = k
        tcol2 = None
        if all(k in idx for k in ('open', 'high', 'low', 'close')):
            body = lines[1:]
            src = 'header'
            if 'time' in idx and cells0[idx['time']] == 'date' and 'time' in cells0:
                tcol2 = cells0.index('time')
        else:
            body = lines
            n0 = len(first.split(sep))
            if n0 >= 6 and ':' in first.split(sep)[1]:
                idx = {'time': 0, 'open': 2, 'high': 3, 'low': 4, 'close': 5}
                tcol2 = 1
            elif n0 >= 5:
                idx = {'time': 0, 'open': 1, 'high': 2, 'low': 3, 'close': 4}
            elif n0 == 4:
                idx = {'open': 0, 'high': 1, 'low': 2, 'close': 3}
            else:
                raise ValueError('读不出开高低收四列 / cannot find open, high, low, close columns')
            src = 'noheader'
        for ln in body:
            cells = ln.split(sep)
            if len(cells) <= max(idx.values()):
                continue
            vals = [cells[idx[k]] for k in ('open', 'high', 'low', 'close')]
            if comma_dec:
                vals = [v.replace(',', '.') for v in vals]
            nums = [_num(v) for v in vals]
            if None in nums:
                continue
            dec = max([dec] + [_decimals(v) for v in vals])
            if 'time' in idx:
                raw = cells[idx['time']]
                if tcol2 is not None and tcol2 < len(cells):
                    raw = raw.strip() + ' ' + cells[tcol2].strip()
                label, tnum = _time_label(raw)
            else:
                label, tnum = '', None
            rows.append([label, tnum] + nums)
    if not rows:
        raise ValueError('没有读到有效的 K 线 / no valid candles found')
    # 顺序：时间是数字就按数字排；是"年份开头"的文字就比较数字串，倒序则翻转
    if all(r[1] is not None for r in rows):
        rows.sort(key=lambda r: r[1])
    else:
        a, b = rows[0][0], rows[-1][0]
        if re.match(r'[0-9]{4}[^0-9]', a) and re.match(r'[0-9]{4}[^0-9]', b):
            da, db = re.sub(r'[^0-9]', '', a), re.sub(r'[^0-9]', '', b)
            if len(da) == len(db) and da > db:
                rows.reverse()
    candles, bad = [], 0
    for r in rows:
        o, h, l, c = r[2:6]
        if h < max(o, c) or l > min(o, c):
            bad += 1
            continue
        candles.append({'t': r[0], 'o': o, 'h': h, 'l': l, 'c': c})
    if bad:
        warn.append(f'{bad} 行数据的高低点和开收盘矛盾，已跳过 / {bad} rows skipped (high/low inconsistent with open/close)')
    if len(candles) < 20:
        warn.append('K 线太少（少于 20 根），识别结果参考价值有限 / fewer than 20 candles')
    return candles, {'source': src, 'decimals': min(dec, 8), 'warnings': warn}


# ============================== 2. 识别 ==============================
def _bear(k, i):
    return k[i]['c'] < k[i]['o']


def _bull(k, i):
    return k[i]['c'] > k[i]['o']


def detect(K, params=None):
    """按教程规则识别。K: [{'o','h','l','c'}]。返回纯数据（dict），不含任何主观判断。"""
    p = dict(DEFAULTS)
    p.update(params or {})
    n, N = len(K), int(p['swing'])
    O = [k['o'] for k in K]
    H = [k['h'] for k in K]
    L = [k['l'] for k in K]
    C = [k['c'] for k in K]

    # ATR：真实波幅的简单平均（最近 atr_len 根，含当根）
    tr = []
    for i in range(n):
        if i == 0:
            tr.append(H[i] - L[i])
        else:
            tr.append(max(H[i] - L[i], abs(H[i] - C[i - 1]), abs(L[i] - C[i - 1])))
    atr = []
    for i in range(n):
        s, cnt = 0.0, 0
        for j in range(max(0, i - p['atr_len'] + 1), i + 1):
            s += tr[j]
            cnt += 1
        atr.append(s / cnt)

    # 摆动点：左边 N 根都更低（严格）、右边 N 根不高于它；第 i+N 根收完才确认
    swings = []
    for i in range(N, n - N):
        if all(H[i] > H[j] for j in range(i - N, i)) and all(H[i] >= H[j] for j in range(i + 1, i + N + 1)):
            swings.append({'type': 'high', 'i': i, 'price': H[i], 'confirmed': i + N})
        if all(L[i] < L[j] for j in range(i - N, i)) and all(L[i] <= L[j] for j in range(i + 1, i + N + 1)):
            swings.append({'type': 'low', 'i': i, 'price': L[i], 'confirmed': i + N})
    by_conf = {}
    for s in swings:
        by_conf.setdefault(s['confirmed'], []).append(s)

    events, sweeps, levels, pools = [], [], [], []
    ref = {'high': None, 'low': None}
    trend = 0
    for k in range(n):
        # (1) 流动性：影线越过、收盘收回 = 清扫；收盘越过 = 突破
        for lv in levels:
            if lv['state'] != 'active':
                continue
            if lv['type'] == 'high' and H[k] > lv['price']:
                lv['state'], lv['at'] = ('broken' if C[k] > lv['price'] else 'swept'), k
            elif lv['type'] == 'low' and L[k] < lv['price']:
                lv['state'], lv['at'] = ('broken' if C[k] < lv['price'] else 'swept'), k
            else:
                continue
            if lv['state'] == 'swept':
                sweeps.append({'side': lv['type'], 'i': k, 'level': lv['price'], 'from': lv['i'], 'pool': False})
        for pl in pools:
            if pl['state'] != 'active' or k <= pl['members'][-1]:
                continue
            if pl['type'] == 'high' and H[k] > pl['level']:
                pl['state'], pl['at'] = ('broken' if C[k] > pl['level'] else 'swept'), k
            elif pl['type'] == 'low' and L[k] < pl['level']:
                pl['state'], pl['at'] = ('broken' if C[k] < pl['level'] else 'swept'), k
            else:
                continue
            if pl['state'] == 'swept':
                sweeps.append({'side': pl['type'], 'i': k, 'level': pl['level'], 'from': pl['members'][-1], 'pool': True})
        # (2) 结构：实体收盘越过最近的摆动点
        rh, rl = ref['high'], ref['low']
        if rh is not None and not rh['broken'] and C[k] > rh['price']:
            events.append({'type': 'CHoCH' if trend == -1 else 'BOS', 'dir': 1, 'i': k, 'level': rh['price'],
                           'from': rh['i'], 'first': trend == 0})
            rh['broken'] = True
            trend = 1
        if rl is not None and not rl['broken'] and C[k] < rl['price']:
            events.append({'type': 'CHoCH' if trend == 1 else 'BOS', 'dir': -1, 'i': k, 'level': rl['price'],
                           'from': rl['i'], 'first': trend == 0})
            rl['broken'] = True
            trend = -1
        # (3) 这一根收完后确认的摆动点
        for s in by_conf.get(k, []):
            ref[s['type']] = {'i': s['i'], 'price': s['price'], 'broken': False}
            levels.append({'type': s['type'], 'i': s['i'], 'price': s['price'], 'state': 'active', 'at': None})
            # 等高 / 等低：和之前的同类摆动点几乎同价、中间有明显回落（反弹）、中间没有被越过
            tol = p['eq_tol_atr'] * atr[s['i']]
            prev = [x for x in swings if x['type'] == s['type'] and x['i'] < s['i'] and x['confirmed'] <= k]
            for q in reversed(prev):
                if abs(q['price'] - s['price']) > tol:
                    continue
                lo, hi = q['i'] + 1, s['i']
                if s['type'] == 'low':
                    lvl = min(q['price'], s['price'])
                    if any(L[j] < lvl for j in range(lo, hi)):
                        continue
                    if max(H[lo:hi] or [lvl]) - max(q['price'], s['price']) < p['eq_bounce_atr'] * atr[s['i']]:
                        continue
                else:
                    lvl = max(q['price'], s['price'])
                    if any(H[j] > lvl for j in range(lo, hi)):
                        continue
                    if min(q['price'], s['price']) - min(L[lo:hi] or [lvl]) < p['eq_bounce_atr'] * atr[s['i']]:
                        continue
                # 后面的点不能已经在确认前把这个池子扫掉
                if s['type'] == 'low' and any(L[j] < lvl for j in range(s['i'] + 1, k + 1)):
                    continue
                if s['type'] == 'high' and any(H[j] > lvl for j in range(s['i'] + 1, k + 1)):
                    continue
                joined = False
                for pl in pools:
                    if pl['type'] == s['type'] and pl['state'] == 'active' and pl['members'][-1] == q['i']:
                        pl['members'].append(s['i'])
                        pl['level'] = min(pl['level'], lvl) if s['type'] == 'low' else max(pl['level'], lvl)
                        joined = True
                        break
                if not joined:
                    pools.append({'type': s['type'], 'members': [q['i'], s['i']], 'level': lvl, 'state': 'active', 'at': None})
                break

    # FVG：A、C 不重叠，只有 B 穿过的那一段；从 B 开始向右
    fvgs = []
    for b in range(1, n - 1):
        a, c = b - 1, b + 1
        if L[c] > H[a]:
            d, top, bot = 1, L[c], H[a]
        elif H[c] < L[a]:
            d, top, bot = -1, L[a], H[c]
        else:
            continue
        if top - bot < p['fvg_min_atr'] * atr[b]:
            continue
        f = {'dir': d, 'a': a, 'b': b, 'c': c, 'top': top, 'bottom': bot, 'touched': None, 'filled': None}
        for j in range(c + 1, n):
            if d == 1:
                if f['touched'] is None and L[j] < top:
                    f['touched'] = j
                if L[j] <= bot:
                    f['filled'] = j
                    break
            else:
                if f['touched'] is None and H[j] > bot:
                    f['touched'] = j
                if H[j] >= top:
                    f['filled'] = j
                    break
        fvgs.append(f)

    # OB：每次结构突破，回到这段推动的起点，找位移前最后一根反向 K 线，只取实体
    obs, seen = [], set()
    for e in events:
        s, k, d = e['from'], e['i'], e['dir']
        if k - s < 2:
            continue
        rng = range(s + 1, k + 1)
        if d == 1:
            m = s + 1
            for j in rng:
                if L[j] <= L[m]:
                    m = j
            opp = _bear
        else:
            m = s + 1
            for j in rng:
                if H[j] >= H[m]:
                    m = j
            opp = _bull
        e['origin'] = m
        if opp(K, m):
            j = m
            while j + 1 < k and opp(K, j + 1):
                j += 1
        else:
            j = m - 1
            while j > s and not opp(K, j):
                j -= 1
            if j <= s:
                continue
        if j >= k or (d, j) in seen:
            continue
        seen.add((d, j))
        has_fvg = [f['b'] for f in fvgs if f['dir'] == d and j + 1 <= f['b'] <= k]
        side = 'low' if d == 1 else 'high'
        has_sweep = sorted({w['i'] for w in sweeps if w['side'] == side and s + 1 <= w['i'] <= max(j, m)})
        top, bot = max(O[j], C[j]), min(O[j], C[j])
        ob = {'dir': d, 'i': j, 'top': top, 'bottom': bot, 'break': k, 'break_type': e['type'], 'origin': m,
              'fvg': has_fvg, 'sweep': has_sweep, 'valid': bool(has_fvg and has_sweep),
              'tapped': None, 'invalidated': None}
        for x in range(k + 1, n):
            if d == 1:
                if ob['tapped'] is None and L[x] <= top:
                    ob['tapped'] = x
                if C[x] < bot:
                    ob['invalidated'] = x
                    break
            else:
                if ob['tapped'] is None and H[x] >= bot:
                    ob['tapped'] = x
                if C[x] > top:
                    ob['invalidated'] = x
                    break
        obs.append(ob)

    # ---------------- 强弱判断：不满足就标"弱"（偏重低、容易失效），并写明原因 ----------------
    def pre(x):
        return atr[x - 1] if x > 0 else atr[0]

    def leg_start(e):
        return e['origin'] if 'origin' in e else e['from'] + 1

    for ob in obs:
        j, d, A = ob['i'], ob['dir'], pre(ob['i'])
        body, full = ob['top'] - ob['bottom'], H[ob['i']] - L[ob['i']]
        ratio = body / full if full > 0 else 0.0
        notes = []
        if ratio < p['doji_ratio'] or body < p['doji_atr'] * A:
            notes.append(['ob_doji', ratio, body / A])
        elif ratio < p['full_body_ratio'] or body < p['full_body_atr'] * A:
            notes.append(['ob_thin', ratio, body / A])
        else:
            notes.append(['ob_full', ratio, body / A])
        big = 0.0
        for x in range(j + 1, min(j + 3, n)):
            if (C[x] - O[x]) * d > 0:
                big = max(big, abs(C[x] - O[x]))
        nx = j + 1
        engulf = nx < n and (C[nx] - O[nx]) * d > 0 and (
            (O[nx] <= ob['bottom'] and C[nx] >= ob['top']) if d == 1 else (O[nx] >= ob['top'] and C[nx] <= ob['bottom']))
        if engulf:
            notes.append(['ob_engulf'])
        elif big >= p['disp_atr'] * A:
            notes.append(['ob_disp', big / A])
        else:
            notes.append(['ob_slow', big / A])
        ob['notes'] = notes
        ob['grade'] = 'weak' if any(x[0] in WEAK for x in notes) else 'strong'
    for f in fvgs:
        A = pre(f['b'])
        size = f['top'] - f['bottom']
        notes = [['fvg_small', size / A] if size < p['fvg_weak_atr'] * A else ['fvg_size', size / A]]
        brk = [e['i'] for e in events if e['dir'] == f['dir'] and leg_start(e) <= f['b'] <= e['i']]
        notes.append(['fvg_break', brk[0]] if brk else ['fvg_nobreak'])
        f['notes'] = notes
        f['grade'] = 'weak' if any(x[0] in WEAK for x in notes) else 'strong'
    for w in sweeps:
        i, A = w['i'], pre(w['i'])
        depth = (w['level'] - L[i]) if w['side'] == 'low' else (H[i] - w['level'])
        notes = [['sw_pool']] if w['pool'] else []
        if depth < p['sweep_min_atr'] * A:
            notes.append(['sw_shallow', depth / A])
        end = min(i + p['react_bars'], n - 1)
        if w['side'] == 'low':
            best = max(C[i:end + 1]) - w['level']
        else:
            best = w['level'] - min(C[i:end + 1])
        if best >= p['react_atr'] * A:
            notes.append(['sw_react', best / A])
        elif i + p['react_bars'] > n - 1:
            notes.append(['sw_pending'])
        else:
            notes.append(['sw_noreact', best / A])
        w['notes'] = notes
        w['grade'] = 'weak' if any(x[0] in WEAK for x in notes) else 'strong'
    for e in events:
        i, A = e['i'], pre(e['i'])
        margin = (C[i] - e['level']) * e['dir']
        notes = []
        if margin < p['break_min_atr'] * A:
            notes.append(['br_thin', margin / A])
        st = leg_start(e)
        has_f = any(f['dir'] == e['dir'] and st <= f['b'] <= i for f in fvgs)
        big = (C[i] - O[i]) * e['dir'] >= p['break_body_atr'] * A
        notes.append(['br_disp'] if has_f or big else ['br_nodisp'])
        e['notes'] = notes
        e['grade'] = 'weak' if any(x[0] in WEAK for x in notes) else 'strong'

    # Premium / Discount：最近一次结构突破所在的那段推动（起点 → 之后的极值）
    rng = None
    if events:
        e = events[-1]
        m = e.get('origin')
        if m is not None:
            if e['dir'] == 1:
                lo_i, hi_i = m, m
                for j in range(m, n):
                    if H[j] > H[hi_i]:
                        hi_i = j
                lo, hi = L[lo_i], H[hi_i]
                ote = [hi - r * (hi - lo) for r in OTE]
            else:
                lo_i, hi_i = m, m
                for j in range(m, n):
                    if L[j] < L[lo_i]:
                        lo_i = j
                lo, hi = L[lo_i], H[hi_i]
                ote = [lo + r * (hi - lo) for r in OTE]
            eq = (hi + lo) / 2
            rng = {'dir': e['dir'], 'low_i': lo_i, 'high_i': hi_i, 'low': lo, 'high': hi, 'eq': eq, 'ote': ote,
                   'zone': 'premium' if C[n - 1] > eq else ('discount' if C[n - 1] < eq else 'equilibrium')}

    return {'version': VERSION, 'params': p, 'n': n, 'trend': trend, 'atr': atr[n - 1] if n else None,
            'swings': swings, 'events': events, 'sweeps': sweeps,
            'levels': [{k: v for k, v in lv.items()} for lv in levels], 'pools': pools,
            'fvgs': fvgs, 'obs': obs, 'range': rng}


# ============================== 3. 挑出值得画的 ==============================
def pick2(lst, key):
    """最多挑 2 个：先取最近的强项，不够再用最近的弱项补，最后按时间排序。"""
    strong = [x for x in lst if x['grade'] == 'strong']
    weak = [x for x in lst if x['grade'] != 'strong']
    out = strong[-2:]
    need = 2 - len(out)
    if need > 0:
        out = out + weak[-need:]
    return sorted(out, key=lambda x: x[key])


def select(K, R, last=None):
    """从识别结果里挑出图上要画的项目（不超过约 10 项），每项带依据。坐标用 K 线序号和价格。"""
    n = len(K)
    last = int(last or R['params']['last'])
    v0 = max(0, n - last)
    items = []

    def add(**it):
        items.append(it)

    # 结构：最近 2 次
    for e in [e for e in R['events'] if e['i'] >= v0][-2:]:
        nm = e['type']
        add(type='hline', kind='structure', i1=max(e['from'], v0), i2=e['i'], price=e['level'],
            label=f"{nm}{'↑' if e['dir'] == 1 else '↓'}", grade=e['grade'], ref=('event', R['events'].index(e)))
    # 等高等低：还没被扫的
    for pl in [p for p in R['pools'] if p['state'] == 'active' and p['members'][-1] >= v0][-2:]:
        add(type='hline', kind='liquidity', i1=max(pl['members'][0], v0), i2=n - 1, price=pl['level'],
            label='EQH BSL' if pl['type'] == 'high' else 'EQL SSL', ref=('pool', R['pools'].index(pl)))
    # 清扫：最近 2 次（同一根只标一次）
    shown = []
    for w in reversed(R['sweeps']):
        if w['i'] < v0 or w['i'] in [s['i'] for s in shown]:
            continue
        shown.append(w)
        if len(shown) == 2:
            break
    for w in reversed(shown):
        add(type='marker', kind='liquidity', i=w['i'], price=K[w['i']]['h'] if w['side'] == 'high' else K[w['i']]['l'],
            place='above' if w['side'] == 'high' else 'below', label='sweep', grade=w['grade'], ref=('sweep', R['sweeps'].index(w)))
    # OB：满足三个条件、还没失效的，最多 2 个；强的优先占名额，不够再用弱的补
    for ob in pick2([o for o in R['obs'] if o['valid'] and o['invalidated'] is None and o['i'] >= v0], 'i'):
        add(type='box', kind='ob', i1=ob['i'], i2=n - 1, top=ob['top'], bottom=ob['bottom'],
            label='Bull OB' if ob['dir'] == 1 else 'Bear OB', grade=ob['grade'], ref=('ob', R['obs'].index(ob)))
    # FVG：还没被完全回补的，最多 2 个，同样强的优先
    for f in pick2([f for f in R['fvgs'] if f['filled'] is None and f['b'] >= v0], 'b'):
        add(type='box', kind='fvg', i1=f['b'], i2=n - 1, top=f['top'], bottom=f['bottom'],
            label='FVG' + ('↑' if f['dir'] == 1 else '↓'), grade=f['grade'], ref=('fvg', R['fvgs'].index(f)))
    # 区间
    r = R['range']
    if r and max(r['low_i'], r['high_i']) >= v0:
        add(type='range', kind='range', i1=max(min(r['low_i'], r['high_i']), v0), i2=n - 1,
            high=r['high'], low=r['low'], eq=r['eq'], ote=r['ote'], label='EQ 50%', ref=('range', 0))
    # 对侧流动性：当前价上方最近的未被扫高点、下方最近的未被扫低点
    c = K[-1]['c']
    above = [lv for lv in R['levels'] if lv['type'] == 'high' and lv['state'] == 'active' and lv['price'] > c]
    below = [lv for lv in R['levels'] if lv['type'] == 'low' and lv['state'] == 'active' and lv['price'] < c]
    pool_px = [it['price'] for it in items if it['kind'] == 'liquidity' and it['type'] == 'hline']
    if above:
        lv = min(above, key=lambda x: (x['price'], -x['i']))
        if lv['price'] not in pool_px:
            add(type='hline', kind='target', i1=max(lv['i'], v0), i2=n - 1, price=lv['price'], label='BSL',
                ref=('level', R['levels'].index(lv)))
    if below:
        lv = max(below, key=lambda x: (x['price'], x['i']))
        if lv['price'] not in pool_px:
            add(type='hline', kind='target', i1=max(lv['i'], v0), i2=n - 1, price=lv['price'], label='SSL',
                ref=('level', R['levels'].index(lv)))
    for it in items:
        it['ref'] = list(it['ref'])
    return {'from': v0, 'to': n - 1, 'items': items}


# ============================== 4. 文字报告 ==============================
def report(K, R, sel, info=None, lang='zh'):
    d = (info or {}).get('decimals', 2)
    zh = lang != 'en'

    def P(x):
        return fx(x, d)

    def P1(x):
        return fx(x, d + 1)

    def A2(x):
        return fx(x, 2)

    def PC(x):
        return fx(x * 100, 0) + '%'

    def note(nt):
        c = nt[0]
        if zh:
            return {
                'ob_full': lambda: f'OB 实体饱满（占全长 {PC(nt[1])}，{A2(nt[2])} 倍 ATR）',
                'ob_thin': lambda: f'OB 实体不够饱满（只占全长 {PC(nt[1])}，{A2(nt[2])} 倍 ATR），挂在这里的单不多',
                'ob_doji': lambda: f'OB 接近十字星（实体只占全长 {PC(nt[1])}，{A2(nt[2])} 倍 ATR），多空几乎打平，说明不了大资金在这里成交',
                'ob_engulf': lambda: '下一根就用实体吞没了 OB 的实体，推动很猛',
                'ob_disp': lambda: f'之后 2 根内出现 {A2(nt[1])} 倍 ATR 的大实体，推动有力',
                'ob_slow': lambda: f'之后的推动不够猛（2 根内最大实体只有 {A2(nt[1])} 倍 ATR，也没有吞没 OB 实体）',
                'fvg_size': lambda: f'缺口宽 {A2(nt[1])} 倍 ATR',
                'fvg_small': lambda: f'缺口只有 {A2(nt[1])} 倍 ATR，一根影线就可能补掉',
                'fvg_break': lambda: f'伴随结构突破（{T(nt[1])}）',
                'fvg_nobreak': lambda: '没有伴随结构突破，没有结构配合的 FVG 很容易被一穿而过',
                'sw_pool': lambda: '扫的是等高 / 等低，止损最集中',
                'sw_shallow': lambda: f'只越过 {A2(nt[1])} 倍 ATR，几乎只是碰了一下',
                'sw_react': lambda: f'扫完 3 根内收盘反向离开关键位 {A2(nt[1])} 倍 ATR，有反应',
                'sw_noreact': lambda: f'扫完 3 根内没有明显反应（收盘最多离开关键位 {A2(nt[1])} 倍 ATR）',
                'sw_pending': lambda: '刚发生，还看不出反应',
                'br_thin': lambda: f'收盘只越过关键位 {A2(nt[1])} 倍 ATR，差一点就是假突破',
                'br_disp': lambda: '有位移配合（留下同向 FVG 或突破 K 线实体大）',
                'br_nodisp': lambda: '没有位移配合（没有同向 FVG，突破 K 线实体也不大）',
            }[c]()
        return {
            'ob_full': lambda: f'full-bodied OB candle ({PC(nt[1])} of its range, {A2(nt[2])}×ATR)',
            'ob_thin': lambda: f'OB body is not full ({PC(nt[1])} of its range, {A2(nt[2])}×ATR), so few orders sit there',
            'ob_doji': lambda: f'OB is nearly a doji ({PC(nt[1])} of its range, {A2(nt[2])}×ATR): buyers and sellers drew, which says little about big orders',
            'ob_engulf': lambda: 'the next candle engulfs the OB body: a forceful move',
            'ob_disp': lambda: f'a {A2(nt[1])}×ATR body within 2 candles: a forceful move',
            'ob_slow': lambda: f'the move away is weak (largest body within 2 candles is {A2(nt[1])}×ATR, and no engulfing)',
            'fvg_size': lambda: f'gap is {A2(nt[1])}×ATR wide',
            'fvg_small': lambda: f'gap is only {A2(nt[1])}×ATR, one wick can fill it',
            'fvg_break': lambda: f'part of a structure break ({T(nt[1])})',
            'fvg_nobreak': lambda: 'no structure break with it; an FVG without structure is easily run through',
            'sw_pool': lambda: 'it took equal highs / lows, where stops cluster most',
            'sw_shallow': lambda: f'it went only {A2(nt[1])}×ATR beyond the level, barely a touch',
            'sw_react': lambda: f'within 3 candles price closed {A2(nt[1])}×ATR back from the level: a reaction',
            'sw_noreact': lambda: f'no clear reaction within 3 candles (closes got at most {A2(nt[1])}×ATR back from the level)',
            'sw_pending': lambda: 'too recent to see a reaction',
            'br_thin': lambda: f'the close cleared the level by only {A2(nt[1])}×ATR, close to a false break',
            'br_disp': lambda: 'backed by displacement (a same-direction FVG or a large breaking body)',
            'br_nodisp': lambda: 'no displacement (no same-direction FVG and a small breaking body)',
        }[c]()

    def grade_line(obj):
        weak = [note(x) for x in obj['notes'] if x[0] in WEAK]
        good = [note(x) for x in obj['notes'] if x[0] not in WEAK]
        sep = '；' if zh else '; '
        if obj['grade'] == 'strong':
            return ('   → 强：' if zh else '   → Strong: ') + sep.join(good)
        t = ('   → 弱，偏重低、容易失效：' if zh else '   → Weak, low weight, fails easily: ') + sep.join(weak)
        if good:
            t += ('。好的一面：' if zh else '. On the plus side: ') + sep.join(good)
        return t

    def T(i):
        t = K[i]['t']
        return f'#{i}' + (f' ({t})' if t else '')

    def dirw(x):
        return ('多' if x == 1 else '空') if zh else ('bullish' if x == 1 else 'bearish')

    out = []
    out.append('SMC 识别报告（程序按规则计算，不是交易建议）' if zh else 'SMC detection report (rule-based, not trading advice)')
    out.append((f'K 线 {len(K)} 根，图上显示 {T(sel["from"])} 到 {T(sel["to"])}；摆动点参数 N={R["params"]["swing"]}；最新收盘 {P(K[-1]["c"])}'
                if zh else f'{len(K)} candles, chart shows {T(sel["from"])} to {T(sel["to"])}; swing N={R["params"]["swing"]}; last close {P(K[-1]["c"])}'))
    tr = {1: '上涨（最近一次结构突破向上）', -1: '下跌（最近一次结构突破向下）', 0: '未确定（还没有结构突破）'} if zh else \
        {1: 'up (last structure break was upward)', -1: 'down (last structure break was downward)', 0: 'undetermined (no structure break yet)'}
    out.append(('当前结构方向：' if zh else 'Structure: ') + tr[R['trend']])
    for w in (info or {}).get('warnings', []):
        out.append('⚠ ' + w)
    out.append('')
    for n_, it in enumerate(sel['items'], 1):
        kind, idx = it['ref'][0], it['ref'][1]
        graded = {'event': 'events', 'sweep': 'sweeps', 'ob': 'obs', 'fvg': 'fvgs'}.get(kind)
        if kind == 'event':
            e = R['events'][idx]
            gate = ('守门点' if e['type'] == 'CHoCH' else '摆动点') if zh else ('guard point' if e['type'] == 'CHoCH' else 'swing point')
            first = ('（之前方向未知，这是第一次突破）' if zh else ' (first break; prior direction unknown)') if e['first'] else ''
            if zh:
                out.append(f'{n_}. 【结构】{e["type"]}（{dirw(e["dir"])}）：{T(e["i"])} 收盘 {P(K[e["i"]]["c"])}，'
                           f'实体收{"上" if e["dir"] == 1 else "下"}破 {T(e["from"])} 的{gate} {P(e["level"])}{first}')
            else:
                out.append(f'{n_}. [Structure] {e["type"]} ({dirw(e["dir"])}): {T(e["i"])} closed at {P(K[e["i"]]["c"])}, '
                           f'{"above" if e["dir"] == 1 else "below"} the {gate} {P(e["level"])} at {T(e["from"])}{first}')
        elif kind == 'pool':
            pl = R['pools'][idx]
            ms = '、'.join(T(i) for i in pl['members']) if zh else ', '.join(T(i) for i in pl['members'])
            if zh:
                out.append(f'{n_}. 【流动性】{"等高 BSL" if pl["type"] == "high" else "等低 SSL"} {P(pl["level"])}：{ms} 几乎同价'
                           f'（差距不超过 {R["params"]["eq_tol_atr"]} 倍 ATR），中间有明显{"回落" if pl["type"] == "high" else "反弹"}，至今未被扫')
            else:
                out.append(f'{n_}. [Liquidity] {"Equal highs (BSL)" if pl["type"] == "high" else "Equal lows (SSL)"} {P(pl["level"])}: {ms} '
                           f'within {R["params"]["eq_tol_atr"]}×ATR, with a clear pullback between; not yet swept')
        elif kind == 'sweep':
            w = R['sweeps'][idx]
            c = K[w['i']]
            what = ('等高' if w['side'] == 'high' else '等低') if w['pool'] else ('高点' if w['side'] == 'high' else '低点')
            if zh:
                ext = f'最高 {P(c["h"])}' if w['side'] == 'high' else f'最低 {P(c["l"])}'
                out.append(f'{n_}. 【清扫】{T(w["i"])} 影线越过 {T(w["from"])} 的{what} {P(w["level"])}（{ext}），'
                           f'收盘 {P(c["c"])} 收回到里面')
            else:
                ext = f'high {P(c["h"])}' if w['side'] == 'high' else f'low {P(c["l"])}'
                what = ('equal highs' if w['side'] == 'high' else 'equal lows') if w['pool'] else ('swing high' if w['side'] == 'high' else 'swing low')
                out.append(f'{n_}. [Sweep] {T(w["i"])} wicked beyond the {what} {P(w["level"])} at {T(w["from"])} ({ext}) '
                           f'and closed back inside at {P(c["c"])}')
        elif kind == 'ob':
            ob = R['obs'][idx]
            st = ''
            if ob['tapped'] is not None:
                st = (f'；{T(ob["tapped"])} 首次回到区域' if zh else f'; first return at {T(ob["tapped"])}')
            else:
                st = ('；之后还没回来过' if zh else '; not revisited yet')
            if zh:
                out.append(f'{n_}. 【订单区】看{"涨" if ob["dir"] == 1 else "跌"} OB {T(ob["i"])}，只取实体 {P(ob["top"])}–{P(ob["bottom"])}：'
                           f'位移前最后一根{"阴" if ob["dir"] == 1 else "阳"}线；三个条件 ✓清扫（{"、".join(T(i) for i in ob["sweep"])}）'
                           f' ✓FVG（B={"、".join(T(i) for i in ob["fvg"])}） ✓{ob["break_type"]}（{T(ob["break"])}）{st}')
            else:
                out.append(f'{n_}. [Order block] {"Bullish" if ob["dir"] == 1 else "Bearish"} OB {T(ob["i"])}, body only {P(ob["top"])}–{P(ob["bottom"])}: '
                           f'last {"down" if ob["dir"] == 1 else "up"} candle before displacement; ✓sweep ({", ".join(T(i) for i in ob["sweep"])}) '
                           f'✓FVG (B={", ".join(T(i) for i in ob["fvg"])}) ✓{ob["break_type"]} ({T(ob["break"])}){st}')
        elif kind == 'fvg':
            f = R['fvgs'][idx]
            if zh:
                cmp_ = (f'A {T(f["a"])} 最高 {P(K[f["a"]]["h"])} < C {T(f["c"])} 最低 {P(K[f["c"]]["l"])}' if f['dir'] == 1 else
                        f'A {T(f["a"])} 最低 {P(K[f["a"]]["l"])} > C {T(f["c"])} 最高 {P(K[f["c"]]["h"])}')
                st = f'；{T(f["touched"])} 起被部分回补' if f['touched'] is not None else '；尚未回补'
                out.append(f'{n_}. 【FVG】{dirw(f["dir"])}头 FVG {P(f["top"])}–{P(f["bottom"])}（B={T(f["b"])}）：{cmp_}，中间没有重叠{st}')
            else:
                cmp_ = (f'A {T(f["a"])} high {P(K[f["a"]]["h"])} < C {T(f["c"])} low {P(K[f["c"]]["l"])}' if f['dir'] == 1 else
                        f'A {T(f["a"])} low {P(K[f["a"]]["l"])} > C {T(f["c"])} high {P(K[f["c"]]["h"])}')
                st = f'; partly filled from {T(f["touched"])}' if f['touched'] is not None else '; unfilled'
                out.append(f'{n_}. [FVG] {dirw(f["dir"])} FVG {P(f["top"])}–{P(f["bottom"])} (B={T(f["b"])}): {cmp_}, no overlap{st}')
        elif kind == 'range':
            r = R['range']
            zn = {'premium': 'Premium（贵区）', 'discount': 'Discount（便宜区）', 'equilibrium': '均衡点'} if zh else \
                {'premium': 'premium', 'discount': 'discount', 'equilibrium': 'equilibrium'}
            o = ' / '.join(P1(x) for x in r['ote'])
            lo_s, hi_s = f'{P(r["low"])}（{T(r["low_i"])}）', f'{P(r["high"])}（{T(r["high_i"])}）'
            lo_e, hi_e = f'{P(r["low"])} ({T(r["low_i"])})', f'{P(r["high"])} ({T(r["high_i"])})'
            if zh:
                leg = f'上涨推动：低点 {lo_s} 到高点 {hi_s}' if r['dir'] == 1 else f'下跌推动：高点 {hi_s} 到低点 {lo_s}'
                out.append(f'{n_}. 【区间】最近一段{leg}，50% 均衡点 {P1(r["eq"])}；当前收盘在 {zn[r["zone"]]}；'
                           f'OTE 0.62/0.705/0.79 = {o}（从推动终点往回量）')
            else:
                leg = f'up leg: low {lo_e} to high {hi_e}' if r['dir'] == 1 else f'down leg: high {hi_e} to low {lo_e}'
                out.append(f'{n_}. [Range] last {leg}, equilibrium {P1(r["eq"])}; price is in {zn[r["zone"]]}; '
                           f'OTE 0.62/0.705/0.79 = {o} (measured back from the leg end)')
        elif kind == 'level':
            lv = R['levels'][idx]
            if zh:
                out.append(f'{n_}. 【对侧流动性】{"上方最近的未扫高点 BSL" if lv["type"] == "high" else "下方最近的未扫低点 SSL"} {P(lv["price"])}（{T(lv["i"])}）')
            else:
                out.append(f'{n_}. [Liquidity] nearest untaken {"swing high above (BSL)" if lv["type"] == "high" else "swing low below (SSL)"} {P(lv["price"])} ({T(lv["i"])})')
        if graded:
            out.append(grade_line(R[graded][idx]))
    if not sel['items']:
        out.append('图上范围内没有识别到符合规则的项目。' if zh else 'Nothing in view meets the rules.')
    cand = [o for o in R['obs'] if not o['valid'] and o['invalidated'] is None and o['i'] >= sel['from']][-2:]
    if cand:
        out.append('')
        out.append('不满足 OB 三个条件的候选（只能算 POI / 反应区，不画在图上）：' if zh else 'OB candidates that fail the three conditions (POI only, not drawn):')
        for ob in cand:
            miss = []
            if not ob['sweep']:
                miss.append('之前没有清扫' if zh else 'no sweep before it')
            if not ob['fvg']:
                miss.append('位移没有留下 FVG' if zh else 'no FVG in the displacement')
            out.append(f'- {T(ob["i"])} {P(ob["top"])}–{P(ob["bottom"])}' + ('：' + '、'.join(miss) if zh else ': ' + ', '.join(miss)))
    out.append('')
    if zh:
        out.append('强 / 弱：按实体是否饱满、推动是否有力、缺口大小、清扫深度和反应、突破幅度判断（标准见 09 第五节）。"弱"不是错，而是偏重低、容易失效，图上画成虚线。')
        out.append('程序没有判断的：诱导（Miller 严格口径）、多周期方向、消息面、拒绝针和入场触发。这些需要你自己核对。')
        out.append('识别规则见 references/09-数据识别引擎.md。仅供学习，不构成交易建议。')
    else:
        out.append('Strong / weak: graded by body fullness, force of the move, gap size, sweep depth and reaction, and break margin (rules in 09 section 5). "Weak" is not wrong, but low weight and easy to fail; it is drawn dashed.')
        out.append('Not judged by the program: inducement (Miller strict view), higher-timeframe bias, news, rejection wicks and entry triggers. Check these yourself.')
        out.append('Rules: references/09-数据识别引擎.md. For learning only, not trading advice.')
    return '\n'.join(out)


# ============================== 5. 画图 ==============================
def plot(K, R, sel, path, info=None, title=''):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    d = (info or {}).get('decimals', 2)
    v0, v1 = sel['from'], sel['to']
    col = {'structure': '#cfd8dc', 'liquidity': '#f5c542', 'fvg': '#4f8cff', 'ob': '#b47cff', 'target': '#26a69a'}
    fig = plt.figure(figsize=(16, 9), dpi=100, facecolor='#131722')
    ax = fig.add_axes([0.02, 0.06, 0.9, 0.88], facecolor='#131722')
    lo = min(K[i]['l'] for i in range(v0, v1 + 1))
    hi = max(K[i]['h'] for i in range(v0, v1 + 1))
    pad = (hi - lo) * 0.06 or 1
    for i in range(v0, v1 + 1):
        k = K[i]
        cc = '#26a69a' if k['c'] >= k['o'] else '#ef5350'
        ax.vlines(i, k['l'], k['h'], color=cc, lw=1)
        ax.add_patch(Rectangle((i - .32, min(k['o'], k['c'])), .64, max(abs(k['c'] - k['o']), (hi - lo) * 0.001), color=cc))
    right = v1 + max(4, (v1 - v0) // 12)

    def tag(x, y, s, c, va='bottom', ha='right'):
        ax.text(x, y, s, color=c, fontsize=10, va=va, ha=ha, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.2', fc='#131722', ec='none', alpha=0.8))

    for ix, it in enumerate(sel['items'], 1):
        k = it['kind']
        wk = it.get('grade') == 'weak'
        no = f'{ix} '
        lab = it['label'] + (' (weak)' if wk else '')
        if it['type'] == 'hline':
            ax.hlines(it['price'], it['i1'], right if k in ('liquidity', 'target') else it['i2'],
                      color=col[k], lw=1.4, linestyles=':' if wk else ('--' if k != 'structure' else '-'))
            if k == 'structure':
                tag(it['i2'] + .6, it['price'], no + lab + f' {fx(it["price"], d)}', col[k], va='center', ha='left')
            else:
                tag(right, it['price'], no + lab + f' {fx(it["price"], d)}', col[k])
        elif it['type'] == 'box':
            ax.add_patch(Rectangle((it['i1'] - .5, it['bottom']), right - it['i1'] + .5, it['top'] - it['bottom'],
                                   fc=col[k], alpha=0.1 if wk else 0.22, ec=col[k], lw=1.2, ls='--' if wk else '-'))
            tag(it['i1'] - .4, it['bottom'], no + lab, col[k], va='top', ha='left')
        elif it['type'] == 'marker':
            ax.plot([it['i']], [it['price']], 'o', ms=14, mfc='none', mec=col[k], mew=2, alpha=0.55 if wk else 1)
            tag(it['i'], it['price'] + (pad * .5 if it['place'] == 'above' else -pad * .5), no + lab, col[k],
                va='bottom' if it['place'] == 'above' else 'top', ha='center')
        elif it['type'] == 'range':
            ax.add_patch(Rectangle((it['i1'] - .5, it['eq']), right - it['i1'] + .5, it['high'] - it['eq'], fc='#ef5350', alpha=0.05, ec='none'))
            ax.add_patch(Rectangle((it['i1'] - .5, it['low']), right - it['i1'] + .5, it['eq'] - it['low'], fc='#26a69a', alpha=0.05, ec='none'))
            ax.hlines(it['eq'], it['i1'], right, color='#97a1b3', lw=1, linestyles=':')
            tag(it['i1'] - .4, it['eq'], no + f'EQ 50% {fx(it["eq"], d + 1)}', '#97a1b3', ha='left')
            ax.add_patch(Rectangle((it['i1'] - .5, min(it['ote'][0], it['ote'][2])), right - it['i1'] + .5,
                                   abs(it['ote'][2] - it['ote'][0]), fc='#ff9f43', alpha=0.08, ec='#ff9f43', lw=.6, ls=':'))
            tag(it['i1'] - .4, it['ote'][1], 'OTE', '#ff9f43', va='center', ha='left')
    ax.set_xlim(v0 - 1, right + 1)
    ax.set_ylim(lo - pad, hi + pad)
    ax.yaxis.tick_right()
    ax.tick_params(axis='y', colors='#b2b5be', labelsize=10)
    ticks = list(range(v0, v1 + 1, max(1, (v1 - v0) // 8)))
    ax.set_xticks(ticks)
    ax.set_xticklabels([(K[i]['t'] or f'#{i}')[-11:] for i in ticks], color='#b2b5be', fontsize=9)
    ax.grid(color='#2a2e39', lw=.5)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.text(v0, hi + pad * .55, (title + '   ' if title else '') + 'SMC detector · rule-based, not trading advice',
            color='#b2b5be', fontsize=11)
    fig.savefig(path, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)


# ============================== 命令行 ==============================
def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description='SMC detector')
    ap.add_argument('data')
    ap.add_argument('--swing', type=int, default=DEFAULTS['swing'])
    ap.add_argument('--last', type=int, default=DEFAULTS['last'])
    ap.add_argument('--png')
    ap.add_argument('--json')
    ap.add_argument('--lang', default='zh')
    ap.add_argument('--title', default='')
    a = ap.parse_args(argv)
    K, info = parse(open(a.data, encoding='utf-8-sig', errors='replace').read())
    R = detect(K, {'swing': a.swing, 'last': a.last})
    sel = select(K, R, a.last)
    print(report(K, R, sel, info, a.lang))
    if a.png:
        plot(K, R, sel, a.png, info, a.title)
    if a.json:
        json.dump({'info': info, 'detect': R, 'select': sel}, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main(sys.argv[1:])
