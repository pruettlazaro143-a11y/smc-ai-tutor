"""生成进阶概念与入场模型的示意图（折线示意，非真实行情）。
在仓库根目录运行：python3 tools/gen_models.py
输出：diagrams/models/svg/*.svg，并同步到 skills/smc-learning/assets/models/
"""
import os, shutil

OUT = 'diagrams/models/svg'
SKILL = 'skills/smc-learning/assets/models'
W, H = 640, 380
PX, PY, PW, PH = 28, 74, 584, 270  # 绘图区
C = dict(bg='#0f1218', panel='#141922', border='#2b3442', text='#e6eaf0', muted='#8a94a6',
         path='#cfd8dc', supply='#ef5350', demand='#26a69a', liq='#f5c542', fib='#4f8cff', ob='#b47cff')
FONT = "'PingFang SC','Microsoft YaHei','Noto Sans CJK SC','Noto Sans SC',sans-serif"


def X(x): return PX + 14 + x / 100 * (PW - 28)
def Y(y): return PY + 10 + y / 100 * (PH - 20)
def esc(s): return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


REG = {}


def check(cond, msg):
    if not cond:
        raise AssertionError('model check failed: ' + msg)


def above(a, b):
    """a is at a higher PRICE than b (smaller y, because y grows downward)."""
    return a[1] < b[1]


def svg(name, title, sub, path, levels=(), zones=(), labels=(), boxes=(), arrow=True, kind='supply', verify=None):
    REG[name] = dict(path=path, levels=levels, zones=zones)
    if verify:
        verify(path)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT}">',
         f'<rect width="{W}" height="{H}" fill="{C["bg"]}"/>',
         f'<text x="28" y="36" font-size="20" font-weight="600" fill="{C["text"]}">{esc(title)}</text>',
         f'<text x="28" y="58" font-size="13" fill="{C["muted"]}">{esc(sub)}</text>',
         f'<rect x="{PX}" y="{PY}" width="{PW}" height="{PH}" rx="6" fill="{C["panel"]}" stroke="{C["border"]}"/>']
    for x1, x2, y1, y2, col, lab in zones:
        col = C.get(col, col)
        o.append(f'<rect x="{X(x1):.1f}" y="{Y(y1):.1f}" width="{X(x2) - X(x1):.1f}" height="{Y(y2) - Y(y1):.1f}" fill="{col}" fill-opacity="0.16" stroke="{col}" stroke-opacity="0.8" stroke-dasharray="4 3"/>')
        if lab:
            o.append(f'<text x="{X(x2) - 4:.1f}" y="{Y(y1) - 5:.1f}" font-size="12" text-anchor="end" fill="{col}">{esc(lab)}</text>')
    for x1, x2, y1, y2, col in boxes:
        col = C.get(col, col)
        o.append(f'<rect x="{X(x1):.1f}" y="{Y(y1):.1f}" width="{X(x2) - X(x1):.1f}" height="{Y(y2) - Y(y1):.1f}" fill="none" stroke="{col}" stroke-opacity="0.7"/>')
    for y, x1, x2, lab, col in levels:
        col = C.get(col, col)
        o.append(f'<line x1="{X(x1):.1f}" y1="{Y(y):.1f}" x2="{X(x2):.1f}" y2="{Y(y):.1f}" stroke="{col}" stroke-width="1.3" stroke-dasharray="6 4"/>')
        if lab:
            o.append(f'<text x="{X(x2) + 4:.1f}" y="{Y(y) + 4:.1f}" font-size="12" fill="{col}">{esc(lab)}</text>')
    pts = ' '.join(f'{X(x):.1f},{Y(y):.1f}' for x, y in path)
    o.append(f'<polyline points="{pts}" fill="none" stroke="{C["path"]}" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>')
    if arrow:
        (x0, y0), (x1, y1) = path[-2], path[-1]
        import math
        a = math.atan2(Y(y1) - Y(y0), X(x1) - X(x0))
        tx, ty = X(x1), Y(y1)
        p1 = (tx - 11 * math.cos(a - 0.45), ty - 11 * math.sin(a - 0.45))
        p2 = (tx - 11 * math.cos(a + 0.45), ty - 11 * math.sin(a + 0.45))
        o.append(f'<polygon points="{tx:.1f},{ty:.1f} {p1[0]:.1f},{p1[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}" fill="{C["path"]}"/>')
    for x, y, t, col, anchor in labels:
        col = C.get(col, col)
        o.append(f'<rect x="{X(x) - (len(t) * 7 + 6) * (0.5 if anchor == "middle" else 0):.1f}" y="{Y(y) - 13:.1f}" width="{len(t) * 7 + 6 if t.isascii() else len(t) * 12.5 + 6:.1f}" height="17" rx="3" fill="{C["bg"]}" fill-opacity="0"/>')
        o.append(f'<text x="{X(x):.1f}" y="{Y(y):.1f}" font-size="12.5" text-anchor="{anchor}" fill="{col}" font-weight="600">{esc(t)}</text>')
    o.append(f'<text x="{W - 12}" y="{H - 12}" font-size="11" text-anchor="end" fill="{C["muted"]}">示意图，非真实行情</text>')
    o.append('</svg>')
    open(os.path.join(OUT, name + '.svg'), 'w', encoding='utf-8').write('\n'.join(o))


