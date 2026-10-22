"""Pro 功能门控 — 控制 Free / Pro / Studio 三档权限。

用法:
    from ashare_quant.pro_gates import check_gates
    allowed, message = check_gates("free", "debate")
    if not allowed:
        print(message)  # 提示升级
"""

from __future__ import annotations

import json
import os
import time
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# 套餐定义
# ---------------------------------------------------------------------------

PRO_GATES: Dict[str, Dict[str, object]] = {
    "free": {
        "debate_daily_limit": 3,       # 每日辩论次数上限
        "multi_stock": False,           # 多标的组合
        "realtime_signal": False,       # 实时信号推送
        "backtest_library": False,      # 回测策略库
        "max_combo_stocks": 1,          # 组合最大标的数
        "institutional_signal": False,  # 机构级信号
    },
    "pro": {
        "debate_daily_limit": -1,       # -1 = 不限
        "multi_stock": True,
        "realtime_signal": True,
        "backtest_library": False,
        "max_combo_stocks": 3,
        "institutional_signal": False,
    },
    "studio": {
        "debate_daily_limit": -1,
        "multi_stock": True,
        "realtime_signal": True,
        "backtest_library": True,
        "max_combo_stocks": 5,
        "institutional_signal": True,
    },
}

# 功能 → 所需最低套餐
_FEATURE_MIN_PLAN = {
    "debate":        None,        # 所有套餐可用（有次数限制）
    "multi_stock":   "pro",
    "realtime":      "pro",
    "backtest_lib":  "studio",
    "inst_signal":   "studio",
}

_PLAN_RANK = {"free": 0, "pro": 1, "studio": 2}

# ---------------------------------------------------------------------------
# 每日计数器（简易文件持久化，生产环境换 Redis/DB）
# ---------------------------------------------------------------------------

_STATE_DIR = os.path.join(os.path.dirname(__file__), "..", ".pro_state")


def _state_path() -> str:
    os.makedirs(_STATE_DIR, exist_ok=True)
    return os.path.join(_STATE_DIR, "debate_count.json")


def _load_count() -> Dict:
    path = _state_path()
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"date": "", "count": 0}


def _save_count(data: Dict) -> None:
    with open(_state_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def _today_str() -> str:
    return time.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# 核心校验
# ---------------------------------------------------------------------------

def check_gates(plan: str, action: str) -> Tuple[bool, str]:
    """校验当前套餐是否允许执行某操作。

    Parameters
    ----------
    plan : str
        当前套餐: "free" / "pro" / "studio"
    action : str
        操作类型: "debate" / "multi_stock" / "realtime" / "backtest_lib" / "inst_signal"

    Returns
    -------
    (allowed, message) — allowed=True 放行；False 时 message 含升级提示。
    """
    plan = plan.lower().strip()
    if plan not in PRO_GATES:
        return False, f"未知套餐: {plan}，可选 free / pro / studio"

    gate = PRO_GATES[plan]
    min_plan = _FEATURE_MIN_PLAN.get(action)

    # debate 特殊处理：检查每日次数
    if action == "debate":
        limit = gate["debate_daily_limit"]
        if limit == -1:
            return True, "Pro 不限次数 ✅"

        state = _load_count()
        today = _today_str()
        if state["date"] != today:
            state = {"date": today, "count": 0}
            _save_count(state)

        if state["count"] >= limit:
            return False, (
                f"⚠️ Free 套餐今日已用完 {limit} 次辩论额度。"
                f"\n👉 升级 Pro 享无限辩论 + 多标的组合 + 实时信号 → 查看 pricing.md"
            )

        state["count"] += 1
        _save_count(state)
        remaining = limit - state["count"]
        return True, f"今日剩余 {remaining} 次免费辩论"

    # 其他功能：检查套餐等级
    if min_plan is None:
        return True, ""

    if _PLAN_RANK.get(plan, 0) < _PLAN_RANK.get(min_plan, 0):
        return False, (
            f"⚠️ 此功能需要 {min_plan.upper()} 套餐。"
            f"\n👉 当前: {plan.upper()} → 升级至 {min_plan.upper()} 解锁"
        )

    return True, ""


# ---------------------------------------------------------------------------
# CLI 便捷入口
# ---------------------------------------------------------------------------

def get_remaining_free(plan: str = "free") -> int:
    """返回今日剩余免费辩论次数（free 套餐）；Pro/Studio 返回 -1。"""
    gate = PRO_GATES.get(plan.lower(), PRO_GATES["free"])
    limit = gate["debate_daily_limit"]
    if limit == -1:
        return -1
    state = _load_count()
    today = _today_str()
    if state["date"] != today:
        return limit
    return max(0, limit - state["count"])


if __name__ == "__main__":
    # 快速演示
    for plan in ["free", "pro", "studio"]:
        print(f"\n--- {plan.upper()} ---")
        for action in ["debate", "multi_stock", "realtime", "backtest_lib", "inst_signal"]:
            ok, msg = check_gates(plan, action)
            status = "✅" if ok else "🔒"
            print(f"  {status} {action}: {msg or ('允许' if ok else '拒绝')}")
