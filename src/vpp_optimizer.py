"""
Virtual Power Plant (VPP) Aggregation & Multi-Asset Dispatch Optimizer.
Formulates LP/MILP to maximize Day-Ahead arbitrage profits across BESS, Heat Pumps, and PV with SCADA fallback.
"""

from typing import Dict, Tuple
import numpy as np
import pandas as pd
from scipy.optimize import linprog


class VPPOptimizer:

  def __init__(
      self,
      bess_power_mw: float = 5.0,
      bess_capacity_mwh: float = 10.0,
      bess_eta: float = 0.9486,
      bess_deg_cost: float = 3.0,
      hp_max_mw: float = 2.5,
      hp_min_mw: float = 0.2,
      cop: float = 3.0,
  ):
    self.bess_power_mw = bess_power_mw
    self.bess_capacity_mwh = bess_capacity_mwh
    self.bess_eta = bess_eta
    self.bess_deg_cost = bess_deg_cost
    self.hp_max_mw = hp_max_mw
    self.hp_min_mw = hp_min_mw
    self.cop = cop

  def optimize_dispatch(
      self, df_input: pd.DataFrame
  ) -> Tuple[pd.DataFrame, Dict[str, float]]:
    df = df_input.copy()
    hours = len(df)
    num_vars = 4 * hours  # [P_ch, P_dis, SoC, P_hp]

    # Objective Function: Minimize Cost (or Maximize Net Profit)
    c = np.zeros(num_vars)
    for t in range(hours):
      c[t] = df.loc[t, "spot_price_eur"] + self.bess_deg_cost
      c[hours + t] = -df.loc[t, "spot_price_eur"]
      c[2 * hours + t] = 0.0
      c[3 * hours + t] = df.loc[t, "spot_price_eur"]

    # Equality Constraints: BESS SoC Dynamics
    A_eq = np.zeros((hours, num_vars))
    b_eq = np.zeros(hours)
    for t in range(hours):
      A_eq[t, 2 * hours + t] = 1.0
      A_eq[t, t] = -self.bess_eta
      A_eq[t, hours + t] = 1.0 / self.bess_eta
      if t > 0:
        A_eq[t, 2 * hours + (t - 1)] = -1.0
      else:
        b_eq[0] = 0.5 * self.bess_capacity_mwh

    # Inequality Constraints: Heat Pump Demand Fulfillment
    hp_base_elec = df["thermal_demand_mwth"] / self.cop
    A_ub = np.zeros((hours, num_vars))
    b_ub = np.zeros(hours)
    for t in range(hours):
      A_ub[t, 3 * hours + t] = -1.0
      b_ub[t] = -hp_base_elec.iloc[t]

    # Bounds
    bounds = []
    for _ in range(hours):
      bounds.append((0.0, self.bess_power_mw))
    for _ in range(hours):
      bounds.append((0.0, self.bess_power_mw))
    for _ in range(hours):
      bounds.append(
          (0.1 * self.bess_capacity_mwh, 0.9 * self.bess_capacity_mwh)
      )
    for _ in range(hours):
      bounds.append((self.hp_min_mw, self.hp_max_mw))

    res = linprog(
        c,
        A_ub=A_ub,
        b_ub=b_ub,
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="highs",
    )

    if not res.success:
      raise RuntimeError(f"Optimization Infeasible: {res.message}")

    p_ch_opt = res.x[:hours]
    p_dis_opt = res.x[hours : 2 * hours]
    soc_opt = res.x[2 * hours : 3 * hours]
    p_hp_opt = res.x[3 * hours : 4 * hours]

    vpp_net_opt = (
        df["pv_gen_mw"].values + p_dis_opt - p_ch_opt - p_hp_opt
    )

    # Telemetry Fallback Behavior
    telemetry = df["scada_available"].values
    p_ch_actual = np.where(telemetry == 1.0, p_ch_opt, 0.0)
    p_dis_actual = np.where(telemetry == 1.0, p_dis_opt, 0.0)
    p_hp_actual = np.where(telemetry == 1.0, p_hp_opt, hp_base_elec)
    vpp_net_actual = (
        df["pv_gen_mw"].values + p_dis_actual - p_ch_actual - p_hp_actual
    )

    df["bess_charge_mw"] = p_ch_actual
    df["bess_discharge_mw"] = p_dis_actual
    df["bess_soc_mwh"] = soc_opt
    df["hp_elec_mw"] = p_hp_actual
    df["vpp_net_export_mw"] = vpp_net_actual

    # Financial KPIs
    prices = df["spot_price_eur"].values
    baseline_profit = float(
        np.sum((df["pv_gen_mw"].values - hp_base_elec.values) * prices)
    )
    opt_profit = float(np.sum(vpp_net_opt * prices))
    realized_profit = float(np.sum(vpp_net_actual * prices))

    kpis = {
        "baseline_profit_eur": round(baseline_profit, 2),
        "optimal_profit_eur": round(opt_profit, 2),
        "realized_profit_eur": round(realized_profit, 2),
        "uplift_generated_eur": round(realized_profit - baseline_profit, 2),
        "telemetry_loss_drag_eur": round(opt_profit - realized_profit, 2),
    }

    return df, kpis
