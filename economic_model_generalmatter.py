import streamlit as st
import numpy as np
import pandas as pd
from itertools import product

# --- Page Configuration ---
st.set_page_config(
    page_title="General Matter Economic Model",
    layout="wide"
)

st.title("General Matter Economic Model")
st.caption("Five-year component, battery cell count, maintenance, duty cycle, and FMEA optimization dashboard.")

# --- Help Guide Expander ---
with st.expander("Help Guide"):
    st.markdown("""
    **Overview:**
    This application allows you to configure, evaluate, and optimize component and battery selections for system units over a multi-year horizon.
    
    * **Left Side (Controls & Inputs):** Contains interactive parameters for optimization, financial constraints, power requirements, duty cycles, and preference weights. Use these inputs to model different operational scenarios.
    * **Right Side (Results & Outputs):** Displays real-time financial metrics, required cell counts, system power/energy totals, total discrete objective scores, failure probability counters, and itemized subsystem breakdowns.
    
    ---
    
    **Sidebar Sections:**
    * **Analysis Mode:** Toggle between *Automated Optimization* (evaluates all valid combinations to minimize total cost + penalties) and *Manual Selection* (manually inspect specific component configurations).
    * **Financial & Operational:** Set batch order quantities, initial box budgets, technician labor rates, evaluation horizons, hardware tax rates, and scheduled replacement settings.
    * **Power & Battery Configuration:** Adjust base board power, conversion efficiency, safety capacity multipliers, and usable cell energy discharge ratios.
    * **Duty Cycle Timings:** Define active operational durations and periodic interval frequencies for sensors, localization modules, and actuation assemblies.
    * **Objective Weights:** Tune penalty multipliers applied to risk priority numbers (RPN) and average power draw.
    """)

# --- Sidebar Controls ---
st.sidebar.header("Optimization Parameters")

mode = st.sidebar.radio(
    "Analysis Mode",
    ["Automated Optimization", "Manual Selection (Client Mode)"],
    help="• Automated Optimization: Evaluates all feasible combinations and finds the exact discrete minimum objective.\n• Manual Selection: Allows testing of explicit component choices."
)

st.sidebar.markdown("---")
st.sidebar.subheader("Financial & Operational")

batch_size = st.sidebar.number_input(
    "Batch Order Quantity (Units)", min_value=1, value=1, step=1,
    help="Number of identical boxes in the batch order for volume tier pricing."
)
budget = st.sidebar.number_input(
    "Budget ($)", min_value=100.0, value=2000.00, step=100.0,
    help="Maximum allowable initial purchase expenditure for one box (components + battery cells)."
)
labour = st.sidebar.number_input(
    "Labor Rate ($/hr)", min_value=0.0, value=80.0, step=5.0,
    help="Hourly technician rate for scheduled maintenance and field repair labor."
)
years = st.sidebar.number_input(
    "Analysis Horizon (Years)", min_value=1, value=5, step=1,
    help="Multi-year planning horizon for battery capacity, annual inspections, and failure repairs."
)
include_year5_replacement = st.sidebar.checkbox(
    "Include Scheduled Replacement Every 5 Years", value=True,
    help="Uncheck to turn off automatic scheduled hardware replacements every 5 years."
)
tax_rate = st.sidebar.number_input(
    "Hardware Tax Rate", min_value=0.0, max_value=0.5, value=0.10, step=0.01,
    help="Sales/hardware tax rate applied to component and cell purchases."
)

inspections_per_year = st.sidebar.number_input(
    "Inspection Visits per Year", min_value=0, max_value=12, value=1, step=1,
    help="All selected components are inspected during the same visit."
)
shared_inspection_minutes = st.sidebar.number_input(
    "Shared Access/Setup Time per Visit (min)", min_value=0.0, value=15.0, step=1.0,
    help="Assumed access, setup, and documentation time allocated to one box."
)

st.sidebar.markdown("---")
st.sidebar.subheader("Power & Battery Configuration")

