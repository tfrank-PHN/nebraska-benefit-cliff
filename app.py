import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# Set up page and layout
st.set_page_config(page_title="Advanced Nebraska Benefit Cliff Simulator", layout="wide")

st.title("🌾 Comprehensive Nebraska Public Benefits & Cliff Trajectory Dashboard")
st.markdown("""
This advanced model illustrates the 5-year financial trajectory of a single parent in Nebraska. 
Configure realistic cost frameworks, simulate custom employer incentives, and visualize stacked resource allocation.
""")

# --- STATE AND POLICY COST MATRIX DICTIONARY (2026 ESTIMATES FOR NEBRASKA) ---
household_defaults = {
    1: {"fpl": 1718.00, "rent": 1000, "childcare_per_kid": 800, "food": 450, "medical": 400, "misc": 350},
    2: {"fpl": 2153.00, "rent": 1200, "childcare_per_kid": 800, "food": 700, "medical": 550, "misc": 450},
    3: {"fpl": 2588.00, "rent": 1400, "childcare_per_kid": 750, "food": 950, "medical": 650, "misc": 500},
    4: {"fpl": 3023.00, "rent": 1600, "childcare_per_kid": 700, "food": 1150, "medical": 700, "misc": 550},
    5: {"fpl": 3458.00, "rent": 1800, "childcare_per_kid": 650, "food": 1350, "medical": 750, "misc": 600},
    6: {"fpl": 3893.00, "rent": 2000, "childcare_per_kid": 600, "food": 1550, "medical": 800, "misc": 650}
}

# --- CALLBACK RESET LOGIC FOR COMPONENT STATE SYNCHRONIZATION ---
def apply_family_size_defaults():
    size = st.session_state.get("num_kids_key", 2)
    defs = household_defaults[size]
    st.session_state["rent_key"] = defs["rent"]
    st.session_state["childcare_key"] = defs["childcare_per_kid"]
    st.session_state["food_key"] = defs["food"]
    st.session_state["medical_key"] = defs["medical"]
    st.session_state["misc_key"] = defs["misc"]

if "rent_key" not in st.session_state:
    apply_family_size_defaults()

# --- SIDEBAR: HOUSEHOLD PROFILE ---
st.sidebar.header("👪 Household Profile")
num_children = st.sidebar.slider(
    "Number of Dependent Children", 
    min_value=1, max_value=6, value=2, step=1,
    key="num_kids_key", on_change=apply_family_size_defaults
)

defaults = household_defaults[num_children]

# --- SIDEBAR: PROGRESSION & WAGES ---
st.sidebar.markdown("---")
st.sidebar.header("📈 Career Progression & Raises")
current_wage = st.sidebar.slider("Starting Hourly Wage ($)", min_value=12.0, max_value=45.0, value=16.0, step=0.50)
hours_per_week = st.sidebar.number_input("Hours Worked Per Week", value=40, step=1)

raise_type = st.sidebar.radio("Type of Annual Raise", ["Percentage (%)", "Flat Dollar ($)"])
if raise_type == "Percentage (%)":
    annual_raise_pct = st.sidebar.slider("Annual Wage Increase (%)", min_value=1.0, max_value=15.0, value=2.0, step=0.5) / 100
    annual_raise_flat = 0.0
else:
    annual_raise_flat = st.sidebar.slider("Annual Wage Increase ($/hr)", min_value=0.10, max_value=5.00, value=0.50, step=0.05)
    annual_raise_pct = 0.0

inflation_rate = st.sidebar.slider("Annual Inflation Rate (%)", min_value=1.0, max_value=15.0, value=3.0, step=0.5) / 100

# --- SIDEBAR: COST SLIDERS WITH INTEGRATED RESET ---
st.sidebar.markdown("---")
st.sidebar.header("🏠 Monthly Private-Market Costs")
st.sidebar.button("🔄 Reset Costs to Selected Family Size Defaults", on_click=apply_family_size_defaults)

rent_val = st.sidebar.slider("Housing & Utilities ($/mo)", 500, 5000, key="rent_key", step=50)
childcare_val = st.sidebar.slider("Childcare Cost Per Child ($/mo)", 200, 2000, key="childcare_key", step=50)
food_val = st.sidebar.slider("Food & Groceries ($/mo)", 200, 3000, key="food_key", step=50)
medical_val = st.sidebar.slider("Private Health Insurance Risk ($/mo)", 100, 2500, key="medical_key", step=25)
misc_val = st.sidebar.slider("Other Basic Needs / Transport ($/mo)", 100, 2000, key="misc_key", step=25)