def L(x, y, t, col='text', anchor='middle'):
    return (x, y, t, col, anchor)


def waves(x0, y0, x1, y1, n, amp):
    """从 (x0,y0) 到 (x1,y1) 的 n 个小锯齿"""
    pts = []
    for i in range(n + 1):
        t = i / n
        x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        pts.append((x, y + (amp if i % 2 else 0)))
    return pts


os.makedirs(OUT, exist_ok=True)

# ---------------- A. ICT 补充概念 ----------------
svg('A1-Breaker破坏块', 'A1 破坏块 Breaker（看涨）', 'L → H → 跌破 L（扫流动性）→ 突破 H：H 处失效的看跌 OB 变成支撑',
    [(0, 20), (12, 58), (26, 36), (40, 80), (56, 20), (68, 40), (92, 6)],
    levels=[(36, 26, 56, '', 'path'), (58, 12, 44, '', 'liq')],
    zones=[(24, 92, 36, 44, 'demand', '')],
    labels=[L(92, 54, '看涨 Breaker（原看跌 OB）', 'demand', 'end'), L(26, 30, 'H'), L(12, 66, '前低 L', 'liq'), L(40, 90, '扫 L', 'liq'), L(56, 14, '突破 H', 'demand')])
svg('A2-Mitigation缓解块', 'A2 缓解块 Mitigation（看涨）', 'L → H → 没能跌破 L → 突破 H：和 Breaker 的区别是没有扫流动性',
    [(0, 20), (12, 62), (26, 36), (40, 54), (56, 20), (68, 40), (92, 6)],
    levels=[(36, 26, 56, '', 'path'), (62, 12, 44, '', 'liq')],
    zones=[(24, 92, 36, 44, 'demand', '')],
    labels=[L(92, 54, '看涨 Mitigation', 'demand', 'end'), L(26, 30, 'H'), L(12, 70, '前低 L', 'liq'), L(42, 60, '没跌破 L', 'muted', 'start'), L(56, 14, '突破 H', 'demand')])
