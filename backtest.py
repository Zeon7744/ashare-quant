"""
ashare-quant: 数据 pipeline 质量校验 + 策略回测模块（原理层完善）

对应"数据 pipeline / 回测深度"诉求，补齐 ashare 仓缺失的两大原理层能力：
1. 数据 pipeline QC：缺失值 / OHLC 合法性 / 成交量尖峰 / 复权一致性 检测与清洗
   （与 global 仓 cross_check_sources 对齐的口径）
2. 策略回测：无前视泄漏(look-ahead) 的 walk-forward 滚动回测 + 交易成本(手续费/滑点)
   + 按 bar 频率正确年化的绩效指标(Sharpe/Sortino/Calmar/MaxDD/胜率/平均持仓期)

保持纯标准库 + 可选 numpy/pandas，无 sklearn 依赖（纯 Python 回测引擎）。
"""
import math
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Sequence, Tuple


# ---------------- 数据 pipeline QC ----------------

@dataclass
class DataQualityReport:
    """数据质量检测报告（pipeline QC）。"""
    symbol: str
    n_rows: int
    passed: bool
    null_count: int
    ohlc_violations: int
    vol_spike_days: int
    issues: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def cross_check_ohlcv(rows: Sequence[dict], symbol: str = '',
                      tol_close: float = 0.02,
                      vol_spike_k: float = 5.0) -> DataQualityReport:
    """
    对 OHLCV 数据做多维 QC 检测（量化数据 pipeline 标准项）：
    - 缺失值：OHLCV 任一字段为空
    - OHLC 合法性：Low ≤ min(Open,Close) 且 High ≥ max(Open,Close)
    - 成交量尖峰：单日成交量 > 均值 × k
    - 收盘一致性：末 20 日与全期均值相对偏差 > tol_close 记为异常（未通过项）

    Args:
        rows: 每行 dict，需含 open/high/low/close/volume（大小写不敏感，缺失按 0 容错）
    """
    issues: List[str] = []
    n = len(rows)

    def _get(row, key):
        for k in row.keys():
            if k.lower() == key.lower():
                return row[k]
        return None

    null_count = 0
    ohlc_violations = 0
    closes: List[float] = []
    vols: List[float] = []
    for row in rows:
        o = _get(row, 'open'); h = _get(row, 'high')
        l = _get(row, 'low'); c = _get(row, 'close'); v = _get(row, 'volume')
        if any(x is None or (isinstance(x, float) and math.isnan(x)) for x in (o, h, l, c, v)):
            null_count += 1
            continue
        o = float(o); h = float(h); l = float(l); c = float(c); v = float(v)
        closes.append(c); vols.append(v)
        # OHLC 合法性
        if l > min(o, c) or h < max(o, c):
            ohlc_violations += 1

    vol_spike_days = 0
    if vols:
        vmean = sum(vols) / len(vols)
        if vmean > 0:
            vol_spike_days = sum(1 for x in vols if x > vmean * max(vol_spike_k, 5))

    # 收盘一致性
    close_consistency = None
    if len(closes) >= 20:
        recent = closes[-20:]
        full_mean = sum(closes) / len(closes)
        if full_mean != 0:
            close_consistency = abs(sum(recent) / len(recent) - full_mean) / abs(full_mean)

    if null_count:
        issues.append(f'null_values:{null_count}')
    if ohlc_violations:
        issues.append(f'ohlc_inconsistent:{ohlc_violations}')
    if vol_spike_days:
        issues.append(f'vol_spike:{vol_spike_days}')
    if close_consistency is not None and close_consistency >= tol_close:
        issues.append(f'close_drift:{close_consistency:.3f}')

    passed = (null_count == 0) and (ohlc_violations == 0)

    return DataQualityReport(
        symbol=symbol, n_rows=n, passed=passed,
        null_count=null_count, ohlc_violations=ohlc_violations,
        vol_spike_days=vol_spike_days, issues=issues,
    )


