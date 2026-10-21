import streamlit as st
import numpy as np
import pandas as pd
from itertools import product

# --- Page Configuration ---
st.set_page_config(
    page_title="General Matter Economic Model v2",
    layout="wide"
)

st.title("General Matter Economic Model — Advanced Dashboard")
st.caption("Multi-year component selection, battery cell sizing, duty cycle power profiling, magnet holding mechanics, and FMEA optimization.")

# --- Help Guide Expander ---
with st.expander("Help Guide & Model Overview"):
    st.markdown("""
    **Overview:**
    This application models and optimizes hardware configurations, battery packs, tracking options, microcontrollers, and mechanical attachment mechanics for remote system units over a multi-year horizon.
    
    * **Left Side (Controls & Inputs):** Configure financial constraints, batch volumes, duty cycle timings, power allowances, mechanical friction/safety factors, and objective penalty weights. Hover over any question mark (?) next to inputs or outputs for detailed explanations.
    * **Right Side (Results & Outputs):** Inspect real-time lifecycle cash costs, battery cell requirements, system power/energy totals, total weight, required magnet counts, failure expectations, and itemized subsystem breakdowns.
    
    ---
    
    **Understanding Amortized Facility Cost:**
    * **Facility Cost Total:** Represents one-time initial infrastructure, tooling, and installation labor expenses required to set up tracking and production (e.g., UWB anchors, RFID doorway antennas, AprilTag cameras, and site installation labor).
    * **Amortization:** Because these are one-time fixed setup costs for the entire batch, the model **amortizes** (distributes) the total facility cost evenly across all units in the batch order ($\text{Facility per box} = \frac{\text{Total Facility Cost}}{\text{Batch Order Quantity}}$). Ordering larger batches significantly reduces the facility cost share per individual box.
    """)

# --- Sidebar Controls ---
st.sidebar.header("Optimization Parameters")

mode = st.sidebar.radio(
    "Analysis Mode",
    ["Automated Optimization", "Manual Selection (Client Mode)"],
    help="• Automated Optimization: Evaluates all feasible discrete combinations to find the global minimum objective.\n• Manual Selection: Allows inspecting specific component choices interactively."
)

st.sidebar.markdown("---")
st.sidebar.subheader("Financial & Operational")

batch_size = st.sidebar.number_input(
    "Batch Order Quantity (Units)", min_value=1, value=1, step=1,
    help="? Total number of identical boxes produced in this batch order. Affects volume tier price discounts and amortizes one-time facility/tooling setup costs across units."
)
budget = st.sidebar.number_input(
    "Per-Box Hardware Budget ($)", min_value=100.0, value=2000.00, step=100.0,
    help="? Maximum allowable initial purchase expenditure per individual box (components + battery cells + attachment hardware), excluding amortized facility share."
)
labour = st.sidebar.number_input(
    "Labor Rate ($/hr)", min_value=0.0, value=80.0, step=5.0,
    help="? Hourly technician labor rate charged for scheduled preventative maintenance, inspections, and unscheduled field repairs."
)
years = st.sidebar.number_input(
    "Analysis Horizon (Years)", min_value=1, value=5, step=1,
    help="? Multi-year operational planning horizon over which battery capacity depletion, annual inspection visits, and failure repairs are calculated."
)
include_year5_replacement = st.sidebar.checkbox(
    "Include Scheduled Replacement Every 5 Years", value=True,
    help="? Uncheck to turn off automatic scheduled hardware replacements every 5 years."
)
tax_rate = st.sidebar.number_input(
    "Hardware Tax Rate", min_value=0.0, max_value=0.5, value=0.10, step=0.01,
    help="? Sales or hardware procurement tax rate applied to component, battery cell, and attachment hardware purchases."
)

inspections_per_year = st.sidebar.number_input(
    "Inspection Visits per Year", min_value=0, max_value=12, value=1, step=1,
    help="? Number of scheduled preventative maintenance inspection visits performed per box annually. All components are inspected during the same visit."
)
shared_inspection_minutes = st.sidebar.number_input(
    "Shared Access/Setup Time per Visit (min)", min_value=0.0, value=15.0, step=1.0,
    help="? Fixed technician access, physical site setup, and documentation time allocated to servicing one box per inspection visit."
)