FIB = lambda r: 12 + r * (88 - 12)  # retracement measured down from the impulse high (y=12) toward its low (y=88)
svg('A4-OTE最佳入场区', 'A4 最佳入场区 OTE', '一段推动之后，回撤到 0.62–0.79 区间（0.705 为中心参考）',
    [(4, 88), (14, 70), (20, 76), (34, 40), (40, 48), (52, 12), (58, 34), (62, 28), (68, 62), (90, 4)],
    levels=[(12, 4, 90, '0 终点（高）', 'muted'), (FIB(0.5), 4, 90, '0.5', 'muted'), (FIB(0.62), 50, 90, '0.62', 'fib'),
            (FIB(0.705), 50, 90, '0.705', 'fib'), (FIB(0.79), 50, 90, '0.79', 'fib'), (88, 4, 90, '1 起点（低）', 'muted')],
    zones=[(50, 90, FIB(0.62), FIB(0.79), 'fib', '')],
    verify=lambda P: check(FIB(0.62) <= P[8][1] <= FIB(0.79) and P[5] == (52, 12) and P[0] == (4, 88), 'A4: retrace must land in 0.62-0.79 of the 88->12 impulse'),
    labels=[L(20, 30, '推动起点 → 终点', 'muted', 'start'), L(76, 80, '回撤进 OTE', 'fib')])
svg('A8-PO3三段式', 'A8 PO3 / AMD（看涨日）', '开盘附近横盘 → 向下扫流动性 → 朝真正方向走出主波动',
    [(0, 46), (6, 38), (10, 52), (14, 38), (18, 52), (22, 38), (26, 52), (34, 80), (40, 70), (46, 74), (60, 30), (66, 42), (88, 8)],
    levels=[(46, 0, 92, '开盘价', 'path'), (70, 0, 34, '', 'liq')],
    zones=[],
    labels=[L(2, 76, '前低', 'liq', 'start'), L(13, 34, 'A 吸筹', 'muted'), L(34, 90, 'M 操纵（扫前低）', 'liq'), L(74, 20, 'D 派发', 'demand')])

# ---------------- B. QM / 供需入场模型（均为看跌版） ----------------
qm = [(0, 88), (14, 45), (22, 62), (34, 24), (48, 76), (62, 44), (84, 94)]
svg('B01-QM基础形态', 'B1 QM 卡西莫多（看跌）', 'H → L → HH（扫高）→ LL（破 L）→ 回到 QML 做空区',
    qm, levels=[(45, 14, 92, 'QML', 'liq'), (62, 22, 54, '', 'muted')],
    zones=[(34, 92, 26, 45, 'supply', '供应区')],
    labels=[L(14, 39, 'H'), L(22, 70, 'L'), L(34, 18, 'HH'), L(48, 84, 'LL')])
svg('B02-QM延迟回测', 'B2 QM 延迟回测（看跌）', '跌出 LL 后先在低位横盘，过一阵才回到 QML；快速回测则直接回到 QML',
    [(0, 88), (12, 45), (18, 62), (28, 24), (40, 76)] + waves(44, 62, 60, 62, 6, 8) + [(74, 44), (92, 94)],
    levels=[(45, 12, 92, 'QML', 'liq'), (62, 42, 66, '小区间高点', 'muted')],
    zones=[(28, 92, 26, 45, 'supply', '供应区')],
    labels=[L(12, 39, 'H'), L(18, 70, 'L'), L(28, 18, 'HH'), L(40, 84, 'LL')])
svg('B03-影线QM', 'B3 影线 QM（DM Shadow）', 'QM 的头部只是一根 K 线的影线：刺破前高后马上被吞没',
    [(0, 88), (14, 45), (22, 62), (30, 50), (33, 18), (36, 52), (48, 76), (62, 42), (84, 94)],
    levels=[(45, 14, 92, 'QML', 'liq')],
    zones=[(33, 92, 18, 45, 'supply', '影线范围')],
    labels=[L(14, 39, 'H'), L(22, 70, 'L'), L(33, 12, '影线头部'), L(48, 84, 'LL')])
