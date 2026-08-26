#!/usr/bin/env python3
"""
test_anomaly_separability.py — Unit test proving Isolation Forest separability across anomaly archetypes (MAR-X2).
"""

import math
import sys
import unittest
from pathlib import Path
import numpy as np
from sklearn.ensemble import IsolationForest

# Add metrics & protocol to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "experiments" / "metrics"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "experiments" / "protocol"))
import evaluation_metrics as em
import statistical_methods as sm

class TestAnomalySeparability(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(42)
        n_normal = 1000
        
        # Normal feature distribution:
        # [mid_price, spread, spread_bps, log_return, rolling_vol, order_imbalance, volume]
        mid_prices = 100.0 + np.cumsum(rng.normal(0, 0.01, n_normal))
        spreads = np.clip(rng.normal(0.02, 0.005, n_normal), 0.01, 0.05)
        spread_bps = (spreads / mid_prices) * 10000.0
        log_returns = rng.normal(0, 0.0005, n_normal)
        rolling_vols = np.clip(rng.normal(0.001, 0.0002, n_normal), 0.0005, 0.002)
        order_imbalances = np.clip(rng.normal(0.0, 0.2, n_normal), -0.6, 0.6)
        volumes = rng.integers(10, 100, n_normal).astype(float)
        
        self.X_normal = np.column_stack([
            mid_prices, spreads, spread_bps, log_returns, rolling_vols, order_imbalances, volumes
        ])
        
        # Injected Archetype 1: Price Shock (extreme log_return & rolling_vol)
        n_shock = 50
        shock_mid = 100.0 + np.ones(n_shock) * 5.0 # +5% jump
        shock_spread = np.ones(n_shock) * 0.05
        shock_spread_bps = (shock_spread / shock_mid) * 10000.0
        shock_log_ret = np.ones(n_shock) * 0.045 # 90x normal sigma
        shock_vol = np.ones(n_shock) * 0.015
        shock_imb = np.zeros(n_shock)
        shock_v = np.ones(n_shock) * 500.0
        self.X_shock = np.column_stack([
            shock_mid, shock_spread, shock_spread_bps, shock_log_ret, shock_vol, shock_imb, shock_v
        ])
        
        # Injected Archetype 2: Spread Blowout (extreme spread & spread_bps)
        n_spread = 50
        spread_mid = 100.0 * np.ones(n_spread)
        spread_blowout = np.ones(n_spread) * 0.80 # 40x normal spread
        spread_bps_blowout = (spread_blowout / spread_mid) * 10000.0
        spread_log_ret = np.zeros(n_spread)
        spread_vol = np.ones(n_spread) * 0.005
        spread_imb = np.zeros(n_spread)
        spread_v = np.ones(n_spread) * 200.0
        self.X_spread = np.column_stack([
            spread_mid, spread_blowout, spread_bps_blowout, spread_log_ret, spread_vol, spread_imb, spread_v
        ])
        
        # Injected Archetype 3: Quote Stuffing (extreme order_imbalance & message volume burst)
        n_stuff = 50
        stuff_mid = 100.0 * np.ones(n_stuff)
        stuff_spread = np.ones(n_stuff) * 0.05
        stuff_spread_bps = (stuff_spread / stuff_mid) * 10000.0
        stuff_log_ret = np.zeros(n_stuff)
        stuff_vol = np.ones(n_stuff) * 0.005
        stuff_imb = np.ones(n_stuff) * 0.99 # OFI near +1.0
        stuff_v = np.ones(n_stuff) * 1500.0 # High volume quote burst
        self.X_stuff = np.column_stack([
            stuff_mid, stuff_spread, stuff_spread_bps, stuff_log_ret, stuff_vol, stuff_imb, stuff_v
        ])


    def test_isolation_forest_separability(self):
        # Train Isolation Forest on normal background data
        model = IsolationForest(n_estimators=100, max_samples=256, random_state=42)
        model.fit(self.X_normal)
        
        # Score_samples returns negative anomaly score in [-1.0, 0.0]; convert to standard score in [0.0, 1.0]
        # s(x) = 0.5 - decision_function(x) / 2.0
        norm_scores = 0.5 - model.decision_function(self.X_normal)
        shock_scores = 0.5 - model.decision_function(self.X_shock)
        spread_scores = 0.5 - model.decision_function(self.X_spread)
        stuff_scores = 0.5 - model.decision_function(self.X_stuff)
        
        # Normal score mean should be near 0.45 - 0.50
        self.assertLess(np.mean(norm_scores), 0.55)
        
        # All 3 anomaly archetypes must achieve high anomaly scores
        self.assertGreater(np.mean(shock_scores), 0.60)
        self.assertGreater(np.mean(spread_scores), 0.65)
        self.assertGreater(np.mean(stuff_scores), 0.55)
        
        # AUC-ROC for each archetype vs normal background must be > 0.95
        auc_shock = em.compute_auc_roc(
            [0]*len(norm_scores) + [1]*len(shock_scores),
            np.concatenate([norm_scores, shock_scores])
        )
        auc_spread = em.compute_auc_roc(
            [0]*len(norm_scores) + [1]*len(spread_scores),
            np.concatenate([norm_scores, spread_scores])
        )
        auc_stuff = em.compute_auc_roc(
            [0]*len(norm_scores) + [1]*len(stuff_scores),
            np.concatenate([norm_scores, stuff_scores])
        )
        
        self.assertGreater(auc_shock, 0.95)
        self.assertGreater(auc_spread, 0.95)
        self.assertGreater(auc_stuff, 0.95)
        
        # Statistical significance: Mann-Whitney / Cliff's delta large
        delta_shock = sm.cliffs_delta(shock_scores, norm_scores)
        delta_spread = sm.cliffs_delta(spread_scores, norm_scores)
        delta_stuff = sm.cliffs_delta(stuff_scores, norm_scores)
        
        self.assertGreaterEqual(delta_shock, 0.80)
        self.assertGreaterEqual(delta_spread, 0.80)
        self.assertGreaterEqual(delta_stuff, 0.80)

if __name__ == "__main__":
    unittest.main()
