# ashare-quant 报告输出目录
CI 定时刷新（.github/workflows/data-pipeline.yml）会把每日 A 股 MLP 高置信信号写到这里。
- 数据源：akshare（国内首选，免注册）
- 模型：MLP 高置信（confidence ≥ 阈值 才入选）
