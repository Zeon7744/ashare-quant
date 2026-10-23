"""
统一收款层 — 爱发电 afdian 网关 + 免费版限次/深度功能需付费 + 爱发电赞赏码框架。

环境变量（全部走 env，不落代码）：
  JZ_AFDIAN_USER      爱发电 user_id
  JZ_AFDIAN_TOKEN     爱发电 API token
  JZ_AFDIAN_BASE      API 基址（默认 https://afdian.com/api）
  JZ_AFDIAN_RETURN    支付成功跳转地址

网关选择：BILLING_GATEWAY=noop|afdian（缺省 noop）
"""
import os
import time
import uuid
import json
import urllib.request


# ─────────────────────────── 配置 ───────────────────────────

PAYWALL_RULES = {
    "free": {"daily_limit": 3, "label": "免费版"},
    "pro":  {"daily_limit": -1, "label": "PRO ¥{PRO_PRICE}/月"},
    "enterprise": {"daily_limit": -1, "label": "企业 ¥{ENT_PRICE}/月"},
}

# 各仓价格锚点（与 README/pricing.md 对齐）
PRO_PRICE = os.getenv("JZ_PRO_PRICE_CNY", "199")
ENT_PRICE = os.getenv("JZ_ENT_PRICE_CNY", "1999")

for k, v in PAYWALL_RULES.items():
    if isinstance(v, dict):
        v["label"] = v["label"].format(PRO_PRICE=PRO_PRICE, ENT_PRICE=ENT_PRICE)

_STATE = {"date": "", "count": 0}


def _today():
    return time.strftime("%Y-%m-%d")


# ─────────────────────────── 门控 ───────────────────────────

def check_access(plan: str = "free", action: str = "basic") -> dict:
    """
    检查当前套餐是否允许执行操作。
    返回 {"allowed": bool, "remaining": int, "reason": str, "upgrade_url": str}
    """
    rules = PAYWALL_RULES.get(plan, PAYWALL_RULES["free"])
    limit = rules["daily_limit"]

    if limit == -1:
        return {"allowed": True, "remaining": -1, "reason": "", "upgrade_url": ""}

    if _STATE["date"] != _today():
        _STATE["date"] = _today()
        _STATE["count"] = 0

    if _STATE["count"] >= limit:
        return {
            "allowed": False,
            "remaining": 0,
            "reason": f"free_plan_daily_limit_reached ({limit}/天)，请升级 Pro",
            "upgrade_url": "https://afdian.com/@Zeon7744",
            "http_status": 402,
        }

    _STATE["count"] += 1
    return {
        "allowed": True,
        "remaining": limit - _STATE["count"],
        "reason": "",
        "upgrade_url": "",
    }


def get_pricing() -> list[dict]:
    """返回定价列表，供 UI / README 对齐。"""
    return [
        {"plan": "free", "price": 0, "price_label": "¥0",
         "features": [f"{PAYWALL_RULES['free']['daily_limit']} 次/天", "基础功能", "社区支持"]},
        {"plan": "pro", "price": int(PRO_PRICE), "price_label": f"¥{PRO_PRICE}/月",
         "features": ["不限次", "全部工具", "优先支持"]},
        {"plan": "enterprise", "price": int(ENT_PRICE), "price_label": f"¥{ENT_PRICE}/月",
         "features": ["不限次", "私有部署", "SLA 保障"]},
    ]


# ─────────────────────────── 网关 ───────────────────────────

class NoopGateway:
    """占位网关：不真正扣款，MVP 演示用。"""
    name = "noop"

    def create_order(self, tenant_id, amount_cents, product, plan, order_meta=None):
        oid = "noop_" + str(uuid.uuid4())[:12]
        return {"order_id": oid, "status": "created", "amount_cents": amount_cents,
                "plan": plan, "product": product, "gateway": "noop"}

    def query_callback(self, order_id):
        return {"order_id": order_id, "status": "unpaid", "paid": False}

    def refund(self, order_id, amount_cents, reason=""):
        return {"order_id": order_id, "ok": True, "refunded_cents": amount_cents}


class AfdianGateway:
    """
    爱发电网关（个人创作者 10 分钟开通，API 查订单 + Webhook 回调）。
    环境变量：JZ_AFDIAN_USER / JZ_AFDIAN_TOKEN / JZ_AFDIAN_BASE
    """
    name = "afdian"
    DEFAULT_BASE = "https://afdian.com/api"

    def __init__(self):
        self.user_id = os.environ.get("JZ_AFDIAN_USER", "")
        self.token = os.environ.get("JZ_AFDIAN_TOKEN", "")
        self.base = os.environ.get("JZ_AFDIAN_BASE", self.DEFAULT_BASE)

    def _post(self, path, payload):
        body = dict(payload)
        if self.token:
            body["token"] = self.token
        req = urllib.request.Request(
            f"{self.base}{path}",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def create_order(self, tenant_id, amount_cents, product, plan, order_meta=None):
        if not self.user_id or not self.token:
            return {"order_id": "pending", "status": "created_pending_key",
                    "needs_secret": ["JZ_AFDIAN_USER", "JZ_AFDIAN_TOKEN"]}
        price = round(amount_cents / 100.0, 2)
        out_trade_no = "jz_" + str(uuid.uuid4())[:16]
        payload = {"user_id": self.user_id, "price": str(price),
                   "name": f"{product}({plan})"[:42], "out_trade_no": out_trade_no}
        try:
            result = self._post("/payment/create", payload)
            if result.get("code") != 0:
                return {"order_id": out_trade_no, "status": "gateway_rejected",
                        "code": result.get("code"), "msg": result.get("message", "")}
            data = result.get("data", {})
            return {"order_id": out_trade_no, "status": "created",
                    "pay_url": data.get("url", ""), "gateway": "afdian"}
        except Exception as e:
            return {"order_id": out_trade_no, "status": "gateway_error", "error": str(e)}

    def query_callback(self, order_id):
        if not self.user_id or not self.token:
            return {"order_id": order_id, "status": "pending_key", "paid": False}
        payload = {"user_id": self.user_id, "out_trade_no": order_id}
        try:
            result = self._post("/payment/query", payload)
            data = result.get("data", {})
            paid = data.get("status") in ("paid", "success")
            return {"order_id": order_id, "status": data.get("status", "unknown"), "paid": paid}
        except Exception as e:
            return {"order_id": order_id, "status": "query_failed", "paid": False, "error": str(e)}

    def refund(self, order_id, amount_cents, reason=""):
        if not self.user_id or not self.token:
            return {"order_id": order_id, "ok": False, "note": "爱发电凭据未配"}
        price = round(amount_cents / 100.0, 2)
        payload = {"user_id": self.user_id, "out_trade_no": order_id, "price": str(price)}
        try:
            result = self._post("/payment/refund", payload)
            ok = result.get("code", -1) == 0
            return {"order_id": order_id, "ok": ok, "refunded_cents": amount_cents if ok else 0}
        except Exception as e:
            return {"order_id": order_id, "ok": False, "error": str(e)}


_REGISTRY = {"noop": NoopGateway, "afdian": AfdianGateway}


def get_gateway(name=None):
    name = name or os.environ.get("BILLING_GATEWAY", "noop")
    cls = _REGISTRY.get(name, NoopGateway)
    return cls()


def create_order_for_plan(tenant_id, plan, product="subscription"):
    """便捷入口：按套餐下单。"""
    g = get_gateway()
    amount = int(get_pricing()[1]["price"] if plan == "pro" else 0) * 100
    return g.create_order(tenant_id, amount, product, plan)
