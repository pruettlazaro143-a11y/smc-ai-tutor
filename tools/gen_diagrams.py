"""Generate SMC teaching diagrams as standalone SVG files.

All candle data is synthetic. Every annotation is computed from the candle
data itself, so labels always sit on the right candles.
"""
import os
import random
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "diagrams/svg"
os.makedirs(OUT, exist_ok=True)

BRAND = "SMC 认知学习 · 示意图，非真实行情"
FONT = "'PingFang SC','Microsoft YaHei','Noto Sans CJK SC','Noto Sans SC',sans-serif"

C = {
    "bg": "#0f1218", "panel": "#141922", "grid": "#1f2632", "axis": "#2b3442",
    "text": "#e6eaf0", "muted": "#8a94a6",
    "bull": "#26a69a", "bear": "#ef5350",
    "liq": "#f5c542", "struct": "#cfd8dc", "fvg": "#4f8cff", "ob": "#b47cff",
    "prem": "#ef5350", "disc": "#26a69a", "eq": "#9aa4b2",
    "entry": "#4f8cff", "sl": "#ef5350", "tp": "#26a69a", "warn": "#ff9f43",
}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text_w(s, fs):
    w = 0
    for ch in s:
        w += fs * (1.0 if ord(ch) > 0x2E80 else 0.58)
    return w


def gen_path(waypoints, seed=1, noise=0.35, wick=(0.15, 0.7)):
    """waypoints: list of (index, price). Returns list of [o,h,l,c]."""
    rnd = random.Random(seed)
    closes = {}
    for (i0, p0), (i1, p1) in zip(waypoints, waypoints[1:]):
        lo, hi = min(p0, p1), max(p0, p1)
        for i in range(i0, i1 + 1):
            t = (i - i0) / (i1 - i0)
            p = p0 + (p1 - p0) * t
            if i not in (i0, i1):
                p += rnd.uniform(-noise, noise) * abs(p1 - p0) / max(1, (i1 - i0)) * 1.6
                p = min(max(p, lo + 0.05), hi - 0.05)
            closes[i] = p
    n = waypoints[-1][0] + 1
    wp = {i: p for i, p in waypoints}
    candles = []
    prev = closes[0] - (waypoints[1][1] - waypoints[0][1]) * 0.05
    for i in range(n):
        o, c = prev, closes[i]
        w1, w2 = rnd.uniform(*wick), rnd.uniform(*wick)
        h, l = max(o, c) + w1, min(o, c) - w2
        if i in wp and 0 < i < n - 1:
            # make the waypoint candle the clear extreme
            before, after = closes.get(i - 1, c), closes.get(i + 1, c)
            if c >= before and c >= after:
                h = c + wick[1] * 1.6
            elif c <= before and c <= after:
                l = c - wick[1] * 1.6
        candles.append([o, h, l, c])
        prev = c
    return candles


class Chart:
    def __init__(self, title, subtitle="", w=900, h=500):
        self.W, self.H = w, h
        self.title, self.subtitle = title, subtitle
        self.panels = []
        self.els = []

    def panel(self, candles, x0, y0, x1, y1, pad=None, label=None):
        p = Panel(self, candles, x0, y0, x1, y1, pad, label)
        self.panels.append(p)
        return p

    def svg(self):
        out = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.W} {self.H}" '
            f'width="{self.W}" height="{self.H}" font-family="{FONT}">',
            f'<rect width="{self.W}" height="{self.H}" fill="{C["bg"]}"/>',
            f'<text x="28" y="40" font-size="22" font-weight="700" fill="{C["text"]}">{esc(self.title)}</text>',
        ]
        if self.subtitle:
            out.append(f'<text x="28" y="66" font-size="14" fill="{C["muted"]}">{esc(self.subtitle)}</text>')
        for p in self.panels:
            out.extend(p.render())
        out.extend(self.els)
        out.append(
            f'<text x="{self.W - 20}" y="{self.H - 14}" font-size="11" text-anchor="end" fill="{C["muted"]}">{esc(BRAND)}</text>'
        )
        out.append("</svg>")
        return "\n".join(out)

    def save(self, name):
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(self.svg())


