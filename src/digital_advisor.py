# -*- coding: utf-8 -*-
"""
数字投顾主模块 - A股选股推荐与每日简报

合规要点（证券法第172条）：
  - 必须有免责声明："不构成投资建议"
  - 不得承诺收益
  - 高风险产品需风险测评
  - 模拟数据与真实数据明确区分
"""

from __future__ import annotations

import time
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# 导入 ashare-quant 核心模块
from ashare_agent import AShareAgent, StockSignal


DISCLAIMER = """
⚠️ 免责声明：本内容仅为AI辅助分析工具输出，不构成任何投资建议。
股市有风险，投资需谨慎。过往业绩不代表未来表现。
请根据自身风险承受能力独立决策。——不构成投资建议
"""


@dataclass
class AdvisorRecommendation:
    """数字投顾推荐记录"""
    rec_id: str
    stock_code: str
    stock_name: str
    action: str            # BUY / SELL / HOLD
    reason: str
    confidence: float
    risk_level: str        # low / medium / high
    disclaimer_included: bool = True
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rec_id": self.rec_id,
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "action": self.action,
            "reason": self.reason,
            "confidence": round(self.confidence, 2),
            "risk_level": self.risk_level,
            "disclaimer_included": self.disclaimer_included,
            "generated_at": self.generated_at,
        }


class DigitalAdvisorTool:
    """
    数字投顾工具类。

    核心功能：
    - Mock数据演示选股（3只股票推荐）
    - 风险预警提示
    - 每日简报生成
    - 免责声明强制注入

    注意：所有输出均含免责声明，不构成投资建议。
    """

    # Mock股票池（A股知名标的）
    MOCK_STOCKS = [
        {"code": "600519.XSHG", "name": "贵州茅台", "price": 1850.0},
        {"code": "000858.XSHE", "name": "五粮液",   "price": 280.0},
        {"code": "300750.XSHE", "name": "宁德时代", "price": 150.0},
        {"code": "601318.XSHG", "name": "中国平安", "price": 52.0},
        {"code": "000001.XSHE", "name": "平安银行", "price": 12.0},
        {"code": "600036.XSHG", "name": "招商银行", "price": 35.0},
        {"code": "002594.XSHE", "name": "比亚迪",   "price": 260.0},
        {"code": "601012.XSHG", "name": "隆基绿能", "price": 28.0},
    ]

    def __init__(self, agent: Optional[AShareAgent] = None):
        self._agent = agent or AShareAgent(initial_cash=100000.0)
        self._recommendations: List[AdvisorRecommendation] = []

    # ------------------------------------------------------------------
    # 核心接口
    # ------------------------------------------------------------------
    def pick_stocks(self, count: int = 3) -> Dict[str, Any]:
        """
        数字人选股：基于Mock数据推荐指定数量股票。

        Args:
            count: 推荐数量，默认3只

        Returns:
            推荐列表（含免责声明）
        """
        if count < 1 or count > len(self.MOCK_STOCKS):
            count = min(3, len(self.MOCK_STOCKS))

        random.seed(int(time.time()) % 10000)
        selected = random.sample(self.MOCK_STOCKS, k=count)
        recs: List[Dict[str, Any]] = []

        for stock in selected:
            code = stock["code"]
            price = stock["price"]
            # 使用MLP预测器生成信号
            signal = self._agent.analyze(
                stock_code=code,
                price=price,
                momentum_5d=random.uniform(-0.05, 0.08),
                momentum_20d=random.uniform(-0.03, 0.05),
                volume_ratio=random.uniform(0.5, 2.5),
                rsi_14=random.uniform(25.0, 75.0),
                macd_signal=random.uniform(-0.02, 0.02),
                volatility_20d=random.uniform(0.01, 0.04),
                support_proximity=random.uniform(0.3, 0.8),
                resistance_proximity=random.uniform(0.2, 0.7),
            )
            rec = AdvisorRecommendation(
                rec_id=f"REC-{uuid_hash(code)}",
                stock_code=code,
                stock_name=stock["name"],
                action=signal.signal,
                reason=signal.reason,
                confidence=signal.confidence,
                risk_level=self._risk_level(signal.confidence, signal.signal),
            )
            self._recommendations.append(rec)
            recs.append(rec.to_dict())

        return {
            "type": "digital_advisor_recommendation",
            "count": len(recs),
            "recommendations": recs,
            "disclaimer": DISCLAIMER,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "data_type": "mock_data",  # 明确标识为模拟数据
            "warning": "以上为模拟数据演示，不构成投资建议",
        }

    def daily_brief(self) -> Dict[str, Any]:
        """
        每日简报生成（Pro版功能）。

        包含：持仓概览、最新信号、风险提示。
        """
        report = self._agent.report()
        latest_signals = [s.to_dict() for s in self._agent.signals[-5:]]

        return {
            "type": "daily_brief",
            "report": report,
            "latest_signals": latest_signals,
            "disclaimer": DISCLAIMER,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "data_type": "mock_data",
        }

    def get_disclaimer(self) -> str:
        """返回固定免责声明"""
        return DISCLAIMER

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------
    @staticmethod
    def _risk_level(confidence: float, signal: str) -> str:
        """根据信号和置信度估算风险等级"""
        if signal == "SELL" and confidence > 0.7:
            return "medium"
        if signal == "BUY" and confidence > 0.8:
            return "high"  # 高置信买入也需提示风险
        return "low"


def uuid_hash(s: str) -> str:
    """简易哈希，用于生成唯一ID"""
    import hashlib
    return hashlib.md5(s.encode()).hexdigest()[:8]