svg('B04-延续型QM', 'B4 延续型 QM（看跌）', '在已有下跌趋势的回调里形成小 QM，然后顺势继续下跌',
    [(0, 6), (14, 48), (22, 30), (28, 44), (34, 22), (44, 60), (54, 28), (66, 70), (72, 60), (90, 96)],
    levels=[(30, 22, 92, 'QML', 'liq')],
    zones=[(34, 92, 22, 30, 'supply', '')],
    labels=[L(6, 20, '下跌趋势', 'muted', 'start'), L(22, 24, 'H'), L(28, 52, 'L'), L(34, 16, 'HH'), L(44, 68, 'LL')])
svg('B05-双顶假突破', 'B5 2R 假突破（看跌）', '两次触碰同一阻力形成等高 → 刺破等高（扫流动性）→ 跌回下方',
    [(0, 88), (10, 40), (17, 60), (24, 40), (31, 60), (40, 26), (50, 72), (56, 62), (62, 70), (70, 38), (90, 94)],
    levels=[(40, 10, 92, '等高 R', 'liq')],
    zones=[(40, 92, 26, 40, 'supply', '')],
    labels=[L(10, 34, 'R'), L(24, 34, 'R'), L(40, 20, '假突破', 'liq')])
svg('B06-QM再入场', 'B6 QM 再入场（主 QML / 小 QML）', '没回到主 QML 时，在下跌途中的小 QML 再找一次机会',
    [(0, 88), (10, 40), (16, 56), (24, 20), (34, 66), (40, 52), (44, 62), (50, 46), (58, 74), (68, 52), (90, 96)],
    levels=[(40, 10, 92, '主 QML', 'liq'), (52, 40, 92, '小 QML', 'ob')],
    zones=[(50, 92, 46, 52, 'supply', '')],
    labels=[L(10, 34, 'H'), L(24, 14, 'HH'), L(34, 74, 'LL')])
svg('B07-被忽略的QM', 'B7 被忽略的 QM（IQML）', 'QM 形成后没回测就继续跌；之后反弹，先假突破中间阻力，再回到 IQML',
    [(0, 88), (10, 40), (16, 56), (24, 20), (34, 66), (40, 62), (46, 82), (54, 58), (58, 66), (62, 54), (66, 64), (78, 40), (94, 96)],
    levels=[(40, 10, 92, 'IQML', 'liq'), (58, 52, 70, '中间阻力', 'muted')],
    zones=[(24, 92, 22, 40, 'supply', '')],
    labels=[L(10, 34, 'H'), L(24, 14, 'HH'), L(34, 74, 'LL'), L(62, 48, '假突破', 'liq')])
svg('B08-统治者', 'B8 统治者 Ruler', '价格多次围绕同一水平线往返（1–4），第 5 次回到该区域时找入场',
    [(0, 90), (10, 48), (16, 64), (20, 54), (24, 64), (28, 54), (32, 64), (38, 48), (46, 74), (50, 66), (54, 74), (64, 44), (86, 94)],
    levels=[(48, 6, 92, '关键水平', 'liq')],
    zones=[(38, 92, 38, 48, 'supply', '')],
    labels=[L(10, 42, '1'), L(16, 70, '2'), L(24, 72, '3'), L(32, 72, '3'), L(38, 42, '4'), L(64, 40, '5')])
svg('B09-V型双顶', 'B9 V 型双顶（V Twin）', '关键水平附近出现两个快速的 V 形转折，价格回来时容易再次反应',
    [(0, 88), (10, 42), (15, 60), (20, 42), (26, 60), (32, 42), (44, 72), (50, 62), (56, 72), (66, 42), (88, 94)],
    levels=[(42, 6, 92, '', 'liq')],
    zones=[(10, 92, 34, 44, 'supply', '供应区')],
    labels=[L(15, 68, 'V'), L(26, 68, 'V')])
