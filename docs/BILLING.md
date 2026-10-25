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

## 三条收款通道（2026-10-25 结构完善，均未投用）

| # | 通道 | 网关名 | 状态 | 费率 | 到账 | 需填凭据 |
|---|------|--------|------|------|------|----------|
| 1 | 面包多 Pay（mbd.pub） | `mbd` | 结构完整，默认降级待开通 | 2%+0.1元/笔（<0.5元免收，官方核实） | 支付宝 5 分钟内；微信次日自动提现到银行卡 | MBD_APP_ID + MBD_API_KEY（mbd.pub 控制台取） |
| 2 | 微信小程序虚拟支付 | （miniprogram/PAY_CHANNEL） | 骨架已完善（config/pay_virtual.js），默认 none | iOS 12% / Android 1%（官方核实，以开通页为准），T+3 | 个人主体灰度中 | AppID + OfferID + AppKey + 回调 URL（白皇在小程序后台申请） |
| 3 | 支付宝/微信个人赞赏码（兜底） | `praise` | 无密钥可用，默认降级待填码值 | 0 抽成（个人码） | 实时（支付宝/微信） | PRAISE_ALIPAY_QR / PRAISE_WX_QR（个人码码值，手机 App 生成） |

### 赞赏码合规边界（待核实/以官方规则为准）
- 个人收款码非经营收款，长期大额经营收款会被风控；大额触发线经验值：单笔 5000 元、日累计 1万 元（支付宝经验值，非官方红线）
- 税务：个人经营收款若形成持续收入，建议并入年度经营所得申报（个体户/小微更合规）
- 赞赏码定位为「mbed 未开通期间的轻量兜底」，非长期主力；主力通道为 mbd.pub 或 小程序虚拟支付

### 开通验证前置清单（白皇开通后，我如何真验）
- mbd.pub：填 MBD_API_KEY/MBD_APP_ID → 跑 `billing.get_gateway('mbd').create_order(...)` → 验证返回 body（form HTML）可正常渲染 → 1 元真实下单 → 核 Webhook 回调（out_trade_no 匹配）
- 虚拟支付：填 AppID/OfferID/AppKey + PAY_CHANNEL=wx_virtual → 真机调试 wx.requestVirtualPayment → 验 signData/paySig 签名 → 沙盒环境（env=1）下单
- 赞赏码：填 PRAISE_ALIPAY_QR → 扫真码付 1 元 → 白皇手动核对到账 → 调 `mark_paid(order_id)` 放行 → 台账 praise_ledger.jsonl 有 paid 记录
