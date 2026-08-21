# 🔋 Virtual Power Plant (VPP) Aggregation & MILP Dispatch Optimizer

[![CI Pipeline](https://img.shields.io/badge/CI%20Pipeline-passing-brightgreen?logo=github&style=flat-square)](https://github.com/Mohammadrezarefaei/vpp-aggregation-milp-dispatch-optimizer/actions)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://vpp-aggregation-milp-dispatch-optimizer-jvkccfkxr3zkbpgug7wzm2.streamlit.app/)

A mathematical optimization and asset-scheduling framework for a Virtual Power Plant (VPP) operating in European Day-Ahead power markets (**EPEX Spot**). Aggregates and dispatches heterogeneous flexible distributed energy resources (**BESS, Industrial Heat Pumps, and Solar PV**) subject to physical operating limits, cycle degradation costs, and real-time **IoT/SCADA telemetry dropout fallbacks**.

---

## 🚀 Live Interactive Demo
👉 **[Access the Live Streamlit Web App](https://vpp-aggregation-milp-dispatch-optimizer-jvkccfkxr3zkbpgug7wzm2.streamlit.app/)**

---

## 📌 Optimization Formulation & Microstructure

1. **Mixed-Integer / Linear Programming (MILP/LP) Core:**
   * Jointly optimizes 24-hour physical schedules to maximize wholesale arbitrage margins while respecting inter-temporal constraints:
     $$\max_{P_{\text{ch}}, P_{\text{dis}}, P_{\text{hp}}} \sum_{t=1}^{24} \Big[ \big( P_{\text{pv},t} + P_{\text{dis},t} - P_{\text{ch},t} - P_{\text{hp},t} \big) \cdot \lambda_t - C_{\text{deg}} \cdot P_{\text{dis},t} \Big]$$

2. **Heterogeneous Asset Constraints:**
   * **Utility BESS:** State-of-Charge (SoC) continuity dynamics, charging/discharging efficiency losses ($\eta_{\text{rt}} \approx 90\%$), and dynamic C-rate degradation throughput penalties.
   * **Industrial Heat Pumps (HP):** Thermally driven base electric load with flexible buffer shifting capability ($P_{\text{hp}} \ge D_{\text{th}}/\text{COP}$).
   * **Commercial PV:** Dynamic solar generation feed-in under midday merit-order spot suppression.

3. **Telemetry Dropout & Fallback Mechanics:**
   * Simulates real-time SCADA signal interruptions (15% dropout rate). The engine safely transitions unresponsive BESS assets into idle mode ($0\text{ MW}$) and defaults thermal units to baseline demand, quantifying the exact P&L drag caused by communication loss.

---

## 🔍 Key Performance Insights

* **Arbitrage Capture:** Generates significant daily cashflow uplift compared to uncoordinated individual asset dispatch by shifting charging to zero/negative midday solar prices and discharging during evening peak spreads.
* **SCADA Resilience:** Accurately prices operational risk and lost commercial opportunity due to distributed IoT communication drops.

---

## 🛠️ Software Architecture & Automated Testing
* **CI/CD Pipeline:** Fully automated testing via **GitHub Actions** (`pytest` validating BESS SoC feasibility bounds $[10\%, 90\%]$, non-negative power flows, and positive optimization uplift).
* **Modular Core Engine:** Implemented in `src/vpp_optimizer.py` utilizing the High-Performance Simplex/Interior-Point solver (`scipy.optimize.linprog` with HiGHS).
* **Tech Stack:** Python 3.11, SciPy, NumPy, Pandas, Matplotlib, Streamlit, Pytest.