svg('B10-旗形限制', 'B10 旗形限制 Flag Limit（看跌）', '高位横盘成旗 → 下跌吞没前低 → 起跌基底作为供应区',
    [(0, 90), (8, 52), (12, 62), (18, 30), (22, 40), (26, 30), (30, 40), (34, 30), (46, 80), (52, 58), (56, 70), (60, 58), (64, 70), (72, 36), (92, 96)],
    levels=[(62, 4, 44, '前低', 'liq')],
    boxes=[(16, 36, 26, 44, 'muted')],
    zones=[(30, 92, 32, 42, 'supply', 'Flag Limit')],
    labels=[L(26, 22, '旗', 'muted'), L(46, 88, '吞没前低', 'liq'), L(52, 52, 'R1', 'muted'), L(60, 52, 'R2', 'muted')])
svg('B11-双旗形', 'B11 双旗形 Flag A + Flag B', '两层基底叠加：优先看离当前价更近、未被测试的一层',
    [(0, 90), (8, 52), (12, 60), (16, 52), (20, 60), (24, 30), (28, 38), (32, 30), (36, 38), (40, 30), (52, 82), (58, 70), (62, 76), (72, 36), (92, 96)],
    boxes=[(6, 22, 50, 62, 'muted'), (22, 42, 28, 40, 'muted')],
    zones=[(36, 92, 32, 40, 'supply', 'Flag B 限制区')],
    labels=[L(14, 46, 'Flag A', 'muted'), L(32, 22, 'Flag B', 'muted')])
svg('B12-默认假突破', 'B12 默认假突破 Fakeout V1', '下方形成 R1、R2 → 反弹刺破它们 → 到达上方供应区后下跌',
    [(0, 88), (12, 28), (22, 74), (28, 56), (32, 66), (36, 56), (40, 66), (52, 32), (72, 94)],
    levels=[(56, 26, 60, 'R1 / R2', 'muted')],
    zones=[(12, 92, 28, 40, 'supply', '供应区')],
    labels=[L(28, 50, 'R1'), L(36, 50, 'R2'), L(42, 40, '刺破', 'liq', 'end')])
svg('B13-支撑阻力互换假突破', 'B13 支撑阻力互换 Fakeout V2（SR Flip）', '原来的支撑被跌破后变成阻力 → 假突破下方小阻力 → 回到供应区',
    [(0, 90), (8, 40), (12, 56), (20, 24), (30, 76), (36, 56), (40, 66), (44, 56), (48, 66), (56, 32), (78, 94)],
    levels=[(56, 8, 52, 'S → R', 'liq')],
    zones=[(20, 92, 24, 36, 'supply', '供应区')],
    labels=[L(12, 64, 'S'), L(36, 50, 'R1'), L(44, 50, 'R2')])
svg('B14-钻石假突破', 'B14 钻石假突破 Fakeout V3', '供应区下方先扩张后收敛，QM 的头部与 R1 / R2 同一水平',
    [(0, 88), (12, 28), (22, 72), (28, 50), (32, 60), (36, 50), (40, 68), (44, 56), (48, 72), (54, 50), (58, 60), (68, 32), (88, 96)],
    levels=[(50, 24, 60, '', 'liq')],
    zones=[(12, 92, 28, 40, 'supply', '')],
    labels=[L(28, 44, 'R1'), L(36, 44, 'R2'), L(54, 44, '头')])
svg('B15-最大痛苦位', 'B15 最大痛苦位 MPL', '多次触碰阻力堆积止损 → 猎杀止损 → 吞没前低：猎杀区就是供应区',
    [(0, 88), (8, 40), (12, 54), (16, 40), (20, 54), (26, 40), (30, 48), (34, 40), (40, 26), (52, 80), (58, 64), (62, 72), (72, 32), (92, 96)],
    levels=[(40, 6, 40, '', 'muted'), (54, 10, 48, '前低', 'liq')],
    zones=[(40, 92, 26, 40, 'supply', 'MPL')],
    labels=[L(8, 34, 'R'), L(16, 34, 'R'), L(26, 34, 'R'), L(40, 20, '猎杀止损', 'liq'), L(52, 88, '吞没前低', 'liq')])
