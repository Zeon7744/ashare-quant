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

免费=每日高置信信号（Gitee 公开）；Pro=实时信号+组合管理；企业=私有部署

- **免费**：立即 [安装/克隆] 使用，命中配额即可升级。
- **Pro**：[Gitee Pro 订阅](https://gitee.com/Zeon7744) 解锁高级能力。
- **企业**：私有部署 / 定制需求 → 见 `pricing.md`，或联系商务（GitHub Issues / Gitee）。

> 详细定价与 SKU 见 [pricing.md](pricing.md) ｜ 支持项目见 [FUNDING.yml](FUNDING.yml)

---

## 快速上手
依赖安装：
```bash
python3 -m pip install -r requirements.txt
```

## 变现路径
研究仓，变现路径=开源背书→量化内容输出→咨询/课程（非代码直接售卖）。
> 定价与赞助：见仓库内 pricing.md / FUNDING.yml（若有）。

---

## ⚖️ 法控声明（Non-investment-advice disclaimer）

- **非投资建议 / 非投资顾问**：本项目是 A 股研究与教学用途的量化工具，**不构成任何投资建议、证券研究意见或投资顾问服务**。回测胜率、夏普、walk-forward 等指标均基于历史行情，**不代表未来收益**，不构成买卖依据。
- **合规免责**：使用本工具产生的任何 A 股交易决策由使用者自行承担，本项目作者不对任何交易结果、亏损或合规责任负责。实盘交易请自行遵守中国《证券法》及交易所规则。
- **数据脱敏**：行情数据来自公开数据源（东财/新浪等），不涉任何真实个人账户或持仓；若接入真实数据，仅读取公开行情，**不采集、不存储任何用户私人信息或交易账户凭据**。
- **使用边界**：仅可用于研究与学习，不得用于违反当地证券法规的用途。

> 发布产物 / 付费门 / 法控总览：见 `DISTRIBUTION.md`