shared_power = st.sidebar.number_input(
    "Shared Board Power Allowance (mW)", min_value=0.0, value=2.0, step=0.05,
    help="Unmeasured load allowance for logging, processing, and other electronics."
)
conversion_efficiency = st.sidebar.slider(
    "DC-DC Conversion Efficiency", min_value=0.50, max_value=1.00, value=0.90, step=0.01,
    help="Efficiency of voltage regulation/boost circuitry transferring energy from battery to load."
)
reserve_factor = st.sidebar.slider(
    "Battery Reserve Factor Multiplier", min_value=1.00, max_value=2.00, value=1.20, step=0.05,
    help="Safety margin multiplier for battery capacity sizing."
)
usable_fraction = st.sidebar.slider(
    "Usable Battery Discharge Fraction", min_value=0.10, max_value=1.00, value=0.70, step=0.05,
    help="Usable fraction of nominal capacity."
)

st.sidebar.markdown("---")
st.sidebar.subheader("Duty Cycle Timings (Seconds)")

temp_on = st.sidebar.number_input("Temp Sensor Active (s)", min_value=0.01, value=1.0)
temp_interval = st.sidebar.number_input("Temp Sensor Interval (s)", min_value=1.0, value=21600.0)

uwb_on = st.sidebar.number_input("UWB Active (s)", min_value=0.01, value=0.1)
uwb_interval = st.sidebar.number_input("UWB Interval (s)", min_value=1.0, value=43200.0)

gnss_on = st.sidebar.number_input("GNSS Active (s)", min_value=0.1, value=60.0)
gnss_interval = st.sidebar.number_input("GNSS Interval (s)", min_value=1.0, value=302400.0)

releases_per_year = st.sidebar.number_input("Releases / Year", min_value=0.0, value=2.0)
release_seconds = st.sidebar.number_input("Release Duration (s)", min_value=0.0, value=5.0)

st.sidebar.markdown("---")
st.sidebar.subheader("Objective Weights")

risk_weight = st.sidebar.slider(
    "RPN Risk Penalty ($ / 100 RPN)", min_value=0.0, max_value=200.0, value=50.0, step=5.0,
    help="Dollar-equivalent penalty per 100 Risk Priority Number (RPN) points."
)
power_weight = st.sidebar.slider(
    "Power Penalty ($ / avg mW)", min_value=0.0, max_value=20.0, value=1.0, step=0.5,
    help="Dollar-equivalent preference score penalty per average milliwatt of system load."
)

# --- Code Calculations ---
tax_multiplier = 1 + tax_rate
hours = years * 365 * 24