svg('B16-双重支撑阻力', 'B16 双重支撑阻力 Double SSR', '上层原是阻力、下层原是支撑；跌破下层后反弹，要先穿过翻转的下层，再到上层供应区',
    [(0, 90), (8, 40), (12, 56), (16, 40), (20, 56), (24, 40), (28, 56), (32, 30), (42, 76), (48, 64), (52, 70), (62, 36), (82, 96)],
    levels=[(40, 4, 92, '上层', 'liq'), (56, 4, 92, '下层', 'liq')],
    zones=[(32, 92, 30, 40, 'supply', '')],
    labels=[L(12, 64, 'S'), L(20, 64, 'S'), L(8, 34, 'R'), L(16, 34, 'R'), L(48, 86, '跌破下层', 'liq')])
svg('B17-三推', 'B17 三推 3 Drive', '分三段推向供应区，力度逐渐减弱，第三推到达区域后反转',
    [(0, 90), (10, 28), (18, 78), (28, 58), (32, 66), (45, 46), (50, 54), (66, 34), (84, 96)],
    zones=[(10, 92, 26, 38, 'supply', '供应区')],
    labels=[L(27, 78, '1 Drive', 'muted', 'start'), L(41, 66, '2 Drive', 'muted', 'start'), L(60, 56, '3 Drive', 'muted', 'start')])
svg('B18-反复敲打', 'B18 反复敲打 CAN CAN', '先在供应区快速触碰多次，再缓慢、重叠地磨回来，最终回到区域后下跌',
    [(0, 88), (6, 30), (8, 36), (10, 30), (12, 36), (14, 30), (24, 84)] + waves(26, 70, 66, 30, 4, 20) + [(86, 96)],
    zones=[(6, 92, 26, 36, 'supply', '供应区')],
    labels=[L(10, 22, '多次触碰', 'muted'), L(44, 70, '缓慢重叠的回升', 'muted')])
svg('B19-压缩', 'B19 压缩 Compression', '重叠、阶梯式、力度很弱地靠近供应区；途中的小需求区都被清除',
    [(0, 88), (12, 28), (22, 84)] + waves(24, 70, 62, 34, 4, 18) + [(82, 96)],
    zones=[(12, 92, 26, 36, 'supply', '供应区')],
    boxes=[(30, 37, 73, 81, 'demand'), (49, 56, 55, 63, 'demand')],
    labels=[L(46, 92, '小需求区被逐一清除', 'demand')])
svg('B20-压缩流动性与假突破', 'B20 压缩流动性 CPLQ', '压缩中形成等高（LQ）→ 先向上扫掉等高 → 再从供应区下跌',
    [(0, 88), (12, 24), (22, 78), (28, 62), (32, 70), (36, 56), (40, 64), (44, 50), (48, 58), (52, 50), (56, 58), (62, 30), (82, 96)],
    levels=[(50, 40, 53, 'LQ', 'liq')],
    zones=[(12, 92, 24, 34, 'supply', '供应区')],
    labels=[L(48, 44, 'R  R', 'muted'), L(62, 24, '扫 LQ', 'liq')])

# ---------------- 逐图核对：标注必须和走势一致 ----------------
def P(name, i):
    return REG[name]['path'][i]


def in_zone(name, pt):
    x1, x2, y1, y2 = REG[name]['zones'][0][:4]
    return x1 <= pt[0] <= x2 and min(y1, y2) <= pt[1] <= max(y1, y2)


