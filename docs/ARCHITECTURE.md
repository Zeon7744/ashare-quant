# ashare-quant 模块结构

## 目录
```
ashare-quant/
├── ashare_quant/
│   ├── debate.py        # 多空辩论（多智能体）
│   ├── backtest.py      # 回测引擎
│   ├── data/            # 数据获取
│   └── pro_gates.py    # PRO 门控（PRO_GATES/check_gates）
├── billing.py           # 收款层：NoopGateway + AfdianGateway + PAYWALL_RULES + check_access
├── backtest.py          # 顶层回测入口
└── docs/
```

## 数据流
1. `debate.py` 拉取行情 → 多空角色辩论 → 输出看多/看空理由
2. `backtest.py` 读策略参数 → 逐日撮合 → 输出收益曲线/指标
3. 调用前走 `billing.check_access(plan, action)`；PRO_GATES 控制辩论股数

## 门控模型
- `PRO_GATES`: free(3/天), pro(不限次, 3 股), studio(不限次, 5 股+回测)
- 计数器存 `.pro_state/debate_count.json`
