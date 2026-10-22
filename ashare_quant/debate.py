"""Bull–bear debate framework.

Given a stock, automatically generate structured bull (看多) and bear (看空)
arguments from quant data (trend, valuation, momentum, position), with a
regime-dependent verdict.

Design goals
------------
- Pure standard library.  No third-party imports.
- Pluggable data layer: accepts pre-computed factor dicts (``bull_points``,
  ``bear_points`` already extracted) OR calls the built-in extractor that
  reads from a saved CSV file (see ``extract_factors``).
- Output is deterministic and machine-readable (JSON-serialisable dict).

Usage (standalone, no network):
    python -m ashare_quant.debate --stock 600519 --csv data/factors.csv

Usage (from code):
    from ashare_quant.debate import generate_debate
    result = generate_debate("600519", factors=...)
    print(result["verdict"])

Usage (via agent):
    from ashare_agent import Agent
    from ashare_quant.debate import generate_debate
    # agent.run() populates agent.factors; pass it to generate_debate
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Pro 门控（可选依赖，不影响核心逻辑）
# ---------------------------------------------------------------------------

def _check_pro_gate() -> None:
    """检查 Free 套餐辩论次数限制；超限打印升级提示并退出。"""
    try:
        from ashare_quant.pro_gates import check_gates
        plan = os.environ.get("ASHARE_PLAN", "free")
        allowed, message = check_gates(plan, "debate")
        if not allowed:
            print(message, file=sys.stderr)
            sys.exit(0)  # 优雅退出，非错误
    except ImportError:
        pass  # pro_gates 未安装时跳过检查

# ---------------------------------------------------------------------------
# Thresholds (match regime.py thresholds, kept inline for stand-alone clarity)
# ---------------------------------------------------------------------------

RSI_STRONG = 55
RSI_WEAK = 45
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
PRICE_DEV_STRONG = 1.05
PRICE_DEV_WEAK = 0.95
MOM120B = 3.0
MOM120S = 0.0
MOM20B = 5.0
MOM20S = -3.0
PERIODE = 100


# ---------------------------------------------------------------------------
# Factor extraction
# ---------------------------------------------------------------------------

def extract_factors(df, code: str) -> Dict[str, Any]:
    """Build a flat factor dict from a DataFrame-like object.

    Expects ``df`` to have these columns (from data_pipeline):
        close_sma20, mom_120, mom_20, rsi_14, atr_14, vol_20,
        per_30m, per_20d, pos_20d, price_pct_252d
    plus optionally ``trend_strength_pct`` (from regime.py)
    and ``sma50_below_sma200_pct``.

    Returns a dict with keys:
        code, close, sma20, mom_120, mom_20, rsi_14, atr_14,
        vol_20, per_30m, pos_252d, trend_strength_pct
    """
    try:
        import pandas as pd  # type: ignore
    except ImportError:
        pd = None

    def _col(name: str, default=None):
        if pd is not None:
            try:
                if name in df.columns:
                    return df[name]
            except Exception:
                pass
        return default

    return {
        "code": code,
        "close": _col("close", _col("close_sma20")),
        "sma20": _col("close_sma20"),
        "mom_120": _col("mom_120"),
        "mom_20": _col("mom_20"),
        "rsi_14": _col("rsi_14"),
        "atr_14": _col("atr_14"),
        "vol_20": _col("vol_20"),
        "per_30m": _col("per_30m"),
        "pos_252d": _col("price_pct_252d"),
        "trend_strength_pct": _col("trend_strength_pct"),
    }


# ---------------------------------------------------------------------------
# Bull / bear point builders
# ---------------------------------------------------------------------------

def _bull_points(f: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return list of bull-argument dicts; empty if no positive signals."""
    pts: List[Dict[str, Any]] = []

    # 1. Trend (price vs SMA20)
    close, sma20 = f.get("close"), f.get("sma20")
    if close is not None and sma20 is not None and sma20 > 0:
        dev = (close - sma20) / sma20
        if dev > 0:
            pts.append({
                "dim": "趋势",
                "point": f"价格高于 SMA20 约 {dev*100:.1f}%",
                "evidence": f"close={close:.2f}, sma20={sma20:.2f}",
            })

    # 2. RSI momentum
    rsi = f.get("rsi_14")
    if rsi is not None:
        if RSI_STRONG <= rsi <= RSI_OVERBOUGHT:
            pts.append({
                "dim": "动量",
                "point": f"RSI {rsi:.1f}，处于强势区间（{RSI_STRONG}–{RSI_OVERBOUGHT}）",
                "evidence": f"rsi_14={rsi}",
            })

    # 3. 120-day momentum
    mom120 = f.get("mom_120")
    if mom120 is not None and mom120 > MOM120B:
        pts.append({
            "dim": "中期动量",
            "point": f"120日动量 {mom120:+.1f}%（>{MOM120B}%，中期趋势走强）",
            "evidence": f"mom_120={mom120:+.2f}",
        })

    # 4. 20-day momentum
    mom20 = f.get("mom_20")
    if mom20 is not None and mom20 > MOM20B:
        pts.append({
            "dim": "短期动量",
            "point": f"20日动量 {mom20:+.1f}%（>{MOM20B}%，短期资金流入明显）",
            "evidence": f"mom_20={mom20:+.2f}",
        })

    # 5. Valuation
    per = f.get("per_30m")
    if per is not None and 0 < per <= PERIODE:
        pts.append({
            "dim": "估值",
            "point": f"30个月 PER {per:.1f}，低于历史均值 100，估值有安全边际",
            "evidence": f"per_30m={per:.1f}",
        })

    # 6. Position in 252-day range
    pos = f.get("pos_252d")
    if pos is not None and pos >= 0.85:
        pts.append({
            "dim": "区间位置",
            "point": f"处于252日区间的 {pos*100:.0f}% 位置（接近历史高点，突破确认）",
            "evidence": f"pos_252d={pos:.2f}",
        })

    # 7. Trend strength (composite)
    ts = f.get("trend_strength_pct")
    if ts is not None and ts > 0:
        pts.append({
            "dim": "趋势强度",
            "point": f"趋势强度 {ts:+.1f}%（SMA20 vs SMA50 多头排列）",
            "evidence": f"trend_strength_pct={ts:+.2f}",
        })

    return pts


