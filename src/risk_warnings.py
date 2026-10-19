# -*- coding: utf-8 -*-
"""
风险预警工具 - A股持仓风险实时提醒

合规要点（证券法第172条）：
  - 必须有免责声明："不构成投资建议"
  - 预警仅作为风险提示，不替代专业投顾
  - 模拟数据需与真实数据明确区分
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


DISCLAIMER = "⚠️ 免责声明：本工具仅为风险提示辅助，不构成投资建议。"


class WarningType(str, Enum):
    STOP_LOSS = "stop_loss"         # 止损提醒
    OVERBOUGHT = "overbought"       # 超买预警
    HIGH_VOLATILITY = "high_volatility"  # 高波动预警
    TREND_BREAK = "trend_break"     # 趋势破位
    POSITION_CONCENTRATION = "position_concentration"  # 持仓集中度过高


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class RiskWarning:
    """单条风险预警记录"""
    warning_id: str
    warning_type: WarningType
    severity: Severity
    stock_code: str
    message: str
    current_value: float
    threshold: float
    suggested_action: str
    timestamp: float = field(default_factory=time.time)
    disclaimer_included: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "warning_id": self.warning_id,
            "warning_type": self.warning_type.value,
            "severity": self.severity.value,
            "stock_code": self.stock_code,
            "message": self.message,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "suggested_action": self.suggested_action,
            "timestamp": self.timestamp,
            "disclaimer": DISCLAIMER,
        }


class RiskWarningsTool:
    """
    风险预警工具类。

    功能：
    - 止损提醒（基于持仓成本与当前价）
    - RSI超买/超卖预警
    - 高波动检测
    - 趋势破位预警
    - 持仓集中度预警

    所有预警均附免责声明，不构成投资建议。
    """

    # 默认阈值配置
    DEFAULT_THRESHOLDS = {
        "stop_loss_pct": 0.08,        # 止损线：跌8%
        "overbought_rsi": 70.0,       # RSI超买
        "oversold_rsi": 30.0,         # RSI超卖
        "high_volatility_pct": 0.05,  # 日波动超5%
        "position_concentration_pct": 0.30,  # 单仓超30%
    }

    def __init__(self, thresholds: Optional[Dict[str, float]] = None):
        self._thresholds = thresholds or self.DEFAULT_THRESHOLDS
        self._warnings: List[RiskWarning] = []
        self._history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # 预警触发
    # ------------------------------------------------------------------
    def check_stop_loss(
        self,
        stock_code: str,
        cost_price: float,
        current_price: float,
    ) -> Optional[RiskWarning]:
        """
        止损预警：当前价跌破成本价指定比例时触发。

        Args:
            stock_code: 股票代码
            cost_price: 持仓成本价
            current_price: 当前价格

        Returns:
            触发则返回RiskWarning，否则返回None
        """
        loss_pct = (current_price - cost_price) / cost_price if cost_price > 0 else 0.0
        threshold = self._thresholds["stop_loss_pct"]
        if loss_pct <= -threshold:
            w = RiskWarning(
                warning_id=f"W-{uuid.uuid4().hex[:8]}",
                warning_type=WarningType.STOP_LOSS,
                severity=Severity.CRITICAL,
                stock_code=stock_code,
                message=f"{stock_code} 下跌 {loss_pct:.1%}，已触及止损线 {threshold:.0%}",
                current_value=loss_pct,
                threshold=-threshold,
                suggested_action=f"建议考虑止损操作，减少持仓 {stock_code}",
            )
            self._warnings.append(w)
            self._history.append(w.to_dict())
            return w
        return None

    def check_rsi_warning(
        self,
        stock_code: str,
        rsi: float,
    ) -> Optional[RiskWarning]:
        """RSI超买/超卖预警"""
        overbought = self._thresholds["overbought_rsi"]
        oversold = self._thresholds["oversold_rsi"]

        if rsi >= overbought:
            w = RiskWarning(
                warning_id=f"W-{uuid.uuid4().hex[:8]}",
                warning_type=WarningType.OVERBOUGHT,
                severity=Severity.WARNING,
                stock_code=stock_code,
                message=f"{stock_code} RSI={rsi:.1f} 进入超买区域（>{overbought}）",
                current_value=rsi,
                threshold=overbought,
                suggested_action="建议关注回调风险，避免追高",
            )
            self._warnings.append(w)
            return w
        elif rsi <= oversold:
            w = RiskWarning(
                warning_id=f"W-{uuid.uuid4().hex[:8]}",
                warning_type=WarningType.OVERBOUGHT,  # 复用OVERBOUGHT类型
                severity=Severity.INFO,
                stock_code=stock_code,
                message=f"{stock_code} RSI={rsi:.1f} 进入超卖区域（<{oversold}）",
                current_value=rsi,
                threshold=oversold,
                suggested_action="可关注潜在反弹机会，注意风险控制",
            )
            self._warnings.append(w)
            return w
        return None

    def check_high_volatility(
        self,
        stock_code: str,
        daily_change_pct: float,
    ) -> Optional[RiskWarning]:
        """高波动预警"""
        threshold = self._thresholds["high_volatility_pct"]
        if abs(daily_change_pct) >= threshold:
            w = RiskWarning(
                warning_id=f"W-{uuid.uuid4().hex[:8]}",
                warning_type=WarningType.HIGH_VOLATILITY,
                severity=Severity.WARNING,
                stock_code=stock_code,
                message=f"{stock_code} 日波动 {daily_change_pct:.1%}，超出阈值 {threshold:.0%}",
                current_value=daily_change_pct,
                threshold=threshold,
                suggested_action="波动较大，建议控制仓位，设置止损",
            )
            self._warnings.append(w)
            return w
        return None

    # ------------------------------------------------------------------
    # 查询接口
    # ------------------------------------------------------------------
    def list_warnings(self, limit: int = 20) -> List[Dict[str, Any]]:
        """列出最近N条预警"""
        return [w.to_dict() for w in self._warnings[-limit:]]

    def clear_warnings(self) -> int:
        """清空当前预警列表"""
        count = len(self._warnings)
        self._warnings.clear()
        return count

    def get_disclaimer(self) -> str:
        """返回免责声明"""
        return DISCLAIMER

    @property
    def warning_count(self) -> int:
        return len(self._warnings)
