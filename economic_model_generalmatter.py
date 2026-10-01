"""THE BOX: component and battery optimization dashboard.

Windows installation: python -m pip install streamlit numpy
Windows launch: python -m streamlit run economic_model_generalmatter.py

Annual failure probabilities are planning assumptions.
Expected failure replacements = years * annual probability under an annual
Bernoulli model (at most one modeled failure replacement per component per year).
Scheduled replacements are separate. This is not a physical limit on failures.
Battery replacement counts refer to packs; purchases include all cells per pack.
"""
import streamlit as st
import numpy as np
import pandas as pd
from itertools import product


# --- Page Configuration ---
st.set_page_config(
    page_title="THE BOX — Integrated Component & Battery Pack Optimizer",
    page_icon="🔋",
    layout="wide"
)


st.title("🔋 THE BOX — Component & Battery Pack Optimizer")
st.caption("Five-year component, battery cell count, maintenance, duty cycle, and FMEA optimization dashboard.")


# --- Fixed Operational Assumptions ---
RELEASES_PER_YEAR = 2.0  # Fixed assumption: 2 releases per year
RELEASE_SECONDS = 5.0     # Fixed assumption: 5 seconds per release event


# --- Default Component Data & Power Configurations ---
LC_MODES = {
    "PA": (3.3 * (9.7 + .127), 3.3 * .013),
    "AB": (3.3 * (33.0 + .130), 3.3 * .013),
    "PB": (1.8 * (15.6 + .122), 1.8 * .013)
}


# Columns: purchase dollars, inspection minutes PER VISIT, replacement hours,
# diagnosis hours, annual probability of one failure replacement.
# Inspection time per visit for each box is set globally via sidebar controls.
# Failure probabilities are unchanged estimates from the supplied model.
DATA = np.array([
    [19.99, 0, .50, .25, .010],   # 0 PT-1000
    [5.55,  0, .50, .25, .015],   # 1 TMP61
    [19.95, 0, .50, .25, .020],   # 2 ADXL362
    [20.00, 0, .50, .25, .010],   # 3 SQ-ASB
    [40.00, 0, .50, .50, .015],   # 4 Qorvo DWM3001CDK
    [25.00, 0, .50, .50, .015],   # 5 LC76G
    [51.50, 0, .50, .50, .015],   # 6 SAM-M10Q
    [20.00, 0, .25, .25, .010],   # 7 Tadiran: purchase per cell, service per pack
    [8.00,  0, .25, .25, .020],   # 8 Panasonic: purchase per cell, service per pack
    [100.00,0, .50, .50, .020],   # 9 Aluminum: inspect seals, cracks, corrosion
    [65.00, 0, .50, .50, .030],   # 10 PETG: inspect seals, cracks, deformation
    [15.00, 0, .25, .25, .005],   # 11 C clamp
    [12.00, 0, .25, .25, .005],   # 12 Permanent magnet
    [200.00,0, .50, .50, .020],   # 13 Energize-to-release magnet assembly
])


NAMES = [
    "PT-1000", "TMP61", "ADXL362", "SQ-ASB", "Qorvo DWM3001CDK",
    "LC76G", "SAM-M10Q", "Tadiran TLH-5903/P", "Panasonic BK120AAHA01",
    "Aluminum enclosure", "PETG enclosure", "C clamp", "Permanent magnet",
    "Energize-to-release magnet"
]


CATEGORIES = [(0, 1), (2, 3), (4,), (5, 6), (7, 8), (9, 10), (11, 12, 13)]
CAT_NAMES = [
    "Temperature Sensor", "Shock Sensor", "Indoor Location",
    "Outdoor Location", "Battery Chemistry", "Enclosure", "Attachment"
]


# --- Sidebar Controls ---
st.sidebar.header("🕹️ Optimization Parameters")


mode = st.sidebar.radio(
    "Analysis Mode",
    ["Automated Optimization", "Manual Selection (Client Mode)"],
    help="• Automated Optimization: Tests all feasible combinations and finds the exact discrete minimum objective.\n• Manual Selection: Allows testing of explicit component and battery choices."
)


st.sidebar.markdown("---")
st.sidebar.subheader("💰 Financial & Operational")


