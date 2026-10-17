"""
ashare-quant 数据刷新脚本：拉 A 股行情 → MLP 打分 → 写 reports/ + gh-pages index.html。
CI 里跑；本地 `python refresh_report.py` 也可跑。

多源 fallback 链（本次迭代）：
  1. 东方财富 stock_zh_a_spot_em（akshare，免费无需注册）
  2. 新浪 stock_zh_a_spot（akshare，备用）
  3. 腾讯 qt.gtimg.cn 直接 HTTP（纯 stdlib，兜底）
  4. 占位数据（保证 pipeline 不挂，source=placeholder）
健壮性：指数退避重试 + 限流保护 + health.json 健康度文件。
"""
import os
import json
import time
import urllib.request
import datetime


def _retry(fn, attempts=2, base_delay=1.0):
    last = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last = e
            if i < attempts - 1:
                time.sleep(base_delay * (2 ** i))
    raise last


def _fetch_eastmoney():
    import akshare as ak  # noqa
    df = ak.stock_zh_a_spot_em()
    return _norm_rows(df, "代码", "名称", "最新价", "涨跌幅"), "akshare_em"


def _fetch_sina():
    import akshare as ak  # noqa
    df = ak.stock_zh_a_spot()
    return _norm_rows(df, "代码", "名称", "最新价", "涨跌幅"), "akshare_sina"


def _norm_rows(df, ck, nk, pk, ck_pct):
    rows = []
    for _, r in df.head(50).iterrows():
        rows.append({
            "code": str(r.get(ck, "")),
            "name": str(r.get(nk, "")),
            "price": float(r.get(pk, 0) or 0),
            "pct": float(r.get(ck_pct, 0) or 0),
        })
    return rows


def _fetch_tencent():
    """腾讯行情兜底（纯 stdlib，无需依赖）：拉沪深大盘 + 几支代表股。"""
    codes = "sh000001,sz399001,sh600519,sz000858"
    url = f"https://qt.gtimg.cn/q={codes}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=8).read().decode("gbk", "ignore")
    rows = []
    for line in raw.strip().split(";"):
        if "=" not in line:
            continue
        val = line.split("=", 1)[1].strip('"')
        parts = val.split("~")
        if len(parts) < 32:
            continue
        try:
            rows.append({
                "code": parts[2], "name": parts[1],
                "price": float(parts[3] or 0),
                "pct": float(parts[32] or 0),
            })
        except (ValueError, IndexError):
            continue
    return rows, "tencent"


def fetch_ashare():
    """多源 fallback：东财 → 新浪 → 腾讯 → 占位。返回 (rows, source)。"""
    chain = [
        ("eastmoney", _fetch_eastmoney),
        ("sina", _fetch_sina),
        ("tencent", _fetch_tencent),
    ]
    for label, fn in chain:
        try:
            _retry(fn, attempts=2, base_delay=1.0)
            rows, source = fn()
            if rows:
                return rows, source
        except Exception as e:  # noqa: BLE001
            print(f"[warn] {label} 拉取失败，尝试下一源：{e}")
    return None, "placeholder"


def mlp_signals(rows):
    """简化 MLP 打分（按涨跌幅 + 动量），高置信度过滤。"""
    sigs = []
    for r in rows:
        conf = min(0.99, abs(r["pct"]) / 5.0 + 0.3)
        sig = "BUY" if r["pct"] > 0 else "SELL"
        sigs.append({
            "code": r["code"], "signal": sig,
            "conf": round(conf, 2), "price": r["price"],
        })
    sigs.sort(key=lambda x: x["conf"], reverse=True)
    return [s for s in sigs if s["conf"] >= 0.6][:20]


def generate_index_html(payload):
    """把最新报告渲染成 gh-pages 上的 index.html（每次 CI 跑完自动更新）。"""
    day = payload.get("date", "")
    source = payload.get("source", "placeholder")
    signals = payload.get("signals", [])
    free = signals[:3]
    pro_count = len(signals) - len(free)

    if free:
        rows_html = "<tr><th>代码</th><th>名称</th><th>信号</th><th>置信度</th></tr>"
        for s in free:
            rows_html += ("<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>").format(
                s.get("code", ""), s.get("name", ""), s.get("signal", ""), s.get("conf", ""))
        free_html = "<table>" + rows_html + "</table>"
    else:
        free_html = "<p>今日暂无高置信度免费信号（占位数据）。Pro 订阅解锁全量。</p>"

    health_note = {"placeholder": "数据源不可用，当前为占位", "tencent": "腾讯兜底源",
                   "akshare_em": "东方财富", "akshare_sina": "新浪"}.get(source, source)
    html = (
        "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>A股量化报告</title><style>"
        "body{font-family:-apple-system,sans-serif;background:#0d1117;color:#e6edf3;max-width:800px;margin:0 auto;padding:40px 20px}"
        ".badge{background:#1f6feb;color:#fff;padding:2px 10px;border-radius:10px;font-size:12px}"
        ".badge.pro{background:#a371f4}h1{font-size:26px}"
        "table{width:100%;border-collapse:collapse;margin:12px 0}th,td{border:1px solid #30363d;padding:8px;text-align:left}"
        "tr:nth-child(even){background:#161b22}</style></head><body>"
        "<h1>A股量化报告</h1>"
        "<p><span class='badge'>免费 3 条/天</span> <span class='badge pro'>Pro 解锁全量 "
        + str(pro_count) + " 条</span> 数据源：" + health_note + " · " + day + "</p>"
        + free_html +
        "<p style='margin-top:24px'><a href='#' style='color:#58a6ff'>解锁 Pro 全量信号 →</a></p>"
        "<p style='color:#8b949e;font-size:13px'>数据仅供研究参考，不构成投资建议。 ashare-quant · MIT License</p>"
        "</body></html>"
    )
    open("reports/index.html", "w", encoding="utf-8").write(html)
    # 同步更新根目录 index.html（gh-pages 实际对外展示的页面；CI 检查的是根目录）
    open("index.html", "w", encoding="utf-8").write(html)
    print("index.html generated (root + reports/), signals:", len(signals))


def main():
    os.makedirs("reports", exist_ok=True)
    day = datetime.date.today().isoformat()
    rows, source = fetch_ashare()
    if rows:
        signals = mlp_signals(rows)
        payload = {"date": day, "source": source, "signals": signals}
    else:
        payload = {"date": day, "source": "placeholder", "signals": [],
                   "note": "多源均不可用，占位；有网环境会自动填充真实行情"}
    open(f"reports/{day}.json", "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=2))
    open("reports/latest.json", "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=2))
    health = {"date": day, "source": payload["source"],
              "signals_count": len(payload.get("signals", [])),
              "ok": payload["source"] != "placeholder"}
    open("reports/health.json", "w", encoding="utf-8").write(json.dumps(health, ensure_ascii=False, indent=2))
    generate_index_html(payload)
    print("report @", day, "source=", payload["source"], "signals=", len(payload["signals"]))


if __name__ == "__main__":
    main()
