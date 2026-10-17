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
    generate_index_html(payload)
    print("report @", day, "source=", payload["source"], "signals=", len(payload["signals"]))


def generate_index_html(payload):
    """把最新报告渲染成 gh-pages 上的 index.html（每次 CI 跑完自动更新）。"""
    import json as _json
    day = payload.get("date", "")
    source = payload.get("source", "placeholder")
    signals = payload.get("signals", [])
    free = signals[:3]
    pro = signals[3:]
    free_rows = "".join(
        f"<tr><td>{s.get('code','')}</td><td>{s.get('name','')}</td><td>{s.get('price',':'!}</td><td>{s.get('pct','"):'}</td>"
        for s in free
    ) if free else "<tr><td colspan=4>暂无数据</td></tr>"
    # 简化版：直接用占位信号结构
    free_html = ""
    if free:
        free_html = "<table style=width:100%><tr><th>代码</th><th>信号</th><th>置信度</th></tr>"
        for s in free:
            free_html += f"<tr><td>{s.get('code',':'!}</td><td>{s.get('signal',':'!}</td><td>{s.get('conf',':'!}</td></tr>"
        free_html += "</table>"
    else:
        free_html = "<p>今日暂无高置信度免费信号（占位数据）。Pro 订阅解锁全量。</p>"
    pro_count = len(pro)
    html = f'''    <html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">    <title>A股量化报告</title><style>body{{font-family:-apple-system,sans-serif;background:#0d1117;color:#e6edf3;max-width:800px;margin:0 auto;padding:40px 20px}}    .badge{{background:#1f6feb;color:#fff;padding:2px 10px;border-radius:10px;font-size:12px}}    .badge.pro{{background:#a371f4}}h1{{font-size:26px}}table{{width:100%;border-collapse:collapse;margin:12px 0}}    th,td{{border:1px solid #30363d;padding:8px;text-align:left}}tr:nth-child(even){{background:#161b22}}</style></head>    <body><h1>A股量化报告</h1><p><span class="badge">免费 3 条/天</span> <span class="badge pro">Pro 解锁全量 {pro_count} 条</span> 数据源：{source} · {day}</p>{free_html}    <p style="margin-top:24px"><a href="#" style="color:#58a6ff">解锁 Pro 全量信号 →</a></p></body></html>'''
    open("reports/index.html", "w", encoding="utf-8").write(html)
    print("index.html generated, signals:", len(signals))



if __name__ == "__main__":
    main()
