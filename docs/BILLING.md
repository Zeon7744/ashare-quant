# ashare-quant 收款与门控（面包多 Pay mbd）

## 定价档位（与 billing.py 对齐）
| 档位 | 价格 | 限制 |
|---|---|---|
| Free | ¥0 | 3 次/天辩论 |
| Pro | ¥199/月 | 不限次，3 股辩论 |
| 企业 | ¥1999/月 | 不限次，5 股+回测+API |

## 收款流程（先体验后付费）
1. 免费调用，超限 402 + 升级链接（面包多 Pay https://mbd.com/@Zeon7744）
2. 付款 → `billing.MbdGateway.query_callback` 核验 → 本地提权
3. 无 key 时走 `noop` 安全降级

## 环境变量
`JZ_mbd_USER` / `JZ_mbd_TOKEN` / `BILLING_GATEWAY`（noop|mbd）