class Panel:
    def __init__(self, chart, candles, x0, y0, x1, y1, pad=None, label=None):
        self.ch, self.cs = chart, candles
        valid_candles(candles, label or "panel")
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.label = label
        lo = min(c[2] for c in candles)
        hi = max(c[1] for c in candles)
        pad = pad if pad is not None else (hi - lo) * 0.14
        self.lo, self.hi = lo - pad, hi + pad
        self.n = len(candles)
        self.step = (x1 - x0) / (self.n + 1.5)
        self.under = []  # zones drawn under candles
        self.over = []

    # coordinates
    def x(self, i):
        return self.x0 + self.step * (i + 1)

    def y(self, p):
        return self.y1 - (p - self.lo) / (self.hi - self.lo) * (self.y1 - self.y0)

    def H(self, i):
        return self.cs[i][1]

    def L(self, i):
        return self.cs[i][2]

    def O(self, i):
        return self.cs[i][0]

    def Cl(self, i):
        return self.cs[i][3]

    def argmax_h(self, i0, i1):
        i = max(range(i0, i1 + 1), key=lambda k: self.cs[k][1])
        return i, self.cs[i][1]

    def argmin_l(self, i0, i1):
        i = min(range(i0, i1 + 1), key=lambda k: self.cs[k][2])
        return i, self.cs[i][2]

    def first_close_above(self, level, start):
        for k in range(start, self.n):
            if self.cs[k][3] > level:
                return k
        raise ValueError(f"no close above {level}")

    def first_close_below(self, level, start):
        for k in range(start, self.n):
            if self.cs[k][3] < level:
                return k
        raise ValueError(f"no close below {level}")

    # annotations
    def zone(self, i0, i1, p0, p1, color, label=None, opacity=0.18, where="under", lpos="tl", lcolor=None):
        xa, xb = self.x(i0) - self.step * 0.5, self.x(i1) + self.step * 0.5
        ya, yb = self.y(max(p0, p1)), self.y(min(p0, p1))
        tgt = self.under if where == "under" else self.over
        tgt.append(
            f'<rect x="{xa:.1f}" y="{ya:.1f}" width="{xb - xa:.1f}" height="{yb - ya:.1f}" '
            f'fill="{color}" fill-opacity="{opacity}" stroke="{color}" stroke-opacity="0.7" stroke-width="1"/>'
        )
        if label:
            if lpos == "tl":
                self.tag(xa + 4, ya - 6, label, lcolor or color, anchor="start")
            elif lpos == "bl":
                self.tag(xa + 4, yb + 18, label, lcolor or color, anchor="start")
            elif lpos == "in":
                self.tag(xa + 6, (ya + yb) / 2 + 5, label, lcolor or color, anchor="start", box=False)

    def ob(self, i, i1, label, color, opacity=0.2, lpos="bl"):
        """OB zone = candle BODY (open..close); wick extremes as dotted buffer lines."""
        o, c = self.O(i), self.Cl(i)
        self.zone(i, i1, max(o, c), min(o, c), color, label, opacity=opacity, lpos=lpos)
        xa, xb = self.x(i) - self.step * 0.5, self.x(i1) + self.step * 0.5
        for pr in (self.H(i), self.L(i)):
            self.over.append(
                f'<line x1="{xa:.1f}" y1="{self.y(pr):.1f}" x2="{xb:.1f}" y2="{self.y(pr):.1f}" '
                f'stroke="{color}" stroke-width="1" stroke-dasharray="2 3" stroke-opacity="0.7"/>'
            )

    def hline(self, p, i0, i1, color, label=None, dash="6 4", lpos="end", width=1.4, above=True):
        xa, xb = self.x(i0), self.x(i1)
        yy = self.y(p)
        self.over.append(
            f'<line x1="{xa:.1f}" y1="{yy:.1f}" x2="{xb:.1f}" y2="{yy:.1f}" stroke="{color}" '
            f'stroke-width="{width}" stroke-dasharray="{dash}"/>'
        )
        if label:
            ty = yy - 7 if above else yy + 17
            if lpos == "end":
                self.tag(xb, ty, label, color, anchor="end")
            elif lpos == "start":
                self.tag(xa, ty, label, color, anchor="start")
            elif lpos == "right":
                self.tag(xb + 6, yy + 5, label, color, anchor="start")
            elif lpos == "mid":
                self.tag((xa + xb) / 2, ty, label, color, anchor="middle")

    def seg(self, i0, p0, i1, p1, color, dash="5 4", width=1.3):
        self.over.append(
            f'<line x1="{self.x(i0):.1f}" y1="{self.y(p0):.1f}" x2="{self.x(i1):.1f}" y2="{self.y(p1):.1f}" '
            f'stroke="{color}" stroke-width="{width}" stroke-dasharray="{dash}" stroke-opacity="0.8"/>'
        )

    def mark(self, i, where, label, color, off=14):
        """Label above high ('h') or below low ('l') of candle i."""
        if where == "h":
            yy = self.y(self.H(i)) - off
        else:
            yy = self.y(self.L(i)) + off + 12
        self.tag(self.x(i), yy, label, color, anchor="middle")

    def badge(self, i, p, n, color):
        cx, cy = self.x(i), self.y(p)
        self.over.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="11" fill="{color}"/>'
            f'<text x="{cx:.1f}" y="{cy + 4.5:.1f}" font-size="13" font-weight="700" text-anchor="middle" fill="{C["bg"]}">{n}</text>'
        )

    def arrow(self, i0, p0, i1, p1, color):
        x0, y0, x1, y1 = self.x(i0), self.y(p0), self.x(i1), self.y(p1)
        import math
        a = math.atan2(y1 - y0, x1 - x0)
        hx1, hy1 = x1 - 9 * math.cos(a - 0.4), y1 - 9 * math.sin(a - 0.4)
        hx2, hy2 = x1 - 9 * math.cos(a + 0.4), y1 - 9 * math.sin(a + 0.4)
        self.over.append(
            f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{color}" stroke-width="1.6"/>'
            f'<polygon points="{x1:.1f},{y1:.1f} {hx1:.1f},{hy1:.1f} {hx2:.1f},{hy2:.1f}" fill="{color}"/>'
        )

    def tag(self, x, y, s, color, anchor="start", box=True, fs=13):
        w = text_w(s, fs)
        if anchor == "start":
            bx = x - 4
        elif anchor == "end":
            bx = x - w - 4
        else:
            bx = x - w / 2 - 4
        if box:
            self.over.append(
                f'<rect x="{bx:.1f}" y="{y - fs:.1f}" width="{w + 8:.1f}" height="{fs + 6:.1f}" rx="3" '
                f'fill="{C["bg"]}" fill-opacity="0.85"/>'
            )
        self.over.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-size="{fs}" text-anchor="{anchor}" fill="{color}" font-weight="600">{esc(s)}</text>'
        )

    def render(self):
        out = [
            f'<rect x="{self.x0}" y="{self.y0}" width="{self.x1 - self.x0}" height="{self.y1 - self.y0}" '
            f'fill="{C["panel"]}" stroke="{C["axis"]}" rx="6"/>'
        ]
        for k in range(1, 5):
            yy = self.y0 + (self.y1 - self.y0) * k / 5
            out.append(
                f'<line x1="{self.x0}" y1="{yy:.1f}" x2="{self.x1}" y2="{yy:.1f}" stroke="{C["grid"]}" stroke-width="1"/>'
            )
        if self.label:
            out.append(
                f'<text x="{self.x0 + 12}" y="{self.y0 + 22}" font-size="14" font-weight="700" fill="{C["muted"]}">{esc(self.label)}</text>'
            )
        out.extend(self.under)
        bw = max(3, self.step * 0.62)
        for i, (o, h, l, c) in enumerate(self.cs):
            col = C["bull"] if c >= o else C["bear"]
            xx = self.x(i)
            out.append(
                f'<line x1="{xx:.1f}" y1="{self.y(h):.1f}" x2="{xx:.1f}" y2="{self.y(l):.1f}" stroke="{col}" stroke-width="1.3"/>'
            )
            top, bot = self.y(max(o, c)), self.y(min(o, c))
            out.append(
                f'<rect x="{xx - bw / 2:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{max(1.2, bot - top):.1f}" fill="{col}"/>'
            )
        out.extend(self.over)
        return out


