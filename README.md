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