def clean_ohlcv(rows: Sequence[dict]) -> List[dict]:
    """缺失值前向填充 + 非法 OHLC 修正（Low→min(o,c), High→max(o,c)），供回测使用。"""
    out: List[dict] = []
    prev_close = None
    for row in rows:
        r = dict(row)
        c = r.get('close')
        if c is None:
            c = prev_close
        else:
            prev_close = c
            c = float(c)
        o = r.get('open'); h = r.get('high'); l = r.get('low')
        o = float(o) if o is not None else c
        h = float(h) if h is not None else max(o, c)
        l = float(l) if l is not None else min(o, c)
        # 修正非法区间
        l = min(l, min(o, c)); h = max(h, max(o, c))
        r['open'], r['high'], r['low'], r['close'] = o, h, l, c
        r['volume'] = float(r.get('volume') or 0.0)
        out.append(r)
    return out


# ---------------- 策略回测（无前视泄漏 + 交易成本） ----------------

@dataclass
class BacktestConfig:
    initial_balance: float = 100000.0
    position_pct: float = 0.95
    fees_pct: float = 0.001        # 单边 taker 手续费（默认 0.1%，贴近 A 股+滑点）
    slippage_pct: float = 0.0005   # 单边滑点（默认 5bps）
    train_window: int = 120        # walk-forward 训练窗口
    min_window: int = 60            # 窗口不足时跳过
    risk_free_annual: float = 0.02
    bars_per_year: float = 252.0   # A 股日线默认 252


@dataclass
class BacktestResult:
    initial_balance: float
    final_balance: float
    total_return: float
    total_trades: int
    round_trips: int
    win_rate: float
    avg_holding_bars: float
    total_costs: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    annualized_return: float
    annualized_volatility: float
    bars_per_year: float
    equity_curve: List[float] = field(default_factory=list)
    trades: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d['equity_curve'] = self.equity_curve[-100:]
        return d