def check(cond, msg):
    """Hard assertion used to keep every annotation consistent with the candle data."""
    if not cond:
        raise AssertionError("diagram check failed: " + msg)


def valid_candles(cs, name):
    for i, (o, h, l, c) in enumerate(cs):
        check(h >= max(o, c) - 1e-9 and l <= min(o, c) + 1e-9, f"{name}: candle {i} high/low does not contain body")


def is_swing_high(p, i, k=2):
    return all(p.H(i) >= p.H(j) for j in range(max(0, i - k), min(p.n, i + k + 1)))


def is_swing_low(p, i, k=2):
    return all(p.L(i) <= p.L(j) for j in range(max(0, i - k), min(p.n, i + k + 1)))


def legend(chart, items, x, y):
    for k, (col, s) in enumerate(items):
        yy = y + k * 22
        chart.els.append(f'<rect x="{x}" y="{yy - 11}" width="14" height="14" rx="2" fill="{col}"/>')
        chart.els.append(f'<text x="{x + 22}" y="{yy + 1}" font-size="13" fill="{C["text"]}">{esc(s)}</text>')


# ---------------------------------------------------------------- 00 overview
def d00():
    ch = Chart("SMC 七步阅读顺序", "每一步回答一个问题，少一步，判断就少一层依据", 900, 400)
    steps = [
        ("结构", ["涨、跌", "还是震荡？"], C["struct"]),
        ("位置", ["现在是贵区", "还是便宜区？"], C["eq"]),
        ("流动性", ["下一步", "去扫哪里？"], C["liq"]),
        ("位移", ["推动有没有", "真力量？"], C["warn"]),
        ("订单区", ["在哪里", "等反应？"], C["ob"]),
        ("触发", ["什么时候", "扣扳机？"], C["fvg"]),
        ("执行", ["入场、止损", "和目标"], C["tp"]),
    ]
    bw, bh, gap = 112, 150, 12
    x, y = 28, 104
    for k, (t, q, col) in enumerate(steps):
        ch.els.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="10" fill="{C["panel"]}" stroke="{col}" stroke-width="2"/>')
        ch.els.append(f'<circle cx="{x + bw / 2}" cy="{y + 34}" r="16" fill="{col}"/>')
        ch.els.append(f'<text x="{x + bw / 2}" y="{y + 40}" font-size="16" font-weight="700" text-anchor="middle" fill="{C["bg"]}">{k + 1}</text>')
        ch.els.append(f'<text x="{x + bw / 2}" y="{y + 82}" font-size="19" font-weight="700" text-anchor="middle" fill="{C["text"]}">{esc(t)}</text>')
        for j, ln in enumerate(q):
            ch.els.append(f'<text x="{x + bw / 2}" y="{y + 110 + j * 19}" font-size="13" text-anchor="middle" fill="{C["muted"]}">{esc(ln)}</text>')
        if k < len(steps) - 1:
            ax = x + bw + 1
            ch.els.append(f'<polygon points="{ax},{y + bh / 2 - 6} {ax + gap - 2},{y + bh / 2} {ax},{y + bh / 2 + 6}" fill="{C["muted"]}"/>')
        x += bw + gap
    ch.els.append(f'<text x="450" y="306" font-size="16" text-anchor="middle" fill="{C["text"]}">方向（结构） → 立场（位置） → 时机（触发）</text>')
    ch.els.append(f'<text x="450" y="336" font-size="14" text-anchor="middle" fill="{C["muted"]}">不猜底 · 不猜顶 · 不提前：等扫 · 等位移 · 等结构 · 等回踩 · 等触发</text>')
    ch.save("00-七步阅读顺序.svg")


