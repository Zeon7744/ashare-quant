"""
ashare-quant: 市场状态检测（Regime Detection）

基于波动率、动量、成交量三维判定 A 股市场状态：
- 牛市（BULL）：波动率低 + 趋势向上 + 成交量放大
- 熊市（BEAR）：波动率高 + 趋势向下 + 成交量萎缩
- 震荡（RANGE）：波动率中等 + 无明显趋势
- 过渡（TRANSITION）：状态切换期

输出 RegimeReport，供 backtest.py / ashare_agent.py 状态感知调用。
"""
import json
import math
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Sequence
from enum import Enum


class Regime(Enum):
    BULL = "bull"
    BEAR = "bear"
    RANGE = "range"
    TRANSITION = "transition"


@dataclass
class VolatilitySignal:
    """波动率信号"""
    realized_vol: float          # 年化波动率（%）
    vol_regime: str              # low/medium/high
    vol_trend: str               # rising/falling/stable


@dataclass
class MomentumSignal:
    """动量信号"""
    mom_20: float                # 20 日动量（%）
    mom_60: float                # 60 日动量（%）
    trend: str                   # up/down/sideways


@dataclass
class VolumeSignal:
    """成交量信号"""
    vol_ratio_20: float          # 当前成交量 / 20 日均量
    vol_regime: str              # expanding/contracting/neutral


@dataclass
class RegimeReport:
    """市场状态报告"""
    symbol: str
    date: str
    regime: Regime
    confidence: float            # 0-1
    bull_score: float            # 0-1
    bear_score: float            # 0-1
    range_score: float           # 0-1
    signals: Dict[str, any]
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d['regime'] = self.regime.value
        return d

    def is_bullish(self) -> bool:
        return self.regime == Regime.BULL and self.confidence > 0.6

    def is_bearish(self) -> bool:
        return self.regime == Regime.BEAR and self.confidence > 0.6


def calc_realized_vol(prices: Sequence[float], period: int = 20) -> float:
    """计算年化波动率（%）"""
    if len(prices) < period + 1:
        return 0.0
    returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(-period, 0)]
    if not returns or all(r == 0 for r in returns):
        return 0.0
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    daily_vol = math.sqrt(variance)
    return daily_vol * math.sqrt(252) * 100  # 转年化百分比


def classify_vol(vol: float) -> str:
    if vol < 20:
        return "low"
    elif vol < 40:
        return "medium"
    else:
        return "high"


def calc_momentum(prices: Sequence[float], window: int) -> float:
    if len(prices) < window:
        return 0.0
    return (prices[-1] - prices[-window]) / prices[-window] * 100


def classify_trend(mom: float) -> str:
    if mom > 5:
        return "up"
    elif mom < -5:
        return "down"
    else:
        return "sideways"


def detect_regime(
    prices: Sequence[float],
    volumes: Optional[Sequence[float]] = None,
    symbol: str = "UNKNOWN",
    date: str = ""
) -> RegimeReport:
    """
    主检测函数：基于三维信号判定市场状态
    
    Args:
        prices: 收盘价序列（最新在前）
        volumes: 成交量序列（可选）
        symbol: 标的代码
        date: 检测日期
    
    Returns:
        RegimeReport
    """
    if len(prices) < 60:
        return RegimeReport(
            symbol=symbol, date=date, regime=Regime.TRANSITION,
            confidence=0.0, bull_score=0.5, bear_score=0.5, range_score=0.5,
            signals={}, notes=["数据不足，无法检测"]
        )
    
    # 波动率信号
    vol_20 = calc_realized_vol(prices[-20:]) if len(prices) >= 20 else 0
    vol_signal = VolatilitySignal(
        realized_vol=vol_20,
        vol_regime=classify_vol(vol_20),
        vol_trend="stable"
    )
    
    # 动量信号
    mom_20 = calc_momentum(prices, 20)
    mom_60 = calc_momentum(prices, 60)
    mom_signal = MomentumSignal(
        mom_20=mom_20, mom_60=mom_60,
        trend=classify_trend(max(mom_20, mom_60))
    )
    
    # 成交量信号
    vol_signal_obj = VolumeSignal(vol_ratio_20=1.0, vol_regime="neutral")
    if volumes and len(volumes) >= 20:
        avg_vol_20 = sum(volumes[-21:-1]) / 20
        curr_vol = volumes[-1]
        ratio = curr_vol / avg_vol_20 if avg_vol_20 > 0 else 1.0
        vol_signal_obj = VolumeSignal(
            vol_ratio_20=ratio,
            vol_regime="expanding" if ratio > 1.5 else ("contracting" if ratio < 0.7 else "neutral"),
        )
    
    # 综合评分
    bull_score = 0.0
    bear_score = 0.0
    range_score = 0.0
    notes = []
    
    # 波动率贡献
    if vol_signal.vol_regime == "low":
        bull_score += 0.3
    elif vol_signal.vol_regime == "high":
        bear_score += 0.3
    else:
        range_score += 0.2
    
    # 动量贡献
    if mom_signal.trend == "up":
        bull_score += 0.4
        notes.append("趋势向上")
    elif mom_signal.trend == "down":
        bear_score += 0.4
        notes.append("趋势向下")
    else:
        range_score += 0.3
        notes.append("无明显趋势")
    
    # 成交量贡献
    if vol_signal_obj.vol_regime == "expanding" and mom_signal.trend == "up":
        bull_score += 0.2
        notes.append("放量上涨")
    elif vol_signal_obj.vol_regime == "contracting" and mom_signal.trend == "down":
        bear_score += 0.2
        notes.append("缩量下跌")
    else:
        range_score += 0.1
    
    # 判定状态
    max_score = max(bull_score, bear_score, range_score)
    if max_score == bull_score and bull_score >= 0.6:
        regime = Regime.BULL
    elif max_score == bear_score and bear_score >= 0.6:
        regime = Regime.BEAR
    elif max_score == range_score and range_score >= 0.4:
        regime = Regime.RANGE
    else:
        regime = Regime.TRANSITION
    
    confidence = max_score
    
    return RegimeReport(
        symbol=symbol, date=date, regime=regime,
        confidence=confidence, bull_score=bull_score,
        bear_score=bear_score, range_score=range_score,
        signals={
            "volatility": vol_signal.to_dict() if hasattr(vol_signal, 'to_dict') else vars(vol_signal),
            "momentum": vars(mom_signal),
            "volume": vars(vol_signal_obj),
        },
        notes=notes
    )
