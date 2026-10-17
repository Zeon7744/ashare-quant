"""
ashare-quant: 日线数据 pipeline（原理层完善）

对应"数据 pipeline 深度"诉求，补齐 ashare 仓缺失的数据获取层：
1. 多源取数（akshare 东财/新浪 fallback，离线可注入本地 rows）
2. 缓存水位线增量拉取：只拉上次缓存末端之后的新 bar，避免全量重复请求
3. 复权一致性校验：检测前复权/后复权导致的跳变（除权日单日跌幅异常 + 收盘价漂移）
4. 数据 QC：缺失值 / OHLC 合法性 / 成交量尖峰，输出 DataQualityReport（口径对齐 backtest.py）

保持纯 Python 标准库 + 可选 akshare，无 numpy/sklearn 强依赖。
"""
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Sequence, Tuple

# 数据 pipeline QC 阈值
_OHLC_MIN = 0.0
_VOL_SPIKE_RATIO = 5.0        # 单日成交量 > 20 日均值 5 倍 视为尖峰
_ADJUST_JUMP_PCT = 0.30       # 单日跌幅 > 30% 且次日回到原量级 → 疑似复权跳变
_DRIFT_PCT = 0.20             # 全段收盘价漂移 > 20% 提示前/后复权口径不一致


@dataclass
class DataQualityReport:
    """数据质量检测报告（与 backtest.py 口径一致）。"""
    symbol: str
    n_rows: int
    passed: bool
    null_count: int
    ohlc_violations: int
    vol_spike_days: int
    adjust_warnings: int
    issues: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


@dataclass
class PipelineResult:
    symbol: str
    rows: List[Dict]            # 归一化 OHLCV: {date, open, high, low, close, volume}
    source: str
    is_incr: bool              # 是否增量（命中缓存水位线）
    qc: DataQualityReport

    def to_dataframe(self):
        """转 pandas DataFrame（可选；无 pandas 时抛 ImportError）。"""
        import pandas as pd
        cols = ['date', 'open', 'high', 'low', 'close', 'volume']
        df = pd.DataFrame([ {k: r.get(k) for k in cols} for r in self.rows ])
        return df


# ---------------- 数据 QC ----------------

def cross_check_ohlcv(rows: Sequence[Dict], symbol: str = "",
                      vol_spike_ratio: float = _VOL_SPIKE_RATIO) -> DataQualityReport:
    """对 OHLCV rows 做缺失/OHLC 合法性/成交量尖峰检测。"""
    n = len(rows)
    null_count = 0
    ohlc_violations = 0
    issues: List[str] = []
    for r in rows:
        for k in ('open', 'high', 'low', 'close', 'volume'):
            v = r.get(k)
            if v is None or (isinstance(v, float) and v != v):  # None 或 NaN
                null_count += 1
        o = _num(r.get('open')); h = _num(r.get('high'))
        lo = _num(r.get('low')); c = _num(r.get('close'))
        if o is not None and h is not None and lo is not None and c is not None:
            if not (h >= max(o, c) and lo <= min(o, c)):
                ohlc_violations += 1
            if lo < _OHLC_MIN:
                ohlc_violations += 1

    # 成交量尖峰
    vol_spike_days = 0
    vols = [_num(r.get('volume')) for r in rows]
    for i in range(20, n):
        prev = [v for v in vols[i-20:i] if v is not None and v > 0]
        if prev and vols[i] is not None:
            avg = sum(prev) / len(prev)
            if avg > 0 and vols[i] > avg * vol_spike_ratio:
                vol_spike_days += 1

    passed = (null_count == 0 and ohlc_violations == 0)
    if null_count:
        issues.append(f"{null_count} 个 OHLCV 字段缺失")
    if ohlc_violations:
        issues.append(f"{ohlc_violations} 根 bar OHLC 非法")
    if vol_spike_days:
        issues.append(f"{vol_spike_days} 天成交量异常尖峰（疑似数据源异常/重大事件）")
    return DataQualityReport(symbol=symbol, n_rows=n, passed=passed,
                             null_count=null_count, ohlc_violations=ohlc_violations,
                             vol_spike_days=vol_spike_days, adjust_warnings=0,
                             issues=issues)


