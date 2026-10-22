# 📈 Ashare Quant — A股量化投资分析系统

> **A股市场量化分析工具** — 多因子选股 · 回测引擎 · 策略优化  
> 基于yfinance和akshare的数据获取，支持沪深京三大交易所

[![GitHub Stars](https://img.shields.io/github/stars/Zeon7744/ashare-quant?style=social)](https://github.com/Zeon7744/ashare-quant)
[![GitHub Forks](https://img.shields.io/github/forks/Zeon7744/ashare-quant?style=social)](https://github.com/Zeon7744/ashare-quant/forks)
[![GitHub License](https://img.shields.io/github/license/Zeon7744/ashare-quant)](https://github.com/Zeon7744/ashare-quant/blob/main/LICENSE)
[![Gitee Stars](https://gitee.com/Zeon7744/ashare-quant/badge/star.svg?theme=gvp)](https://gitee.com/Zeon7744/ashare-quant)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)

---

## 📌 这是 GitHub 官方主仓

> **Gitee 镜像**: [gitee.com/Zeon7744/ashare-quant](https://gitee.com/Zeon7744/ashare-quant)

Issues 和 PR 请在 GitHub 提交。

---

## ⚡ 快速开始

```bash
git clone https://github.com/Zeon7744/ashare-quant.git
cd ashare-quant
pip install -r requirements.txt
python main.py
```

---

## 🛠️ 核心功能

| 模块 | 功能 |
|------|------|
| **数据获取** | akshare/yfinance 获取A股实时行情 |
| **因子计算** | 市盈率、市净率、ROE、动量等30+因子 |
| **回测引擎** | 历史策略回测，支持滑点手续费 |
| **策略优化** | 遗传算法/网格搜索优化参数 |
| **可视化** | 收益曲线、回撤分析、因子IC图 |

---

## 📁 项目结构

```
ashare-quant/
├── main.py              # 主程序入口
├── data_fetcher.py      # 数据获取模块
├── factor_calculator.py # 因子计算模块
├── backtest.py          # 回测引擎
├── strategy.py          # 策略实现
├── optimizer.py         # 策略优化
├── visualizer.py        # 可视化工具
├── requirements.txt     # 依赖列表
└── README.md           # 项目文档
```

---

## ⚠️ 注意事项

- 本系统仅供研究学习使用
- 不构成投资建议
- 投资有风险，决策需谨慎

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

---

## 📄 许可证

MIT License

---

**开发者**: Zeon7744  
**最后更新**: 2026-09-25  
**GitHub**: https://github.com/Zeon7744/ashare-quant

---

## 🚀 免费 → Pro → 企业（变现入口）

免费=每日高置信信号；Pro=¥199/月（实时信号+组合管理）；企业=¥1999/月（私有部署）

- **免费**：立即 [安装/克隆] 使用，命中配额即可升级。
- **Pro（¥199/月）**：[爱发电订阅](https://afdian.net/@Zeon7744) 解锁高级能力。
- **企业（¥1999/月）**：私有部署 / 定制需求 → [联系商务](https://afdian.net/@Zeon7744)。

> 详细定价见 [pricing.md](pricing.md)

---

## 快速上手
依赖安装：
```bash
python3 -m pip install -r requirements.txt
```

## 变现路径
研究仓，变现路径=开源背书→量化内容输出→咨询/课程（非代码直接售卖）。
> 定价：见 [pricing.md](pricing.md) | 订阅：[爱发电 @Zeon7744](https://afdian.net/@Zeon7744)

---


---

## ⚖️ 商用与合规

### 开源范围
- 代码（量化因子、回测框架、Agent 分析、数据管道）以 MIT License 开放，可自由使用、修改与商用。
- 以下部分不属于开源范围：Pro/企业档位的托管服务（实时信号、组合管理、私有部署、定制策略）。

### 付费功能边界
- 免费（¥0）：每日高置信信号（回测口径）+ 开源代码
- Pro（¥199/月）：实时信号 + 组合管理 + 回测
- 企业（¥1999/月）：私有部署 + 定制策略 + API 接入 + SLA 保障

### 内容版权
- 回测指标、因子代码、文档：MIT 适用范围为全部 Python 代码与测试
- 行情数据来自公开来源，不存储任何真实个人账户或持仓
- 开源素材/剧本（如有）：CC0/MIT 适用范围以 LICENSE 为准

### 合规免责
- 本项目是 A 股研究与教学用途的量化工具，**不构成任何投资建议、证券研究意见或投资顾问服务**
- 回测胜率、夏普、walk-forward 等指标均基于历史行情，**不代表未来收益**，不构成买卖依据
- 使用本工具产生的任何 A 股交易决策由使用者自行承担，本项目作者不对任何交易结果、亏损或合规责任负责
- 实盘交易请自行遵守中国《证券法》及交易所规则；本项目不托管真实资金

---

## ⚖️ 法控声明（Non-investment-advice disclaimer）

- **非投资建议 / 非投资顾问**：本项目是 A 股研究与教学用途的量化工具，**不构成任何投资建议、证券研究意见或投资顾问服务**。回测胜率、夏普、walk-forward 等指标均基于历史行情，**不代表未来收益**，不构成买卖依据。
- **合规免责**：使用本工具产生的任何 A 股交易决策由使用者自行承担，本项目作者不对任何交易结果、亏损或合规责任负责。实盘交易请自行遵守中国《证券法》及交易所规则。
- **数据脱敏**：行情数据来自公开数据源（东财/新浪等），不涉任何真实个人账户或持仓；若接入真实数据，仅读取公开行情，**不采集、不存储任何用户私人信息或交易账户凭据**。
- **使用边界**：仅可用于研究与学习，不得用于违反当地证券法规的用途。

> 发布产物 / 付费门 / 法控总览：见 `DISTRIBUTION.md`


---

## 💰 订阅支持

| 档位 | 价格 | 核心权益 |
|------|------|----------|
| 免费 | ¥0 | 每日高置信信号 |
| Pro | ¥199/月 | 实时信号 + 组合管理 + 回测 |
| 企业 | ¥1999/月 | 私有部署 + 定制策略 |

👉 **[立即订阅 — 爱发电](https://afdian.net/@Zeon7744)**（支付宝 / 微信支付）

> 详细定价见 [pricing.md](pricing.md)


---

## 💛 支持 & 发布（爱发电双通道）

本仓通过**爱发电**完成「**创作者赞赏/订阅收款**」与「**作品/内容社区发布**」双通道运营，二者共存：

| 通道 | 用途 | 入口 |
|------|------|------|
| 💰 爱发电收款 | 赞赏、订阅、Pro 会员、赞助维护 | [爱发电 @Zeon7744](https://afdian.net/@Zeon7744) |
| 📣 爱发电社区发布 | 作品展示、内容连载、粉丝互动、发布分发 | [爱发电社区 @Zeon7744](https://afdian.com/user/0c59dda8a1bb11f19b9552540025c377) |

- **收款**：赞赏 / 订阅 Pro / 企业赞助，支付宝 + 微信支付，无需备案域名
- **社区发布**：把本仓产出（作品 / 剧本 / 工具演示 / 案例）在爱发电社区连载发布，沉淀粉丝、引流回仓
- 两通道独立共存，按需选用；收款不强制绑定社区发布

> 本仓内容仅供创作参考，发布前请完成人工合规审查与平台备案。
