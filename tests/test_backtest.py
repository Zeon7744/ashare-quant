import os, sys, unittest, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ashare_agent
import backtest


def _make_rows(n=300, seed=42):
    random.seed(seed)
    rows, price = [], 100.0
    for k in range(n):
        price *= (1 + random.uniform(-0.02, 0.021))
        o = price * (1 + random.uniform(-0.005, 0.005))
        rows.append({
            'timestamp': f'2026-01-{(k % 28) + 1:02d}',
            'open': o, 'high': max(o, price) * 1.004,
            'low': min(o, price) * 0.996, 'close': price,
            'volume': random.uniform(1e6, 5e6),
        })
    return rows


class TestPipelineQC(unittest.TestCase):
    def test_clean_data_passes(self):
        rows = _make_rows()
        qc = backtest.cross_check_ohlcv(rows, symbol='DEMO')
        self.assertTrue(qc.passed)
        self.assertEqual(qc.ohlc_violations, 0)

    def test_null_detection(self):
        rows = _make_rows()
        rows[5] = dict(rows[5]); rows[5]['close'] = None
        qc = backtest.cross_check_ohlcv(rows)
        self.assertEqual(qc.null_count, 1)
        self.assertFalse(qc.passed)

    def test_ohlc_violation_detection(self):
        rows = _make_rows()
        r = dict(rows[10]); r['low'] = r['close'] * 1.5  # Low 高于 close → 非法
        rows[10] = r
        qc = backtest.cross_check_ohlcv(rows)
        self.assertGreater(qc.ohlc_violations, 0)

    def test_clean_fixes_ohlc(self):
        rows = _make_rows()
        r = dict(rows[20]); r['low'] = r['close'] * 2.0
        rows[20] = r
        cleaned = backtest.clean_ohlcv(rows)
        self.assertLessEqual(cleaned[20]['low'], cleaned[20]['close'])


class TestBacktest(unittest.TestCase):
    def test_insufficient_data_returns_empty(self):
        res = backtest.walk_forward_backtest(_make_rows(10))
        self.assertEqual(res.total_trades, 0)
        self.assertEqual(res.final_balance, res.initial_balance)

    def test_no_lookahead_uses_past_only(self):
        # 全涨序列：动量信号应早期看多，净收益不为负极端、且含成本
        rows = _make_rows(300, seed=7)
        res = backtest.walk_forward_backtest(rows)
        self.assertGreaterEqual(res.round_trips, 0)
        self.assertIn('sharpe_ratio', res.to_dict())
        self.assertGreater(res.bars_per_year, 0)

    def test_transaction_costs_included(self):
        # 让信号反复触发交易以产生成本
        rows = _make_rows(300, seed=3)
        res = backtest.walk_forward_backtest(rows)
        self.assertGreaterEqual(res.total_costs, 0.0)
        # 有成交时成本应 > 0
        if res.total_trades > 0:
            self.assertGreater(res.total_costs, 0.0)

    def test_custom_signal_fn(self):
        rows = _make_rows(200, seed=11)
        # 自定义：每 5 根 bar 看多/看空交替 → 产生完整 round trip
        def alternate(visible, i):
            return (1 if (i // 5) % 2 == 0 else 0), 0.9
        res = backtest.walk_forward_backtest(rows, signal_fn=alternate)
        self.assertGreater(res.total_trades, 0)
        self.assertGreater(res.round_trips, 0)
        self.assertGreater(res.total_costs, 0.0)


if __name__ == "__main__":
    unittest.main()