# --- SIDEBAR: NEW EMPLOYER INCENTIVE ACTION PANEL ---
st.sidebar.markdown("---")
st.sidebar.header("💼 Employer Voluntary Incentives")
st.sidebar.markdown("*Simulate non-taxable fringe benefits that bypass standard public benefit arithmetic rules.*")
emp_childcare_subsidy = st.sidebar.slider("Direct Childcare Support (Sec. 129) ($/mo)", 0, 1000, 0, 50)
emp_tuition = st.sidebar.slider("Tuition Reimbursement Allowance (Sec. 127) ($/mo)", 0, 437, 0, 25)
emp_transit = st.sidebar.slider("Transit / Gas Card Commuter Benefit ($/mo)", 0, 300, 0, 25)
emp_bridge = st.sidebar.slider("Private Transition 'Bridge Fund' Stipend ($/mo)", 0, 1000, 0, 50)

# --- DYNAMIC CALCULATION CORE ---
FPL_MONTHLY_BASE = defaults["fpl"]
MEDICAID_LIMIT_PCT, SNAP_LIMIT_PCT, CCAP_LIMIT_PCT = 1.38, 1.65, 1.85
TANF_LIMIT_BASE = 1132.50 + (393.00 * num_children)

total_childcare_market = childcare_val * num_children
STARTING_SURVIVAL_NEED = rent_val + total_childcare_market + food_val + medical_val + misc_val

# Baseline Subsidy Max Values
VAL_TANF = 300.00 + (100.00 * num_children)
VAL_SNAP = 250.00 * num_children
VAL_MEDICAID = medical_val
VAL_CCAP = total_childcare_market

data = []
for year in range(1, 6):
    if raise_type == "Percentage (%)":
        wage = current_wage * ((1 + annual_raise_pct) ** (year - 1))
    else:
        wage = current_wage + (annual_raise_flat * (year - 1))
        
    gross_monthly_earnings = (wage * hours_per_week * 52) / 12
    inflated_survival_need = STARTING_SURVIVAL_NEED * ((1 + inflation_rate) ** (year - 1))
    current_fpl = FPL_MONTHLY_BASE * ((1 + inflation_rate) ** (year - 1))
    
    cliffs_hit = []
    
    if gross_monthly_earnings <= TANF_LIMIT_BASE:
        tanf_received = VAL_TANF
    else:
        tanf_received = 0.0
        cliffs_hit.append("TANF/ADC Cash")
        
    if gross_monthly_earnings <= (MEDICAID_LIMIT_PCT * current_fpl):
        medicaid_received = VAL_MEDICAID
    else:
        medicaid_received = 0.0
        cliffs_hit.append("Medicaid")
        
    if gross_monthly_earnings <= (SNAP_LIMIT_PCT * current_fpl):
        snap_received = VAL_SNAP
    else:
        snap_received = 0.0
        cliffs_hit.append("SNAP Food Aid")
        
    if gross_monthly_earnings <= (CCAP_LIMIT_PCT * current_fpl):
        ccap_received = VAL_CCAP
        if gross_monthly_earnings > current_fpl:
            ccap_received -= (0.07 * gross_monthly_earnings)
    else:
        ccap_received = 0.0
        cliffs_hit.append("Childcare Subsidy")

    total_employer_incentives = emp_childcare_subsidy + emp_tuition + emp_transit + emp_bridge
    total_benefits_value = tanf_received + snap_received + medicaid_received + ccap_received
    
    net_resources = gross_monthly_earnings + total_benefits_value + total_employer_incentives
    
    if net_resources < inflated_survival_need:
        bridge_fund_needed = inflated_survival_need - net_resources
    else:
        bridge_fund_needed = 0.0

    primary_fault = ", ".join(cliffs_hit) if cliffs_hit else "None (Fully Assisted)"
    if net_resources >= inflated_survival_need:
        primary_fault = "N/A - Self Sufficient"

    data.append({
        "Year": f"Year {year}",
        "Hourly Wage": f"${wage:.2f}",
        "Gross Monthly Earnings": gross_monthly_earnings,
        "Public Assistance Remaining": total_benefits_value,
        "Employer Fringe Incentives": total_employer_incentives,
        "Total Household Resources": net_resources,
        "Required Cost of Living": inflated_survival_need,
        "Monthly Deficit Gap": bridge_fund_needed,
        "Active Program Cliffs Triggered": primary_fault
    })

df = pd.DataFrame(data)

# --- USER INTERFACE LAYOUT ---
col_table, col_metrics = st.columns([2.5, 1])

with col_table:
    st.subheader(f"📊 5-Year Financial Projection Matrix (1 Adult + {num_children} Children)")
    st.dataframe(
        df.style.format({
            "Gross Monthly Earnings": "${:.2f}",
            "Public Assistance Remaining": "${:.2f}",
            "Employer Fringe Incentives": "${:.2f}",
            "Total Household Resources": "${:.2f}",
            "Required Cost of Living": "${:.2f}",
            "Monthly Deficit Gap": "${:.2f}"
        }),
        use_container_width=True,
        hide_index=True
    )