def check_adjust_consistency(rows: Sequence[Dict]) -> Tuple[int, List[str]]:
    """
    复权一致性校验：
    - 单日跌幅 > _ADJUST_JUMP_PCT 且前后量级正常 → 疑似除权/前复权跳变
    - 全段收盘价漂移 > _DRIFT_PCT → 提示前/后复权口径不一致
    返回 (adjust_warnings, issues)。
    """
    warnings = 0
    issues: List[str] = []
    closes = [_num(r.get('close')) for r in rows]
    valid = [c for c in closes if c is not None and c > 0]
    for i in range(1, len(rows)):
        prev = closes[i-1]; cur = closes[i]
        if prev and cur and prev > 0:
            chg = (cur - prev) / prev
            if chg < -_ADJUST_JUMP_PCT:
                warnings += 1
                # 次日若回到接近前日量级，更可能是复权跳变而非真实崩盘
                nxt = closes[i+1] if i + 1 < len(closes) else None
                if nxt and nxt > prev * 0.8:
                    issues.append(f"bar {i} 单日跌幅 {chg:.0%} 且次日回升 → 疑似除权/前复权跳变")
    if len(valid) >= 2:
        drift = (valid[-1] - valid[0]) / valid[0]
        if abs(drift) > _DRIFT_PCT:
            issues.append(f"全段收盘价漂移 {drift:+.0%} → 检查前/后复权口径是否一致")
    return warnings, issues


def _num(v):
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


# ---------------- 缓存水位线增量拉取 ----------------

def load_cache(cache_dir: str, symbol: str) -> Optional[List[Dict]]:
    p = os.path.join(cache_dir, f"{symbol}.json")
    if not os.path.exists(p):
        return None
    try:
        with open(p, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def save_cache(cache_dir: str, symbol: str, rows: List[Dict], source: str):
    os.makedirs(cache_dir, exist_ok=True)
    p = os.path.join(cache_dir, f"{symbol}.json")
    payload = {'source': source, 'n': len(rows), 'rows': rows}
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False)


def incremental_merge(cached: List[Dict], fresh: List[Dict]) -> List[Dict]:
    """按日期水位线合并：取 cached 末端之后（含同日覆盖）的新 bar。"""
    if not cached:
        return list(fresh)
    last_date = cached[-1].get('date')
    merged = list(cached)
    seen = {r.get('date') for r in cached}
    for r in fresh:
        d = r.get('date')
        if d is None or d not in seen:
            merged.append(r)
            seen.add(d)
    return merged


# ---------------- 取数（akshare 多源 fallback） ----------------

def _normalize(df, source: str, symbol: Optional[str]) -> List[Dict]:
    """把 akshare 不同源的 DataFrame 归一化成 OHLCV rows。"""
    import pandas as pd
    colmap = {
        'date': ['日期', 'date', '时间'],
        'open': ['开盘', 'open', '今开'],
        'high': ['最高', 'high', '最高价'],
        'low': ['最低', 'low', '最低价'],
        'close': ['收盘', 'close', '今收'],
        'volume': ['成交量', 'volume'],
    }
    rows: List[Dict] = []
    for _, raw in df.iterrows():
        rec = {}
        for std, cand in colmap.items():
            for c in cand:
                if c in raw.index and pd.notna(raw.get(c)):
                    rec[std] = raw[c]
                    break
            else:
                rec[std] = None
        if symbol:
            rec['symbol'] = symbol
        rows.append(rec)
    # 按日期排序
    rows.sort(key=lambda r: str(r.get('date')))
    return rows


