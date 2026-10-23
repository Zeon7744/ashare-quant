"""
ashare-quant: A-Share Quantitative Agent with MLP Prediction
"""
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
import billing

@dataclass
class StockSignal:
    """Trading signal for a single stock."""
    stock_code: str
    signal: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float  # 0.0 - 1.0
    price: float
    timestamp: float
    reason: str

@dataclass
class Portfolio:
    """Portfolio state."""
    cash: float
    positions: Dict[str, float]
    total_value: float
    # 完善：累计已实现盈亏（卖出现金 - 买入成本），供 report/win_rate 使用
    realized_pnl: float = 0.0
    # 修复：_last_prices 此前无定义，仅在 agent.__init__ 里 monkey-patch 注入；
    # 直接构造 Portfolio 调 add_position/remove_position 会 AttributeError。
    # 现作为 dataclass 字段，default_factory 给独立实例兜底。
    _last_prices: Dict[str, float] = field(default_factory=dict)
    
    @property
    def position_count(self):
        return len(self.positions)
    
    def add_position(self, stock_code: str, shares: float, price: float):
        cost = shares * price
        if cost > self.cash:
            return False
        self.cash -= cost
        self.positions[stock_code] = self.positions.get(stock_code, 0) + shares
        self._last_prices[stock_code] = price  # 记最新价
        self.total_value = self.cash + sum(
            self.positions.get(s, 0) * p for s, p in self._last_prices.items()
            if s in self.positions
        )
        return True
    
    def remove_position(self, stock_code: str, shares: float, price: float):
        current = self.positions.get(stock_code, 0)
        if shares > current:
            return False
        sell_cost = shares * self._last_prices.get(stock_code, price)
        realized = shares * price - sell_cost
        self.realized_pnl += realized
        self.cash += shares * price
        self.positions[stock_code] = current - shares
        if self.positions[stock_code] == 0:
            del self.positions[stock_code]
            self._last_prices.pop(stock_code, None)
        self.total_value = self.cash + sum(
            self.positions.get(s, 0) * p for s, p in self._last_prices.items()
            if s in self.positions
        )
        return True

# Simple MLP-inspired prediction model
class MLPPredictor:
    """
    Simplified MLP for A-share price prediction.
    Uses momentum + volume + technical indicators.
    """
    
    def __init__(self, hidden_sizes=(32, 16)):
        self.hidden_sizes = hidden_sizes
        # Simple weights initialized randomly
        import random
        random.seed(42)
        input_size = 8
        self.w1 = [[random.gauss(0, 0.1) for _ in range(input_size)] for _ in range(hidden_sizes[0])]
        self.b1 = [0.0] * hidden_sizes[0]
        self.w2 = [[random.gauss(0, 0.1) for _ in range(hidden_sizes[0])] for _ in range(hidden_sizes[1])]
        self.b2 = [0.0] * hidden_sizes[1]
        self.w3 = [random.gauss(0, 0.1) for _ in range(hidden_sizes[1])]
        self.b3 = 0.0
    
    def predict(self, features: List[float]) -> float:
        """
        features: [momentum_5d, momentum_20d, volume_ratio, 
                   rsi_14, macd_signal, volatility_20d, 
                   support_proximity, resistance_proximity]
        Returns: 0-1 buy probability
        """
        # Layer 1
        h1 = [0.0] * len(self.w1)
        for i, row in enumerate(self.w1):
            s = self.b1[i]
            for j, w in enumerate(row):
                s += w * (features[j] if j < len(features) else 0)
            h1[i] = max(0, s)  # ReLU
        
        # Layer 2
        h2 = [0.0] * len(self.w2)
        for i, row in enumerate(self.w2):
            s = self.b2[i]
            for j, w in enumerate(row):
                s += w * h1[j]
            h2[i] = max(0, s)
        
        # Output
        s = self.b3
        for j, w in enumerate(self.w3):
            s += w * h2[j]
        return 1.0 / (1.0 + pow(2.71828, -s))  # sigmoid
    
    def generate_signal(self, stock_code: str, price: float, 
                        momentum_5d: float, momentum_20d: float,
                        volume_ratio: float, rsi_14: float,
                        macd_signal: float, volatility_20d: float,
                        support_proximity: float, resistance_proximity: float) -> StockSignal:
        """Generate a trading signal based on technical indicators."""
        features = [momentum_5d, momentum_20d, volume_ratio,
                    rsi_14, macd_signal, volatility_20d,
                    support_proximity, resistance_proximity]
        
        buy_prob = self.predict(features)
        
        # A-share specific rules
        # 1. RSI > 70: overbought, avoid buying
        # 2. RSI < 30: oversold, potential buy
        # 3. High volatility: reduce position size
        # 4. Volume confirmation: need > 1.5x avg volume for breakouts
        
        if buy_prob > 0.65 and rsi_14 < 60 and volume_ratio > 1.2:
            signal = 'BUY'
            confidence = min(0.95, buy_prob * (1 + volume_ratio * 0.1))
            reason = f"MLP score {buy_prob:.2f}, RSI {rsi_14:.0f}, Vol {volume_ratio:.1f}x"
        elif buy_prob < 0.35 or (rsi_14 > 70 and momentum_5d < 0):
            signal = 'SELL'
            confidence = min(0.95, 1 - buy_prob)
            reason = f"Weak MLP {buy_prob:.2f}" + (f", RSI overbought {rsi_14:.0f}" if rsi_14 > 70 else "")
        else:
            signal = 'HOLD'
            confidence = 0.5
            reason = "Indicators neutral"
        
        return StockSignal(
            stock_code=stock_code,
            signal=signal,
            confidence=confidence,
            price=price,
            timestamp=time.time(),
            reason=reason
        )

