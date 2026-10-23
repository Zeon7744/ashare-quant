#!/usr/bin/env bash
# ashare-quant 一键启动：辩论 + 回测
set -euo pipefail
cd "$(dirname "$0")"
python3 -m ashare_quant.debate --stock 600519
python3 backtest.py