n = 'A1-Breaker破坏块'
check(above(P(n, 2), P(n, 1)) and not above(P(n, 3), P(n, 1)) and above(P(n, 4), P(n, 2)) and in_zone(n, P(n, 5)), 'A1 breaker: L, H, sweep below L, break above H, retest zone')
n = 'A2-Mitigation缓解块'
check(above(P(n, 3), P(n, 1)) and above(P(n, 4), P(n, 2)) and in_zone(n, P(n, 5)), 'A2 mitigation: higher low, break above H, retest zone')
n = 'A8-PO3三段式'
check(P(n, 7)[1] > 70 and max(y for _, y in REG[n]['path'][:7]) < 60 and P(n, -1)[1] < 20, 'A8 PO3: accumulation near open, sweep below prior low, expansion up')
for n, (h, l, hh, ll, rt) in {'B01-QM基础形态': (1, 2, 3, 4, 5), 'B02-QM延迟回测': (1, 2, 3, 4, -2),
                              'B03-影线QM': (1, 2, 4, 6, 7), 'B04-延续型QM': (2, 3, 4, 5, 6),
                              'B06-QM再入场': (1, 2, 3, 4, None), 'B07-被忽略的QM': (1, 2, 3, 4, None)}.items():
    check(above(P(n, hh), P(n, h)) and not above(P(n, ll), P(n, l)) and P(n, ll)[1] > P(n, l)[1], f'{n}: HH above H and LL below L')
    if rt is not None:
        check(in_zone(n, P(n, rt)), f'{n}: retest must reach the supply zone')
n = 'B06-QM再入场'
check(above(P(n, 7), P(n, 5)) and P(n, 8)[1] > P(n, 6)[1] and in_zone(n, P(n, 9)) and not above(P(n, 9), (0, 40)), 'B06: small QM and re-entry below main QML')
n = 'B07-被忽略的QM'
check(P(n, 5)[1] > 40 and above(P(n, 9), (0, 58)) and in_zone(n, P(n, 11)), 'B07: QML skipped, fakeout of middle resistance, return to IQML')
n = 'B05-双顶假突破'
check(P(n, 1)[1] == P(n, 3)[1] == 40 and above(P(n, 5), P(n, 1)) and in_zone(n, P(n, 9)), 'B05: equal highs, sweep above, retest')
n = 'B10-旗形限制'
check(P(n, 7)[1] > 62 or P(n, 8)[1] > 62, 'B10: engulf the prior low')
check(in_zone(n, P(n, 13)), 'B10: retest flag limit')
n = 'B12-默认假突破'
check(above(P(n, 7), (0, 56)) and in_zone(n, P(n, 7)), 'B12: rally pierces R1/R2 and reaches supply')
n = 'B13-支撑阻力互换假突破'
check(P(n, 4)[1] > 56 and P(n, 5)[1] == 56 and P(n, 7)[1] == 56 and in_zone(n, P(n, 9)), 'B13: S broken, retested from below as R, then supply')
n = 'B15-最大痛苦位'
check(above(P(n, 8), (0, 40)) and P(n, 9)[1] > 54 and in_zone(n, P(n, 12)), 'B15: stop hunt above R, engulf prior low, retest MPL')
n = 'B16-双重支撑阻力'
check(above(P(n, 7), (0, 40)) and P(n, 8)[1] > 56 and above(P(n, 11), (0, 40)), 'B16: break lower level, rally back through both levels')
n = 'B17-三推'
d = [(P(n, a)[1] - P(n, b)[1]) / (P(n, b)[0] - P(n, a)[0]) for a, b in ((2, 3), (4, 5), (6, 7))]
check(d[0] > d[1] > d[2] > 0 and above(P(n, 5), P(n, 3)) and above(P(n, 7), P(n, 5)) and in_zone(n, P(n, 7)), f'B17: three higher pushes with falling slope {d}')
for n in REG:
    zs = REG[n]['zones']
    if n.startswith('B') and zs:
        check(any(in_zone(n, pt) for pt in REG[n]['path'][2:]), f'{n}: price never reaches its zone')

os.makedirs(SKILL, exist_ok=True)
for f in os.listdir(OUT):
    shutil.copy(os.path.join(OUT, f), os.path.join(SKILL, f))
print('models:', len(os.listdir(OUT)))