def mk(start, items, seed=7, wick=(0.12, 0.45)):
    """items: close, or (close, high, low) with None = auto. open = previous close."""
    rnd = random.Random(seed)
    out, prev = [], start
    for it in items:
        c, h, l = (it, None, None) if not isinstance(it, tuple) else it
        o = prev
        hh = max(o, c) + rnd.uniform(*wick) if h is None else max(h, o, c)
        ll = min(o, c) - rnd.uniform(*wick) if l is None else min(l, o, c)
        out.append([o, hh, ll, c])
        prev = c
    return out


# ---------------------------------------------------------------- 01 structure
def d01():
    ch = Chart("市场结构：HH / HL 与 LH / LL", "上涨靠更高的高点 + 更高的低点维持；下跌反之", 900, 500)
    up = gen_path([(0, 100), (6, 108), (10, 104), (16, 113), (20, 109), (26, 118), (30, 114.5), (35, 122)], seed=3)
    dn = gen_path([(0, 122), (6, 114), (10, 118), (16, 109), (20, 113), (26, 104), (30, 108), (35, 100)], seed=5)
    a = ch.panel(up, 24, 86, 444, 470, label="上涨结构")
    b = ch.panel(dn, 456, 86, 876, 470, label="下跌结构")
    pts = [(0, "l", None)]
    seq = [(6, "h", "HH"), (10, "l", "HL"), (16, "h", "HH"), (20, "l", "HL"), (26, "h", "HH"), (30, "l", "HL")]
    for i in (6, 16, 26):
        check(is_swing_high(a, i), f"d01 up: {i} not swing high")
    for i in (10, 20, 30):
        check(is_swing_low(a, i), f"d01 up: {i} not swing low")
    check(a.H(6) < a.H(16) < a.H(26), "d01 up: highs not rising")
    check(a.L(0) < a.L(10) < a.L(20) < a.L(30), "d01 up: lows not rising")
    for i in (6, 16, 26):
        check(is_swing_low(b, i), f"d01 down: {i} not swing low")
    for i in (10, 20, 30):
        check(is_swing_high(b, i), f"d01 down: {i} not swing high")
    check(b.L(6) > b.L(16) > b.L(26), "d01 down: lows not falling")
    check(b.H(0) > b.H(10) > b.H(20) > b.H(30), "d01 down: highs not falling")
    prev = (0, a.L(0))
    for i, w, lab in seq:
        p = a.H(i) if w == "h" else a.L(i)
        a.seg(prev[0], prev[1], i, p, C["struct"])
        a.mark(i, w, lab, C["tp"])
        prev = (i, p)
    seqd = [(6, "l", "LL"), (10, "h", "LH"), (16, "l", "LL"), (20, "h", "LH"), (26, "l", "LL"), (30, "h", "LH")]
    prev = (0, b.H(0))
    for i, w, lab in seqd:
        p = b.H(i) if w == "h" else b.L(i)
        b.seg(prev[0], prev[1], i, p, C["struct"])
        b.mark(i, w, lab, C["bear"])
        prev = (i, p)
    ch.save("01-市场结构.svg")


# ---------------------------------------------------------------- 02 BOS CHoCH MSS
def d02():
    ch = Chart("BOS / CHoCH / MSS", "BOS = 原方向延续；CHoCH = 第一个转向信号；MSS = CHoCH 后反方向再出 BOS，反转确认", 900, 520)
    cs = gen_path([(0, 121), (6, 113), (9, 116.5), (15, 109), (18, 112.5), (24, 103.5), (29, 114.5), (33, 108.5), (40, 119)], seed=11)
    p = ch.panel(cs, 24, 86, 876, 490)
    # downtrend BOS: break of LL at idx 15 (first close below)
    i_ll, ll = p.argmin_l(13, 17)
    k = p.first_close_below(ll, i_ll + 2)
    p.hline(ll, i_ll, k, C["bear"], "BOS 下跌延续（收盘跌破前低）", lpos="start", above=False)
    check(k <= 24 and p.Cl(k) < ll, "d02: down BOS candle")
    i_lh, lh = p.argmax_h(17, 19)
    check(i_lh == 18 and is_swing_high(p, 18), "d02: LH label not on the swing high")
    check(p.H(18) < p.H(9), "d02: 18 is not a lower high")
    p.mark(18, "h", "LH 守门点", C["warn"])
    k2 = p.first_close_above(lh, 19)
    check(k2 >= 25, "d02: CHoCH happened earlier than drawn")
    check(p.argmin_l(22, 26)[0] == 24 and is_swing_low(p, 24), "d02: LL label not on the low")
    p.hline(lh, i_lh, k2, C["warn"], "CHoCH 第一次转向", lpos="end")
    i_h, hh = p.argmax_h(27, 31)
    i_hl, hl = p.argmin_l(31, 35)
    p.mark(i_hl, "l", "HL", C["tp"])
    k3 = p.first_close_above(hh, i_hl)
    check(i_hl > k2 and hl > p.L(24), "d02: HL must form after CHoCH and above the LL")
    check(all(p.Cl(j) <= hh for j in range(i_h + 1, k3)), "d02: new-direction BOS drawn late")
    p.hline(hh, i_h, k3 + 2, C["tp"], "BOS 新方向 → MSS 确认反转", lpos="end")
    p.mark(24, "l", "LL", C["bear"])
    ch.save("02-BOS-CHoCH-MSS.svg")


