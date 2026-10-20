/* SMC 识别引擎（JavaScript 版）。规则与 tools/smc_detect.py 逐行对应，tools/test_detect.py 会比对两边结果。
 * 浏览器里：<script src="smc-detect.js"></script> 之后用 window.SMCDetect
 * Node 里：const SMC = require('./smc-detect.js')
 * 规则说明见 skills/smc-learning/references/09-数据识别引擎.md
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.SMCDetect = factory();
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  var VERSION = 1;
  var DEFAULTS = { swing: 3, atr_len: 14, eq_tol_atr: 0.1, eq_bounce_atr: 0.5, fvg_min_atr: 0.0, last: 120 };
  var OTE = [0.62, 0.705, 0.79];

  // ============================== 1. 读数据 ==============================
  var NAMES = {
    open: ['open', 'o', '开盘', '开盘价', '开'],
    high: ['high', 'h', '最高', '最高价', '高'],
    low: ['low', 'l', '最低', '最低价', '低'],
    close: ['close', 'c', '收盘', '收盘价', '收', 'close/last', 'last', 'price'],
    time: ['time', 'date', 'datetime', 'timestamp', 'opentime', 'open time', 'gmt time', 'local time', '日期', '时间', '交易日期']
  };
  var KEYS = ['open', 'high', 'low', 'close', 'time'];

  function stripQ(s) { return s.trim().replace(/^["']+|["']+$/g, '').trim(); }
  function norm(cell) { return stripQ(cell).replace(/^[<>]+|[<>]+$/g, '').trim().toLowerCase(); }
  function num(s) {
    s = stripQ(String(s));
    if (!/^[+-]?([0-9]+\.?[0-9]*|\.[0-9]+)([eE][+-]?[0-9]+)?$/.test(s)) return null;
    var v = parseFloat(s);
    return isFinite(v) ? v : null;
  }
  function decimals(s) {
    s = stripQ(String(s));
    if (s.toLowerCase().indexOf('e') >= 0 || s.indexOf('.') < 0) return 0;
    return s.split('.')[1].replace(/0+$/, '').length;
  }
  function pad2(x) { return (x < 10 ? '0' : '') + x; }
  function fmtUnix(v) {
    if (v > 1e11) v = v / 1000.0;
    var d = new Date(Math.trunc(v) * 1000);
    return d.getUTCFullYear() + '-' + pad2(d.getUTCMonth() + 1) + '-' + pad2(d.getUTCDate()) + ' ' + pad2(d.getUTCHours()) + ':' + pad2(d.getUTCMinutes());
  }
  function timeLabel(raw) {
    raw = stripQ(raw);
    if (/^[0-9]{9,13}(\.[0-9]+)?$/.test(raw)) return [fmtUnix(parseFloat(raw)), parseFloat(raw)];
    return [raw, null];
  }

  function parse(text) {
    text = text.replace(/^﻿+/, '').trim();
    var rows = [], warn = [], dec = 0, src, i, k;
    if (text.charAt(0) === '[') {
      var data = JSON.parse(text);
      data.forEach(function (r) {
        var vals = r.slice(1, 5).map(String), nums = vals.map(num);
        if (nums.indexOf(null) >= 0) return;
        vals.forEach(function (v) { dec = Math.max(dec, decimals(v)); });
        var t = r[0], isNum = typeof t === 'number' || /^[0-9]+$/.test(String(t));
        rows.push([isNum ? fmtUnix(parseFloat(t)) : String(t), isNum ? parseFloat(t) : null].concat(nums));
      });
      src = 'json';
    } else {
      var lines = text.split(/\r?\n/).filter(function (ln) { return ln.trim(); });
      var first = lines[0], sep;
      if (first.indexOf('\t') >= 0) sep = '\t';
      else if (first.split(';').length > first.split(',').length) sep = ';';
      else sep = ',';
      var commaDec = sep === ';' && text.indexOf(',') >= 0 && text.indexOf('.') < 0;
      var cells0 = first.split(sep).map(norm), idx = {}, used = [];
      KEYS.forEach(function (key) {
        cells0.forEach(function (cell, kk) {
          if (NAMES[key].indexOf(cell) >= 0 && !(key in idx) && used.indexOf(kk) < 0) { idx[key] = kk; used.push(kk); }
        });
      });
      var tcol2 = null, body;
      if (['open', 'high', 'low', 'close'].every(function (x) { return x in idx; })) {
        body = lines.slice(1); src = 'header';
        if ('time' in idx && cells0[idx.time] === 'date' && cells0.indexOf('time') >= 0) tcol2 = cells0.indexOf('time');
      } else {
        body = lines;
        var f0 = first.split(sep), n0 = f0.length;
        if (n0 >= 6 && f0[1].indexOf(':') >= 0) { idx = { time: 0, open: 2, high: 3, low: 4, close: 5 }; tcol2 = 1; }
        else if (n0 >= 5) idx = { time: 0, open: 1, high: 2, low: 3, close: 4 };
        else if (n0 === 4) idx = { open: 0, high: 1, low: 2, close: 3 };
        else throw new Error('读不出开高低收四列 / cannot find open, high, low, close columns');
        src = 'noheader';
      }
      var maxIdx = Math.max.apply(null, Object.keys(idx).map(function (x) { return idx[x]; }));
      body.forEach(function (ln) {
        var cells = ln.split(sep);
        if (cells.length <= maxIdx) return;
        var vals = ['open', 'high', 'low', 'close'].map(function (x) { return cells[idx[x]]; });
        if (commaDec) vals = vals.map(function (v) { return v.split(',').join('.'); });
        var nums = vals.map(num);
        if (nums.indexOf(null) >= 0) return;
        vals.forEach(function (v) { dec = Math.max(dec, decimals(v)); });
        var label = '', tnum = null;
        if ('time' in idx) {
          var raw = cells[idx.time];
          if (tcol2 !== null && tcol2 < cells.length) raw = raw.trim() + ' ' + cells[tcol2].trim();
          var tl = timeLabel(raw); label = tl[0]; tnum = tl[1];
        }
        rows.push([label, tnum].concat(nums));
      });
    }
    if (!rows.length) throw new Error('没有读到有效的 K 线 / no valid candles found');
    if (rows.every(function (r) { return r[1] !== null; })) rows.sort(function (a, b) { return a[1] - b[1]; });
    else {
      var a = rows[0][0], b = rows[rows.length - 1][0];
      if (/^[0-9]{4}[^0-9]/.test(a) && /^[0-9]{4}[^0-9]/.test(b)) {
        var da = a.replace(/[^0-9]/g, ''), db = b.replace(/[^0-9]/g, '');
        if (da.length === db.length && da > db) rows.reverse();
      }
    }
    var candles = [], bad = 0;
    rows.forEach(function (r) {
      var o = r[2], h = r[3], l = r[4], c = r[5];
      if (h < Math.max(o, c) || l > Math.min(o, c)) { bad++; return; }
      candles.push({ t: r[0], o: o, h: h, l: l, c: c });
    });
    if (bad) warn.push(bad + ' 行数据的高低点和开收盘矛盾，已跳过 / ' + bad + ' rows skipped (high/low inconsistent with open/close)');
    if (candles.length < 20) warn.push('K 线太少（少于 20 根），识别结果参考价值有限 / fewer than 20 candles');
    return [candles, { source: src, decimals: Math.min(dec, 8), warnings: warn }];
  }

  // ============================== 2. 识别 ==============================
  function detect(K, params) {
    var p = {}, key;
    for (key in DEFAULTS) p[key] = DEFAULTS[key];
    for (key in (params || {})) p[key] = params[key];
    var n = K.length, N = Math.trunc(p.swing), i, j, k;
    var O = K.map(function (x) { return x.o; }), H = K.map(function (x) { return x.h; }),
      L = K.map(function (x) { return x.l; }), C = K.map(function (x) { return x.c; });
    var bear = function (x) { return C[x] < O[x]; }, bull = function (x) { return C[x] > O[x]; };

    var tr = [], atr = [];
    for (i = 0; i < n; i++) tr.push(i === 0 ? H[i] - L[i] : Math.max(H[i] - L[i], Math.abs(H[i] - C[i - 1]), Math.abs(L[i] - C[i - 1])));
    for (i = 0; i < n; i++) {
      var s = 0.0, cnt = 0;
      for (j = Math.max(0, i - p.atr_len + 1); j < i + 1; j++) { s += tr[j]; cnt++; }
      atr.push(s / cnt);
    }

    var swings = [];
    for (i = N; i < n - N; i++) {
      var okH = true, okL = true;
      for (j = i - N; j < i; j++) { if (!(H[i] > H[j])) okH = false; if (!(L[i] < L[j])) okL = false; }
      for (j = i + 1; j < i + N + 1; j++) { if (!(H[i] >= H[j])) okH = false; if (!(L[i] <= L[j])) okL = false; }
      if (okH) swings.push({ type: 'high', i: i, price: H[i], confirmed: i + N });
      if (okL) swings.push({ type: 'low', i: i, price: L[i], confirmed: i + N });
    }
    var byConf = {};
    swings.forEach(function (sw) { (byConf[sw.confirmed] = byConf[sw.confirmed] || []).push(sw); });

    var events = [], sweeps = [], levels = [], pools = [], ref = { high: null, low: null }, trend = 0;
    for (k = 0; k < n; k++) {
      levels.forEach(function (lv) {
        if (lv.state !== 'active') return;
        if (lv.type === 'high' && H[k] > lv.price) { lv.state = C[k] > lv.price ? 'broken' : 'swept'; lv.at = k; }
        else if (lv.type === 'low' && L[k] < lv.price) { lv.state = C[k] < lv.price ? 'broken' : 'swept'; lv.at = k; }
        else return;
        if (lv.state === 'swept') sweeps.push({ side: lv.type, i: k, level: lv.price, from: lv.i, pool: false });
      });
      pools.forEach(function (pl) {
        if (pl.state !== 'active' || k <= pl.members[pl.members.length - 1]) return;
        if (pl.type === 'high' && H[k] > pl.level) { pl.state = C[k] > pl.level ? 'broken' : 'swept'; pl.at = k; }
        else if (pl.type === 'low' && L[k] < pl.level) { pl.state = C[k] < pl.level ? 'broken' : 'swept'; pl.at = k; }
        else return;
        if (pl.state === 'swept') sweeps.push({ side: pl.type, i: k, level: pl.level, from: pl.members[pl.members.length - 1], pool: true });
      });
      var rh = ref.high, rl = ref.low;
      if (rh !== null && !rh.broken && C[k] > rh.price) {
        events.push({ type: trend === -1 ? 'CHoCH' : 'BOS', dir: 1, i: k, level: rh.price, from: rh.i, first: trend === 0 });
        rh.broken = true; trend = 1;
      }
      if (rl !== null && !rl.broken && C[k] < rl.price) {
        events.push({ type: trend === 1 ? 'CHoCH' : 'BOS', dir: -1, i: k, level: rl.price, from: rl.i, first: trend === 0 });
        rl.broken = true; trend = -1;
      }
      (byConf[k] || []).forEach(function (sw) {
        ref[sw.type] = { i: sw.i, price: sw.price, broken: false };
        levels.push({ type: sw.type, i: sw.i, price: sw.price, state: 'active', at: null });
        var tol = p.eq_tol_atr * atr[sw.i];
        var prev = swings.filter(function (x) { return x.type === sw.type && x.i < sw.i && x.confirmed <= k; });
        for (var qi = prev.length - 1; qi >= 0; qi--) {
          var q = prev[qi];
          if (Math.abs(q.price - sw.price) > tol) continue;
          var lo = q.i + 1, hi = sw.i, lvl, jj, bad = false, ext;
          if (sw.type === 'low') {
            lvl = Math.min(q.price, sw.price);
            for (jj = lo; jj < hi; jj++) if (L[jj] < lvl) bad = true;
            if (bad) continue;
            ext = lo < hi ? Math.max.apply(null, H.slice(lo, hi)) : lvl;
            if (ext - Math.max(q.price, sw.price) < p.eq_bounce_atr * atr[sw.i]) continue;
          } else {
            lvl = Math.max(q.price, sw.price);
            for (jj = lo; jj < hi; jj++) if (H[jj] > lvl) bad = true;
            if (bad) continue;
            ext = lo < hi ? Math.min.apply(null, L.slice(lo, hi)) : lvl;
            if (Math.min(q.price, sw.price) - ext < p.eq_bounce_atr * atr[sw.i]) continue;
          }
          for (jj = sw.i + 1; jj < k + 1; jj++) {
            if (sw.type === 'low' && L[jj] < lvl) bad = true;
            if (sw.type === 'high' && H[jj] > lvl) bad = true;
          }
          if (bad) continue;
          var joined = false;
          for (var pi = 0; pi < pools.length; pi++) {
            var pl = pools[pi];
            if (pl.type === sw.type && pl.state === 'active' && pl.members[pl.members.length - 1] === q.i) {
              pl.members.push(sw.i);
              pl.level = sw.type === 'low' ? Math.min(pl.level, lvl) : Math.max(pl.level, lvl);
              joined = true; break;
            }
          }
          if (!joined) pools.push({ type: sw.type, members: [q.i, sw.i], level: lvl, state: 'active', at: null });
          break;
        }
      });
    }

    var fvgs = [];
    for (var b = 1; b < n - 1; b++) {
      var a = b - 1, c = b + 1, d, top, bot;
      if (L[c] > H[a]) { d = 1; top = L[c]; bot = H[a]; }
      else if (H[c] < L[a]) { d = -1; top = L[a]; bot = H[c]; }
      else continue;
      if (top - bot < p.fvg_min_atr * atr[b]) continue;
      var f = { dir: d, a: a, b: b, c: c, top: top, bottom: bot, touched: null, filled: null };
      for (j = c + 1; j < n; j++) {
        if (d === 1) {
          if (f.touched === null && L[j] < top) f.touched = j;
          if (L[j] <= bot) { f.filled = j; break; }
        } else {
          if (f.touched === null && H[j] > bot) f.touched = j;
          if (H[j] >= top) { f.filled = j; break; }
        }
      }
      fvgs.push(f);
    }

    var obs = [], seen = {};
    events.forEach(function (e) {
      var s = e.from, k2 = e.i, d = e.dir, m = s + 1, jj, opp;
      if (k2 - s < 2) return;
      if (d === 1) { for (jj = s + 1; jj < k2 + 1; jj++) if (L[jj] <= L[m]) m = jj; opp = bear; }
      else { for (jj = s + 1; jj < k2 + 1; jj++) if (H[jj] >= H[m]) m = jj; opp = bull; }
      e.origin = m;
      var j2;
      if (opp(m)) { j2 = m; while (j2 + 1 < k2 && opp(j2 + 1)) j2++; }
      else { j2 = m - 1; while (j2 > s && !opp(j2)) j2--; if (j2 <= s) return; }
      if (j2 >= k2 || seen[d + ':' + j2]) return;
      seen[d + ':' + j2] = true;
      var hasFvg = fvgs.filter(function (f) { return f.dir === d && j2 + 1 <= f.b && f.b <= k2; }).map(function (f) { return f.b; });
      var side = d === 1 ? 'low' : 'high', hi2 = Math.max(j2, m), set = {};
      sweeps.forEach(function (w) { if (w.side === side && s + 1 <= w.i && w.i <= hi2) set[w.i] = true; });
      var hasSweep = Object.keys(set).map(Number).sort(function (x, y) { return x - y; });
      var top = Math.max(O[j2], C[j2]), bot = Math.min(O[j2], C[j2]);
      var ob = { dir: d, i: j2, top: top, bottom: bot, break: k2, break_type: e.type, origin: m,
        fvg: hasFvg, sweep: hasSweep, valid: !!(hasFvg.length && hasSweep.length), tapped: null, invalidated: null };
      for (var x = k2 + 1; x < n; x++) {
        if (d === 1) {
          if (ob.tapped === null && L[x] <= top) ob.tapped = x;
          if (C[x] < bot) { ob.invalidated = x; break; }
        } else {
          if (ob.tapped === null && H[x] >= bot) ob.tapped = x;
          if (C[x] > top) { ob.invalidated = x; break; }
        }
      }
      obs.push(ob);
    });

    var rng = null;
    if (events.length) {
      var e = events[events.length - 1], m = e.origin;
      if (m !== undefined) {
        var loI = m, hiI = m, lo, hi, ote;
        if (e.dir === 1) {
          for (j = m; j < n; j++) if (H[j] > H[hiI]) hiI = j;
          lo = L[loI]; hi = H[hiI];
          ote = OTE.map(function (r) { return hi - r * (hi - lo); });
        } else {
          for (j = m; j < n; j++) if (L[j] < L[loI]) loI = j;
          lo = L[loI]; hi = H[hiI];
          ote = OTE.map(function (r) { return lo + r * (hi - lo); });
        }
        var eq = (hi + lo) / 2;
        rng = { dir: e.dir, low_i: loI, high_i: hiI, low: lo, high: hi, eq: eq, ote: ote,
          zone: C[n - 1] > eq ? 'premium' : (C[n - 1] < eq ? 'discount' : 'equilibrium') };
      }
    }
    return { version: VERSION, params: p, n: n, trend: trend, atr: n ? atr[n - 1] : null, swings: swings, events: events,
      sweeps: sweeps, levels: levels, pools: pools, fvgs: fvgs, obs: obs, range: rng };
  }

  // ============================== 3. 挑出值得画的 ==============================
  function lastN(arr, k) { return arr.slice(Math.max(0, arr.length - k)); }

  function select(K, R, last) {
    var n = K.length;
    last = Math.trunc(last || R.params.last);
    var v0 = Math.max(0, n - last), items = [];
    lastN(R.events.filter(function (e) { return e.i >= v0; }), 2).forEach(function (e) {
      items.push({ type: 'hline', kind: 'structure', i1: Math.max(e.from, v0), i2: e.i, price: e.level,
        label: e.type + (e.dir === 1 ? '↑' : '↓'), ref: ['event', R.events.indexOf(e)] });
    });
    lastN(R.pools.filter(function (pl) { return pl.state === 'active' && pl.members[pl.members.length - 1] >= v0; }), 2).forEach(function (pl) {
      items.push({ type: 'hline', kind: 'liquidity', i1: Math.max(pl.members[0], v0), i2: n - 1, price: pl.level,
        label: pl.type === 'high' ? 'EQH BSL' : 'EQL SSL', ref: ['pool', R.pools.indexOf(pl)] });
    });
    var shown = [];
    for (var si = R.sweeps.length - 1; si >= 0; si--) {
      var w = R.sweeps[si];
      if (w.i < v0 || shown.some(function (s) { return s.i === w.i; })) continue;
      shown.push(w);
      if (shown.length === 2) break;
    }
    shown.reverse().forEach(function (w) {
      items.push({ type: 'marker', kind: 'liquidity', i: w.i, price: w.side === 'high' ? K[w.i].h : K[w.i].l,
        place: w.side === 'high' ? 'above' : 'below', label: 'sweep', ref: ['sweep', R.sweeps.indexOf(w)] });
    });
    lastN(R.obs.filter(function (o) { return o.valid && o.invalidated === null && o.i >= v0; }), 2).forEach(function (ob) {
      items.push({ type: 'box', kind: 'ob', i1: ob.i, i2: n - 1, top: ob.top, bottom: ob.bottom,
        label: ob.dir === 1 ? 'Bull OB' : 'Bear OB', ref: ['ob', R.obs.indexOf(ob)] });
    });
    lastN(R.fvgs.filter(function (f) { return f.filled === null && f.b >= v0; }), 2).forEach(function (f) {
      items.push({ type: 'box', kind: 'fvg', i1: f.b, i2: n - 1, top: f.top, bottom: f.bottom,
        label: 'FVG' + (f.dir === 1 ? '↑' : '↓'), ref: ['fvg', R.fvgs.indexOf(f)] });
    });
    var r = R.range;
    if (r && Math.max(r.low_i, r.high_i) >= v0) {
      items.push({ type: 'range', kind: 'range', i1: Math.max(Math.min(r.low_i, r.high_i), v0), i2: n - 1,
        high: r.high, low: r.low, eq: r.eq, ote: r.ote, label: 'EQ 50%', ref: ['range', 0] });
    }
    var c = K[n - 1].c;
    var above = R.levels.filter(function (lv) { return lv.type === 'high' && lv.state === 'active' && lv.price > c; });
    var below = R.levels.filter(function (lv) { return lv.type === 'low' && lv.state === 'active' && lv.price < c; });
    var poolPx = items.filter(function (it) { return it.kind === 'liquidity' && it.type === 'hline'; }).map(function (it) { return it.price; });
    if (above.length) {
      var best = above[0];
      above.forEach(function (lv) { if (lv.price < best.price || (lv.price === best.price && lv.i > best.i)) best = lv; });
      if (poolPx.indexOf(best.price) < 0) items.push({ type: 'hline', kind: 'target', i1: Math.max(best.i, v0), i2: n - 1,
        price: best.price, label: 'BSL', ref: ['level', R.levels.indexOf(best)] });
    }
    if (below.length) {
      var bestL = below[0];
      below.forEach(function (lv) { if (lv.price > bestL.price || (lv.price === bestL.price && lv.i > bestL.i)) bestL = lv; });
      if (poolPx.indexOf(bestL.price) < 0) items.push({ type: 'hline', kind: 'target', i1: Math.max(bestL.i, v0), i2: n - 1,
        price: bestL.price, label: 'SSL', ref: ['level', R.levels.indexOf(bestL)] });
    }
    return { from: v0, to: n - 1, items: items };
  }

  // ============================== 4. 文字报告 ==============================
  function report(K, R, sel, info, lang) {
    var d = info && info.decimals != null ? info.decimals : 2, zh = lang !== 'en';
    function P(x) { return x.toFixed(d); }
    function P1(x) { return x.toFixed(d + 1); }
    function T(i) { var t = K[i].t; return '#' + i + (t ? ' (' + t + ')' : ''); }
    function dirw(x) { return zh ? (x === 1 ? '多' : '空') : (x === 1 ? 'bullish' : 'bearish'); }
    function J(arr, sep) { return arr.map(T).join(sep); }
    var out = [];
    out.push(zh ? 'SMC 识别报告（程序按规则计算，不是交易建议）' : 'SMC detection report (rule-based, not trading advice)');
    out.push(zh ? 'K 线 ' + K.length + ' 根，图上显示 ' + T(sel.from) + ' 到 ' + T(sel.to) + '；摆动点参数 N=' + R.params.swing + '；最新收盘 ' + P(K[K.length - 1].c)
      : K.length + ' candles, chart shows ' + T(sel.from) + ' to ' + T(sel.to) + '; swing N=' + R.params.swing + '; last close ' + P(K[K.length - 1].c));
    var tr = zh ? { '1': '上涨（最近一次结构突破向上）', '-1': '下跌（最近一次结构突破向下）', '0': '未确定（还没有结构突破）' }
      : { '1': 'up (last structure break was upward)', '-1': 'down (last structure break was downward)', '0': 'undetermined (no structure break yet)' };
    out.push((zh ? '当前结构方向：' : 'Structure: ') + tr[String(R.trend)]);
    ((info && info.warnings) || []).forEach(function (w) { out.push('⚠ ' + w); });
    out.push('');
    sel.items.forEach(function (it, ix) {
      var n_ = ix + 1, kind = it.ref[0], idx = it.ref[1];
      if (kind === 'event') {
        var e = R.events[idx];
        var gate = zh ? (e.type === 'CHoCH' ? '守门点' : '摆动点') : (e.type === 'CHoCH' ? 'guard point' : 'swing point');
        var first = e.first ? (zh ? '（之前方向未知，这是第一次突破）' : ' (first break; prior direction unknown)') : '';
        if (zh) out.push(n_ + '. 【结构】' + e.type + '（' + dirw(e.dir) + '）：' + T(e.i) + ' 收盘 ' + P(K[e.i].c) + '，实体收' + (e.dir === 1 ? '上' : '下') + '破 ' + T(e.from) + ' 的' + gate + ' ' + P(e.level) + first);
        else out.push(n_ + '. [Structure] ' + e.type + ' (' + dirw(e.dir) + '): ' + T(e.i) + ' closed at ' + P(K[e.i].c) + ', ' + (e.dir === 1 ? 'above' : 'below') + ' the ' + gate + ' ' + P(e.level) + ' at ' + T(e.from) + first);
      } else if (kind === 'pool') {
        var pl = R.pools[idx];
        if (zh) out.push(n_ + '. 【流动性】' + (pl.type === 'high' ? '等高 BSL' : '等低 SSL') + ' ' + P(pl.level) + '：' + J(pl.members, '、') + ' 几乎同价（差距不超过 ' + R.params.eq_tol_atr + ' 倍 ATR），中间有明显' + (pl.type === 'high' ? '回落' : '反弹') + '，至今未被扫');
        else out.push(n_ + '. [Liquidity] ' + (pl.type === 'high' ? 'Equal highs (BSL)' : 'Equal lows (SSL)') + ' ' + P(pl.level) + ': ' + J(pl.members, ', ') + ' within ' + R.params.eq_tol_atr + '×ATR, with a clear pullback between; not yet swept');
      } else if (kind === 'sweep') {
        var w = R.sweeps[idx], c = K[w.i], what, ext;
        if (zh) {
          what = w.pool ? (w.side === 'high' ? '等高' : '等低') : (w.side === 'high' ? '高点' : '低点');
          ext = w.side === 'high' ? '最高 ' + P(c.h) : '最低 ' + P(c.l);
          out.push(n_ + '. 【清扫】' + T(w.i) + ' 影线越过 ' + T(w.from) + ' 的' + what + ' ' + P(w.level) + '（' + ext + '），收盘 ' + P(c.c) + ' 收回到里面');
        } else {
          what = w.pool ? (w.side === 'high' ? 'equal highs' : 'equal lows') : (w.side === 'high' ? 'swing high' : 'swing low');
          ext = w.side === 'high' ? 'high ' + P(c.h) : 'low ' + P(c.l);
          out.push(n_ + '. [Sweep] ' + T(w.i) + ' wicked beyond the ' + what + ' ' + P(w.level) + ' at ' + T(w.from) + ' (' + ext + ') and closed back inside at ' + P(c.c));
        }
      } else if (kind === 'ob') {
        var ob = R.obs[idx];
        var st = ob.tapped !== null ? (zh ? '；' + T(ob.tapped) + ' 首次回到区域' : '; first return at ' + T(ob.tapped)) : (zh ? '；之后还没回来过' : '; not revisited yet');
        if (zh) out.push(n_ + '. 【订单区】看' + (ob.dir === 1 ? '涨' : '跌') + ' OB ' + T(ob.i) + '，只取实体 ' + P(ob.top) + '–' + P(ob.bottom) + '：位移前最后一根' + (ob.dir === 1 ? '阴' : '阳') + '线；三个条件 ✓清扫（' + J(ob.sweep, '、') + '） ✓FVG（B=' + J(ob.fvg, '、') + '） ✓' + ob.break_type + '（' + T(ob.break) + '）' + st);
        else out.push(n_ + '. [Order block] ' + (ob.dir === 1 ? 'Bullish' : 'Bearish') + ' OB ' + T(ob.i) + ', body only ' + P(ob.top) + '–' + P(ob.bottom) + ': last ' + (ob.dir === 1 ? 'down' : 'up') + ' candle before displacement; ✓sweep (' + J(ob.sweep, ', ') + ') ✓FVG (B=' + J(ob.fvg, ', ') + ') ✓' + ob.break_type + ' (' + T(ob.break) + ')' + st);
      } else if (kind === 'fvg') {
        var f = R.fvgs[idx], cmp, st2;
        if (zh) {
          cmp = f.dir === 1 ? 'A ' + T(f.a) + ' 最高 ' + P(K[f.a].h) + ' < C ' + T(f.c) + ' 最低 ' + P(K[f.c].l) : 'A ' + T(f.a) + ' 最低 ' + P(K[f.a].l) + ' > C ' + T(f.c) + ' 最高 ' + P(K[f.c].h);
          st2 = f.touched !== null ? '；' + T(f.touched) + ' 起被部分回补' : '；尚未回补';
          out.push(n_ + '. 【FVG】' + dirw(f.dir) + '头 FVG ' + P(f.top) + '–' + P(f.bottom) + '（B=' + T(f.b) + '）：' + cmp + '，中间没有重叠' + st2);
        } else {
          cmp = f.dir === 1 ? 'A ' + T(f.a) + ' high ' + P(K[f.a].h) + ' < C ' + T(f.c) + ' low ' + P(K[f.c].l) : 'A ' + T(f.a) + ' low ' + P(K[f.a].l) + ' > C ' + T(f.c) + ' high ' + P(K[f.c].h);
          st2 = f.touched !== null ? '; partly filled from ' + T(f.touched) : '; unfilled';
          out.push(n_ + '. [FVG] ' + dirw(f.dir) + ' FVG ' + P(f.top) + '–' + P(f.bottom) + ' (B=' + T(f.b) + '): ' + cmp + ', no overlap' + st2);
        }
      } else if (kind === 'range') {
        var r = R.range;
        var zn = zh ? { premium: 'Premium（贵区）', discount: 'Discount（便宜区）', equilibrium: '均衡点' } : { premium: 'premium', discount: 'discount', equilibrium: 'equilibrium' };
        var o = r.ote.map(P1).join(' / ');
        var loS = P(r.low) + '（' + T(r.low_i) + '）', hiS = P(r.high) + '（' + T(r.high_i) + '）';
        var loE = P(r.low) + ' (' + T(r.low_i) + ')', hiE = P(r.high) + ' (' + T(r.high_i) + ')';
        if (zh) out.push(n_ + '. 【区间】最近一段' + (r.dir === 1 ? '上涨推动：低点 ' + loS + ' 到高点 ' + hiS : '下跌推动：高点 ' + hiS + ' 到低点 ' + loS) + '，50% 均衡点 ' + P1(r.eq) + '；当前收盘在 ' + zn[r.zone] + '；OTE 0.62/0.705/0.79 = ' + o + '（从推动终点往回量）');
        else out.push(n_ + '. [Range] last ' + (r.dir === 1 ? 'up leg: low ' + loE + ' to high ' + hiE : 'down leg: high ' + hiE + ' to low ' + loE) + ', equilibrium ' + P1(r.eq) + '; price is in ' + zn[r.zone] + '; OTE 0.62/0.705/0.79 = ' + o + ' (measured back from the leg end)');
      } else if (kind === 'level') {
        var lv = R.levels[idx];
        if (zh) out.push(n_ + '. 【对侧流动性】' + (lv.type === 'high' ? '上方最近的未扫高点 BSL' : '下方最近的未扫低点 SSL') + ' ' + P(lv.price) + '（' + T(lv.i) + '）');
        else out.push(n_ + '. [Liquidity] nearest untaken ' + (lv.type === 'high' ? 'swing high above (BSL)' : 'swing low below (SSL)') + ' ' + P(lv.price) + ' (' + T(lv.i) + ')');
      }
    });
    if (!sel.items.length) out.push(zh ? '图上范围内没有识别到符合规则的项目。' : 'Nothing in view meets the rules.');
    var cand = lastN(R.obs.filter(function (o) { return !o.valid && o.invalidated === null && o.i >= sel.from; }), 2);
    if (cand.length) {
      out.push('');
      out.push(zh ? '不满足 OB 三个条件的候选（只能算 POI / 反应区，不画在图上）：' : 'OB candidates that fail the three conditions (POI only, not drawn):');
      cand.forEach(function (ob) {
        var miss = [];
        if (!ob.sweep.length) miss.push(zh ? '之前没有清扫' : 'no sweep before it');
        if (!ob.fvg.length) miss.push(zh ? '位移没有留下 FVG' : 'no FVG in the displacement');
        out.push('- ' + T(ob.i) + ' ' + P(ob.top) + '–' + P(ob.bottom) + (zh ? '：' + miss.join('、') : ': ' + miss.join(', ')));
      });
    }
    out.push('');
    if (zh) {
      out.push('程序没有判断的：诱导（Miller 严格口径）、多周期方向、消息面、拒绝针和入场触发。这些需要你自己核对。');
      out.push('识别规则见 references/09-数据识别引擎.md。仅供学习，不构成交易建议。');
    } else {
      out.push('Not judged by the program: inducement (Miller strict view), higher-timeframe bias, news, rejection wicks and entry triggers. Check these yourself.');
      out.push('Rules: references/09-数据识别引擎.md. For learning only, not trading advice.');
    }
    return out.join('\n');
  }

  return { VERSION: VERSION, DEFAULTS: DEFAULTS, parse: parse, detect: detect, select: select, report: report };
}));
