"""在一张 K 线截图上画 SMC 标注。

用法：python3 annotate.py 截图.png 标注.json 输出.png

标注格式见 skills/smc-learning/references/08-截图标注规范.md。
同一份 JSON 也可以放进仓库的 annotator/index.html（标注器网页）里打开、拖动校正。
这个文件刻意写成单文件、只依赖 Pillow，方便 AI 在自带的代码环境里直接复制运行。
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

COLORS = {
    'structure': (207, 216, 220), 'liquidity': (245, 197, 66), 'fvg': (79, 140, 255),
    'ob': (180, 124, 255), 'premium': (239, 83, 80), 'discount': (38, 166, 154),
    'entry': (79, 140, 255), 'sl': (239, 83, 80), 'tp': (38, 166, 154), 'note': (255, 159, 67),
}
CJK_FONTS = [
    '/System/Library/Fonts/PingFang.ttc', '/System/Library/Fonts/STHeiti Medium.ttc',
    'C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc', '/usr/share/fonts/truetype/arphic/uming.ttc',
]


def load_font(size):
    for p in CJK_FONTS:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size), True
            except OSError:
                pass
    for p in ('DejaVuSans-Bold.ttf', 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(p, size), False
        except OSError:
            pass
    return ImageFont.load_default(), False


class Mapper:
    """把 0–1 相对坐标或价格换算成像素。价格需要 calibration（两个价格刻度及其相对高度）。"""

    def __init__(self, w, h, calib):
        self.w, self.h, self.c = w, h, calib or {}

    def x(self, v):
        return float(v) * self.w

    def y_of(self, item, ykey, pkey):
        if ykey in item:
            return float(item[ykey]) * self.h
        if pkey in item:
            c = self.c
            if not all(k in c for k in ('price_a', 'y_a', 'price_b', 'y_b')):
                raise ValueError(f'"{pkey}" 需要 calibration：price_a / y_a / price_b / y_b')
            pa, ya, pb, yb = float(c['price_a']), float(c['y_a']), float(c['price_b']), float(c['y_b'])
            if pa == pb:
                raise ValueError('calibration 的两个价格不能相同')
            return (ya + (float(item[pkey]) - pa) * (yb - ya) / (pb - pa)) * self.h
        raise ValueError(f'缺少 {ykey} 或 {pkey}：{item}')


def validate(spec):
    """标注本身的逻辑检查：发现明显矛盾就报错，而不是画出一张错图。"""
    errs = []
    for k, it in enumerate(spec.get('items', [])):
        t = it.get('type')
        if t not in ('hline', 'box', 'line', 'marker', 'label', 'arrow'):
            errs.append(f'第 {k + 1} 项：未知类型 {t}')
        if t == 'box':
            top, bot = it.get('price_top'), it.get('price_bottom')
            if top is not None and bot is not None and float(top) <= float(bot):
                errs.append(f'第 {k + 1} 项（{it.get("label", "")}）：price_top 必须高于 price_bottom')
            fv = it.get('fvg_check')
            if fv:  # {"a_high": .., "c_low": ..} 或 {"a_low": .., "c_high": ..}
                if 'a_high' in fv and float(fv['c_low']) <= float(fv['a_high']):
                    errs.append(f'第 {k + 1} 项：C 的最低点不高于 A 的最高点，不是多头 FVG')
                if 'a_low' in fv and float(fv['c_high']) >= float(fv['a_low']):
                    errs.append(f'第 {k + 1} 项：C 的最高点不低于 A 的最低点，不是空头 FVG')
        for key in ('x', 'x1', 'x2', 'y', 'y1', 'y2'):
            if key in it and not (0 <= float(it[key]) <= 1):
                errs.append(f'第 {k + 1} 项：{key}={it[key]} 超出 0–1')
    if errs:
        raise ValueError('标注没有通过检查：\n' + '\n'.join(errs))


def draw(img_path, spec, out_path):
    validate(spec)
    im = Image.open(img_path).convert('RGBA')
    w, h = im.size
    m = Mapper(w, h, spec.get('calibration'))
    over = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    fs = max(14, w // 70)
    font, cjk = load_font(fs)
    lw = max(2, w // 600)

    def text_of(it, key='label'):
        s = it.get(key) or it.get('text') or ''
        if not cjk and any(ord(ch) > 127 for ch in s):
            s = it.get(key + '_en') or it.get('text_en') or s.encode('ascii', 'ignore').decode() or '?'
        if it.get('confidence') == 'low' and s:
            s += ' ?'
        return s

    def tag(x, y, s, col, anchor='la'):
        if not s:
            return
        bb = d.textbbox((x, y), s, font=font, anchor=anchor)
        d.rectangle((bb[0] - 4, bb[1] - 3, bb[2] + 4, bb[3] + 3), fill=(15, 18, 24, 210))
        d.text((x, y), s, font=font, fill=col + (255,), anchor=anchor)

    def dashed(x0, y0, x1, y1, col, width, dash=10, gap=7):
        import math
        L = math.hypot(x1 - x0, y1 - y0) or 1
        n = int(L // (dash + gap)) + 1
        for i in range(n):
            a = i * (dash + gap) / L
            b = min(1, (i * (dash + gap) + dash) / L)
            d.line((x0 + (x1 - x0) * a, y0 + (y1 - y0) * a, x0 + (x1 - x0) * b, y0 + (y1 - y0) * b), fill=col + (255,), width=width)

    for it in spec.get('items', []):
        col = COLORS.get(it.get('kind', 'note'), COLORS['note'])
        low = it.get('confidence') == 'low'
        t = it['type']
        if t == 'hline':
            y = m.y_of(it, 'y', 'price')
            x0, x1 = m.x(it.get('x1', 0)), m.x(it.get('x2', 1))
            dashed(x0, y, x1, y, col, lw) if (low or it.get('dash', True)) else d.line((x0, y, x1, y), fill=col + (255,), width=lw)
            tag(x1 - 6, y - 4, text_of(it), col, 'rb')
        elif t == 'box':
            y1 = m.y_of(it, 'y1', 'price_top')
            y2 = m.y_of(it, 'y2', 'price_bottom')
            x0, x1 = m.x(it['x1']), m.x(it.get('x2', 1))
            top, bot = min(y1, y2), max(y1, y2)
            d.rectangle((x0, top, x1, bot), fill=col + (50,))
            for a, b, c2, e in ((x0, top, x1, top), (x0, bot, x1, bot), (x0, top, x0, bot), (x1, top, x1, bot)):
                dashed(a, b, c2, e, col, max(1, lw - 1)) if low else d.line((a, b, c2, e), fill=col + (230,), width=max(1, lw - 1))
            if it.get('label_pos') == 'br':  # 文字放在区域右下角（左下角被别的标注占用时）
                tag(x1 - 6, bot + 6, text_of(it), col, 'ra')
            else:
                tag(x0 + 6, bot + 6, text_of(it), col, 'la')
        elif t in ('line', 'arrow'):
            xa, xb = m.x(it['x1']), m.x(it['x2'])
            ya, yb = m.y_of(it, 'y1', 'price1'), m.y_of(it, 'y2', 'price2')
            dashed(xa, ya, xb, yb, col, lw) if low else d.line((xa, ya, xb, yb), fill=col + (255,), width=lw)
            if t == 'arrow':
                import math
                ang = math.atan2(yb - ya, xb - xa)
                L = fs * 0.9
                d.polygon([(xb, yb), (xb - L * math.cos(ang - 0.45), yb - L * math.sin(ang - 0.45)),
                           (xb - L * math.cos(ang + 0.45), yb - L * math.sin(ang + 0.45))], fill=col + (255,))
            tag((xa + xb) / 2, min(ya, yb) - 6, text_of(it), col, 'mb')
        elif t == 'marker':
            x, y = m.x(it['x']), m.y_of(it, 'y', 'price')
            r = fs * 0.45
            d.ellipse((x - r, y - r, x + r, y + r), outline=col + (255,), width=lw)
            below = it.get('place', 'below') == 'below'
            tag(x, y + r + 4 if below else y - r - 4, text_of(it, 'text'), col, 'mt' if below else 'mb')
        elif t == 'label':
            tag(m.x(it['x']), m.y_of(it, 'y', 'price'), text_of(it, 'text'), col, 'mm')
    foot = '学习性分析，不构成交易建议 · 标注位置为估计' if cjk else 'Study only, not trading advice. Positions are estimates.'
    tag(w - 8, h - 8, foot, (138, 148, 166), 'rb')
    Image.alpha_composite(im, over).convert('RGB').save(out_path)
    return out_path


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    spec = json.load(open(sys.argv[2], encoding='utf-8'))
    print('saved', draw(sys.argv[1], spec, sys.argv[3]))
