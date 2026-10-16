"""
ashare-quant 数据刷新脚本：拉 A 股行情 → MLP 打分 → 写 reports/。
CI 里跑；本地 `python refresh_report.py` 也可跑。
国内数据源优先 akshare；拉不到（无网/限流）时回退占位，保证 pipeline 不挂。
"""
import os
import json
import datetime


def fetch_ashare():
    """尝试用 akshare 拉当日 A 股行情，失败返回 None。"""
    try:
        import akshare as ak  # noqa
        df = ak.stock_zh_a_spot_em()
        rows = []
        for _, r in df.head(50).iterrows():
            rows.append(
                {
                    "code": str(r.get("代码")),
                    "name": str(r.get("名称")),
                    "price": float(r.get("最新价", 0)),
                    "pct": float(r.get("涨跌幅", 0)),
                }
            )
        return rows
    except Exception as e:
        print("[warn] akshare 拉取失败，回退占位：", e)
        return None


def mlp_signals(rows):
    """用 ashare_agent 的 StockSignal 做简化 MLP 打分（占位模型：按涨跌幅）。"""
    import ashare_agent

    sigs = []
    for r in rows:
        conf = min(0.99, abs(r["pct"]) / 5.0 + 0.3)
        sig = "BUY" if r["pct"] > 0 else "SELL"
        s = ashare_agent.StockSignal(
            stock_code=r["code"], signal=sig, confidence=round(conf, 2),
            price=r["price"], timestamp=0.0, reason="简化MLP(涨跌幅)",
        )
        sigs.append(s)
    # 高置信筛选
    return [s for s in sigs if s.confidence >= 0.6][:20]


def main():
    os.makedirs("reports", exist_ok=True)
    day = datetime.date.today().isoformat()
    rows = fetch_ashare()
    if rows:
        signals = mlp_signals(rows)
        payload = {"date": day, "source": "akshare", "signals": [
            {"code": s.stock_code, "signal": s.signal, "conf": s.confidence, "price": s.price}
            for s in signals
        ]}
    else:
        payload = {"date": day, "source": "placeholder", "signals": [],
                   "note": "akshare 不可用，占位；有网环境会自动填充"}
    open(f"reports/{day}.json", "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=2))
    open("reports/latest.json", "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=2))
    print("report @", day, "source=", payload["source"], "signals=", len(payload["signals"]))


if __name__ == "__main__":
    main()