def _bear_points(f: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return list of bear-argument dicts; empty if no negative signals."""
    pts: List[Dict[str, Any]] = []

    # 1. Price below SMA20
    close, sma20 = f.get("close"), f.get("sma20")
    if close is not None and sma20 is not None and sma20 > 0:
        dev = (close - sma20) / sma20
        if dev < 0:
            pts.append({
                "dim": "趋势",
                "point": f"价格低于 SMA20 约 {abs(dev)*100:.1f}%，短期趋势偏弱",
                "evidence": f"close={close:.2f}, sma20={sma20:.2f}",
            })

    # 2. RSI weak / overbought
    rsi = f.get("rsi_14")
    if rsi is not None:
        if rsi <= RSI_OVERSOLD:
            pts.append({
                "dim": "动量",
                "point": f"RSI {rsi:.1f}，处于超卖区（<{RSI_OVERSOLD}），持续走弱",
                "evidence": f"rsi_14={rsi}",
            })
        elif rsi >= RSI_OVERBOUGHT:
            pts.append({
                "dim": "动量",
                "point": f"RSI {rsi:.1f}，超买（>{RSI_OVERBOUGHT}），随时可能回调",
                "evidence": f"rsi_14={rsi}",
            })

    # 3. 120-day momentum negative
    mom120 = f.get("mom_120")
    if mom120 is not None and mom120 < MOM120S:
        pts.append({
            "dim": "中期动量",
            "point": f"120日动量 {mom120:+.1f}%（<{MOM120S}%，中期趋势下行）",
            "evidence": f"mom_120={mom120:+.2f}",
        })

    # 4. 20-day momentum weak
    mom20 = f.get("mom_20")
    if mom20 is not None and mom20 < MOM20S:
        pts.append({
            "dim": "短期动量",
            "point": f"20日动量 {mom20:+.1f}%（<{MOM20S}%，短期资金流出）",
            "evidence": f"mom_20={mom20:+.2f}",
        })

    # 5. Valuation high
    per = f.get("per_30m")
    if per is not None and per > PERIODE:
        pts.append({
            "dim": "估值",
            "point": f"30个月 PER {per:.1f}，高于历史均值 100，估值有回落风险",
            "evidence": f"per_30m={per:.1f}",
        })

    # 6. Position near bottom (contrarian buy signal — we flag it as bear)
    pos = f.get("pos_252d")
    if pos is not None and pos <= 0.15:
        pts.append({
            "dim": "区间位置",
            "point": f"处于252日区间的 {pos*100:.0f}% 位置（接近历史低点，持续承压）",
            "evidence": f"pos_252d={pos:.2f}",
        })

    # 7. Volatility high
    vol = f.get("vol_20")
    atr = f.get("atr_14")
    if vol is not None and atr is not None and atr > 0:
        ratio = vol / atr
        if ratio > 2.5:
            pts.append({
                "dim": "波动率",
                "point": f"20日波动率/ATR 比率 {ratio:.1f}，波动异常放大，警惕风险",
                "evidence": f"vol_20={vol}, atr_14={atr}",
            })

    return pts


# ---------------------------------------------------------------------------
# Verdict logic
# ---------------------------------------------------------------------------

def _verdict(bull_pts: List[Dict], bear_pts: List[Dict],
              f: Dict[str, Any]) -> Dict[str, Any]:
    """Combine bull/bear signals into a regime + action verdict."""
    bull_n = len(bull_pts)
    bear_n = len(bear_pts)

    rsi = f.get("rsi_14")
    mom120 = f.get("mom_120")
    mom20 = f.get("mom_20")

    # Regime determination (mirrors regime.py logic)
    if rsi is not None and RSI_STRONG <= rsi <= RSI_OVERBOUGHT:
        regime = "bull"
    elif rsi is not None and RSI_WEAK < rsi < RSI_STRONG:
        regime = "neutral"
    elif rsi is not None and rsi <= RSI_OVERSOLD:
        regime = "bear"
    else:
        regime = "neutral"

    # Override: strong momentum signals can upgrade regime
    if mom120 is not None and mom120 > MOM120B and mom20 is not None and mom20 > MOM20B:
        regime = "bull"
    elif mom120 is not None and mom120 < MOM120S and mom20 is not None and mom20 < MOM20S:
        regime = "bear"

    # Score: bull_pts count - bear_pts count, clipped
    score = max(-10, min(10, bull_n - bear_n + 2))  # +2 bias: bull args are rarer

    # Action mapping
    if regime == "bull" and score >= 3:
        action = "buy_or_add"
    elif regime == "bull" and score >= 1:
        action = "watch"
    elif regime == "bear" and score <= -3:
        action = "reduce_or_avoid"
    elif regime == "bear" and score <= -1:
        action = "watch_bear"
    else:
        action = "hold_or_wait"

    # Confidence heuristic
    confidence = min(1.0, (abs(score) + 1) / 10.0)

    return {
        "regime": regime,
        "score": score,
        "action": action,
        "confidence": round(confidence, 2),
        "bull_count": bull_n,
        "bear_count": bear_n,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_debate(code: str,
                    factors: Optional[Dict[str, Any]] = None,
                    csv_path: Optional[str] = None) -> Dict[str, Any]:
    """Generate a structured bull/bear debate for a stock.

    Parameters
    ----------
    code : str
        Stock code, e.g. ``"600519"``.
    factors : dict, optional
        Pre-computed factor dict (from ``extract_factors`` or a custom source).
        Keys expected: close, sma20, mom_120, mom_20, rsi_14, atr_14,
        vol_20, per_30m, pos_252d, trend_strength_pct.
    csv_path : str, optional
        Path to a CSV file with one row per factor (see ``_load_csv_factors``).

    Returns
    -------
    dict with keys:
        code, bull_points (list), bear_points (list), verdict (dict),
        summary (str)
    """
    if factors is None and csv_path:
        factors = _load_csv_factors(csv_path, code)
    if factors is None:
        # Fall back to deterministic demo factors so the CLI always works offline
        factors = _demo_factors(code)

    bull_pts = _bull_points(factors)
    bear_pts = _bear_points(factors)
    verdict = _verdict(bull_pts, bear_pts, factors)

    # Human-readable summary
    if not bull_pts and not bear_pts:
        summary = f"{code}：无明确多空信号，观望。"
    else:
        bull_str = "、".join(p["point"] for p in bull_pts[:3]) if bull_pts else "无"
        bear_str = "、".join(p["point"] for p in bear_pts[:3]) if bear_pts else "无"
        summary = (f"{code}：多方 {len(bull_pts)} 条 / 空方 {len(bear_pts)} 条；"
                   f"看多 → {bull_str}；看空 → {bear_str}；"
                   f"判定 = {verdict['action']}（{verdict['confidence']:.0%} 置信）")

    return {
        "code": code,
        "bull_points": bull_pts,
        "bear_points": bear_pts,
        "verdict": verdict,
        "summary": summary,
    }


def _load_csv_factors(csv_path: str, code: str) -> Dict[str, Any]:
    """Load factors from a CSV file.

    Expected CSV columns (any subset):
        code, close, sma20, mom_120, mom_20, rsi_14, atr_14,
        vol_20, per_30m, pos_252d, trend_strength_pct

    Falls back to built-in demo data if file not found.
    """
    if not os.path.isfile(csv_path):
        return _demo_factors(code)

    import csv
    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    if not rows:
        return _demo_factors(code)

    # Try to find the row matching code; if not, use last row
    target = None
    for row in rows:
        if row.get("code", "").strip() == code.strip():
            target = row
            break
    if target is None:
        target = rows[-1]

    f: Dict[str, Any] = {}
    for k in ["close", "sma20", "mom_120", "mom_20", "rsi_14",
              "atr_14", "vol_20", "per_30m", "pos_252d", "trend_strength_pct"]:
        v = target.get(k)
        if v is not None and v.strip():
            try:
                f[k] = float(v)
            except ValueError:
                pass
    f["code"] = code
    return f


def _demo_factors(code: str) -> Dict[str, Any]:
    """Return deterministic demo factors (for offline / demo runs)."""
    # Demo factors for 600519 (Kweichow Moutai) — plausible bull case
    if code == "600519":
        return {
            "code": code,
            "close": 1720.0, "sma20": 1650.0,
            "mom_120": 8.2, "mom_20": 3.1,
            "rsi_14": 62.0, "atr_14": 35.0, "vol_20": 60.0,
            "per_30m": 28.0, "pos_252d": 0.91,
            "trend_strength_pct": 4.2,
        }
    # Generic neutral demo
    return {
        "code": code,
        "close": 50.0, "sma20": 50.0,
        "mom_120": 0.0, "mom_20": 0.0,
        "rsi_14": 50.0, "atr_14": 1.0, "vol_20": 1.0,
        "per_30m": 100.0, "pos_252d": 0.50,
        "trend_strength_pct": 0.0,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_debate(result: Dict[str, Any]) -> None:
    """Pretty-print a debate result to stdout."""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, UnicodeEncodeError):
        pass
    code = result["code"]
    v = result["verdict"]
    print("=" * 64)
    print(f"  多空辩论  |  {code}  |  regime={v['regime']}  |  "
          f"action={v['action']}  |  confidence={v['confidence']:.0%}")
    print("=" * 64)
    print(f"\n  🐂  看多理由（{v['bull_count']} 条）")
    for i, p in enumerate(result["bull_points"], 1):
        print(f"    {i}. [{p['dim']}] {p['point']}")
        print(f"         证据: {p['evidence']}")
    print(f"\n  🐻  看空理由（{v['bear_count']} 条）")
    for i, p in enumerate(result["bear_points"], 1):
        print(f"    {i}. [{p['dim']}] {p['point']}")
        print(f"         证据: {p['evidence']}")
    print(f"\n  结论: {result['summary']}")
    print()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="A-share bull-bear debate generator")
    ap.add_argument("--stock", required=True,
                    help="Stock code, e.g. 600519")
    ap.add_argument("--csv", default=None,
                    help="Path to factor CSV (optional; uses demo data if omitted)")
    ap.add_argument("--json", action="store_true",
                    help="Output as JSON instead of formatted text")
    args = ap.parse_args()

    # Pro 门控：Free 超限则提示升级并退出
    _check_pro_gate()

    factors = None
    if args.csv:
        factors = _load_csv_factors(args.csv, args.stock)

    result = generate_debate(args.stock, factors=factors, csv_path=args.csv)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_debate(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