budget = st.sidebar.number_input(
    "Budget ($)", min_value=100.0, value=40000.00, step=1000.0,
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
    help="Includes hardware and pack replacement at years 5, 10, etc., including a replacement exactly at the horizon. Uncheck to omit planned replacements."
)


inspections_per_year = st.sidebar.number_input(
    "Inspection Visits per Year", min_value=0, max_value=12, value=1, step=1,
    help="All selected components are inspected during the same visit."
)
shared_inspection_minutes = st.sidebar.number_input(
    "Shared Access/Setup Time per Visit (min)", min_value=0.0, value=15.0, step=1.0,
    help="Assumed access, setup, and documentation time allocated to one box. Charged once per visit, not once per component."
)

st.sidebar.markdown("---")
st.sidebar.subheader("⚡ Power & Battery Configuration")


shared_power = st.sidebar.number_input(
    "Shared Board Power Allowance (mW)", min_value=0.0, value=1.21, step=0.05,
    help="Unmeasured load allowance for logging, processing, and other electronics. DC-DC losses and the release coil are accounted for separately."
)
conversion_efficiency = st.sidebar.slider(
    "DC-DC Conversion Efficiency", min_value=0.50, max_value=1.00, value=0.90, step=0.01,
    help="Efficiency of voltage regulation/boost circuitry transferring energy from battery to load."
)
reserve_factor = st.sidebar.slider(
    "Battery Reserve Factor Multiplier", min_value=1.00, max_value=2.00, value=1.20, step=0.05,
    help="Safety margin multiplier for battery capacity sizing (e.g., 1.20 = 20% extra energy buffer)."
)
allow_panasonic = st.sidebar.checkbox(
    "Enable Panasonic Battery Chemistry", value=False,
    help="Enable Panasonic NiMH cells for evaluation. Leave disabled if 5-year un-recharged usable capacity retention is unverified."
)


panasonic_frac_input = 0.15
if allow_panasonic:
    panasonic_frac_input = st.sidebar.number_input(
        "Panasonic Usable Capacity Fraction (Assumed)",
        min_value=0.01, max_value=1.00, value=0.15, step=0.01,
        help="Scenario assumption for the interval between planned pack replacements, not a verified retention specification."
    )
    st.sidebar.caption("Panasonic retention is unverified; enabling it evaluates a hypothetical scenario.")

st.sidebar.markdown("---")
st.sidebar.subheader("⏱️ Duty Cycle Timings (Seconds)")


temp_on = st.sidebar.number_input("Temp Sensor Active (s)", min_value=0.01, value=1.0, help="Duration temperature sensor is excited per cycle.")
temp_int = st.sidebar.number_input("Temp Sensor Interval (s)", min_value=1.0, value=300.0, help="Time period between temperature measurements.")


uwb_on = st.sidebar.number_input("UWB Active (s)", min_value=0.01, value=0.1, help="UWB transceiver active ranging burst duration.")
uwb_int = st.sidebar.number_input("UWB Interval (s)", min_value=1.0, value=60.0, help="Time period between UWB bursts.")


gnss_on = st.sidebar.number_input("GNSS Active (s)", min_value=0.1, value=60.0, help="Time spent acquiring and tracking GNSS position fix.")
gnss_int = st.sidebar.number_input("GNSS Interval (s)", min_value=1.0, value=3600.0, help="Time period between GNSS position updates.")


lc76g_variant = st.sidebar.selectbox(
    "LC76G GNSS Power Profile", ["PA", "AB", "PB"], index=0,
    help="Hardware power profile for LC76G GNSS receiver module."
)


st.sidebar.markdown("---")
st.sidebar.subheader("⚖️ Objective Weights")


risk_weight = st.sidebar.slider(
    "RPN Risk Penalty ($ / 100 RPN)", min_value=0.0, max_value=200.0, value=50.0, step=5.0,
    help="Dollar-equivalent penalty per 100 Risk Priority Number (RPN) points."
)
power_weight = st.sidebar.slider(
    "Power Penalty ($ / avg mW)", min_value=0.0, max_value=20.0, value=1.0, step=0.5,
    help="Dollar-equivalent preference score penalty per average milliwatt of system load."
)


