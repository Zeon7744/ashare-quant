# 发布与变现（ashare-quant）

> 定位：**A 股研究与教学量化工具仓**，变现路径 = 开源背书 → 量化内容输出 → 咨询/课程（非代码直接售卖）。
> 本仓不改破坏性接口，仅补法控、发布产物与变现入口说明。

## 1. 付费门 / 定价入口（免费 → Pro CTA）
- **免费（OSS）层**：数据 pipeline（多源 QC / 复权一致性 / 缓存水位线增量拉取）、walk-forward 回测、agent 信号全链路开源（MIT License）。
- **Pro / 变现层 CTA**（走 FUNDING.yml + 咨询，非代码售卖）：
  - GitHub Sponsors（见 `FUNDING.yml`）
  - A 股策略研究 / 课程
  - 实盘行情数据源接入（专业数据 API key 配套，另行报价）
- **CTA 文案**：
  > 免费层已含数据 QC + walk-forward 回测 + 前视校验；
  > 需要实盘数据接入 / 策略咨询 → Sponsors 或企业报价。

## 2. GitHub 发布产物（Release）
- 每里程碑打 tag：`v0.x` 迭代、`v1.0` 稳定版。
- Release 附产物：
  - `ashare-quant-sources.tar.gz`（源码）
  - `walk_forward_report_YYYYMMDD.md`（当次回测快照，含数据 QC 结论 + 胜率/夏普 + 前视校验）
- 自动发布：`.github/workflows/` 可加 `release.yml`（tag → GitHub Release + 生成回测快照）。

## 3. 可运行 demo
- `python3 -m pytest tests/`：全量测试（含 backtest + data_pipeline，离线可跑）。
- `python3 ashare_agent.py`：A 股 agent 信号全链路演示。

## 4. 法控（已同步进 README）
- **非投资建议**：本工具为研究/教学用途，不构成投资建议、证券研究意见或投资顾问服务；回测指标基于历史行情，不代表未来收益。
- **合规免责**：交易决策由使用者自行负责，实盘请遵守《证券法》及交易所规则。
- **数据脱敏**：行情数据来自公开数据源，不涉真实个人账户；接入真实数据仅读公开行情，不采集/存储私人信息或账户凭据。

## 5. 变更记录
- 2026-10-18：补法控声明 + 发布产物/变现入口说明（本文件）；不改任何核心代码接口。