# ---------------------------------------------------------------- 03 liquidity sweep
def d03():
    ch = Chart("流动性清扫：等低下方的止损池", "越明显的等高等低，越容易被扫；刺穿后迅速收回 = 清扫，不是突破", 900, 500)
    cs = mk(113, [112.2, 110.6, 109.0, 107.4, 106.0, (104.9, None, 104.0), 105.8, 107.2, 108.6, 109.4,
                  108.6, 107.3, 106.1, (105.0, None, 104.0), 106.0, 107.4, 108.3, 107.6, 106.7, 105.6,
                  (105.3, None, 101.6), 107.6, 109.8, 109.2, 111.0, 112.6, 113.4, 114.8], seed=21)
    p = ch.panel(cs, 24, 86, 876, 470)
    lvl = 104.0
    check(abs(p.L(5) - lvl) < 1e-9 and abs(p.L(13) - lvl) < 1e-9, "d03: equal lows")
    check(all(p.L(j) > lvl for j in range(0, 20) if j not in (5, 13)), "d03: another candle broke the equal lows")
    check(p.L(20) < lvl and p.Cl(20) > lvl, "d03: sweep candle must pierce and close back above")
    p.hline(lvl, 5, 20, C["liq"], "等低 Equal Lows", lpos="start", above=True)
    p.zone(5, 20, lvl - 0.15, lvl - 2.2, C["liq"], "SSL 卖方流动性：多头止损聚集在这里", opacity=0.10, lpos="bl")
    p.mark(5, "l", "低点 1", C["muted"], off=-2)
    p.mark(13, "l", "低点 2", C["muted"], off=-2)
    p.tag(p.x(20) + 14, p.y(101.9), "扫损：刺穿后收回", C["warn"], anchor="start")
    p.tag(p.x(27), p.y(116.2), "扫完 + 位移，才是真机会", C["tp"], anchor="end")
    ch.save("03-流动性清扫.svg")


# ---------------------------------------------------------------- 04 inducement
def d04():
    ch = Chart("诱导（Inducement）：先扫内部回撤，BOS 才算数", "靠近回撤起点的区域往往是“饵”，真正可用的 OB 在诱导被扫之后形成", 900, 560)
    cs = mk(103.4, [103.9, 104.6, 105.4, 106.4, 107.4, 108.4, (109.4, 110.0, None),   # 0-6 impulse, top idx6
                  108.6, (107.7, None, 107.2),                                       # 7-8 pullback, IDM low idx8
                  108.4, 109.0, 108.3,                                               # 9-11 small bounce
                  (107.0, None, 106.6), (106.0, None, 105.6),                        # 12 sweeps IDM, 13 = OB
                  108.4, 110.8, 112.0, 111.3, 110.7, 112.4, 113.9], seed=8)
    p = ch.panel(cs, 24, 86, 876, 530)
    top = p.H(6)
    idm = p.L(8)
    check(is_swing_high(p, 6) and is_swing_low(p, 8), "d04: top / IDM swing points")
    check(all(p.H(j) < top for j in range(7, 14)), "d04: no break of the top before the sweep")
    check(all(p.L(j) > idm for j in range(9, 12)), "d04: IDM swept too early")
    check(p.L(12) < idm, "d04: candle 12 must sweep IDM")
    check(p.Cl(13) < p.O(13) and p.Cl(14) > p.O(14), "d04: OB must be the last bearish candle before displacement")
    check(p.O(13) - p.Cl(13) >= 0.5 * (p.H(13) - p.L(13)), "d04: OB candle must be full-bodied")
    kb = p.first_close_above(top, 9)
    check(kb == 15, f"d04: BOS candle expected 15, got {kb}")
    p.zone(7, 8, p.H(7), idm, C["bear"], None, opacity=0.14)
    p.tag(p.x(7) - p.step * 0.5, p.y(top) - 10, "诱导区 ↓ 会被吃掉，不做", C["bear"])
    p.hline(idm, 8, 12, C["liq"], "IDM 诱导点", lpos="start", above=False)
    p.tag(p.x(12) + 8, p.y(p.L(12)) + 22, "扫掉 IDM", C["warn"], anchor="end")
    p.ob(13, p.n - 1, "有效 OB（取实体）：诱导完成后形成", C["ob"], opacity=0.2)
    k = p.first_close_above(top, 13)
    p.hline(top, 6, p.n - 1, C["tp"], "有效 BOS：先扫 IDM，再实体收盘突破", lpos="end")
    ch.save("04-诱导Inducement.svg")