class AShareAgent:
    """
    A-Share Quantitative Trading Agent.
    Manages portfolio, generates signals, tracks performance.
    """
    
    def __init__(self, initial_cash: float = 100000.0):
        self.predictor = MLPPredictor()
        self.portfolio = Portfolio(
            cash=initial_cash,
            positions={},
            total_value=initial_cash
        )
        self.signals: List[StockSignal] = []
        self.trade_history: List[dict] = []
        self._last_prices: Dict[str, float] = {}
        self.portfolio._last_prices = self._last_prices
    
    def analyze(self, stock_code: str, price: float, 
                momentum_5d: float = 0.05, momentum_20d: float = 0.02,
                volume_ratio: float = 1.0, rsi_14: float = 50.0,
                macd_signal: float = 0.0, volatility_20d: float = 0.02,
                support_proximity: float = 0.5, resistance_proximity: float = 0.5) -> StockSignal:
        """Analyze a stock and generate a signal."""
        self._last_prices[stock_code] = price
        signal = self.predictor.generate_signal(
            stock_code, price,
            momentum_5d, momentum_20d, volume_ratio,
            rsi_14, macd_signal, volatility_20d,
            support_proximity, resistance_proximity
        )
        self.signals.append(signal)
        return signal
    
    def execute(self, signal: StockSignal) -> Optional[dict]:
        """Execute a trading signal."""
        trade = {
            'signal': signal,
            'executed': False,
            'shares': 0,
            'cost': 0,
            'timestamp': time.time()
        }
        
        if signal.signal == 'BUY' and signal.confidence > 0.6:
            # Position sizing: allocate based on confidence
            allocation = min(self.portfolio.cash * signal.confidence, 10000)
            shares = int(allocation / signal.price / 100) * 100  # 100-share lots
            if shares > 0 and self.portfolio.add_position(signal.stock_code, shares, signal.price):
                trade['executed'] = True
                trade['shares'] = shares
                trade['cost'] = shares * signal.price
                trade['profit'] = 0.0  # 买入后待卖出现金才计入
                self.trade_history.append(trade)
        elif signal.signal == 'SELL' and signal.stock_code in self.portfolio.positions:
            shares = self.portfolio.positions[signal.stock_code]
            base_price = self._last_prices.get(signal.stock_code, signal.price)
            if self.portfolio.remove_position(signal.stock_code, shares, signal.price):
                trade['executed'] = True
                trade['shares'] = shares
                trade['cost'] = shares * signal.price
                trade['profit'] = shares * (signal.price - base_price)
                self.trade_history.append(trade)
        
        return trade
    
    def report(self) -> dict:
        """Generate portfolio report."""
        # 完善：持仓估值 = Σ(股数 × 最新价)；旧版把 _last_prices 当成 (shares, price) 对
        # 且 `if p in self._last_prices` 误把 price 当 key，导致 total_value 计算错误。
        holdings_value = sum(
            self.portfolio.positions.get(code, 0) * price
            for code, price in self._last_prices.items()
            if code in self.portfolio.positions
        )
        total = self.portfolio.cash + holdings_value
        return {
            'cash': self.portfolio.cash,
            'positions': dict(self.portfolio.positions),
            'total_value': total,
            'realized_pnl': self.portfolio.realized_pnl,
            'signals_generated': len(self.signals),
            'trades_executed': len(self.trade_history),
            'win_rate': self._calc_win_rate()
        }

    def _calc_win_rate(self) -> float:
        if not self.trade_history:
            return 0.0
        wins = sum(1 for t in self.trade_history if t.get('profit', 0) > 0)
        return wins / len(self.trade_history)

    # ---- 数据 pipeline 接入（P0 缺口补齐） ----
    def analyze_from_pipeline(self, rows: List[dict], stock_code: str,
                              data: str = 'qfq') -> StockSignal:
        """
        从 data_pipeline 产出的 OHLCV rows 自动计算技术指标并生成信号。
        打通 数据获取 → 特征 → 信号 链路（此前 agent 需手动喂 price/指标）。

        Args:
            rows: 归一化 OHLCV（{date, open, high, low, close, volume}），按日期升序
            stock_code: 标的代码
        """
        close = [r.get('close') for r in rows if r.get('close') is not None]
        vol = [r.get('volume') for r in rows if r.get('volume') is not None]
        if len(close) < 5:
            return StockSignal(stock_code, 'HOLD', 0.0, float(close[-1]) if close else 0.0,
                               time.time(), 'insufficient history')
        price = float(close[-1])
        m5 = (close[-1] - close[-5]) / close[-5] if len(close) >= 5 else 0.0
        m20 = (close[-1] - close[-20]) / close[-20] if len(close) >= 20 else m5
        v20 = _stdev(vol[-20:]) / _mean(vol[-20:]) if len(vol) >= 20 else 1.0
        # RSI-14 / 简化波动 / 支阻（滚动 20）
        rsi14 = _rsi(close)
        vol20 = _ann_vol(close)
        sup, res = _support_resistance(close)
        return self.analyze(
            stock_code, price, m5, m20, v20, rsi14, 0.0, vol20, sup, res,
        )

    def load_ohlcv(self, symbol: str, source: str = 'eastmoney',
                   start_date: str = '', end_date: str = '',
                   adjust: str = 'qfq', cache_dir: Optional[str] = None) -> dict:
        """拉取 A 股日线 OHLCV（多源 + 缓存水位线增量 + 复权一致性 QC）。"""
        from data_pipeline import fetch_daily_ohlcv
        res = fetch_daily_ohlcv(symbol, source=source, start_date=start_date,
                                 end_date=end_date, adjust=adjust, cache_dir=cache_dir)
        return {
            'rows': res.rows,
            'source': res.source,
            'is_incr': res.is_incr,
            'qc': res.qc.to_dict(),
        }


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _stdev(xs: List[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return (sum((x - m) ** 2 for x in xs) / len(xs)) ** 0.5


def _rsi(closes: List[float], period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    gains = losses = 0.0
    for i in range(len(closes) - period, len(closes)):
        d = closes[i] - closes[i - 1]
        if d >= 0:
            gains += d
        else:
            losses += -d
    if gains + losses == 0:
        return 50.0
    rs = (gains / period) / max(losses / period, 1e-9)
    return 100.0 - 100.0 / (1.0 + rs)


def _ann_vol(closes: List[float], bars_per_year: float = 252.0) -> float:
    if len(closes) < 3:
        return 0.0
    rets = [(closes[i] - closes[i - 1]) / closes[i - 1]
            for i in range(1, len(closes)) if closes[i - 1] > 0]
    return _stdev(rets) * (bars_per_year ** 0.5)


def _support_resistance(closes: List[float], window: int = 20) -> Tuple[float, float]:
    seg = closes[-window:]
    if not seg:
        return 0.0, 0.0
    return float(min(seg)), float(max(seg))
    
    def _calc_win_rate(self) -> float:
        if not self.trade_history:
            return 0.0
        wins = sum(1 for t in self.trade_history if t.get('profit', 0) > 0)
        return wins / len(self.trade_history)

# Demo
if __name__ == '__main__':
    agent = AShareAgent(initial_cash=100000)
    
    # Simulate analysis of some stocks
    demo_stocks = [
        ('600519', 1850.0, 0.03, 0.08, 1.5, 55.0, 0.02, 0.015, 0.7, 0.3),
        ('000858', 280.0, 0.05, 0.02, 2.1, 45.0, 0.03, 0.025, 0.6, 0.4),
        ('300750', 150.0, -0.02, 0.05, 0.8, 35.0, -0.01, 0.035, 0.4, 0.6),
    ]
    
    print("=== A-Share Quant Agent Demo ===")
    print(f"Initial cash: {agent.portfolio.cash}\n")
    
    for stock_code, price, m5, m20, vol, rsi, macd, v20, sp, rp in demo_stocks:
        signal = agent.analyze(stock_code, price, m5, m20, vol, rsi, macd, v20, sp, rp)
        trade = agent.execute(signal)
        print(f"  {stock_code}: {signal.signal} ({signal.confidence:.2f}) - {signal.reason}")
        if trade and trade['executed']:
            print(f"    Executed: {trade['shares']} shares @ {price}")
    
    report = agent.report()
    print(f"\n=== Portfolio Report ===")
    print(f"Cash: {report['cash']}")
    print(f"Positions: {report['positions']}")
    print(f"Signals: {report['signals_generated']}, Trades: {report['trades_executed']}")


def gate_access(plan="free"):
    """有偿授权门控：免费限次，PRO 解锁高级因子/回测"""
    return billing.check_access(plan)
