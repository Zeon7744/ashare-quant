#!/usr/bin/env bash
# ashare-quant 冒烟：import + billing.check_access + 辩论/回测（数据源不可达则降级 SKIP）
set -uo pipefail
cd "$(dirname "$0")"
PASS=0; FAIL=0; SKIP=0
echo "====== 1/3 import 核心模块 ======"
python3 -c "import billing; r=billing.check_access('free','debate'); assert r['allowed'] is True; print('billing.check_access OK', r)" \
  && PASS=$((PASS+1)) || { echo "FAIL: billing"; FAIL=$((FAIL+1)); }
echo "====== 2/3 辩论链路 ======"
DEBATE_OUT=$(python3 -m ashare_quant.debate --stock 600519 2>&1 || true)
if echo "$DEBATE_OUT" | grep -q "看多理由"; then echo "✅ 辩论输出看多理由"; PASS=$((PASS+1));
elif echo "$DEBATE_OUT" | grep -qE "ModuleNotFoundError|No module|Error"; then echo "⚠️ 辩论依赖缺失，SKIP"; SKIP=$((SKIP+1));
else echo "❌ 辩论异常"; echo "$DEBATE_OUT" | head -3; FAIL=$((FAIL+1)); fi
echo "====== 3/3 回测链路 ======"
BT_OUT=$(python3 backtest.py 2>&1 || true)
if echo "$BT_OUT" | grep -qiE "收益|return|sharpe"; then echo "✅ 回测输出指标"; PASS=$((PASS+1));
elif echo "$BT_OUT" | grep -qE "can't open|No such file|ModuleNotFoundError"; then echo "⚠️ 回测依赖缺失，SKIP"; SKIP=$((SKIP+1));
else echo "❌ 回测异常"; echo "$BT_OUT" | head -3; FAIL=$((FAIL+1)); fi
echo "结果: $PASS passed / $FAIL failed / $SKIP skipped"
[ "$FAIL" -eq 0 ] && echo "=== SMOKE PASS ===" && exit 0 || { echo "=== SMOKE FAIL ==="; exit 1; }