# Scheduled replacement multiplier logic
scheduled_replacement_count = (years // 5) if include_year5_replacement else 0

# Data array: [Purchase Price, Inspection Min, Replacement Hr, Debug Hr, Annual Failure Probability]
data = np.array([
    [3.145, 2, .50, .25, .010],   # 0 uxcell 10K NTC
    [6.31,  2, .50, .25, .015],   # 1 NPSSH103F3 NTC
    [20.00, 2, .50, .25, .010],   # 2 SQ-ASD Shock Sensor
    [29.50, 1, .50, .50, .015],   # 3 Qorvo DWM3001C
    [8.29,  1, .50, .50, .015],   # 4 LC76G Multi-GNSS
    [13.75, 1, .50, .50, .015],   # 5 SAM-M10Q-00B
    [25.11, 2, .25, .25, .010],   # 6 Tadiran TL-5930/S
    [4.97,  2, .25, .25, .020],   # 7 Panasonic BK120AAHA01
    [100.00, 2, .50, .50, .020],  # 8 Aluminum Enclosure
    [23.02, 2, .50, .50, .030],   # 9 PETG Enclosure
    [88.07, 2, .25, .25, .005],   # 10 C Clamp
    [77.04, 2, .25, .25, .005],   # 11 Permanent Magnet
    [33.80, 2, .50, .50, .020],   # 12 Energize-to-release Magnet
])

names = [
    "uxcell 10K NTC Probe", "NPSSH103F3T1NDM01 Temp Sensor", "SQ-ASD",
    "Qorvo DWM3001C", "LC76G Multi-GNSS", "SAM-M10Q-00B",
    "Tadiran TL-5930/S", "Panasonic BK120AAHA01",
    "Aluminum Enclosure", "PETG Enclosure", "C Clamp",
    "Permanent Magnet", "Energize-to-release Magnet"
]

categories = [(0, 1), (2,), (3,), (4, 5), (6, 7), (8, 9), (10, 11, 12)]
cat_names = [
    "Temperature Sensor", "Shock Sensor", "Indoor Location",
    "Outdoor Location", "Battery Chemistry", "Enclosure", "Attachment"
]

bulk_prices = {
    0: [(10, None, 3.145), (100, None, 3.145), (1000, None, 3.145)],
    1: [(10, None, 5.44), (100, None, 4.79), (1000, None, 4.31)],
    2: [(50, None, 15.00)],
    3: [(10, None, 29.50), (100, None, 29.50), (1000, None, 29.50)],
    4: [(10, None, 7.19), (100, None, 6.2824), (1000, None, 5.53651)],
    5: [(10, None, 13.75), (100, None, 13.75), (1000, None, 11.23752)],
    6: [(10, None, 22.00), (100, None, 17.07), (1000, None, 11.00)],
    7: [(10, None, 3.91), (100, None, 3.42), (1000, None, 2.78)],
    11: [(50, None, 57.31)],
}

def unit_price(j, order_quantity):
    return tax_multiplier * min(
        [data[j, 0]] + [price for low, high, price in bulk_prices.get(j, [])
                        if low <= order_quantity and (high is None or order_quantity <= high)]
    )

nominal_cell_wh = np.array([3.6 * 19.0, 1.2 * 1.2])
usable_energy = nominal_cell_wh * usable_fraction * conversion_efficiency
pack_hardware_cost = np.array([0.0, 0.0])

purchase, inspection_minutes, replacement_hours, diagnosis_hours, p = data.T
events = years * p
inspection_visits = years * inspections_per_year
shared_inspection_cost = inspection_visits * labour * shared_inspection_minutes / 60.0

initial = np.array([unit_price(j, batch_size) for j in range(13)])
initial[6:8] = pack_hardware_cost
inspections = inspection_visits * labour * inspection_minutes / 60.0
replacement = initial + labour * replacement_hours
scheduled = scheduled_replacement_count * replacement
maintenance = inspections + scheduled

repair_purchase = purchase * tax_multiplier
repair_purchase[6:8] = pack_hardware_cost
repair_event = repair_purchase + labour * (replacement_hours + diagnosis_hours)
repairs = events * repair_event
cost = initial + maintenance + repairs

lowest_cell_prices = np.array([
    min([purchase[j]] + [tier[2] for tier in bulk_prices.get(j, [])])
    for j in (6, 7)
])
max_cells = np.floor(budget / (tax_multiplier * lowest_cell_prices)).astype(int)

tadiran_rpn = 240 + 144 + 96       # 480
panasonic_rpn = 96 + 120 + 243 + 96 # 555
rpn = np.zeros(13)
rpn[6:8] = [tadiran_rpn, panasonic_rpn]

power_data = np.array([
    [0.33, 0, 0],                  # 0 uxcell
    [0.33, 0, 0],                  # 1 NPSSH103F3
    [0.00363, 0, 0.00363],         # 2 SQ-ASD
    [120.0, 0, 0.00255],           # 3 Qorvo
    [32.66, 32.66, 0.0429],        # 4 LC76G
    [45.91, 45.91, 0.0924],        # 5 SAM-M10Q
    [0, 0, 0],                     # 6 Tadiran
    [0, 0, 0],                     # 7 Panasonic
    [0, 0, 0],                     # 8 Aluminum
    [0, 0, 0],                     # 9 PETG
    [0, 0, 0],                     # 10 C Clamp
    [0, 0, 0],                     # 11 Permanent Magnet
    [6800.0, 0, 0],                # 12 Energize-to-release
])

active_fraction = np.zeros(13)
active_fraction[0:2] = temp_on / temp_interval
active_fraction[2] = 1.0
active_fraction[3] = uwb_on / uwb_interval
active_fraction[4:6] = gnss_on / gnss_interval
active_fraction[12] = releases_per_year * release_seconds / (365 * 24 * 3600)

acquisition_fraction = np.zeros(13)
idle_fraction = 1 - active_fraction - acquisition_fraction

operating, acquisition, idle = power_data.T
power = (active_fraction * operating + acquisition_fraction * acquisition + idle_fraction * idle)
energy = power * hours / 1000.0

# --- Layout Implementation ---
col_left, col_right = st.columns([1, 1])
selected_indices = {}
best_cells = 1
b_type = 0

with col_left:
    st.subheader("Hardware & Battery Selection")
    
    if mode == "Manual Selection (Client Mode)":
        st.info("Pick components manually to inspect real-time capacity and cost metrics.")
        for cat_idx, (cat_name, tuple_indices) in enumerate(zip(cat_names, categories)):
            options = [names[i] for i in tuple_indices]
            choice = st.selectbox(f"Select {cat_name}:", options, key=f"select_{cat_idx}")
            selected_indices[cat_name] = tuple_indices[options.index(choice)]
            
        chosen_indices = np.array(list(selected_indices.values()))
        b_type = chosen_indices[4] - 6
        avg_power = shared_power + power[chosen_indices].sum()
        pack_energy = avg_power * hours / 1000.0
        best_cells = max(1, int(np.ceil(reserve_factor * pack_energy / usable_energy[b_type])))
    else:
        st.success("Optimization Mode Active — Evaluating exact discrete combinations.")
        best = None
        minimum = np.inf
        feasible_count = 0

        for choice in product(*categories):
            i = np.array(choice)
            b = choice[4] - 6
            
            average_power = shared_power + power[i].sum()
            pack_energy = average_power * hours / 1000.0
            required_cells = max(1, int(np.ceil(reserve_factor * pack_energy / usable_energy[b])))
            
            combination_feasible = False
            for n_cells in range(required_cells, max_cells[b] + 1):
                cell_initial = unit_price(6 + b, batch_size * n_cells)
                cell_maintenance = scheduled_replacement_count * cell_initial
                cell_repairs = events[6 + b] * unit_price(6 + b, n_cells)
                cell_cost = cell_initial + cell_maintenance + cell_repairs

                upfront = initial[i].sum() + n_cells * cell_initial
                if upfront > budget:
                    continue

                obj = (cost[i].sum() + n_cells * cell_cost + shared_inspection_cost
                       + risk_weight * rpn[i].sum() / 100.0 + power_weight * average_power)
                
                combination_feasible = True
                if obj < minimum:
                    minimum, best = obj, i
                    best_battery, best_cells = b, n_cells

            feasible_count += int(combination_feasible)

        if best is None:
            st.error("Over Budget or Infeasible! No component combination satisfies the budget.")
            st.stop()
        else:
            b_type = best_battery
            for cat_name, idx_val in zip(cat_names, best):
                selected_indices[cat_name] = idx_val
                count_str = f" x{best_cells} cells" if idx_val in (6, 7) else ""
                st.markdown(f"**{cat_name}:** `{names[idx_val]}{count_str}`")
            st.caption(f"Feasible configurations evaluated: {feasible_count} combinations")

# --- Detailed Evaluation ---
chosen_indices = np.array(list(selected_indices.values()))
cell_idx = 6 + b_type
cell_initial_price = unit_price(cell_idx, batch_size * best_cells)
cell_maintenance_price = scheduled_replacement_count * cell_initial_price
cell_repairs_price = events[cell_idx] * unit_price(cell_idx, best_cells)

initial_total = initial[chosen_indices].sum() + best_cells * cell_initial_price
inspection_total = inspections[chosen_indices].sum() + shared_inspection_cost
scheduled_total = scheduled[chosen_indices].sum() + best_cells * cell_maintenance_price
repair_total = repairs[chosen_indices].sum() + best_cells * cell_repairs_price
cash_total = initial_total + inspection_total + scheduled_total + repair_total

avg_load_mW = shared_power + power[chosen_indices].sum()
five_yr_energy_wh = avg_load_mW * hours / 1000.0

tot_risk_pen = risk_weight * rpn[chosen_indices].sum() / 100.0
tot_power_pen = power_weight * avg_load_mW
total_objective = cash_total + tot_risk_pen + tot_power_pen

# --- Failure Probabilities & Counters Calculations ---
# Expected failures for one box over selected horizon
expected_failures_per_box = events[chosen_indices].sum()
# Total expected failed parts across all units in the batch
total_expected_failed_parts = expected_failures_per_box * batch_size

# Probability of at least one component failing in a single box over the horizon:
# P(at least 1 failure) = 1 - P(no failures across all components)
# For each component: P_survival_annual = 1 - p_i
# P_survival_horizon = (1 - p_i) ^ years
p_chosen = p[chosen_indices]
prob_no_failure_single_box = np.prod((1.0 - p_chosen) ** years)
prob_at_least_one_failure_single_box = 1.0 - prob_no_failure_single_box

with col_right:
    st.subheader("Financial, Power & Energy Summary")
    
    m1, m2 = st.columns(2)
    m1.metric(
        "Initial Box & Pack Purchase",
        f"${initial_total:,.2f}",
        delta=f"${budget - initial_total:,.2f} under budget" if initial_total <= budget else "OVER BUDGET",
        delta_color="normal" if initial_total <= budget else "inverse"
    )
    m2.metric(f"{years}-Year Total Cash Cost", f"${cash_total:,.2f}")
    
    m3, m4 = st.columns(2)
    m3.metric("Required Battery Cells", f"{best_cells} cells", delta=f"{best_cells * usable_energy[b_type]:.1f} Wh usable capacity")
    m4.metric("System Average Load", f"{avg_load_mW:.4f} mW", delta=f"{five_yr_energy_wh:.2f} Wh / {years} yrs")
    
    st.markdown("---")
    
    m5, m6 = st.columns(2)
    m5.metric(
        f"Expected Failed Parts ({years} Yrs)",
        f"{total_expected_failed_parts:.2f} parts",
        delta=f"{expected_failures_per_box:.2f} per box across {batch_size} unit(s)"
    )
    m6.metric(
        f"Box Failure Risk ({years} Yrs)",
        f"{prob_at_least_one_failure_single_box * 100:.2f}%",
        help="Probability that at least one component in a single box experiences a failure over the planning horizon."
    )
    
    st.markdown("---")
    st.metric("Total Discrete Objective Score", f"${total_objective:,.2f}")
    st.caption("Objective includes non-cash risk and power penalties; cash cost is shown above.")
    
    m7, m8 = st.columns(2)
    m7.metric("Initial Batch Order Cost", f"${batch_size * initial_total:,.2f}")
    m8.metric(f"{years}-Yr Batch Order Cash Cost", f"${batch_size * cash_total:,.2f}")

# --- Breakdown Table ---
st.markdown("---")
st.subheader("Subsystem & Battery Cell Itemized Breakdown")

rows = []
for cat_name, idx_val in selected_indices.items():
    is_batt = idx_val in (6, 7)
    cnt = best_cells if is_batt else 1
    
    c_init = (cnt * cell_initial_price) if is_batt else initial[idx_val]
    c_insp = inspections[idx_val]
    c_repl = (cnt * cell_maintenance_price) if is_batt else scheduled[idx_val]
    c_rep = (cnt * cell_repairs_price) if is_batt else repairs[idx_val]
    c_tot = c_init + c_insp + c_repl + c_rep
    pwr = power[idx_val]
    
    rows.append({
        "Subsystem": cat_name,
        "Item": names[idx_val],
        "Quantity": cnt,
        "Initial ($)": f"${c_init:,.2f}",
        "Inspections ($)": f"${c_insp:,.2f}",
        "Scheduled Replacement ($)": f"${c_repl:,.2f}",
        "Expected Failure Replacement Count": round(float(events[idx_val]), 3),
        "Expected Repairs ($)": f"${c_rep:,.2f}",
        "Total Cash ($)": f"${c_tot:,.2f}",
        "Avg Load (mW)": f"{pwr:.6f}"
    })
    
rows.append({
    "Subsystem": "Shared visit / electronics",
    "Item": "Access, setup, documentation / board power allowance",
    "Quantity": 1,
    "Initial ($)": "$0.00",
    "Inspections ($)": f"${shared_inspection_cost:,.2f}",
    "Scheduled Replacement ($)": "$0.00",
    "Expected Failure Replacement Count": 0.0,
    "Expected Repairs ($)": "$0.00",
    "Total Cash ($)": f"${shared_inspection_cost:,.2f}",
    "Avg Load (mW)": f"{shared_power:.6f}"
})

st.dataframe(pd.DataFrame(rows), width="stretch")

# --- Source Code Expander ---
st.markdown("---")
with st.expander("Show Complete Application Source Code"):
    try:
        with open(__file__, "r") as f:
            code_text = f.read()
        st.code(code_text, language="python")
    except Exception:
        st.info("Source code display is available when executed directly from file.")
