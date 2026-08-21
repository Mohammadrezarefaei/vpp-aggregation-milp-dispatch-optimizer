"""Streamlit Web App: Virtual Power Plant (VPP) Aggregated Dispatch Optimizer."""

import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from src.vpp_optimizer import VPPOptimizer

st.set_page_config(
    page_title="VPP Multi-Asset Dispatch Optimizer",
    page_icon="🔋",
    layout="wide"
)

st.title("🔋 VPP Multi-Asset Aggregation & MILP Dispatch Optimizer")
st.markdown("Optimal **EPEX Day-Ahead Arbitrage** scheduling across heterogeneous flexible assets (**BESS, Industrial Heat Pumps, Rooftop PV**) under **IoT SCADA Dropouts**.")

# Sidebar Parameters
st.sidebar.header("⚙️ Battery Storage (BESS)")
bess_power = st.sidebar.slider("BESS Power (MW)", 1.0, 15.0, 5.0, 1.0)
bess_cap = st.sidebar.slider("BESS Capacity (MWh)", 2.0, 30.0, 10.0, 2.0)
deg_cost = st.sidebar.slider("Degradation Cost (€/MWh)", 0.0, 10.0, 3.0, 0.5)

st.sidebar.header("⚙️ Flexible Thermal & Solar")
pv_capacity = st.sidebar.slider("Rooftop PV Peak (MWp)", 2.0, 20.0, 8.0, 1.0)
hp_max = st.sidebar.slider("Heat Pump Max Power (MW)", 1.0, 5.0, 2.5, 0.5)
scada_dropout_rate = st.sidebar.slider("SCADA Dropout Rate (%)", 0, 40, 15, 5)

@st.cache_data
def generate_market_data(pv_cap, dropout_pct):
    np.random.seed(42)
    hours = 24
    h_arr = np.arange(hours)
    
    spot = 65.0 + 35.0 * np.sin(2 * np.pi * (h_arr - 6) / 24) + np.random.normal(0, 5.0, hours)
    spot[12:16] -= 25.0
    
    thermal_demand = np.array([
        2.2, 2.0, 1.8, 1.8, 2.0, 2.5, 3.2, 3.5, 3.0, 2.5, 2.2, 2.0,
        1.8, 1.8, 2.0, 2.2, 2.8, 3.5, 3.8, 3.5, 3.0, 2.8, 2.5, 2.2
    ])
    
    solar_profile = np.sin(np.pi * np.clip(h_arr - 6, 0, 12) / 12) ** 2
    pv_gen = pv_cap * solar_profile * np.random.uniform(0.85, 1.0, hours)
    
    p_drop = dropout_pct / 100.0
    scada = np.random.choice([1.0, 0.0], size=hours, p=[1.0 - p_drop, p_drop])
    
    return pd.DataFrame({
        "hour": h_arr,
        "spot_price_eur": spot,
        "thermal_demand_mwth": thermal_demand,
        "pv_gen_mw": pv_gen,
        "scada_available": scada
    })

df_raw = generate_market_data(pv_capacity, scada_dropout_rate)
optimizer = VPPOptimizer(
    bess_power_mw=bess_power,
    bess_capacity_mwh=bess_cap,
    bess_deg_cost=deg_cost,
    hp_max_mw=hp_max
)

df_res, kpis = optimizer.optimize_dispatch(df_raw)

# Metrics Display
m1, m2, m3, m4 = st.columns(4)
m1.metric("Realized VPP Profit", f"€{kpis['realized_profit_eur']:,.2f} / day")
m2.metric("Unoptimized Baseline", f"€{kpis['baseline_profit_eur']:,.2f} / day")
m3.metric("Net Optimization Uplift", f"€{kpis['uplift_generated_eur']:,.2f}", delta=f"+€{kpis['uplift_generated_eur']:,.2f}")
m4.metric("SCADA Telemetry Drag", f"-€{kpis['telemetry_loss_drag_eur']:,.2f}", delta=f"-{kpis['telemetry_loss_drag_eur']:,.2f} €", delta_color="inverse")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("⚡ Aggregated Dispatch & Asset Power Stacking")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

    ax1.plot(df_res["hour"], df_res["spot_price_eur"], color="#DC2626", lw=2.0, label="Spot DA Price (€/MWh)")
    ax1.set_ylabel("Price [€/MWh]", color="#DC2626", fontweight="bold")
    ax1.grid(True, linestyle=":", alpha=0.6)

    ax1_twin = ax1.twinx()
    ax1_twin.step(df_res["hour"], df_res["vpp_net_export_mw"], where="mid", color="#2563EB", lw=2.2, label="Net VPP Export (MW)")
    ax1_twin.set_ylabel("Net Export [MW]", color="#2563EB", fontweight="bold")
    ax1.set_title("VPP Aggregated Dispatch under Telemetry Dropouts", fontsize=10, fontweight="bold")

    ax2.bar(df_res["hour"] - 0.2, df_res["pv_gen_mw"], width=0.4, color="#F59E0B", alpha=0.7, label="Solar PV (MW)")
    ax2.bar(df_res["hour"] + 0.2, df_res["bess_discharge_mw"], width=0.4, color="#10B981", alpha=0.8, label="BESS Disch (MW)")
    ax2.bar(df_res["hour"] + 0.2, -df_res["bess_charge_mw"], width=0.4, color="#6366F1", alpha=0.8, label="BESS Chg (MW)")
    ax2.step(df_res["hour"], -df_res["hp_elec_mw"], where="mid", color="#EC4899", lw=2.0, label="Heat Pump (MW)")

    dropouts = df_res[df_res["scada_available"] == 0.0]["hour"].values
    for dh in dropouts:
        ax2.axvspan(dh - 0.5, dh + 0.5, color="#94A3B8", alpha=0.25, label="SCADA Drop (Fallback)" if dh == dropouts[0] else "")

    ax2.set_xlabel("Hour of Day [0-23]", fontweight="bold")
    ax2.set_ylabel("Power [MW]", fontweight="bold")
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.legend(loc="upper right", frameon=True, fontsize=7.5, ncol=2)

    plt.tight_layout()
    st.pyplot(fig)

with col2:
    st.subheader("📋 Performance Summary")
    st.dataframe(
        pd.DataFrame({
            "Metric": ["Baseline Daily Revenue", "Optimal Dispatch Profit", "Realized Daily Profit", "Net Value Uplift", "SCADA Signal Drag", "BESS Storage Size"],
            "Value": [
                f"€{kpis['baseline_profit_eur']:,.2f}",
                f"€{kpis['optimal_profit_eur']:,.2f}",
                f"€{kpis['realized_profit_eur']:,.2f}",
                f"€{kpis['uplift_generated_eur']:,.2f}",
                f"-€{kpis['telemetry_loss_drag_eur']:,.2f}",
                f"{bess_power:.1f} MW / {bess_cap:.1f} MWh"
            ]
        }),
        hide_index=True,
        use_container_width=True
    )
    st.markdown("""
    **Operational Mechanics:**
    * **Arbitrage Capture:** BESS charges during midday solar suppression and discharges during morning/evening peak spreads.
    * **Thermal Demand:** Heat pump consumption shifts dynamically according to price signals while guaranteeing heat supply.
    * **SCADA Fallback:** Protects physical assets by holding BESS idle during IoT signal drops.
    """)

st.markdown("---")
st.caption("Virtual Power Plant (VPP) High-Dimensional MILP Optimization Framework for European Power Markets.")
