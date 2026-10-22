#!/usr/bin/env bash
# run.sh — 一键安装依赖 + 运行多空辩论
# 用法: bash run.sh [股票代码]  (默认 600519)
set -euo pipefail

STOCK="${1:-600519}"

echo "📦 安装依赖..."
pip install -r requirements.txt -q 2>/dev/null || pip install -r requirements.txt

echo "🚀 运行多空辩论: ${STOCK}"
python -m ashare_quant.debate --stock "$STOCK"
