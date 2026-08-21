"""Automated Pytest Suite for VPP Dispatch Optimizer."""

import pytest
import numpy as np
import pandas as pd
from src.vpp_optimizer import VPPOptimizer


@pytest.fixture
def sample_24h_vpp_data():
  hours = 24
  h = np.arange(hours)
  spot = 70.0 + 30.0 * np.sin(2 * np.pi * (h - 6) / 24)
  thermal = np.full(hours, 2.4)
  pv = 6.0 * np.sin(np.pi * np.clip(h - 6, 0, 12) / 12) ** 2
  scada = np.ones(hours)
  scada[18] = 0.0  # single dropout

  return pd.DataFrame({
      "hour": h,
      "spot_price_eur": spot,
      "thermal_demand_mwth": thermal,
      "pv_gen_mw": pv,
      "scada_available": scada,
  })


def test_vpp_optimization_uplift(sample_24h_vpp_data):
  optimizer = VPPOptimizer()
  df_res, kpis = optimizer.optimize_dispatch(sample_24h_vpp_data)

  assert len(df_res) == 24
  assert kpis["realized_profit_eur"] >= kpis["baseline_profit_eur"]
  assert kpis["uplift_generated_eur"] > 0.0


def test_bess_soc_limits(sample_24h_vpp_data):
  optimizer = VPPOptimizer(bess_capacity_mwh=10.0)
  df_res, _ = optimizer.optimize_dispatch(sample_24h_vpp_data)

  assert df_res["bess_soc_mwh"].min() >= 0.99  # >= 10% (1.0 MWh)
  assert df_res["bess_soc_mwh"].max() <= 9.01  # <= 90% (9.0 MWh)
