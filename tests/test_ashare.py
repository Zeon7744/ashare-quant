import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ashare_agent

class TestSignal(unittest.TestCase):
    def test_stock_signal(self):
        s = ashare_agent.StockSignal(
            stock_code="600000", signal="BUY", confidence=0.8,
            price=30.0, timestamp=0.0, reason="MLP 高置信")
        self.assertEqual(s.stock_code, "600000")
        self.assertTrue(0.0 <= s.confidence <= 1.0)

    def test_portfolio_count(self):
        p = ashare_agent.Portfolio(cash=1000.0, positions={"600000": 100}, total_value=3000.0)
        self.assertEqual(p.position_count, 1)

if __name__ == "__main__":
    unittest.main()