# ---------------------------------------------------------------- 05 FVG
def d05():
    ch = Chart("FVG 公允价值缺口：三根 K 线规则", "多头 FVG = A 的最高点 与 C 的最低点之间、没有被 A 和 C 覆盖的空档；B 是位移 K 线", 900, 540)
    # left: anatomy, only A B C
    abc = [[100.4, 101.6, 99.8, 101.2],    # A
           [101.3, 106.6, 101.0, 106.2],   # B displacement
           [106.2, 107.4, 104.2, 107.0]]   # C
    L = ch.panel(abc, 24, 86, 330, 510, pad=1.2, label="① 只看三根")
    a_hi, c_lo = L.H(0), L.L(2)
    check(c_lo > a_hi, "d05 left: no FVG")
    L.zone(1, 1, c_lo, a_hi, C["fvg"], None, opacity=0.3)
    L.hline(a_hi, 0, 2, C["fvg"], "A 最高点 = 下沿", lpos="start", above=False, dash="4 3")
    L.hline(c_lo, 0, 2, C["fvg"], "C 最低点 = 上沿", lpos="start", above=True, dash="4 3")
    L.tag(L.x(0) - 4, L.y((a_hi + c_lo) / 2) + 5, "FVG", C["fvg"], anchor="middle", fs=15)
    L.mark(0, "l", "A", C["text"])
    L.mark(1, "l", "B 位移", C["warn"])
    L.mark(2, "h", "C", C["text"])
    # right: in context
    cs = mk(101.2, [100.6, 101.3, (100.9, None, 100.0), 101.4,          # 0-3 base, A = idx3
                    (106.4, None, 101.3), (107.4, None, 104.6),          # 4 B, 5 C
                    108.3, (109.2, 109.8, None), 108.6, 107.4, 106.4,    # 6-10 retrace
                    (105.0, None, 103.0),                                 # 11 dips to ~CE
                    (106.9, None, 104.6), 108.3, 109.6, 110.9, 112.2], seed=55)
    R = ch.panel(cs, 342, 86, 876, 510, label="② 放回走势里")
    a_hi, c_lo = R.H(3), R.L(5)
    assert c_lo > a_hi, (a_hi, c_lo)
    ce = (a_hi + c_lo) / 2
    R.zone(4, 12, c_lo, a_hi, C["fvg"], None, opacity=0.2)
    R.hline(ce, 4, 12, C["fvg"], "50% 中线", lpos="right", dash="2 3", width=1)
    R.mark(3, "l", "A", C["text"])
    R.mark(4, "l", "B", C["warn"])
    R.mark(5, "h", "C", C["text"])
    R.tag(R.x(11) - 14, R.y(R.L(11)) + 22, "回踩到 FVG 中线附近", C["fvg"], anchor="end")
    R.tag(R.x(12) + 12, R.y(R.H(12)) - 8, "出现反应，才考虑", C["tp"])
    ch.save("05-FVG三根K线.svg")


# ---------------------------------------------------------------- 06 OB
def d06():
    ch = Chart("订单区 OB：位移前最后一根反向 K 线的实体", "OB 三个硬条件：扫过流动性 + 留下失衡(FVG) + 打出结构；区域取实体，影线只作缓冲", 900, 500)
    cs = mk(113, [112.0, 110.6, 109.2, 107.8, (106.4, None, 105.4), 106.8, 108.2, (109.0, 109.8, None),   # 0-7
                  108.1, 107.0, 106.2, (105.5, None, 105.45), (104.0, 105.6, 103.8),                        # 8-12 OB idx12：实体饱满的阴线，影线扫前低 105.4
                  (107.4, None, 104.5), (110.6, None, 107.9), 111.4,                                       # 13-15 displacement
                  110.4, 109.0, 107.6, (106.4, None, 105.0), 107.8, 109.6, 111.2, 112.6, 114.0], seed=14)
    p = ch.panel(cs, 24, 86, 876, 470)
    check(is_swing_low(p, 4), "d06: prior low")
    check(all(p.L(j) > p.L(4) for j in range(5, 12)), "d06: prior low broken before OB")
    check(p.L(12) < p.L(4), "d06: OB candle must sweep the prior low")
    check(p.Cl(12) < p.O(12) and p.Cl(13) > p.O(13), "d06: OB = last bearish candle before displacement")
    body12 = p.O(12) - p.Cl(12)
    check(body12 >= 0.5 * (p.H(12) - p.L(12)), "d06: OB candle must be full-bodied (body >= 50% of range), not a doji")
    check(p.O(13) <= p.Cl(12) and p.Cl(13) >= p.O(12), "d06: next candle engulfs the OB body (forceful displacement)")
    ob_top, ob_bot = max(p.O(12), p.Cl(12)), min(p.O(12), p.Cl(12))
    first_ret = next(j for j in range(15, p.n) if p.L(j) <= ob_top)  # after the displacement candles
    check(first_ret == 19, f"d06: first return to OB expected at 19, got {first_ret}")
    check(p.L(19) >= ob_bot - 0.6, "d06: first return should not blow through the OB")
    p.hline(p.L(4), 4, 12, C["liq"], "前低", lpos="start", above=False)
    p.ob(12, p.n - 1, "看涨 OB：取最后一根阴线的实体", C["ob"])
    p.tag(p.x(p.n - 1), p.y(p.L(12)) + 18, "虚线 = 影线极端，作缓冲参考", C["muted"], anchor="end", fs=12)
    a_hi, c_lo = p.H(12), p.L(14)  # A = 12（OB 那根）, B = 13, C = 14
    assert c_lo > a_hi, (a_hi, c_lo)
    p.zone(13, 17, c_lo, a_hi, C["fvg"], None, opacity=0.18, where="under")
    p.tag(p.x(15.5), p.y((a_hi + c_lo) / 2) + 6, "FVG", C["fvg"], anchor="middle", box=False)
    k = p.first_close_above(p.H(7), 13)
    check(is_swing_high(p, 7) and all(p.H(j) < p.H(7) for j in range(8, 13)), "d06: structure high")
    check(k in (13, 14, 15), "d06: displacement must break structure")
    p.hline(p.H(7), 7, k + 1, C["tp"], "位移打破结构", lpos="start")
    p.mark(19, "h", "首次回到 OB：先看反应再进", C["text"], off=18)
    ch.save("06-订单区OB.svg")