# --- Derived Mathematical Calculations ---
hours = years * 365 * 24
scheduled_replacement_count = years // 5 if include_year5_replacement else 0
# Each planned pack must span the longest interval until the next replacement.
battery_service_years = min(years, 5) if include_year5_replacement else years
battery_service_hours = battery_service_years * 365 * 24


# Usable battery capacity inputs (Tadiran vs Panasonic)
tadiran_frac = 0.70
panasonic_frac = panasonic_frac_input if allow_panasonic else 0.0
usable_fraction = np.array([tadiran_frac, panasonic_frac])
battery_allowed = np.array([1.0, float(allow_panasonic)])


nominal_cell_wh = np.array([3.6 * 2.0, 1.2 * 1.2])  # Tadiran, Panasonic cell Wh
pack_hardware_cost = np.array([0.0, 0.0])


# Calculated duty cycle fractions
temp_fraction = temp_on / temp_int
uwb_fraction = uwb_on / uwb_int
gnss_fraction = gnss_on / gnss_int
if any(fraction > 1 for fraction in (temp_fraction, uwb_fraction, gnss_fraction)):
    st.error("Active time cannot exceed the corresponding measurement interval.")
    st.stop()


# Fixed magnet release active fraction (2 releases per year @ 5s each)
release_active_fraction = (RELEASES_PER_YEAR * RELEASE_SECONDS) / (365 * 24 * 3600)


# Component power draw vector (14 components)
lc_on, lc_idle = LC_MODES[lc76g_variant]
comp_power = np.zeros(14)
comp_power[0:2] = 0.33 * temp_fraction
comp_power[2] = 3.3 * .0027
comp_power[3] = 3.3 * .0011
comp_power[4] = 120 * uwb_fraction + .00255 * (1 - uwb_fraction)
comp_power[5] = lc_on * gnss_fraction + lc_idle * (1 - gnss_fraction)
comp_power[6] = 45.9099 * gnss_fraction + .0924 * (1 - gnss_fraction)
comp_power[13] = 6800.0 * release_active_fraction  # Energize-to-release magnet average power load


# Costs & Failure Repairs calculations
purchase, inspection_minutes, replacement_hours, diagnosis_hours, p = DATA.T
# Annual Bernoulli assumption: p is the chance of one modeled failure replacement
# in a year. E[N] = years*p, with a modeled maximum of years PER COMPONENT/PACK.
# Fractions are averages across many equivalent boxes, not partial replacements.
events = years * p
inspection_visits = years * inspections_per_year
shared_inspection_cost = inspection_visits * labour * shared_inspection_minutes / 60.0


initial_cost = purchase.copy()
initial_cost[7:9] = pack_hardware_cost
inspections = inspection_visits * labour * inspection_minutes / 60.0
replacement = initial_cost + labour * replacement_hours
scheduled = scheduled_replacement_count * replacement
repairs = events * (replacement + labour * diagnosis_hours)


cell_initial = purchase[7:9].copy()
cell_maintenance = scheduled_replacement_count * cell_initial
cell_repairs = events[7:9] * cell_initial


rpn = np.zeros(14)
rpn[7] = 480  # Tadiran
rpn[8] = 555  # Panasonic


usable_energy = nominal_cell_wh * usable_fraction * conversion_efficiency


# --- Application Layout ---
col_left, col_right = st.columns([1, 1])
selected_indices = {}


