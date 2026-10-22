#!/usr/bin/env bash
# smoke_test.sh — 快速验证 debate + backtest 核心链路
set -euo pipefail

PASS=0
FAIL=0

echo "====== 1/2  debate --stock 600519 ======"
DEBATE_OUT=$(python -m ashare_quant.debate --stock 600519 2>&1) || true
echo "$DEBATE_OUT"

if echo "$DEBATE_OUT" | grep -q "看多理由"; then
  echo "✅ 包含「看多理由」"
  PASS=$((PASS+1))
else
  echo "❌ 缺少「看多理由」"
  FAIL=$((FAIL+1))
fi

if echo "$DEBATE_OUT" | grep -q "看空理由"; then
  echo "✅ 包含「看空理由」"
  PASS=$((PASS+1))
else
  echo "❌ 缺少「看空理由」"
  FAIL=$((FAIL+1))
fi

echo ""
echo "====== 2/2  backtest.py ======"
BT_OUT=$(python backtest.py 2>&1) || true
echo "$BT_OUT"

if echo "$BT_OUT" | grep -qE "QC passed|回测"; then
  echo "✅ backtest 正常输出"
  PASS=$((PASS+1))
else
  echo "❌ backtest 输出异常"
  FAIL=$((FAIL+1))
fi

echo ""
echo "====== 结果: ${PASS} passed / ${FAIL} failed ======"
[ "$FAIL" -eq 0 ] || exit 1
