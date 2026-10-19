"""
备用数据源模块
当 akshare 不可用时，切换到备用数据源
"""
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class FallbackDataProvider:
    """备用数据提供商"""
    
    MOCK_STOCKS = [
        {"code": "600519", "name": "贵州茅台", "price": 1680.00, "change": 1.25},
        {"code": "000858", "name": "五粮液", "price": 145.50, "change": -0.82},
        {"code": "601318", "name": "中国平安", "price": 48.20, "change": 0.56},
    ]
    
    @staticmethod
    def get_mock_stock_data(symbol: str) -> List[Dict]:
        """生成模拟股票数据"""
        base_price = random.uniform(10, 1000)
        data = []
        for i in range(30):
            date = (datetime.now() - timedelta(days=30-i)).strftime("%Y-%m-%d")
            price = base_price * (1 + random.uniform(-0.05, 0.05))
            volume = random.randint(100000, 10000000)
            data.append({
                "date": date,
                "open": price * (1 + random.uniform(-0.02, 0.02)),
                "high": price * (1 + random.uniform(0, 0.03)),
                "low": price * (1 + random.uniform(-0.03, 0)),
                "close": price,
                "volume": volume,
            })
        return data
    
    @staticmethod
    def get_mock_fund_data() -> List[Dict]:
        """生成模拟基金数据"""
        return [
            {"code": "159915", "name": "创业板ETF", "nav": 1.25, "change": 0.8},
            {"code": "510300", "name": "沪深300ETF", "nav": 3.85, "change": 0.3},
        ]


def get_data_or_fallback(func, fallback_func, *args, **kwargs):
    """
    尝试执行主函数，失败时使用备用函数
    """
    try:
        result = func(*args, **kwargs)
        return result, False
    except Exception as e:
        print(f"[WARNING] 主数据源失败: {str(e)[:50]}，切换到备用数据源")
        fallback_result = fallback_func(*args, **kwargs)
        return fallback_result, True