with col_left:
    st.subheader("📦 Hardware & Battery Selection")
    
    if mode == "Manual Selection (Client Mode)":
        st.info("Pick components manually to inspect real-time capacity and cost metrics.")
        for cat_idx, (cat_name, tuple_indices) in enumerate(zip(CAT_NAMES, CATEGORIES)):
            options = [NAMES[i] for i in tuple_indices]
            choice = st.selectbox(f"Select {cat_name}:", options, key=f"select_{cat_idx}")
            selected_indices[cat_name] = tuple_indices[options.index(choice)]
    else:
        st.success("🤖 Optimization Mode Active — Evaluating exact discrete combinations.")
        best_combo = None
        min_obj = float("inf")
        feasible_count = 0
        
        for choice in product(*CATEGORIES):
            i = np.array(choice)
            b = choice[4] - 7
            if not battery_allowed[b]:
                continue
            
            avg_pwr = shared_power + comp_power[i].sum()
            energy_wh = avg_pwr * hours / 1000.0
            
            if usable_energy[b] <= 0:
                continue
                
            pack_energy_wh = avg_pwr * battery_service_hours / 1000.0
            n_cells = max(1, int(np.ceil(reserve_factor * pack_energy_wh / usable_energy[b])))
            upfront = initial_cost[i].sum() + n_cells * cell_initial[b]
            
            if upfront > budget:
                continue
                
            insp_cost = inspections[i].sum() + shared_inspection_cost
            repl_cost = scheduled[i].sum() + n_cells * cell_maintenance[b]
            rep_cost = repairs[i].sum() + n_cells * cell_repairs[b]
            cash = upfront + insp_cost + repl_cost + rep_cost
            
            r_pen = risk_weight * rpn[i].sum() / 100.0
            p_pen = power_weight * avg_pwr
            obj = cash + r_pen + p_pen
            
            feasible_count += 1
            if obj < min_obj:
                min_obj = obj
                best_combo = (i, b, n_cells, avg_pwr, energy_wh, upfront, insp_cost, repl_cost, rep_cost, cash, r_pen, p_pen)
                
        if best_combo is None:
            st.error("⚠️ Over Budget or Infeasible! No enabled battery configuration satisfies the initial budget.")
        else:
            opt_indices, opt_b, opt_n, *_ = best_combo
            for cat_name, idx_val in zip(CAT_NAMES, opt_indices):
                selected_indices[cat_name] = idx_val
                count_str = f" x{opt_n} cells" if idx_val in (7, 8) else ""
                st.markdown(f"**{cat_name}:** `{NAMES[idx_val]}{count_str}`")
            st.caption(f"Feasible configurations evaluated: {feasible_count} of 96")


