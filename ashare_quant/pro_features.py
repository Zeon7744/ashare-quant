"""Pro 功能开关 — 每个付费功能一个布尔开关，默认关闭。

订阅后通过环境变量或配置文件启用：
    ASHARE_PRO_FEATURES=multi_stock,realtime,backtest_lib

或在 .pro_state/features.json 中配置：
    {"multi_stock": true, "realtime": true}
"""

from __future__ import annotations

import json
import os
from typing import Dict, List

# ---------------------------------------------------------------------------
# 功能注册表
# ---------------------------------------------------------------------------

PRO_FEATURES: List[Dict[str, object]] = [
    {
        "key": "multi_stock",
        "name": "多标的组合辩论",
        "description": "同时辩论多个股票，自动对比多空强度",
        "min_plan": "pro",
        "enabled": False,
    },
    {
        "key": "realtime",
        "name": "实时信号推送",
        "description": "盘中实时监控，多空信号变化即时推送",
        "min_plan": "pro",
        "enabled": False,
    },
    {
        "key": "backtest_lib",
        "name": "回测策略库",
        "description": "内置 20+ 经典量化策略回测模板",
        "min_plan": "studio",
        "enabled": False,
    },
    {
        "key": "inst_signal",
        "name": "机构级信号",
        "description": "资金流向、大单追踪、机构持仓分析",
        "min_plan": "studio",
        "enabled": False,
    },
    {
        "key": "advanced_regime",
        "name": "高级市场状态识别",
        "description": "多因子融合的市场状态判断（牛市/熊市/震荡）",
        "min_plan": "pro",
        "enabled": False,
    },
]


# ---------------------------------------------------------------------------
# 开关控制
# ---------------------------------------------------------------------------

_STATE_DIR = os.path.join(os.path.dirname(__file__), "..", ".pro_state")


def _config_path() -> str:
    return os.path.join(_STATE_DIR, "features.json")


def load_feature_states() -> Dict[str, bool]:
    """加载功能开关状态。

    优先级：环境变量 > 配置文件 > 默认值(False)
    """
    states: Dict[str, bool] = {f["key"]: False for f in PRO_FEATURES}

    # 1. 配置文件
    config = _config_path()
    if os.path.isfile(config):
        try:
            with open(config, "r", encoding="utf-8") as fh:
                saved = json.load(fh)
                for k, v in saved.items():
                    if k in states:
                        states[k] = bool(v)
        except Exception:
            pass

    # 2. 环境变量覆盖（最高优先级）
    env_features = os.environ.get("ASHARE_PRO_FEATURES", "")
    if env_features.strip():
        for key in env_features.split(","):
            key = key.strip()
            if key in states:
                states[key] = True

    return states


def is_feature_enabled(key: str) -> bool:
    """检查某功能是否启用。"""
    states = load_feature_states()
    return states.get(key, False)


def enable_feature(key: str) -> None:
    """持久化启用某功能（订阅后调用）。"""
    os.makedirs(_STATE_DIR, exist_ok=True)
    states = load_feature_states()
    states[key] = True
    with open(_config_path(), "w", encoding="utf-8") as fh:
        json.dump(states, fh, ensure_ascii=False, indent=2)


def disable_feature(key: str) -> None:
    """持久化关闭某功能。"""
    os.makedirs(_STATE_DIR, exist_ok=True)
    states = load_feature_states()
    states[key] = False
    with open(_config_path(), "w", encoding="utf-8") as fh:
        json.dump(states, fh, ensure_ascii=False, indent=2)


def list_features(with_state: bool = True) -> str:
    """返回功能列表的可读字符串。"""
    states = load_feature_states() if with_state else {}
    lines = []
    for f in PRO_FEATURES:
        status = ""
        if with_state:
            status = " ✅" if states.get(f["key"]) else " 🔒"
        lines.append(f"  [{f['min_plan'].upper():6s}] {f['name']}{status}")
        lines.append(f"          {f['description']}")
    return "\n".join(lines)


if __name__ == "__main__":
    print("📋 Pro 功能列表：")
    print(list_features(with_state=True))
    print(f"\n配置路径: {_config_path()}")