with col_metrics:
    st.subheader("🏛️ Policy Aggregates")
    cumulative_bridge_cost = df["Monthly Deficit Gap"].sum() * 12
    st.metric(
        label="Total 5-Year Net Deficit Gap",
        value=f"${cumulative_bridge_cost:,.2f}"
    )
    st.info(f"Target Monthly Self-Sufficiency Baseline: ${STARTING_SURVIVAL_NEED:,.2f}")

# --- TEXT POLICY CONTEXT FOR LAWMAKERS ---
st.markdown("---")
st.subheader("📋 Context Matrix: Dynamic Nebraska Program Limits & Thresholds")
st.markdown(f"""
Based on a household size of **1 Adult and {num_children} Children**, the active legal limits 
determining whether a family hits a cliff drop include:
*   **TANF/ADC Cash Assistance Cutoff:** **\\${TANF_LIMIT_BASE:,.2f} / month** gross income limit.
*   **Medicaid Expansion Threshold (138% FPL):** **\\${(MEDICAID_LIMIT_PCT * FPL_MONTHLY_BASE):,.2f} / month** gross income limit.
*   **SNAP Food Assistance Eligibility Line (165% FPL):** **\\${(SNAP_LIMIT_PCT * FPL_MONTHLY_BASE):,.2f} / month** gross income limit.
*   **Childcare Subsidy Entry Threshold (185% FPL via LB 304):** **\\${(CCAP_LIMIT_PCT * FPL_MONTHLY_BASE):,.2f} / month** gross income limit.
""")

# --- THE ADVANCED ALTAIR LAYERED CHART ENGINE ---
st.markdown("---")
st.subheader("📉 The Benefit Cliff Visualization: Total Resources vs. Local Survival Threshold")

# Generate 35 clean evaluation columns across standard wages
wage_axis = np.linspace(12.0, 50.0, 35)
plot_points = []

for w in wage_axis:
    gross = (w * hours_per_week * 52) / 12
    
    t_val = VAL_TANF if gross <= TANF_LIMIT_BASE else 0
    m_val = VAL_MEDICAID if gross <= (MEDICAID_LIMIT_PCT * FPL_MONTHLY_BASE) else 0
    s_val = VAL_SNAP if gross <= (SNAP_LIMIT_PCT * FPL_MONTHLY_BASE) else 0
    c_val = VAL_CCAP if gross <= (CCAP_LIMIT_PCT * FPL_MONTHLY_BASE) else 0
    if c_val > 0 and gross > FPL_MONTHLY_BASE:
        c_val -= (0.07 * gross)
        
    tot_public = t_val + m_val + s_val + c_val
tot_employer = emp_childcare_subsidy + emp_tuition + emp_transit + emp_bridge
# Pack parameters inside data series matrix configurations
plot_points.append({"Hourly Wage": w, "Resource Value": gross, "Type": "1. Gross Earned Wages"})
plot_points.append({"Hourly Wage": w, "Resource Value": tot_public, "Type": "2. Public Assistance"})
plot_points.append({"Hourly Wage": w, "Resource Value": tot_employer, "Type": "3. Employer Fringe"})
chart_df = pd.DataFrame(plot_points)
Create a flat reference dataset for the baseline cost line
line_df = pd.DataFrame({
"Hourly Wage": wage_axis,
"Cost Value": [STARTING_SURVIVAL_NEED] * len(wage_axis)
})
Layer 1: The Stacked Bars for the Resource Components
bars = alt.Chart(chart_df).mark_bar(size=14).encode(
x=alt.X("Hourly Wage:Q", title="Hourly Wage ($)"),
y=alt.Y("Resource Value:Q", title="Total Monthly Resources ($)", stack=True),
color=alt.Color("Type:N", scale=alt.Scale(
domain=["1. Gross Earned Wages", "2. Public Assistance", "3. Employer Fringe"],
range=["#2ecc71", "#ff4b4b", "#f1c40f"]
), title="Resource Layer")
)
Layer 2: The Independent Solid Line for Cost of Living
line = alt.Chart(line_df).mark_line(color="#00c0f2", strokeWidth=3.5).encode(
x="Hourly Wage:Q",
y="Cost Value:Q"
)
Overlay both components onto the screen inside a single layout window
st.altair_chart(bars + line, use_container_width=True)
st.caption("""
🟩 Green Bars = Gross Wages. 🟥 Red Bars = Public Assistance Value. 🟨 Yellow Bars = Employer Incentives. 🔵 Solid Blue Line = Real Out-Of-Pocket Cost of Living Baseline.
""")