# ---------------------------------------------------------------- 07 premium discount
def d07():
    ch = Chart("Premium / Discount：先看位置，再看信号", "取一段决定结构的波段画 50% 线：上半贵区偏找空，下半便宜区偏找多", 900, 500)
    cs = gen_path([(0, 104), (3, 100), (10, 112), (13, 109), (20, 120), (26, 106.5), (32, 117)], seed=31, noise=0.25)
    p = ch.panel(cs, 24, 86, 876, 470)
    i_lo, lo = p.argmin_l(1, 5)
    i_hi, hi = p.argmax_h(18, 22)
    eq = (lo + hi) / 2
    end = p.n - 1
    p.zone(i_lo, end, hi, eq, C["prem"], None, opacity=0.09)
    p.zone(i_lo, end, eq, lo, C["disc"], None, opacity=0.09)
    p.tag(p.x(i_lo) + 6, p.y(hi) + 24, "Premium 贵区：偏找空，不追多", C["prem"])
    p.tag(p.x(end), p.y(lo) - 12, "Discount 便宜区：偏找多，不追空", C["disc"], anchor="end")
    p.hline(eq, i_lo, end, C["eq"], "Equilibrium 50%", lpos="end")
    p.hline(hi, i_hi, end, C["muted"], "波段高点 100%", lpos="end", dash="2 3")
    p.hline(lo, i_lo, end, C["muted"], "波段低点 0%", lpos="end", dash="2 3", above=False)
    i_r, _ = p.argmin_l(24, 28)
    check(p.L(i_r) < eq, "d07: the 'back to discount' low must be below 50%")
    check(lo < eq < hi, "d07: range")
    p.mark(i_r, "l", "回到便宜区再找多", C["tp"])
    ch.save("07-Premium-Discount.svg")


# ---------------------------------------------------------------- 08 full entry
def d08():
    ch = Chart("完整入场节奏：扫 → 位移 → CHoCH → 回踩 → 触发", "示意多头场景：止损放在结构失效点，目标看对侧流动性", 900, 560)
    cs = mk(121, [122.2, (123.5, 124.0, None), 122.0, 120.0, 118.5, 119.6, 117.0, 115.2, (116.4, 116.8, None),  # 0-8
                  114.0, 112.0, 110.4, (108.9, None, 108.2), 109.8, (110.8, 111.2, None), 110.0, 109.2,        # 9-16
                  (108.8, 109.3, 106.6),                                                                        # 17 sweep
                  (111.8, None, 108.6), (113.4, None, 111.4),                                                   # 18-19 displacement / CHoCH
                  112.6, 111.6, (110.7, None, 110.2), (111.9, None, 110.5),                                     # 20-23 retrace + trigger
                  113.0, 114.5, 115.2, 114.4, 116.0, 117.8, 119.0, 118.4, 120.5, 122.0, 123.4, (124.6, 125.0, None)],
            seed=41)
    p = ch.panel(cs, 24, 86, 876, 530)
    ssl = p.L(12)
    check(is_swing_low(p, 12), "d08: SSL swing low")
    check(all(p.L(j) > ssl for j in range(13, 17)), "d08: SSL broken before sweep")
    check(p.L(17) < ssl and p.Cl(17) > ssl, "d08: sweep candle must pierce SSL and close back above")
    p.hline(ssl, 12, 18, C["liq"], "前低 SSL", lpos="start", above=False)
    p.badge(17, p.L(17) - 1.2, "1", C["liq"])
    p.tag(p.x(17) + 16, p.y(p.L(17) - 1.2) + 5, "扫流动性", C["liq"])
    p.badge(18, p.L(18) - 1.0, "2", C["warn"])
    p.tag(p.x(18) + 16, p.y(p.L(18) - 1.0) + 5, "位移", C["warn"])
    lh = p.H(14)
    check(is_swing_high(p, 14), "d08: LH must be a swing high")
    k = p.first_close_above(lh, 15)
    check(k == 18, f"d08: CHoCH candle expected 18, got {k}")
    p.hline(lh, 14, k + 1, C["text"], "3 CHoCH", lpos="start")
    a_hi, c_lo = p.H(17), p.L(19)
    assert c_lo > a_hi
    p.zone(18, 24, c_lo, a_hi, C["fvg"], None, opacity=0.18)
    p.badge(22, p.L(22) - 1.0, "4", C["fvg"])
    p.tag(p.x(22) + 16, p.y(p.L(22) - 1.0) + 5, "回踩 FVG", C["fvg"])
    first_touch = next(j for j in range(20, p.n) if p.L(j) <= c_lo)
    check(first_touch in (21, 22), f"d08: first FVG retrace at {first_touch}")
    check(p.Cl(23) > p.O(23), "d08: trigger candle must be bullish")
    check(all(p.L(j) > a_hi for j in range(20, 24)), "d08: retrace must not fill the whole FVG")
    entry = p.Cl(23)
    sl = p.L(17) - 0.4
    tp = p.H(1)
    p.hline(entry, 23, p.n - 1, C["entry"], "5 触发入场", lpos="end", dash="1 0")
    p.hline(sl, 17, p.n - 1, C["sl"], "止损：扫损低点下方", lpos="end", above=False)
    p.hline(tp, 1, p.n - 1, C["tp"], "目标：对侧流动性 BSL（前高）", lpos="end", above=False)
    rr = (tp - entry) / (entry - sl)
    p.tag(p.x(p.n - 1), p.y(entry) - 30, f"盈亏比 ≈ 1:{rr:.1f}", C["text"], anchor="end")
    ch.save("08-完整入场节奏.svg")