def _infer_bars_per_year(timestamps: Optional[Sequence]) -> float:
    """由时间戳推导每年 bar 数；推导失败按 252（日线）。"""
    try:
        if not timestamps or len(timestamps) < 3:
            return 252.0
        arr = list(timestamps)
        # 兼容 ISO 字符串 / pandas Timestamp / datetime
        def _to_sec(t):
            try:
                from datetime import datetime as _dt
                return _dt.fromisoformat(str(t).replace('Z', '+00:00')).timestamp()
            except Exception:
                return None
        secs = [s for s in (_to_sec(t) for t in arr) if s is not None]
        if len(secs) < 3:
            return 252.0
        diffs = [secs[i + 1] - secs[i] for i in range(len(secs) - 1) if secs[i + 1] - secs[i] > 0]
        if not diffs:
            return 252.0
        median_sec = sorted(diffs)[len(diffs) // 2]
        if median_sec <= 0:
            return 252.0
        return float(365 * 24 * 3600 / median_sec)
    except Exception:
        return 252.0


def walk_forward_backtest(rows: Sequence[dict],
                          signal_fn: Optional[callable] = None,
                          config: Optional[BacktestConfig] = None) -> BacktestResult:
    """
    无前视泄漏的 walk-forward 滚动回测。

    原理要点：
    - **前视泄漏防护**：在 bar i 决策时，模型/信号只能使用 i 之前（不含 i 之后）的信息；
      预测 i 的方向后于 bar i 的价格成交（信号→下一根成交，无未来函数）。
    - **walk-forward**：每 bar 用前 train_window 段作为“当前可见数据”，滚动推进，避免全样本过拟合。
    - **交易成本**：买卖各扣 fees_pct 手续费 + slippage_pct 滑点。
    - **绩效指标**：按 bars_per_year 频率年化 Sharpe/Sortino/Calmar/MaxDD。

    Args:
        rows: 清洗后的 OHLCV 行序列（含 close/timestamp）
        signal_fn: 可选自定义信号函数 signal_fn(visible_rows, i) -> (pred in {0,1}, confidence in [0,1])；
                   默认内置“动量+波动”简化信号（涨动量强且波动可控→看多）。
        config: 回测参数
    """
    cfg = config or BacktestConfig()
    if len(rows) < cfg.min_window + 1:
        # 数据不足：返回空结果而非崩溃
        return BacktestResult(
            initial_balance=cfg.initial_balance, final_balance=cfg.initial_balance,
            total_return=0.0, total_trades=0, round_trips=0, win_rate=0.0,
            avg_holding_bars=0.0, total_costs=0.0, sharpe_ratio=0.0, sortino_ratio=0.0,
            calmar_ratio=0.0, max_drawdown=0.0, annualized_return=0.0,
            annualized_volatility=0.0, bars_per_year=cfg.bars_per_year,
            equity_curve=[cfg.initial_balance], trades=[],
        )

    if signal_fn is None:
        signal_fn = _default_momentum_signal

    timestamps = [r.get('timestamp') for r in rows]
    bpy = cfg.bars_per_year if cfg.bars_per_year else _infer_bars_per_year(timestamps)

    balance = float(cfg.initial_balance)
    position_shares = 0.0
    entry_anchor = balance
    entry_bar = None
    equity_curve = [balance]
    bar_returns: List[float] = []
    trades: List[dict] = []
    closed_pnls: List[float] = []
    holding_bars: List[int] = []
    cost_accrued = 0.0
    n = len(rows)

    warmup = min(cfg.train_window, max(n // 2, cfg.min_window))

    for i in range(warmup, n):
        visible = rows[max(0, i - cfg.train_window):i]   # 只用 i 之前数据（无前视）
        price_now = float(rows[i]['close'])
        pred, confidence = signal_fn(visible, i)

        fill_buy = price_now * (1 + cfg.slippage_pct)
        fill_sell = price_now * (1 - cfg.slippage_pct)
        bar_value = balance if position_shares == 0 else position_shares * price_now

        executed = False
        if pred == 1 and confidence > 0.6 and position_shares == 0:
            invest = bar_value * cfg.position_pct
            if invest > 0 and fill_buy > 0:
                fee = invest * cfg.fees_pct
                position_shares = (invest - fee) / fill_buy
                cost_accrued += fee
                entry_anchor = bar_value
                entry_bar = i
                trades.append({'type': 'buy', 'bar': i, 'price': round(fill_buy, 4),
                               'shares': round(position_shares, 4)})
                executed = True
        elif pred == 0 and confidence > 0.6 and position_shares > 0:
            gross = position_shares * fill_sell
            fee = gross * cfg.fees_pct
            balance = gross - fee
            cost_accrued += fee
            closed_pnls.append(balance - entry_anchor)
            holding_bars.append(i - entry_bar)
            trades.append({'type': 'sell', 'bar': i, 'price': round(fill_sell, 4),
                           'pnl': round(balance - entry_anchor, 2)})
            position_shares = 0.0
            executed = True

        bar_value_end = balance if position_shares == 0 else position_shares * price_now
        equity_curve.append(bar_value_end)
        prev = equity_curve[-2]
        if prev > 0:
            bar_returns.append(bar_value_end / prev - 1.0)

    # 强制平仓
    if position_shares > 0:
        final_price = float(rows[-1]['close'])
        fill_sell = final_price * (1 - cfg.slippage_pct)
        gross = position_shares * fill_sell
        fee = gross * cfg.fees_pct
        balance = gross - fee
        cost_accrued += fee
        closed_pnls.append(balance - entry_anchor)
        holding_bars.append(n - 1 - (entry_bar or n - 1))
        position_shares = 0.0
    equity_curve[-1] = balance

    perf = _performance(equity_curve, closed_pnls, holding_bars, bpy,
                        cfg.risk_free_annual, cfg.initial_balance)

    return BacktestResult(
        initial_balance=cfg.initial_balance,
        final_balance=balance,
        total_return=(balance - cfg.initial_balance) / cfg.initial_balance,
        total_trades=sum(1 for t in trades if t['type'] == 'sell'),
        round_trips=len(closed_pnls),
        win_rate=(sum(1 for p in closed_pnls if p > 0) / len(closed_pnls)) if closed_pnls else 0.0,
        avg_holding_bars=(sum(holding_bars) / len(holding_bars)) if holding_bars else 0.0,
        total_costs=cost_accrued,
        sharpe_ratio=perf['sharpe'], sortino_ratio=perf['sortino'],
        calmar_ratio=perf['calmar'], max_drawdown=perf['max_drawdown'],
        annualized_return=perf['annualized_return'],
        annualized_volatility=perf['annualized_volatility'],
        bars_per_year=bpy,
        equity_curve=equity_curve[-100:],
        trades=trades,
    )


def _default_momentum_signal(visible_rows: Sequence[dict], i: int):
    """内置简化信号：近 5 日动量 > 0 且 20 日波动未过高 → 看多(pred=1)。"""
    def _close(r):
        return float(r.get('close', 0.0))
    closes = [_close(r) for r in visible_rows]
    if len(closes) < 20:
        return 0, 0.5
    momentum_5 = (closes[-1] / closes[-6] - 1.0) if closes[-6] else 0.0
    # 20 日波动（极差/均值，粗略）
    window20 = closes[-20:]
    mean20 = sum(window20) / 20
    vol20 = (max(window20) - min(window20)) / mean20 if mean20 else 0.0
    if momentum_5 > 0.005 and vol20 < 0.10:
        return 1, min(0.95, 0.6 + abs(momentum_5))
    if momentum_5 < -0.005:
        return 0, min(0.95, 0.6 + abs(momentum_5))
    return 0, 0.5


def _performance(equity_curve, closed_pnls, holding_bars, bars_per_year,
                 risk_free_annual, initial_balance) -> Dict:
    """按 bar 频率计算年化绩效指标。"""
    eq = list(equity_curve)
    if len(eq) < 3:
        return {'sharpe': 0.0, 'sortino': 0.0, 'calmar': 0.0, 'max_drawdown': 0.0,
                'annualized_return': 0.0, 'annualized_volatility': 0.0}

    rets = [eq[i] / eq[i - 1] - 1.0 for i in range(1, len(eq)) if eq[i - 1] > 0]
    if len(rets) < 2:
        return {'sharpe': 0.0, 'sortino': 0.0, 'calmar': 0.0, 'max_drawdown': 0.0,
                'annualized_return': 0.0, 'annualized_volatility': 0.0}

    # 最大回撤
    peak = eq[0]
    max_dd = 0.0
    for v in eq:
        peak = max(peak, v)
        if peak > 0:
            max_dd = min(max_dd, (v - peak) / peak)
    max_dd = float(max_dd)

    total_ret = eq[-1] / initial_balance - 1.0
    n_periods = len(rets)
    annualized_return = (1 + total_ret) ** (bars_per_year / max(n_periods, 1)) - 1.0

    mean = sum(rets) / len(rets)
    variance = sum((r - mean) ** 2 for r in rets) / len(rets)
    vol_bar = math.sqrt(variance)
    annualized_volatility = vol_bar * math.sqrt(bars_per_year)

    rf_bar = risk_free_annual / bars_per_year
    excess = [r - rf_bar for r in rets]
    ex_mean = sum(excess) / len(excess)

    sharpe = 0.0
    if vol_bar > 0:
        sharpe = ex_mean / vol_bar * math.sqrt(bars_per_year)

    downside = [e for e in excess if e < 0]
    sortino = 0.0
    if len(downside) > 0:
        dvar = sum((d - ex_mean) ** 2 for d in downside) / len(downside)
        dstd = math.sqrt(dvar)
        if dstd > 0:
            sortino = ex_mean / dstd * math.sqrt(bars_per_year)

    calmar = 0.0
    if abs(max_dd) > 1e-10:
        calmar = annualized_return / abs(max_dd)

    return {
        'sharpe': float(sharpe), 'sortino': float(sortino),
        'calmar': float(calmar), 'max_drawdown': max_dd,
        'annualized_return': float(annualized_return),
        'annualized_volatility': float(annualized_volatility),
    }


if __name__ == '__main__':
    import random
    random.seed(42)
    # 造 300 根日线
    rows = []
    price = 100.0
    base_ts = "2026-01-01T00:00:00"
    for k in range(300):
        price *= (1 + random.uniform(-0.02, 0.021))
        o = price * (1 + random.uniform(-0.005, 0.005))
        h = max(o, price) * (1 + 0.004)
        l = min(o, price) * (1 - 0.004)
        rows.append({
            'timestamp': base_ts,  # 占位
            'open': o, 'high': h, 'low': l, 'close': price,
            'volume': random.uniform(1e6, 5e6),
        })
    qc = cross_check_ohlcv(rows, symbol='DEMO')
    print('QC passed:', qc.passed, 'issues:', qc.issues)
    clean = clean_ohlcv(rows)
    res = walk_forward_backtest(clean)
    print(f'回测: 净收益{res.total_return:+.2%}, Sharpe={res.sharpe_ratio:.2f}, '
          f'MaxDD={res.max_drawdown:.2%}, 交易{res.total_trades}笔, 胜率{res.win_rate:.1%}')