# --- Selected Configuration Evaluation ---
if len(selected_indices) == len(CATEGORIES):
    chosen_idx = np.array(list(selected_indices.values()))
    b_type = chosen_idx[4] - 7  # 0 for Tadiran, 1 for Panasonic
    
    avg_load_mW = shared_power + comp_power[chosen_idx].sum()
    avg_battery_output_mW = avg_load_mW / conversion_efficiency
    five_yr_energy_wh = avg_load_mW * hours / 1000.0
    pack_load_energy_wh = avg_load_mW * battery_service_hours / 1000.0
    required_reserve_wh = reserve_factor * pack_load_energy_wh
    
    if usable_energy[b_type] > 0:
        required_cells = max(1, int(np.ceil(required_reserve_wh / usable_energy[b_type])))
    else:
        st.error("Selected battery chemistry is disabled. Enable it to evaluate this scenario.")
        st.stop()
        
    delivered_pack_energy_wh = required_cells * usable_energy[b_type]
    
    # Financial breakdown
    tot_upfront = initial_cost[chosen_idx].sum() + required_cells * cell_initial[b_type]
    tot_inspections = inspections[chosen_idx].sum() + shared_inspection_cost
    tot_replacement = scheduled[chosen_idx].sum() + required_cells * cell_maintenance[b_type]
    tot_repairs = repairs[chosen_idx].sum() + required_cells * cell_repairs[b_type]
    
    tot_cash_cost = tot_upfront + tot_inspections + tot_replacement + tot_repairs
    tot_risk_pen = risk_weight * rpn[chosen_idx].sum() / 100.0
    tot_power_pen = power_weight * avg_load_mW
    total_objective = tot_cash_cost + tot_risk_pen + tot_power_pen


    with col_right:
        st.subheader("📊 Financial, Power & Energy Summary")
        
        m1, m2 = st.columns(2)
        m1.metric(
            "Initial Box & Pack Purchase",
            f"${tot_upfront:,.2f}",
            delta=f"${budget - tot_upfront:,.2f} under budget" if tot_upfront <= budget else "OVER BUDGET",
            delta_color="normal" if tot_upfront <= budget else "inverse"
        )
        m2.metric(f"{years}-Year Total Cash Cost", f"${tot_cash_cost:,.2f}")
        
        m3, m4 = st.columns(2)
        m3.metric("Required Battery Cells", f"{required_cells} cells", delta=f"{delivered_pack_energy_wh:.1f} Wh usable capacity")
        m4.metric("System Average Load", f"{avg_load_mW:.4f} mW", delta=f"{five_yr_energy_wh:.2f} Wh / {years} yrs")
        
        st.markdown("---")
        st.metric("Total Discrete Objective Score", f"${total_objective:,.2f}")
        st.caption("Objective includes non-cash risk and power penalties; cash cost is shown above.")
        m5, m6 = st.columns(2)
        m5.metric("Expected Failure Replacements", f"{events[chosen_idx].sum():.3f}")
        m6.metric("Scheduled Replacements", f"{scheduled_replacement_count * len(chosen_idx)}")
        st.caption("Replacement counts are component/pack events. A battery pack counts as one event, regardless of its cell count.")
        st.caption(f"Each pack is sized for {battery_service_years} years: {required_reserve_wh:.2f} Wh required including reserve.")


    # Itemized Breakdown
    st.markdown("---")
    st.subheader("📋 Subsystem & Battery Cell Itemized Breakdown")
    
    rows = []
    for cat_name, idx_val in selected_indices.items():
        is_batt = idx_val in (7, 8)
        cnt = required_cells if is_batt else 1
        
        # Include fixed pack hardware/labor AND cell purchases so rows reconcile.
        c_init = initial_cost[idx_val] + (cnt * cell_initial[b_type] if is_batt else 0)
        c_insp = inspections[idx_val]
        c_repl = scheduled[idx_val] + (cnt * cell_maintenance[b_type] if is_batt else 0)
        c_rep = repairs[idx_val] + (cnt * cell_repairs[b_type] if is_batt else 0)
        c_tot = c_init + c_insp + c_repl + c_rep
        pwr = comp_power[idx_val]
        
        rows.append({
            "Subsystem": cat_name,
            "Item": NAMES[idx_val],
            "Quantity": cnt,
            "Initial ($)": f"${c_init:,.2f}",
            "Inspections ($)": f"${c_insp:,.2f}",
            "Scheduled Replacement ($)": f"${c_repl:,.2f}",
            "Scheduled Replacement Count": scheduled_replacement_count,
            "Expected Failure Replacement Count": round(float(events[idx_val]), 3),
            "Expected Total Replacement Count": round(float(scheduled_replacement_count + events[idx_val]), 3),
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
        "Scheduled Replacement Count": 0,
        "Expected Failure Replacement Count": 0.0,
        "Expected Total Replacement Count": 0.0,
        "Expected Repairs ($)": "$0.00",
        "Total Cash ($)": f"${shared_inspection_cost:,.2f}",
        "Avg Load (mW)": f"{shared_power:.6f}"
    })
    st.dataframe(rows, width="stretch")
    st.caption("Expected Repairs ($) is a dollar cost, not a replacement count. Counts are shown in separate columns. Displayed row totals can differ by a cent due to rounding.")
    with st.expander("Inspection and replacement assumptions"):
        st.markdown(
            f"Inspections cost technician time: **{years} years × {inspections_per_year} visits/year × minutes/visit ÷ 60 × ${labour:.2f}/hour**. "
            "Component checks share one visit; access/setup is charged once. "
            "These are editable planning estimates, not measured service times."
        )
        st.markdown(
            "**Expected failure replacements = years × annual failure probability.** "
            "The model allows at most one failure replacement per component or battery pack in each year. "
            "Thus the five-year modeled maximum is five unscheduled replacements per component, not five for the entire box. "
            "Actual repeated failures could exceed that assumption. Scheduled replacements are additional."
        )
        st.markdown(
            "For TMP61, the assumed annual failure probability is 1.5%. Over five years, "
            "the expected failure-replacement count is **5 × 0.015 = 0.075**. "
            "With one scheduled year-5 replacement, the expected total is **1.075**. "
            "A fractional expectation is an average across many boxes; most individual sensors would have no failure replacement."
        )
        st.dataframe(pd.DataFrame({
            "Component": NAMES,
            "Assumed Annual Failure Probability (%)": 100 * p,
            "Expected Failure Replacement Count": events
        }), hide_index=True, width="stretch")
        st.caption("Battery failure probabilities are provisional pack-level assumptions. RPN is a priority score, not a failure probability. Capacity retention, board power, and pack peak-current capability still need verification.")
    st.caption("⚠️ *Note: Release magnet power is modeled on a fixed baseline assumption of 2 releases/year @ 5 seconds per event.*")
