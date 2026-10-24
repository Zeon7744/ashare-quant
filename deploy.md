# 部署指南 · ashare-quant

## 本地运行

```bash
# 1. 克隆仓库
git clone https://github.com/Zeon7744/ashare-quant.git
cd ashare-quant

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行多空辩论
python -m ashare_quant.debate --stock 600519

# 4. 运行回测
python backtest.py

# 5. 冒烟测试
bash smoke_test.sh
```

## GitHub Actions 每日 Refresh 报告

仓库已配置 `.github/workflows/` 下的 CI，每日自动运行：

1. **数据采集** — `data_pipeline.py` 拉取最新行情
2. **多空辩论** — `debate.py` 生成看多/看空论点
3. **报告生成** — `refresh_report.py` 输出 Markdown 报告到 `reports/`
4. **页面更新** — `index.html` 自动刷新数据

### 手动触发

```bash
# 在 GitHub 仓库页面 → Actions → Daily Refresh → Run workflow
```

## Pro 版订阅验证要点

### 功能分级

| 功能 | Free | Pro (¥29/月) | Studio (¥99/月) |
|------|------|-------------|----------------|
| 单日辩论次数 | 3 次 | 不限 | 不限 |
| 单标的辩论 | ✅ | ✅ | ✅ |
| 多标的组合 | ❌ | ✅ | ✅ |
| 实时信号推送 | ❌ | ✅ | ✅ |
| 回测策略库 | ❌ | ❌ | ✅ |
| 机构级信号 | ❌ | ❌ | ✅ |

### 订阅验证流程

1. 用户通过面包多 Pay/虎皮椒/虎皮椒完成支付
2. 系统验证支付凭证 → 激活 Pro/Studio 权限
3. `pro_gates.py` 中 `check_gates(plan, action)` 实时校验
4. 超限自动降级并提示升级

### 关键文件

- `ashare_quant/pro_gates.py` — 功能门控逻辑
- `ashare_quant/pro_features.py` — 功能开关配置
- `pricing.md` — 定价说明
