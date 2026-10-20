"""生成字符图库：skills/smc-learning/references/07-字符图库.md

字符图给只能显示文字的 AI 用。所有图都由数据生成（K 线开高低收，或折线拐点），
画之前先跑和 SVG 示意图同一套的逻辑断言，画完再检查关键位置在字符网格上的相对位置，
保证"看到的"和"讲的"一致。

在仓库根目录运行：python3 tools/gen_ascii.py
"""
import sys

ns_d = {}
_src = open('tools/gen_diagrams.py', encoding='utf-8').read()
sys.argv = ['x', '/tmp/_smc_unused']
exec(_src[:_src.index('for fn in (d00')], ns_d)
check = ns_d['check']
valid_candles = ns_d['valid_candles']

ns_m = {}
exec(open('tools/gen_models.py', encoding='utf-8').read(), ns_m)
REG = ns_m['REG']

OUT = 'skills/smc-learning/references/07-字符图库.md'

ZONE_CH = set('.:~')
LINE_CH = set('-=')


class Grid:
    def __init__(self, rows, cols):
        self.R, self.W = rows, cols
        self.g = [[' '] * cols for _ in range(rows)]
        self.right = {}

    def put(self, r, c, ch, over=False):
        if 0 <= r < self.R and 0 <= c < self.W:
            cur = self.g[r][c]
            if over or cur == ' ' or cur in ZONE_CH or (cur in LINE_CH and ch not in ZONE_CH):
                self.g[r][c] = ch

    def text(self, r, c, s, anchor='start'):
        if anchor == 'middle':
            c = c - len(s) // 2
        elif anchor == 'end':
            c = c - len(s) + 1
        for dr, dc in ((0, 0), (-1, 0), (1, 0), (0, -2), (0, 2), (-1, -2), (-1, 2), (1, -2), (1, 2),
                       (-2, 0), (2, 0), (0, -4), (0, 4), (-2, -3), (-2, 3), (2, -3), (2, 3)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < self.R and cc >= 0 and cc + len(s) <= self.W and \
                    all(self.g[rr][cc + k] == ' ' or self.g[rr][cc + k] in ZONE_CH or self.g[rr][cc + k] in LINE_CH for k in range(len(s))):
                for k, ch in enumerate(s):
                    self.g[rr][cc + k] = ch
                return rr
        raise AssertionError(f'ascii: no room for label {s!r} near row {r} col {c}')

    def hline(self, r, c0, c1, label=None, ch='-'):
        for c in range(c0, c1 + 1):
            self.put(r, c, ch)
        if label:
            self.right.setdefault(r, []).append(label)

    def zone(self, r0, r1, c0, c1, ch='.'):
        for r in range(min(r0, r1), max(r0, r1) + 1):
            for c in range(c0, c1 + 1):
                if self.g[r][c] == ' ':
                    self.g[r][c] = ch

    def render(self):
        lines = [''.join(row).rstrip() for row in self.g]
        width = max(len(x) for x in lines)
        out = []
        for r, ln in enumerate(lines):
            if r in self.right:
                ln = ln.ljust(width) + '  ' + ' / '.join(self.right[r])
            out.append(ln.rstrip())
        while out and not out[0].strip():
            out.pop(0)
        while out and not out[-1].strip():
            out.pop()
        return '\n'.join(out)


# ---------------------------------------------------------------- candles
class Candles:
    """Each candle is 3 columns wide + 1 space.  Bullish body = [ ], bearish body = [#]."""

    def __init__(self, cs, rows=14, top=2, bottom=2, extra_cols=0):
        valid_candles(cs, 'ascii')
        self.cs, self.n = cs, len(cs)
        self.lo = min(c[2] for c in cs)
        self.hi = max(c[1] for c in cs)
        self.rows, self.top = rows, top
        self.G = Grid(top + rows + bottom, self.n * 4 + extra_cols)

    def r(self, p):
        return self.top + round((self.hi - p) / (self.hi - self.lo) * (self.rows - 1))

    def c(self, i):
        return i * 4 + 1

    def O(self, i): return self.cs[i][0]
    def H(self, i): return self.cs[i][1]
    def L(self, i): return self.cs[i][2]
    def Cl(self, i): return self.cs[i][3]

    def draw(self):
        for i, (o, h, l, c) in enumerate(self.cs):
            x = self.c(i)
            for r in range(self.r(h), self.r(l) + 1):
                self.G.put(r, x, '|', over=True)
            bull = c >= o
            for r in range(self.r(max(o, c)), self.r(min(o, c)) + 1):
                self.G.put(r, x - 1, '[', over=True)
                self.G.put(r, x, ' ' if bull else '#', over=True)
                self.G.put(r, x + 1, ']', over=True)

    def hline(self, p, i0, i1, label=None, ch='-'):
        self.G.hline(self.r(p), self.c(i0) - 1, self.c(i1) + 1, label, ch)

    def zone(self, p0, p1, i0, i1, ch='.'):
        self.G.zone(self.r(p0), self.r(p1), self.c(i0) - 1, self.c(i1) + 1, ch)

    def below(self, i, s):
        return self.G.text(self.r(self.L(i)) + 1, self.c(i), s, 'middle')

    def above(self, i, s):
        return self.G.text(self.r(self.H(i)) - 1, self.c(i), s, 'middle')

    def axis_labels(self, labels):
        r = self.G.R - 1
        for i, s in labels.items():
            self.G.text(r, self.c(i), s, 'middle')


# ---------------------------------------------------------------- polylines
class Line:
    """Hand-drawn style: every move is a 45-degree diagonal, one row per column.

    Only the vertical order of points matters for SMC (which high is higher, which low
    is lower), so x positions are re-timed from the vertical moves.  A peak at row r is
    drawn as '/\\' on row r; a trough at row r is drawn as '\\/' on row r - 1.
    """

    def __init__(self, path, rows=18, cols=None):
        self.path = path
        self.R = rows
        self.rr = [self.r(y) for _, y in path]
        cols_at = [0]
        for k in range(1, len(path)):
            d = abs(self.rr[k] - self.rr[k - 1])
            cols_at.append(cols_at[-1] + (d if d else max(1, round(abs(path[k][0] - path[k - 1][0]) * 0.3))))
        self.vc = cols_at
        self.G = Grid(rows + 1, cols_at[-1] + 2)
        self.kind = []
        for k in range(len(path)):
            prv = self.rr[k - 1] if k else None
            nxt = self.rr[k + 1] if k + 1 < len(path) else None
            up_before = prv is not None and prv > self.rr[k]
            down_after = nxt is not None and nxt > self.rr[k]
            down_before = prv is not None and prv < self.rr[k]
            up_after = nxt is not None and nxt < self.rr[k]
            if (up_before or prv is None) and (down_after or nxt is None) and (up_before or down_after):
                self.kind.append('peak')
            elif (down_before or prv is None) and (up_after or nxt is None) and (down_before or up_after):
                self.kind.append('trough')
            else:
                self.kind.append('flat')

    def r(self, y):
        return round(y / 100 * (self.R - 1))

    def cx(self, x):
        """map an original x coordinate to a column (piecewise linear through the vertices)"""
        xs = [px for px, _ in self.path]
        if x <= xs[0]:
            return self.vc[0]
        for k in range(1, len(xs)):
            if x <= xs[k]:
                t = (x - xs[k - 1]) / ((xs[k] - xs[k - 1]) or 1)
                return round(self.vc[k - 1] + t * (self.vc[k] - self.vc[k - 1]))
        return self.vc[-1] + round((x - xs[-1]) * 0.3)

    def row_of_level(self, y):
        """levels through peaks sit on the peak row; through troughs on the trough row."""
        rr = self.r(y)
        for k, (_, py) in enumerate(self.path):
            if py == y and self.kind[k] == 'trough':
                return rr - 1
        return rr

    def draw(self):
        for k in range(1, len(self.path)):
            r0, r1, c0 = self.rr[k - 1], self.rr[k], self.vc[k - 1]
            if r1 < r0:
                for s in range(r0 - r1):
                    self.G.put(r0 - 1 - s, c0 + s, '/', over=True)
            elif r1 > r0:
                for s in range(r1 - r0):
                    self.G.put(r0 + s, c0 + s, '\\', over=True)
            else:
                for s in range(self.vc[k] - c0):
                    self.G.put(r0 - 1 if self.kind[k - 1] == 'trough' else r0, c0 + s, '_', over=True)

    def verify(self, name):
        """The text picture must keep every vertical relation of the data."""
        n = len(self.path)
        inner = range(1, n - 1)  # the first and last points are where the drawing starts / ends, not swings
        for i in inner:
            for j in inner:
                if self.kind[i] == self.kind[j] and self.kind[i] in ('peak', 'trough'):
                    yi, yj = self.path[i][1], self.path[j][1]
                    if yi < yj:
                        check(self.vrow(i) < self.vrow(j), f'{name}: vertices {i} and {j} merged or flipped')
                    if yi == yj:
                        check(self.vrow(i) == self.vrow(j), f'{name}: equal vertices {i},{j} drawn at different rows')
        for y, x0, x1 in getattr(self, 'levels', []):
            lr = self.row_of_level(y)
            for k, (x, py) in enumerate(self.path):
                if 0 < k < n - 1 and x0 <= x <= x1 and self.kind[k] in ('peak', 'trough') and py != y:
                    if py < y:
                        check(self.vrow(k) < lr, f'{name}: vertex {k} should be drawn above level {y}')
                    else:
                        check(self.vrow(k) > lr or (self.kind[k] == 'trough' and self.vrow(k) >= lr), f'{name}: vertex {k} should be drawn below level {y}')

    def hline(self, y, x0, x1, label=None, ch='-'):
        self.levels = getattr(self, 'levels', []) + [(y, x0, x1)]
        self.G.W = max(self.G.W, self.cx(x1) + 1)
        for row in self.G.g:
            row.extend([' '] * (self.G.W - len(row)))
        self.G.hline(self.row_of_level(y), self.cx(x0), self.cx(x1), label, ch)

    def zone(self, y0, y1, x0, x1, ch='.'):
        self.G.W = max(self.G.W, self.cx(x1) + 1)
        for row in self.G.g:
            row.extend([' '] * (self.G.W - len(row)))
        self.G.zone(self.row_of_level(y0), self.row_of_level(y1), self.cx(x0), self.cx(x1), ch)

    def vertex(self, x, y):
        return min(range(len(self.path)), key=lambda k: abs(self.path[k][0] - x) + abs(self.path[k][1] - y))

    def label(self, k, s):
        c = self.vc[k]
        if self.kind[k] == 'peak':
            return self.G.text(self.rr[k] - 1, c, s, 'middle')
        if self.kind[k] == 'trough':
            return self.G.text(self.rr[k], c, s, 'middle')
        return self.G.text(self.rr[k] + 1, c, s, 'middle')

    def text(self, x, y, s, anchor='middle'):
        return self.label(self.vertex(x, y), s)

    def vrow(self, k):
        """row where vertex k is visually drawn"""
        return self.rr[k] - 1 if self.kind[k] == 'trough' else self.rr[k]


SECTIONS = []


def add(title, art, caption):
    SECTIONS.append((title, art, caption))


# ================================================================ 基础概念
# 1. 上涨 / 下跌结构
up = [(0, 94), (14, 58), (24, 76), (40, 40), (50, 58), (66, 22), (76, 40), (96, 4)]
check(up[1][1] > up[3][1] > up[5][1] and up[2][1] > up[4][1] > up[6][1] and up[0][1] > up[2][1], 'ascii structure: HH/HL rising')
L1 = Line(up, rows=16)
L1.draw()
L1.text(14, 58, 'H', 'middle')
L1.text(40, 40, 'HH', 'middle')
L1.text(66, 22, 'HH', 'middle')
L1.text(24, 76, 'HL', 'middle')
L1.text(50, 58, 'HL', 'middle')
L1.text(76, 40, 'HL', 'middle')
for (x, y), lab in ((up[1], 'H'), (up[3], 'HH'), (up[5], 'HH')):
    pass
art_up = L1.G.render()
L1.verify('ascii structure')
add('1 上涨结构（HH / HL）', art_up,
    '每个高点比前一个高（HH），每个低点也比前一个低点高（HL），上涨结构完好。下跌结构上下翻转：LH + LL。')

# 2. BOS / CHoCH / MSS
p2 = [(0, 4), (10, 40), (18, 24), (30, 62), (38, 48), (50, 88), (62, 32), (72, 62), (90, 14)]
check(p2[4][1] > p2[2][1], 'ascii BOS: second LH lower')
check(p2[3][1] > p2[1][1] and p2[5][1] > p2[3][1], 'ascii BOS: lower lows')
check(p2[6][1] < p2[4][1], 'ascii CHoCH: rally closes above last LH')
check(p2[7][1] < p2[5][1] and p2[8][1] < p2[6][1], 'ascii MSS: HL then new-direction BOS')
L2 = Line(p2, rows=18)
L2.hline(40, 10, 24, 'BOS down (break of low)')
L2.hline(48, 38, 58, 'CHoCH (close above last LH)')
L2.hline(32, 62, 80, 'BOS up -> MSS')
L2.draw()
L2.text(18, 24, 'LH', 'middle')
L2.text(38, 48, 'LH', 'end')
L2.text(50, 88, 'LL', 'middle')
L2.text(72, 62, 'HL', 'middle')
L2.verify('ascii BOS')
add('2 BOS / CHoCH / MSS', L2.G.render(),
    '下跌中价格跌破前低 = BOS（延续）。之后价格收盘突破最后一个 LH = CHoCH（第一次转向）。回调形成 HL 后再突破 CHoCH 后的高点 = 新方向 BOS，本教程把这一步叫 MSS（反转确认）。')

# 3. 等低与流动性清扫
cs3 = [[110.0, 110.3, 108.4, 108.7], [108.7, 108.9, 106.9, 107.2], [107.2, 107.4, 104.0, 105.4],
       [105.4, 107.6, 105.2, 107.3], [107.3, 108.4, 107.1, 108.1], [108.1, 108.2, 106.4, 106.7],
       [106.7, 106.9, 104.0, 105.5], [105.5, 106.9, 105.3, 106.6], [106.6, 106.8, 105.6, 105.9],
       [105.9, 106.2, 102.4, 105.6], [105.6, 108.2, 105.4, 108.0], [108.0, 110.2, 107.8, 109.9]]
lvl = 104.0
check(cs3[2][2] == lvl == cs3[6][2], 'ascii sweep: equal lows')
check(all(c[2] > lvl for k, c in enumerate(cs3[:9]) if k not in (2, 6)), 'ascii sweep: lows intact before sweep')
check(cs3[9][2] < lvl < cs3[9][3], 'ascii sweep: pierce and close back above')
K3 = Candles(cs3, rows=16, top=1, bottom=2)
check(all(K3.r(min(c[0], c[3])) <= K3.r(lvl) - 2 for c in cs3), 'ascii sweep: every body clearly above the equal lows')
check(all(K3.r(c[2]) <= K3.r(lvl) - 2 for k, c in enumerate(cs3) if k not in (2, 6, 9)), 'ascii sweep: other wicks clearly above the level')
K3.hline(lvl, 2, 9, 'Equal Lows')
K3.draw()
K3.G.text(K3.r(cs3[9][2]) + 1, K3.c(9), 'sweep', 'middle')
K3.G.text(K3.r(lvl) + 2, K3.c(4), 'SSL (stops)', 'middle')
check(K3.r(cs3[9][2]) > K3.r(lvl) > K3.r(cs3[9][3]), 'ascii sweep rows')
add('3 等低与流动性清扫', K3.G.render(),
    '两个相同的低点（Equal Lows）下方堆满多头止损（SSL）。倒数第三根用下影线刺穿后，实体收回到等低上方，这是清扫，不是突破。之后要有位移（连续大阳线）才有意义。')

# 4. 诱导 IDM
p4 = [(0, 94), (30, 18), (38, 30), (44, 46), (50, 36), (60, 62), (70, 40), (80, 8), (96, 4)]
check(p4[3][1] > p4[2][1] and p4[4][1] < p4[3][1] and p4[4][1] > p4[1][1], 'ascii IDM: pullback low, lower bounce')
check(p4[5][1] > p4[3][1], 'ascii IDM: IDM low swept')
check(p4[7][1] < p4[1][1], 'ascii IDM: BOS above top after sweep')
L4 = Line(p4, rows=18)
L4.hline(18, 30, 76, 'BOS (valid: IDM swept first)')
L4.hline(46, 44, 58, 'IDM low')
L4.zone(18, 30, 30, 38, ':')
L4.zone(54, 62, 56, 66, '.')
L4.draw()
L4.text(26, 26, 'decoy', 'end')
L4.text(61, 69, 'valid OB', 'middle')
L4.verify('ascii IDM')
add('4 诱导 Inducement（上涨）', L4.G.render(),
    '上涨中最近一次回撤的低点就是诱导点（IDM）。价格先把它扫掉，再突破前高，这次 BOS 才有效（Miller 的严格口径）。`:` 是靠近回撤起点的"饵"（decoy），`.` 是诱导被扫之后形成的有效 OB。')

# 5. FVG
cs5 = [[99.9, 100.3, 99.4, 99.7], [99.7, 100.2, 99.5, 100.0], [100.0, 100.8, 99.8, 100.6],
       [100.6, 104.6, 100.4, 104.2], [104.2, 105.7, 102.6, 105.2], [105.2, 105.4, 103.8, 104.0],
       [104.0, 104.2, 101.8, 102.4], [102.4, 104.9, 102.2, 104.7]]
A, B, Cc = 2, 3, 4
a_hi, c_lo = cs5[A][1], cs5[Cc][2]
check(c_lo > a_hi, 'ascii FVG: C.low above A.high')
check(a_hi < cs5[6][2] < c_lo or cs5[6][2] <= c_lo, 'ascii FVG: retest enters the gap')
check(all(c[2] > c_lo for c in cs5[Cc + 1:6]), 'ascii FVG: first entry is candle 6')
K5 = Candles(cs5, rows=15, top=1, bottom=2)
K5.zone(c_lo, a_hi, B, len(cs5) - 1, '.')
K5.hline(c_lo, B, len(cs5) - 1, 'top = C.low')
K5.hline(a_hi, B, len(cs5) - 1, 'bottom = A.high')
K5.draw()
K5.axis_labels({A: 'A', B: 'B', Cc: 'C'})
K5.below(6, 'retest')
check(K5.r(a_hi) - K5.r(c_lo) >= 2, 'ascii FVG: visible gap rows')
add('5 FVG（多头）', K5.G.render(),
    'A 的最高点（下沿）和 C 的最低点（上沿）之间没有重叠，`.` 标出的这段就是 FVG。区域从 B 开始向右画，A 和 C 都不在里面。之后价格回到这段空档（retest）时，再观察有没有反应。空头 FVG 上下翻转：A 的最低点到 C 的最高点。')

# 6. 看涨 OB
cs6 = [[110.0, 110.3, 108.6, 108.9], [108.9, 109.1, 107.2, 107.5], [107.5, 107.7, 105.9, 106.2],
       [106.2, 107.6, 106.0, 107.3], [107.3, 108.4, 107.1, 108.1], [108.1, 108.2, 106.9, 107.1],
       [107.1, 107.2, 106.3, 106.4], [106.4, 106.5, 104.8, 105.1], [105.1, 107.6, 105.0, 107.4],
       [107.4, 109.6, 107.3, 109.4], [109.4, 109.8, 108.4, 108.6], [108.6, 108.7, 106.0, 106.9],
       [106.9, 108.9, 106.8, 108.7]]
OBI = 7
prior_low, struct_hi = cs6[2][2], cs6[4][1]
check(all(c[2] > prior_low for c in cs6[3:OBI]), 'ascii OB: prior low intact')
check(cs6[OBI][2] < prior_low and cs6[OBI][3] < cs6[OBI][0] and cs6[OBI + 1][3] > cs6[OBI + 1][0], 'ascii OB: last bearish candle sweeps the low')
check(all(c[1] < struct_hi for c in cs6[5:OBI + 2]) and cs6[OBI + 2][3] > struct_hi, 'ascii OB: displacement closes above structure high')
check(cs6[OBI][1] < cs6[OBI + 2][2], 'ascii OB: FVG after OB')
check(cs6[OBI][0] - cs6[OBI][3] >= 0.5 * (cs6[OBI][1] - cs6[OBI][2]) and cs6[OBI + 1][0] <= cs6[OBI][3] and cs6[OBI + 1][3] >= cs6[OBI][0], 'ascii OB: full-bodied OB, engulfed by the next candle')
ob_top, ob_bot = cs6[OBI][0], cs6[OBI][3]
ret = next(k for k in range(OBI + 3, len(cs6)) if cs6[k][2] <= ob_top)
check(ret == 11, 'ascii OB: first return candle 11')
K6 = Candles(cs6, rows=15, top=1, bottom=2)
K6.zone(ob_top, ob_bot, OBI, len(cs6) - 1, ':')
K6.hline(prior_low, 2, OBI, 'prior low')
K6.hline(struct_hi, 4, OBI + 2, 'structure high')
K6.draw()
K6.below(OBI, 'OB')
K6.below(ret, 'return')
check(K6.r(cs6[OBI][2]) > K6.r(prior_low) and K6.r(cs6[OBI + 2][3]) < K6.r(struct_hi), 'ascii OB rows')
add('6 看涨 OB（取实体）', K6.G.render(),
    '扫掉前低（prior low）的最后一根阴线 `[#]` 就是 OB，`:` 标出的是它的**实体**范围（影线只作缓冲）。之后连续大阳线位移、收盘突破结构高点（structure high），中间留下 FVG。价格第一次回到 OB（return）时先看反应，不直接进。')

# 7. 完整入场节奏
p8 = [(0, 8), (16, 60), (28, 36), (40, 74), (52, 22), (62, 46), (68, 36), (94, 4)]
check(p8[3][1] > p8[1][1], 'ascii entry: sweep below SSL')
check(p8[4][1] < p8[2][1], 'ascii entry: displacement breaks LH (CHoCH)')
check(36 < p8[5][1] <= 50 and p8[5][1] < p8[3][1], 'ascii entry: retrace into FVG zone, above sweep low')
check(p8[7][1] < p8[0][1], 'ascii entry: target = prior high')
L8 = Line(p8, rows=20)
L8.hline(8, 0, 96, 'TP: BSL (prior high)')
L8.hline(60, 16, 46, 'SSL')
L8.hline(36, 28, 50, '3 CHoCH')
L8.hline(80, 40, 96, 'SL (below sweep)')
L8.zone(40, 50, 50, 72, '.')
L8.draw()
L8.label(3, '1 sweep')
L8.label(4, '2')
L8.label(5, '4')
L8.label(6, '5')
L8.verify('ascii entry')
add('7 完整入场节奏（多头）', L8.G.render(),
    '① 扫掉前低 SSL → ② 快速位移 → ③ 收盘突破内部 LH，出现 CHoCH → ④ 回踩到 FVG（`.`）→ ⑤ 出现反应 K 线，触发入场。止损（SL）在扫损低点下方，目标（TP）看上方前高的 BSL。')

# 8. 清扫 vs 真突破
sw = [[104.0, 105.2, 103.8, 105.0], [105.0, 107.4, 104.8, 107.1], [107.1, 107.3, 105.9, 106.2],
      [106.2, 107.2, 106.0, 107.0], [107.0, 108.9, 106.8, 107.1], [107.1, 107.2, 105.2, 105.5], [105.5, 105.6, 103.9, 104.2]]
bk = [[104.0, 105.2, 103.8, 105.0], [105.0, 107.4, 104.8, 107.1], [107.1, 107.3, 105.9, 106.2],
      [106.2, 107.2, 106.0, 107.0], [107.0, 108.9, 106.8, 108.6], [108.6, 108.7, 107.5, 107.8], [107.8, 109.9, 107.6, 109.7]]
lv = 107.4
check(sw[4][1] > lv > sw[4][3] and all(c[3] < lv for c in sw), 'ascii sweep: pierce, close back below')
check(bk[4][3] > lv and all(c[3] > lv for c in bk[4:]) and bk[5][2] > lv - 0.0, 'ascii breakout: close above, retest holds')
Ks = Candles(sw, rows=12, top=1, bottom=2)
Ks.hline(lv, 1, 6)
Ks.draw()
Ks.above(4, 'wick')
Kb = Candles(bk, rows=12, top=1, bottom=2)
Kb.hline(lv, 1, 6)
Kb.draw()
Kb.below(5, 'holds')
left, right = Ks.G.render().split('\n'), Kb.G.render().split('\n')
h = max(len(left), len(right))
left += [''] * (h - len(left))
right += [''] * (h - len(right))
wl = max(len(x) for x in left)
art9 = 'SWEEP'.ljust(wl) + '      BREAKOUT\n' + '\n'.join(a.ljust(wl) + '      ' + b for a, b in zip(left, right))
add('8 清扫 vs 真突破', art9.rstrip(),
    '左：上影线刺穿前高（wick）后收盘回到下方 = 清扫。右：实体收盘站上前高，回踩时守住（holds）= 真突破。区别看收盘和后续。')

# 9. 拒绝针强弱【作者实战经验】
strong = [[110, 110.4, 107.8, 108.2], [108.2, 108.5, 106.2, 106.6], [106.6, 106.9, 104.9, 105.3],
          [105.3, 105.7, 100.6, 105.0], [105.0, 109.6, 104.8, 109.3]]
weak = [[110, 110.4, 107.8, 108.2], [108.2, 108.5, 106.2, 106.6], [106.6, 106.9, 104.9, 105.3],
        [105.3, 105.9, 100.6, 104.4], [104.4, 105.2, 103.6, 104.7]]
check(strong[4][0] <= min(strong[3][0], strong[3][3]) and strong[4][3] >= max(strong[3][0], strong[3][3]), 'ascii pin: engulf')
check(abs(weak[4][3] - weak[4][0]) < abs(weak[3][0] - weak[3][3]), 'ascii pin: weak 2nd smaller')
Kp = Candles(strong, rows=13, top=1, bottom=2)
Kp.draw()
Kp.below(3, 'pin')
Kp.above(4, '2nd')
Kw = Candles(weak, rows=13, top=1, bottom=2)
Kw.draw()
Kw.below(3, 'pin')
Kw.above(4, '2nd')
left, right = Kp.G.render().split('\n'), Kw.G.render().split('\n')
h = max(len(left), len(right))
left += [''] * (h - len(left))
right += [''] * (h - len(right))
wl = max(len(x) for x in left)
art10 = 'STRONG'.ljust(wl) + '        WEAK\n' + '\n'.join(a.ljust(wl) + '        ' + b for a, b in zip(left, right))
add('9 拒绝针强弱【作者实战经验】', art10.rstrip(),
    '左：长下影、短实体的针，第 2 根大阳线用实体吞没针的实体 = 强。右：针的实体也不短，第 2 根小实体犹豫 = 弱，放弃。（作者个人经验，请自行验证）')

# 10. Premium / Discount（文字图）
add('10 Premium / Discount', '''100%  swing high  -------------------------------
                    PREMIUM   (look for shorts)
 50%  equilibrium - - - - - - - - - - - - - - - -
                    DISCOUNT  (look for longs)
  0%  swing low   -------------------------------''',
    '选一段决定结构的波段：50% 线以上是贵区，偏找空；以下是便宜区，偏找多。')

# ================================================================ 进阶模型（与 SVG 同一组折线数据）
MODEL_TXT = {
    'A1-Breaker破坏块': ('A1 破坏块 Breaker（看涨）', [(36, 26, 56, 'H'), (58, 12, 44, 'L')], [(40, 80, 'sweep L'), (56, 20, 'break H')], 'zone', 'L → H → 跌破 L（扫流动性）→ 实体突破 H。H 处原本的看跌 OB 失效，变成支撑区（`.`）。'),
    'A2-Mitigation缓解块': ('A2 缓解块 Mitigation（看涨）', [(36, 26, 56, 'H'), (62, 12, 44, 'L')], [(40, 54, 'higher low'), (56, 20, 'break H')], 'zone', '和 Breaker 一样突破 H，区别是回落时没能跌破 L（没有扫流动性）。'),
    'A4-OTE最佳入场区': ('A4 最佳入场区 OTE', [(12, 4, 90, '0 (high)'), ('FIB50', 4, 90, '0.5'), (88, 4, 90, '1 (low)')], [(68, 62, 'OTE')], 'zone', '从推动起点（1）拉到终点（0），回撤到 0.62–0.79（`.`）是 OTE。它只是位置过滤，仍要等反应。'),
    'A8-PO3三段式': ('A8 PO3 / AMD（看涨日）', [(46, 0, 92, 'open'), (70, 0, 34, 'prior low')], [(12, 40, 'A'), (34, 80, 'M'), (74, 24, 'D')], None, '开盘附近横盘（A 吸筹）→ 向下扫掉前低（M 操纵）→ 向上走出主波动（D 派发）。'),
    'B01-QM基础形态': ('B1 QM 卡西莫多（看跌）', [(45, 14, 92, 'QML')], [(14, 45, 'H'), (22, 62, 'L'), (34, 24, 'HH'), (48, 76, 'LL')], 'zone', 'H → L → HH（扫高）→ LL（跌破 L）→ 反弹回到 QML 与 HH 之间的供应区（`.`）。'),
    'B02-QM延迟回测': ('B2 QM 延迟回测（看跌）', [(45, 12, 92, 'QML')], [(12, 45, 'H'), (18, 62, 'L'), (28, 24, 'HH'), (40, 76, 'LL')], 'zone', '跌出 LL 后先在低位横盘一段，过一阵才回到 QML。'),
    'B03-影线QM': ('B3 影线 QM（DM Shadow）', [(45, 14, 92, 'QML')], [(14, 45, 'H'), (22, 62, 'L'), (33, 18, 'wick'), (48, 76, 'LL')], 'zone', 'QM 的头部只是一根 K 线的影线，区域取影线范围（这一派的特例）。'),
    'B04-延续型QM': ('B4 延续型 QM（看跌）', [(30, 22, 92, 'QML')], [(22, 30, 'H'), (28, 44, 'L'), (34, 22, 'HH'), (44, 60, 'LL')], 'zone', '已有下跌趋势中，回调里形成小 QM，回测 QML 后顺势继续下跌。'),
    'B05-双顶假突破': ('B5 2R 假突破（看跌）', [(40, 10, 92, 'equal highs')], [(10, 40, 'R'), (24, 40, 'R'), (40, 26, 'fake')], 'zone', '两次触碰同一阻力（等高）→ 刺破等高扫流动性 → 跌回下方，回到供应区再观察。'),
    'B06-QM再入场': ('B6 QM 再入场', [(40, 10, 92, 'main QML'), (52, 40, 92, 'small QML')], [(10, 40, 'H'), (24, 20, 'HH'), (34, 66, 'LL')], 'zone', '价格没回到主 QML，在下跌途中形成小 QM，在小 QML 再找一次机会。'),
    'B07-被忽略的QM': ('B7 被忽略的 QM（IQML）', [(40, 10, 92, 'IQML'), (58, 52, 70, 'mid R')], [(10, 40, 'H'), (24, 20, 'HH'), (34, 66, 'LL'), (62, 54, 'fake')], 'zone', 'QM 形成后没回测就继续跌；之后反弹先假突破中间阻力，再回到 IQML。'),
    'B08-统治者': ('B8 统治者 Ruler', [(48, 6, 92, 'key level')], [(10, 48, '1'), (16, 62, '2'), (24, 64, '3'), (32, 64, '3'), (38, 48, '4'), (64, 46, '5')], 'zone', '价格围绕同一水平线反复往返（1–4），第 5 次回到该区域时找入场。'),
    'B09-V型双顶': ('B9 V 型双顶（V Twin）', [(42, 6, 92, '')], [(15, 60, 'V'), (26, 60, 'V')], 'zone', '关键水平附近两个快速 V 形转折，回到这里时容易再次反应。'),
    'B10-旗形限制': ('B10 旗形限制 Flag Limit（看跌）', [(62, 4, 44, 'prior low')], [(26, 30, 'flag'), (46, 80, 'engulf')], 'zone', '高位横盘成旗 → 下跌吞没前低 → 起跌基底（Flag Limit，`.`）作为供应区。'),
    'B11-双旗形': ('B11 双旗形 Flag A + Flag B', [], [(14, 52, 'A'), (32, 30, 'B')], 'zone', '两层基底叠加，优先看离当前价更近、未被测试的 Flag B 限制区。'),
    'B12-默认假突破': ('B12 默认假突破 Fakeout V1', [(56, 26, 60, 'R1/R2')], [(12, 28, 'high'), (28, 56, 'R1'), (36, 56, 'R2')], 'zone', '下方形成 R1、R2 → 反弹刺破它们 → 到达上方供应区后下跌。'),
    'B13-支撑阻力互换假突破': ('B13 SR Flip 假突破 Fakeout V2', [(56, 8, 52, 'S -> R')], [(12, 56, 'S'), (36, 56, 'R1'), (44, 56, 'R2')], 'zone', '支撑 S 被跌破后变成阻力 → 在下方形成 R1、R2 → 假突破后到达供应区。'),
    'B14-钻石假突破': ('B14 钻石假突破 Fakeout V3', [(50, 24, 60, '')], [(28, 50, 'R'), (36, 50, 'R'), (54, 50, 'head')], 'zone', '供应区下方先扩张后收敛，QM 的头部与 R1/R2 在同一水平。'),
    'B15-最大痛苦位': ('B15 最大痛苦位 MPL', [(40, 6, 40, 'R R R'), (54, 10, 48, 'prior low')], [(40, 26, 'hunt'), (52, 80, 'engulf')], 'zone', '多次触碰阻力堆积止损 → 猎杀止损（hunt）→ 吞没前低：猎杀区就是供应区。'),
    'B16-双重支撑阻力': ('B16 双重支撑阻力 Double SSR', [(40, 4, 92, 'upper (R)'), (56, 4, 92, 'lower (S)')], [(48, 76, 'break')], 'zone', '上层原是阻力、下层原是支撑；跌破下层后反弹，先穿过翻转的下层，再到上层供应区。'),
    'B17-三推': ('B17 三推 3 Drive', [], [(28, 58, '1'), (45, 46, '2'), (66, 34, '3')], 'zone', '三段推向供应区，每段越来越缓（力度递减），第三推到达区域后反转。'),
    'B18-反复敲打': ('B18 反复敲打 CAN CAN', [], [(10, 30, 'taps')], 'zone', '先在供应区快速触碰多次，再缓慢、重叠地磨回来，回到区域后下跌。'),
    'B19-压缩': ('B19 压缩 Compression', [], [], 'zone', '重叠、阶梯式、很弱地靠近供应区；途中每个小需求区都被清除，反转往往很快。'),
    'B20-压缩流动性与假突破': ('B20 压缩流动性 CPLQ', [(50, 40, 53, 'LQ')], [(62, 30, 'sweep')], 'zone', '压缩中形成等高（LQ）→ 先向上扫掉等高 → 再从供应区下跌。'),
}
FIB = ns_m['FIB']
for name, (title, levels, labels, zmode, cap) in MODEL_TXT.items():
    spec = REG[name]
    L = Line(spec['path'], rows=20)
    for y, x0, x1, lab in levels:
        y = FIB(0.5) if y == 'FIB50' else y
        L.hline(y, x0, x1, lab or None)
    if zmode and spec['zones']:
        x1, x2, y1, y2 = spec['zones'][0][:4]
        L.zone(y1, y2, x1, x2, '.')
    L.draw()
    for x, y, s in labels:
        L.text(x, y, s)
    L.verify(name)
    add(title, L.G.render(), cap)

# ---------------------------------------------------------------- write
md = ['# 07 · 字符图库（自动生成）', '',
      '> 本文件由 `tools/gen_ascii.py` 生成，请勿手改。每张图都由数据生成，并通过了和 SVG 示意图同一套的逻辑断言。',
      '> 用法：只能显示文字的环境用这里的图。图必须放在代码块里原样输出，不要改动字符；中文解读写在图下面。',
      '> 图例：`[ ]` 阳线实体，`[#]` 阴线实体，`|` 影线，`/` `\\` `_` 走势，`-` 水平关键位，`.` `:` 区域（含义见每张图的解读）。', '']
for title, art, cap in SECTIONS:
    md += [f'## {title}', '', '```', art, '```', '', '解读：' + cap, '']
open(OUT, 'w', encoding='utf-8').write('\n'.join(md))
print('ascii charts:', len(SECTIONS))