st.sidebar.markdown("---")
st.sidebar.subheader("Power & Battery Configuration")

shared_power = st.sidebar.number_input(
    "Shared Board Power Allowance (mW)", min_value=0.0, value=2.0, step=0.05,
    help="? Continuous unmeasured baseline power allowance in milliwatts for board logging, internal microcontrollers, and auxiliary electronics."
)
conversion_efficiency = st.sidebar.slider(
    "DC-DC Conversion Efficiency", min_value=0.50, max_value=1.00, value=0.90, step=0.01,
    help="? Efficiency ratio of voltage regulation and boost circuitry transferring stored chemical energy from the battery pack to system power rails."
)
reserve_factor = st.sidebar.slider(
    "Battery Reserve Factor Multiplier", min_value=1.00, max_value=2.00, value=1.20, step=0.05,
    help="? Safety margin multiplier applied to total calculated energy consumption to ensure battery sizing accommodates self-discharge, cold temperatures, and aging."
)
usable_fraction = st.sidebar.slider(
    "Usable Battery Discharge Fraction", min_value=0.10, max_value=1.00, value=0.70, step=0.05,
    help="? Usable fraction of nominal battery cell capacity before deep discharge cutoff or voltage sag prevents reliable operation."
)

st.sidebar.markdown("---")
st.sidebar.subheader("Duty Cycle Timings (Seconds)")

temp_on = st.sidebar.number_input("Temp Sensor Active (s)", min_value=0.01, value=1.0, help="? Active operational duration in seconds per temperature sampling cycle.")
temp_interval = st.sidebar.number_input("Temp Sensor Interval (s)", min_value=1.0, value=21600.0, help="? Time interval in seconds between successive temperature measurements.")

uwb_on = st.sidebar.number_input("UWB Active (s)", min_value=0.01, value=0.1, help="? Active operational duration in seconds for Ultra-Wideband positioning.")
uwb_interval = st.sidebar.number_input("UWB Interval (s)", min_value=1.0, value=43200.0, help="? Time interval in seconds between UWB indoor location pings.")

gnss_on = st.sidebar.number_input("GNSS Active (s)", min_value=0.1, value=60.0, help="? Active tracking duration in seconds for GNSS satellite fixes.")
gnss_interval = st.sidebar.number_input("GNSS Interval (s)", min_value=1.0, value=302400.0 / 2, help="? Time interval in seconds between outdoor GNSS location fixes.")

releases_per_year = st.sidebar.number_input("Releases / Year", min_value=0.0, value=1.0, help="? Number of mechanical release actuator operations triggered per year.")
release_seconds = st.sidebar.number_input("Release Duration (s)", min_value=0.0, value=10.0, help="? Active activation duration in seconds per release event.")

mcu_on = st.sidebar.number_input("Standalone MCU Active (s)", min_value=0.1, value=1.0, help="? Active processing duration in seconds for standalone microcontrollers.")
mcu_interval = st.sidebar.number_input("Standalone MCU Interval (s)", min_value=1.0, value=60.0, help="? Time interval in seconds between microcontroller processing cycles.")

rfid_on = st.sidebar.number_input("RFID Active (s)", min_value=0.1, value=1.0, help="? Active communication duration in seconds for RFID/NFC chips.")
rfid_interval = st.sidebar.number_input("RFID Interval (s)", min_value=1.0, value=60.0, help="? Time interval in seconds between RFID/NFC polling cycles.")

st.sidebar.markdown("---")
st.sidebar.subheader("Mechanical & Attachment Parameters")

friction = st.sidebar.slider(
    "Vertical Sliding Friction Coefficient", min_value=0.05, max_value=1.00, value=0.20, step=0.05,
    help="? Coefficient of friction between the mounting surface and magnets during vertical sliding loads (ranges from 0.05 for lubricated metal to 1.0 for high-friction contact)."
)
holding_safety_factor = st.sidebar.slider(
    "Holding Safety Factor", min_value=1.0, max_value=5.0, value=3.0, step=0.5,
    help="? Engineering safety factor dividing maximum nominal magnet pull force to calculate reliable working load capacity."
)