# ---------------------------------------------------------------- 09 sweep vs breakout
def d09():
    ch = Chart("清扫 vs 真突破", "看收盘、看后续：清扫会迅速收回，突破会站稳并延续", 900, 500)
    left = gen_path([(0, 104), (5, 110.4), (9, 106.5), (14, 110.3), (16, 108.6), (17, 109.5), (24, 101)], seed=51, noise=0.2)
    left[17] = [109.4, 112.3, 109.1, 109.6]
    left[18][0] = 109.6
    right = gen_path([(0, 104), (5, 110.4), (9, 106.5), (14, 110.3), (16, 108.8), (18, 112.4), (20, 110.9), (25, 117)], seed=52, noise=0.2)
    # retest that holds above the broken high (candles 19-22 set explicitly)
    right[19] = [112.4, 112.6, 111.7, 111.9]
    right[20] = [111.9, 112.2, 111.45, 111.8]
    right[21] = [111.8, 112.9, 111.6, 112.7]
    right[22] = [112.7, 113.56, 112.3, 112.96]
    a = ch.panel(left, 24, 86, 444, 470, label="清扫 Sweep")
    b = ch.panel(right, 456, 86, 876, 470, label="真突破 Breakout")
    lv = max(a.H(5), a.H(14))
    check(all(a.Cl(j) < lv for j in range(0, a.n)), "d09 left: no close above the high in a sweep")
    check(a.H(17) > lv and a.Cl(17) < lv, "d09 left: sweep candle")
    check(all(a.H(j) <= lv for j in range(0, 17)), "d09 left: high pierced before the sweep candle")
    a.hline(lv, 4, 20, C["liq"], "前高", lpos="start")
    a.mark(17, "h", "上影刺穿，收盘回到下方", C["warn"])
    lv2 = max(b.H(5), b.H(14))
    b.hline(lv2, 4, 22, C["liq"], "前高", lpos="start", above=False)
    k = b.first_close_above(lv2, 15)
    check(all(b.H(j) <= lv2 for j in range(0, 15)), "d09 right: level pierced early")
    b.mark(k, "h", "实体收盘站上", C["tp"])
    i_rt, _ = b.argmin_l(19, 21)
    check(b.L(i_rt) > lv2 - 0.35 and all(b.Cl(j) > lv2 for j in range(k, b.n)), "d09 right: retest must hold the level (no close back below)")
    check(i_rt > k, "d09 right: retest after breakout")
    b.mark(i_rt, "l", "回踩不破", C["tp"])
    ch.save("09-清扫vs真突破.svg")


# ---------------------------------------------------------------- 10 rejection wick
def d10():
    ch = Chart("拒绝针：第 2 根 K 线决定强弱", "针本身只是候选；后面那根的态度才说明市场是否真的否决了方向", 900, 480)
    strong = [
        [110, 110.4, 107.8, 108.2], [108.2, 108.5, 106.2, 106.6], [106.6, 106.9, 104.9, 105.3],
        [105.3, 105.7, 100.6, 105.0],  # pin
        [105.0, 109.6, 104.8, 109.3],  # engulf
        [109.3, 111.2, 108.9, 110.9], [110.9, 112.4, 110.4, 112.0],
    ]
    weak = [
        [110, 110.4, 107.8, 108.2], [108.2, 108.5, 106.2, 106.6], [106.6, 106.9, 104.9, 105.3],
        [105.3, 105.9, 100.6, 104.4],  # pin with bigger body
        [104.4, 105.2, 103.6, 104.7],  # hesitant
        [104.7, 105.0, 102.9, 103.3], [103.3, 103.6, 100.2, 100.6],
    ]
    pin, eng = strong[3], strong[4]
    check(pin[2] < min(r[2] for r in strong[:3]), "d10: pin must make the low")
    check((min(pin[0], pin[3]) - pin[2]) > 3 * abs(pin[0] - pin[3]), "d10: strong pin = long wick, small body")
    check(eng[3] > eng[0] and eng[0] <= min(pin[0], pin[3]) and eng[3] >= max(pin[0], pin[3]), "d10: 2nd candle body engulfs the pin body")
    wpin, w2 = weak[3], weak[4]
    check(abs(w2[3] - w2[0]) < abs(wpin[0] - wpin[3]), "d10: weak 2nd candle is smaller than the pin body")
    a = ch.panel(strong, 24, 86, 444, 450, label="强：立刻吞没")
    b = ch.panel(weak, 456, 86, 876, 450, label="弱：犹豫不前")
    a.mark(3, "l", "长下影 + 短实体", C["text"])
    a.tag(a.x(4) - 18, a.y(107), "第 2 根大实体吞没", C["tp"], anchor="end")
    b.mark(3, "l", "影长但实体也不短", C["text"])
    b.mark(4, "h", "第 2 根小实体犹豫", C["warn"], off=40)
    b.mark(6, "l", "→ 放弃", C["bear"])
    ch.save("10-拒绝针强弱.svg")


for fn in (d00, d01, d02, d03, d04, d05, d06, d07, d08, d09, d10):
    fn()
if OUT == "diagrams/svg":  # keep the Skill's copy in sync
    import shutil
    os.makedirs("skills/smc-learning/assets/diagrams", exist_ok=True)
    for f in os.listdir(OUT):
        if f[:2].isdigit() and not f.startswith("11-"):
            shutil.copy(os.path.join(OUT, f), os.path.join("skills/smc-learning/assets/diagrams", f))
print("done", sorted(os.listdir(OUT)))