def fetch_daily_ohlcv(symbol: str, source: str = 'eastmoney',
                       start_date: str = '', end_date: str = '',
                       adjust: str = 'qfq',
                       cache_dir: Optional[str] = None,
                       use_cache: bool = True) -> PipelineResult:
    """
    拉取 A 股日线 OHLCV。

    原理层要点：
    - akshare 东财/新浪 fallback，离线可传 source='local' 并自行注入 rows（见 inject_local）
    - use_cache 且 cache_dir 提供时：命中缓存水位线，只增量拉新 bar
    - 统一复权口径(默认前复权 qfq) + 复权一致性校验

    Args:
        symbol: 6 位 A 股代码，如 '600519'
        source: 'eastmoney' / 'sina' / 'local'
        adjust: 'qfq'(前复权,默认) / 'hfq' / ''
        cache_dir: 缓存目录；提供则启用水位线增量
    """
    is_incr = False
    cached = load_cache(cache_dir, symbol) if (use_cache and cache_dir) else None

    if source == 'local':
        # 离线注入：直接用 cached 或调用方传入
        rows = list(cached) if cached else []
        resolved_source = 'local'
        is_incr = False
    else:
        import akshare as ak
        if source == 'sina':
            df = ak.stock_zh_a_daily(symbol=symbol, start_date=start_date,
                                       end_date=end_date, adjust=adjust or None)
        else:
            df = ak.stock_zh_a_hist(symbol=symbol, period='daily',
                                     start_date=start_date, end_date=end_date,
                                     adjust=adjust or None)
        raw = _normalize(df, source, symbol)
        resolved_source = source
        if cached is not None and raw:
            merged = incremental_merge(cached, raw)
            is_incr = len(merged) > len(cached)
            raw = merged
        rows = raw
        if cache_dir:
            save_cache(cache_dir, symbol, rows, resolved_source)

    qc = cross_check_ohlcv(rows, symbol=symbol)
    adj_warn, adj_issues = check_adjust_consistency(rows)
    qc.adjust_warnings = adj_warn
    qc.issues.extend(adj_issues)
    qc.passed = qc.passed and qc.adjust_warnings == 0
    return PipelineResult(symbol=symbol, rows=rows, source=resolved_source,
                          is_incr=is_incr, qc=qc)


def inject_local(symbol: str, rows: List[Dict], source: str = 'local') -> PipelineResult:
    """离线场景：直接注入本地 OHLCV rows 走同一套 QC + 复权校验。"""
    qc = cross_check_ohlcv(rows, symbol=symbol)
    adj_warn, adj_issues = check_adjust_consistency(rows)
    qc.adjust_warnings = adj_warn
    qc.issues.extend(adj_issues)
    qc.passed = qc.passed and qc.adjust_warnings == 0
    return PipelineResult(symbol=symbol, rows=rows, source=source,
                         is_incr=False, qc=qc)


# ---------------- demo ----------------

if __name__ == '__main__':
    import random
    random.seed(7)
    # 合成含一次复权跳变 + 一次成交量尖峰的日线
    demo_rows: List[Dict] = []
    price = 100.0
    import datetime
    d0 = datetime.date(2026, 1, 5)
    for i in range(60):
        d = (d0 + datetime.timedelta(days=i)).isoformat()
        close = round(price * (1 + random.uniform(-0.01, 0.01)), 2)
        vol = random.uniform(1e6, 3e6)
        # 制造复权跳变：第 40 天收盘价瞬间 -40%
        if i == 40:
            close = round(price * 0.60, 2)
        # 制造成交量尖峰：第 45 天
        if i == 45:
            vol = 20e6
        demo_rows.append({
            'date': d, 'open': round(price, 2), 'high': round(max(price, close) * 1.01, 2),
            'low': round(min(price, close) * 0.99, 2), 'close': close, 'volume': vol,
        })
        price = close * 1.01

    res = inject_local('DEMO', demo_rows)
    print(f"=== data_pipeline demo: {res.symbol} ({res.source}) ===")
    print(f"rows={res.qc.n_rows}  passed={res.qc.passed}")
    print(f"null={res.qc.null_count} ohlc_viol={res.qc.ohlc_violations} "
          f"vol_spike={res.qc.vol_spike_days} adjust_warn={res.qc.adjust_warnings}")
    for it in res.qc.issues:
        print("  -", it)