st.sidebar.markdown("---")
st.sidebar.subheader("Objective Weights")

risk_weight = st.sidebar.slider(
    "RPN Risk Penalty ($ / 100 RPN)", min_value=0.0, max_value=200.0, value=50.0, step=5.0,
    help="? Dollar-equivalent objective preference penalty applied per 100 Risk Priority Number (RPN) points in FMEA evaluation."
)
power_weight = st.sidebar.slider(
    "Power Penalty ($ / avg mW)", min_value=0.0, max_value=20.0, value=1.0, step=0.5,
    help="? Dollar-equivalent objective preference penalty applied per average milliwatt of electrical load drawn by the system."
)

# --- Model Constants & Data Setup ---
tax_multiplier = 1 + tax_rate
hours = years * 365 * 24
scheduled_replacement_count = (years // 5) if include_year5_replacement else 0

data = np.array([
    [3.145 , 1, 0.50, 0.25, 0.010],
    [6.31  , 1, 0.50, 0.25, 0.010],
    [20.00 , 2, 0.50, 0.25, 0.010],
    [29.50 , 1, 0.50, 0.50, 0.015],
    [16.50 , 1, 0.50, 0.50, 0.015],
    [51.50 , 1, 0.50, 0.50, 0.015],
    [25.11 , 2, 0.25, 0.25, 0.020],
    [4.97  , 2, 0.25, 0.25, 0.020],
    [100.00, 2, 0.50, 0.50, 0.020],
    [23.02 , 2, 0.50, 0.50, 0.030],
    [10.00 , 0.5, 0.25, 0.25, 0.005],
    [2.54  , 2, 0.25, 0.25, 0.005],
    [33.80 , 2, 0.50, 0.50, 0.020],
    [4.99  , 1, 0.75, 0.50, 0.015],
    [4.15  , 1, 0.75, 0.50, 0.015],
    [7.44  , 1, 0.75, 0.50, 0.015],
    [1.37  , 0.5, 0.25, 0.25, 0.005],
    [7.86  , 1, 0.50, 0.50, 0.015],
    [15.00 , 1, 0.50, 0.50, 0.015]
])

names = [
    "uxcell 10K NTC Thermal Sensor Probe", "NPSSH103F3T1NDM01",
    "SQ-ASB Shock Sensor", "Qorvo DWM3001CDK",
    "LC76G", "SAM-M10Q",
    "Tadiran TL-5930/S", "Panasonic BK120AAHA01",
    "Aluminum enclosure", "PETG enclosure",
    "AprilTag (printed tag)", "Permanent magnet",
    "Energize-to-release magnet", "ESP32-WROOM-32E-N4",
    "nRF54L15", "nRF52840",
    "NT3H2111_2211 (NT3H2111W0FT1X)", "u-blox MAX-M10M-00B",
    "u-blox MAX-M11N-00B"
]

# Hollow box: 7x7x11 cm outer dimensions with 0.5 cm wall thickness
enclosure_volume_cm3 = (7 * 7 * 11) - (6 * 6 * 10)

weight_data = np.array([
    15, 15, 0.3, 20, 0.5, 5.6,
    92.5, 24,
    2.70 * enclosure_volume_cm3,
    1.27 * enclosure_volume_cm3,
    5, 100, 50, 3, 0.3, 0.74, 0.071, 0.5, 0.5
])
weight = weight_data.copy()
weight[6:8] = 0.0

bulk_prices = {
    0: [(1, None, 3.145)],
    1: [(1, 4, 6.31), (5, 9, 5.678), (10, 24, 5.443), (25, 49, 5.1632), (50, 99, 4.9714),
         (100, 499, 4.7958), (500, 999, 4.44216), (1000, None, 4.31039)],
    2: [(1, None, 20)],
    3: [(1, None, 29.5)],
    4: [(1, None, 16.5)],
    5: [(1, None, 13.75), (250, 250, 11.23752)],
    6: [(1, 19, 25.11), (20, 59, 19.5135), (60, 99, 17.807), (100, 259, 17.0678),
         (260, None, 16.01735)],
    7: [(1, None, 4.97)],
    8: [(1, None, 100)],
    9: [(1, None, 23.02)],
    11: [(1, None, 2.54)],
    12: [(1, None, 33.8)],
    13: [(1, 9, 4.99), (10, 24, 4.314), (25, 99, 4.08), (100, 249, 3.7585),
         (250, None, 3.56568), (650, 650, 2.5)],
    14: [(1, 9, 4.15), (10, 24, 3.584), (25, 99, 3.3888), (100, 249, 3.1196),
         (250, 499, 2.9582), (500, None, 2.84426), (1500, 1500, 2.26001)],
    15: [(1, 9, 7.44), (10, 24, 6.445), (25, 99, 6.1), (100, 249, 5.6258),
         (250, 499, 5.3418), (500, 999, 5.1413), (1000, None, 4.95241),
         (3000, 3000, 3.92001)],
    16: [(1, 9, 1.37), (10, 24, 1.175), (25, 99, 1.108), (100, 249, 1.0162),
         (250, 499, 0.96112), (500, 999, 0.9221), (1000, 1999, 0.88533),
         (2000, 2999, 0.85065), (3000, 4999, 0.83129), (5000, 6999, 0.80783),
         (7000, 9999, 0.79294), (10000, None, 0.77761)],
    17: [(1, None, 7.86), (500, 500, 6.425)],
    18: [(1, None, 15)],
}

def unit_price(j, order_quantity):
    return tax_multiplier * min(
        [data[j, 0]] + [price for low, high, price in bulk_prices.get(j, [])
                       if low <= order_quantity
                       and (high is None or order_quantity <= high)]
    )

nominal_cell_wh = np.array([3.6 * 19.0, 1.2 * 1.2])
usable_energy = nominal_cell_wh * usable_fraction * conversion_efficiency
pack_hardware_cost = tax_multiplier * np.array([5.72, 0.0])

facility_hardware = np.zeros(19)
facility_labor = np.zeros(19)
facility_hardware[3] = 6 * 311.83
facility_labor[3] = 6 * 60 / 60 * 80
facility_hardware[16] = 3 * 952 + 20 * 223.75
facility_labor[16] = 20 * 15 / 60 * 80
facility_hardware[10] = 13 * 139.99
facility_labor[10] = 180 / 60 * 80
facility_before_tax = facility_hardware + facility_labor
facility = tax_multiplier * facility_hardware + facility_labor

purchase, inspection_minutes, replacement_hours, diagnosis_hours, p = data.T
events = years * p
inspection_visits = years * inspections_per_year
shared_inspection_cost = inspection_visits * labour * shared_inspection_minutes / 60.0

initial = np.array([unit_price(j, batch_size) for j in range(len(data))])
initial[6:8] = pack_hardware_cost
inspections = inspection_visits * labour * inspection_minutes / 60.0
replacement = initial + labour * replacement_hours
scheduled = scheduled_replacement_count * replacement
maintenance = inspections + scheduled

repair_purchase = np.array([unit_price(j, 1) for j in range(len(data))])
repair_purchase[6:8] = pack_hardware_cost
repair_event = repair_purchase + labour * (replacement_hours + diagnosis_hours)
repairs = events * repair_event
cost = initial + maintenance + repairs

lowest_cell_prices = np.array([
    min([purchase[j]] + [tier[2] for tier in bulk_prices.get(j, [])])
    for j in (6, 7)
])
max_cells = np.floor(budget / (tax_multiplier * lowest_cell_prices)).astype(int)

tadiran_rpn = 144 + 96 + 240
panasonic_rpn = 96 + 120 + 243 + 96
rpn = np.zeros(len(data))
rpn[6:8] = [tadiran_rpn, panasonic_rpn]

power_data = np.array([
    [0.5445, 0, 0],
    [0.5445, 0, 0],
    [0.00363, 0, 0.00363],
    [120.0, 0, 0.00255],
    [32.4291, 32.4291, 0.0429],
    [45.9099, 45.9099, 0.0924],
    [0, 0, 0],
    [0, 0, 0],
    [0, 0, 0],
    [0, 0, 0],
    [0, 0, 0],
    [0, 0, 0],
    [6800.0, 0, 0],
    [788.7, 0, 0.033],
    [37.2, 0, 0.0087],
    [59.1, 0, 0.00705],
    [0.792, 0, 0.6435],
    [21.6, 29.1, 0.0924],
    [25.47, 30.75, 0.0957]
])

active_fraction = np.zeros(len(data))
active_fraction[0:2] = temp_on / temp_interval
active_fraction[2] = 1.0
active_fraction[3] = uwb_on / uwb_interval
active_fraction[4:6] = gnss_on / gnss_interval
active_fraction[12] = releases_per_year * release_seconds / (365 * 24 * 3600)
active_fraction[13:16] = mcu_on / mcu_interval
active_fraction[16] = rfid_on / rfid_interval
active_fraction[17:19] = 30.0 / gnss_interval

acquisition_fraction = np.zeros(len(data))
acquisition_fraction[17:19] = 30.0 / gnss_interval
idle_fraction = 1 - active_fraction - acquisition_fraction

operating, acquisition, idle = power_data.T
power = (active_fraction * operating + acquisition_fraction * acquisition + idle_fraction * idle)
energy = power * hours / 1000.0

magnet_pull_kgf = np.array([2.0, 2.0])
holding_capacity = 1000 * friction * magnet_pull_kgf / holding_safety_factor

indoor_options_list = ["Qorvo (DWM3001CDK)", "RFID + AprilTags (NT3H2111)"]
magnet_options_list = ["Permanent Magnet", "Energize-to-release Magnet"]

cat_mapping = {
    0: "Temperature Sensor", 1: "Temperature Sensor",
    2: "Shock Sensor",
    3: "Indoor Tracking (Qorvo)",
    4: "Outdoor Location", 5: "Outdoor Location", 17: "Outdoor Location", 18: "Outdoor Location",
    6: "Battery Pack", 7: "Battery Pack",
    8: "Enclosure", 9: "Enclosure",
    10: "AprilTag",
    11: "Attachment Mechanism", 12: "Attachment Mechanism",
    13: "Standalone MCU", 14: "Standalone MCU", 15: "Standalone MCU",
    16: "Indoor Tracking (RFID/NFC)"
}

col_left, col_right = st.columns([1, 1])
selected_indices = {}
best_cells = 1
b_type = 0
best_attachments = 1
best_attachment_initial = 2.54
best_cell_initial = 25.11
best_cell_maintenance = scheduled_replacement_count * 25.11
best_cell_repairs = 0.5

with col_left:
    st.subheader("Hardware & System Configuration")
    
    if mode == "Manual Selection (Client Mode)":
        st.info("Pick components manually to inspect real-time capacity, weight, magnet sizing, and cost metrics.")
        
        c_temp = st.selectbox("Temperature Sensor:", [names[0], names[1]], index=0)
        t_idx = 0 if c_temp == names[0] else 1
        
        c_shock = st.selectbox("Shock Sensor:", [names[2]], index=0)
        s_idx = 2
        
        c_indoor = st.selectbox("Indoor Tracking Option:", indoor_options_list, index=0)
        if c_indoor.startswith("Qorvo"):
            indoor_sel = 3
            mcu_sel = -1
        else:
            indoor_sel = 16
            c_mcu = st.selectbox("Standalone MCU:", [names[13], names[14], names[15]], index=0)
            mcu_sel = 13 if c_mcu == names[13] else (14 if c_mcu == names[14] else 15)
            
        c_outdoor = st.selectbox("Outdoor Location:", [names[4], names[5], names[17], names[18]], index=0)
        o_idx = 4 if c_outdoor == names[4] else (5 if c_outdoor == names[5] else (17 if c_outdoor == names[17] else 18))
        
        c_batt = st.selectbox("Battery Chemistry:", [names[6], names[7]], index=0)
        b_type = 0 if c_batt == names[6] else 1
        
        c_enc = st.selectbox("Enclosure:", [names[8], names[9]], index=1)
        e_idx = 8 if c_enc == names[8] else 9
        
        c_mag = st.selectbox("Attachment Magnet Type:", magnet_options_list, index=0)
        mag_idx = 11 if c_mag.startswith("Permanent") else 12
        
        chosen_list = [t_idx, s_idx, o_idx, 6 + b_type, e_idx, mag_idx]
        if indoor_sel == 3:
            chosen_list.append(3)
        else:
            chosen_list.extend([16, 10, mcu_sel])
            
        chosen_indices = np.array(chosen_list)
        
        avg_pwr = shared_power + power[chosen_indices].sum()
        p_energy = avg_pwr * hours / 1000.0
        best_cells = max(1, int(np.ceil(reserve_factor * p_energy / usable_energy[b_type])))
        
        base_w = weight[chosen_indices].sum() - weight[mag_idx] + best_cells * weight[6 + b_type]
        p_load = holding_capacity[mag_idx - 11] - weight[mag_idx]
        req_mags = 1 if p_load <= 0 else max(1, int(np.ceil(base_w / p_load - 1e-12)))
        best_attachments = req_mags
        best_attachment_initial = unit_price(mag_idx, batch_size * best_attachments)
        
        cell_idx = 6 + b_type
        best_cell_initial = unit_price(cell_idx, batch_size * best_cells)
        best_cell_maintenance = scheduled_replacement_count * best_cell_initial
        best_cell_repairs = events[cell_idx] * unit_price(cell_idx, best_cells)
        
        st.markdown("---")
        st.subheader("Selected Component Breakdown")
        for idx in chosen_indices:
            cat_label = cat_mapping.get(idx, "Subsystem")
            qty_str = f" x{best_cells} cells" if idx in (6, 7) else (f" x{best_attachments} units" if idx in (11, 12) else "")
            st.markdown(f"**{cat_label}:** `{names[idx]}{qty_str}`")
        st.caption(f"Battery chemistry selected: {names[6 + b_type]} ({best_cells} cells)")
        
    else:
        st.success("Optimization Mode Active — Evaluating exact discrete combinations.")
        best = None
        minimum = np.inf
        feasible_count = 0
        combination_count = 0
        
        categories = [(0, 1), (2,), (3, 16), (4, 5, 17, 18), (6, 7), (8, 9), (11, 12), (-1, 13, 14, 15)]
        
        for choice in product(*categories):
            if (choice[2] == 3) != (choice[7] == -1):
                continue
            i = np.array([j for j in choice if j != -1] + ([10] if choice[2] == 16 else []))
            combination_count += 1
            facility_per_box = facility[i].sum() / batch_size
            a = choice[6]
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
                
                base_weight = weight[i].sum() - weight[a] + n_cells * weight[6 + b]
                payload_per_magnet = holding_capacity[a - 11] - weight[a]
                required_attachments = 1
                if base_weight > 0:
                    if payload_per_magnet <= 0:
                        continue
                    required_attachments = max(1, int(np.ceil(base_weight / payload_per_magnet - 1e-12)))
                
                attachment_counts = {required_attachments}
                attachment_counts.update(max(required_attachments, int(np.ceil(low / batch_size)))
                                         for low, high, price in bulk_prices.get(a, []))
                
                for n_attachments in sorted(attachment_counts):
                    if (n_attachments * holding_capacity[a - 11] < base_weight + n_attachments * weight[a]):
                        continue
                    candidate_power = average_power + (n_attachments - 1) * power[a]
                    if n_cells * usable_energy[b] < reserve_factor * hours * candidate_power / 1000:
                        continue
                    attachment_initial = unit_price(a, batch_size * n_attachments)
                    upfront = (initial[i].sum() - initial[a] + n_cells * cell_initial + n_attachments * attachment_initial)
                    if upfront > budget:
                        continue
                    
                    attachment_cost = (scheduled_replacement_count * attachment_initial + inspections[a] + labour * replacement_hours[a] + repairs[a])
                    objective = (cost[i].sum() - cost[a] + n_cells * cell_cost + shared_inspection_cost
                                 + n_attachments * attachment_cost
                                 + risk_weight * rpn[i].sum() / 100 + power_weight * candidate_power
                                 + facility_per_box)
                    combination_feasible = True
                    if objective < minimum:
                        minimum, best = objective, i
                        best_battery, best_cells = b, n_cells
                        best_attachment = a
                        best_attachments, best_attachment_initial = n_attachments, attachment_initial
                        best_cell_initial = cell_initial
                        best_cell_maintenance = cell_maintenance
                        best_cell_repairs = cell_repairs
            feasible_count += int(combination_feasible)
            
        if best is None:
            st.error("Over Budget or Infeasible! No component combination satisfies budget, energy, and holding requirements.")
            st.stop()
        else:
            b_type = best_battery
            chosen_indices = best
            st.markdown("---")
            st.subheader("Optimized Component Breakdown")
            for idx in chosen_indices:
                cat_label = cat_mapping.get(idx, "Subsystem")
                qty_str = f" x{best_cells} cells" if idx in (6, 7) else (f" x{best_attachments} units" if idx == best_attachment else "")
                st.markdown(f"**{cat_label}:** `{names[idx]}{qty_str}`")
            st.caption(f"Feasible configurations evaluated: {feasible_count} of {combination_count}")

# --- Detailed Evaluation Metrics ---
chosen_indices_set = set(chosen_indices)
cell_idx = 6 + b_type
mag_idx = 11 if 11 in chosen_indices_set else 12

initial_total = initial[chosen_indices].sum() - initial[mag_idx] + best_cells * best_cell_initial + best_attachments * best_attachment_initial
inspection_total = inspections[chosen_indices].sum() + shared_inspection_cost + (best_attachments - 1) * inspections[mag_idx]
scheduled_total = scheduled[chosen_indices].sum() - scheduled[mag_idx] + best_cells * best_cell_maintenance + best_attachments * (scheduled_replacement_count * best_attachment_initial + labour * replacement_hours[mag_idx])
repair_total = repairs[chosen_indices].sum() + best_cells * best_cell_repairs + (best_attachments - 1) * repairs[mag_idx]
cash_total = initial_total + inspection_total + scheduled_total + repair_total

avg_load_mW = shared_power + power[chosen_indices].sum() + (best_attachments - 1) * power[mag_idx]
five_yr_energy_wh = avg_load_mW * hours / 1000.0
total_box_weight = weight[chosen_indices].sum() + best_cells * weight[cell_idx] + (best_attachments - 1) * weight[mag_idx]
facility_total = facility[chosen_indices].sum()

expected_failures_box = (events[chosen_indices].sum() - events[mag_idx]) + (best_attachments * events[mag_idx]) + (best_cells * events[cell_idx])
total_expected_failed_parts = expected_failures_box * batch_size
prob_no_fail = np.prod((1.0 - p[chosen_indices]) ** years) * ((1.0 - p[cell_idx]) ** years) ** best_cells
prob_fail_box = 1.0 - prob_no_fail

with col_right:
    st.subheader("Financial, Power & Energy Summary")
    
    m1, m2 = st.columns(2)
    m1.metric(
        "Initial Hardware Purchase (Per Box)",
        f"${initial_total:,.2f}",
        delta=f"${budget - initial_total:,.2f} under budget" if initial_total <= budget else "OVER BUDGET",
        delta_color="normal" if initial_total <= budget else "inverse",
        help="? Total initial upfront purchase expenditure for components, battery cells, and attachment hardware for a single box (includes sales tax)."
    )
    m2.metric(
        f"{years}-Year Total Cash Cost",
        f"${cash_total:,.2f}",
        help=f"? Total cumulative lifecycle cash expenditure over the {years}-year horizon, including initial hardware, preventative maintenance, and expected failure repairs."
    )
    
    m3, m4 = st.columns(2)
    m3.metric(
        "Required Battery Cells",
        f"{best_cells} cells",
        delta=f"{best_cells * usable_energy[b_type]:.1f} Wh usable",
        help="? Exact number of battery cells required in parallel/series to satisfy total multi-year energy demand plus reserve safety factors."
    )
    m4.metric(
        "System Average Load",
        f"{avg_load_mW:.4f} mW",
        delta=f"{five_yr_energy_wh:.2f} Wh / {years} yrs",
        help="? Time-weighted average power draw across all active components, duty cycles, and shared board allowances in milliwatts."
    )
    
    st.markdown("---")
    
    m5, m6 = st.columns(2)
    m5.metric(
        f"Expected Failed Parts ({years} Yrs)",
        f"{total_expected_failed_parts:.2f} parts",
        delta=f"{expected_failures_box:.2f} per box across {batch_size} unit(s)",
        help=f"? Total statistical expected number of component and battery cell failures across the batch order over the {years}-year operational horizon based on annual failure rates ($p$)."
    )
    m6.metric(
        f"Box Failure Risk ({years} Yrs)",
        f"{prob_fail_box * 100:.2f}%",
        help=f"? Statistical probability that at least one component or battery cell within a single box experiences a failure over the {years}-year operational horizon."
    )
    
    st.markdown("---")
    
    m7, m8 = st.columns(2)
    m7.metric(
        "Initial Order Total (w/ Facility)",
        f"${batch_size * initial_total + facility_total:,.2f}",
        help="? Total initial financial outlay for the entire batch order quantity, including initial hardware purchase and amortized facility/tooling setup costs."
    )
    m8.metric(
        "Facility Share Per Box",
        f"${facility_total / batch_size:,.2f}",
        help="? One-time facility, setup, and tooling infrastructure costs amortized (divided evenly) per individual unit across the batch order quantity."
    )

# --- Itemized Breakdown Table ---
st.markdown("---")
st.subheader("Subsystem & Component Itemized Breakdown")

rows = []
for idx_val in chosen_indices:
    is_batt = idx_val in (6, 7)
    is_mag = idx_val in (11, 12)
    cnt = best_cells if is_batt else (best_attachments if is_mag else 1)
    
    c_init = (cnt * best_cell_initial) if is_batt else ((cnt * best_attachment_initial) if is_mag else initial[idx_val])
    c_insp = inspections[idx_val] + ((cnt - 1) * inspections[idx_val] if is_mag or is_batt else 0)
    c_repl = (cnt * (best_cell_maintenance / max(1, best_cells))) if is_batt else ((cnt * (scheduled_replacement_count * best_attachment_initial + labour * replacement_hours[idx_val])) if is_mag else scheduled[idx_val])
    c_rep = (cnt * best_cell_repairs) if is_batt else ((cnt * repairs[idx_val]) if is_mag else repairs[idx_val])
    c_tot = c_init + c_insp + c_repl + c_rep
    pwr = power[idx_val]
    wt = weight_data[idx_val] * cnt
    
    rows.append({
        "Item": names[idx_val],
        "Quantity": cnt,
        "Initial ($)": f"${c_init:,.2f}",
        "Inspections ($)": f"${c_insp:,.2f}",
        "Scheduled Replacement ($)": f"${c_repl:,.2f}",
        "Expected Failures": round(float(events[idx_val] * cnt), 3),
        "Expected Repairs ($)": f"${c_rep:,.2f}",
        "Total Cash ($)": f"${c_tot:,.2f}",
        "Avg Load (mW)": f"{pwr:.6f}",
        "Weight (g)": f"{wt:.2f}"
    })

rows.append({
    "Item": "Shared access, setup, documentation & board power",
    "Quantity": 1,
    "Initial ($)": "$0.00",
    "Inspections ($)": f"${shared_inspection_cost:,.2f}",
    "Scheduled Replacement ($)": "$0.00",
    "Expected Failures": 0.0,
    "Expected Repairs ($)": "$0.00",
    "Total Cash ($)": f"${shared_inspection_cost:,.2f}",
    "Avg Load (mW)": f"{shared_power:.6f}",
    "Weight (g)": "0.00"
})

st.dataframe(pd.DataFrame(rows), use_container_width=True)

# --- Source Code Expander ---
st.markdown("---")
with st.expander("Show Complete Application Source Code"):
    try:
        with open(__file__, "r") as f:
            code_text = f.read()
        st.code(code_text, language="python")
    except Exception:
        st.info("Source code display is available when executed directly from file.")
