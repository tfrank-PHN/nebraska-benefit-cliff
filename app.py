import streamlit as st
import pandas as pd
import numpy as np

# Set up page and layout
st.set_page_config(page_title="Nebraska Benefit Cliff Simulator", layout="wide")

st.title("🌾 Custom Nebraska Public Benefits & Cliff Trajectory Dashboard")
st.markdown("""
This model illustrates the financial trajectory of a single parent in Nebraska over a 5-year career horizon. 
Adjust the household size and specific cost categories to match your local Nebraska county or specific family profile.
""")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("👪 Household Profile")
num_children = st.sidebar.slider("Number of Dependent Children", min_value=1, max_value=4, value=2, step=1)
current_wage = st.sidebar.slider("Starting Hourly Wage ($)", min_value=12.0, max_value=35.0, value=16.0, step=0.50)
hours_per_week = st.sidebar.number_input("Hours Worked Per Week", value=40, step=1)
annual_raise = st.sidebar.slider("Annual Wage Increase (%)", min_value=1.0, max_value=5.0, value=2.0, step=0.5) / 100
inflation_rate = st.sidebar.slider("Annual Cost of Living Inflation (%)", min_value=1.0, max_value=5.0, value=3.0, step=0.5) / 100

st.sidebar.header("🏠 Monthly Private-Market Costs")
rent_cost = st.sidebar.slider("Housing & Utilities ($/mo)", min_value=600, max_value=2500, value=1200, step=50)
childcare_cost_per_kid = st.sidebar.slider("Childcare Cost Per Child ($/mo)", min_value=400, max_value=1500, value=800, step=50)
food_cost = st.sidebar.slider("Food & Groceries ($/mo)", min_value=300, max_value=1500, value=700, step=50)
medical_cost = st.sidebar.slider("Private Health Insurance Risk ($/mo)", min_value=200, max_value=1200, value=550, step=25)
misc_cost = st.sidebar.slider("Transport & Miscellaneous ($/mo)", min_value=200, max_value=1000, value=450, step=25)

# Calculate dynamic starting survival need based on user's cost sliders
total_childcare_market = childcare_cost_per_kid * num_children
STARTING_SURVIVAL_NEED = rent_cost + total_childcare_market + food_cost + medical_cost + misc_cost

# --- DYNAMIC POLICY CONSTANTS (2026 Nebraska Frameworks) ---
# Scale Federal Poverty Level (FPL) guidelines by household size (1 adult + N children)
fpl_matrix = {1: 1718.00, 2: 2153.00, 3: 2588.00, 4: 3023.00}
FPL_MONTHLY_BASE = fpl_matrix.get(num_children, 2153.00)

MEDICAID_LIMIT_PCT = 1.38
SNAP_LIMIT_PCT = 1.65
CCAP_LIMIT_PCT = 1.85
TANF_LIMIT_BASE = 1132.50 + (393.00 * num_children)  # Nebraska CPI updated standard

# Baseline Subsidy Maximum Values
VAL_TANF = 300.00 + (100.00 * num_children)
VAL_SNAP = 250.00 * num_children
VAL_MEDICAID = medical_cost  # Tied directly to the user's customized private health cost slider
VAL_CCAP = total_childcare_market

# --- SIMULATION ENGINE ---
data = []

for year in range(1, 6):
    # Scale hourly wage and gross earnings
    wage = current_wage * ((1 + annual_raise) ** (year - 1))
    gross_monthly_earnings = (wage * hours_per_week * 52) / 12
    
    # Compound parameters by annual inflation
    inflated_survival_need = STARTING_SURVIVAL_NEED * ((1 + inflation_rate) ** (year - 1))
    current_fpl = FPL_MONTHLY_BASE * ((1 + inflation_rate) ** (year - 1))
    
    cliffs_hit = []
    
    # 1. TANF/ADC Cash Aid
    if gross_monthly_earnings <= TANF_LIMIT_BASE:
        tanf_received = VAL_TANF
    else:
        tanf_received = 0.0
        cliffs_hit.append("TANF/ADC Cash")
        
    # 2. Medicaid
    if gross_monthly_earnings <= (MEDICAID_LIMIT_PCT * current_fpl):
        medicaid_received = VAL_MEDICAID
    else:
        medicaid_received = 0.0
        cliffs_hit.append("Medicaid")
        
    # 3. SNAP Food Assistance
    if gross_monthly_earnings <= (SNAP_LIMIT_PCT * current_fpl):
        snap_received = VAL_SNAP
    else:
        snap_received = 0.0
        cliffs_hit.append("SNAP Food Aid")
        
    # 4. Childcare Subsidy (CCAP via LB 304)
    if gross_monthly_earnings <= (CCAP_LIMIT_PCT * current_fpl):
        ccap_received = VAL_CCAP
        if gross_monthly_earnings > current_fpl:
            ccap_received -= (0.07 * gross_monthly_earnings)  # Nebraska 7% family fee
    else:
        ccap_received = 0.0
        cliffs_hit.append("Childcare Subsidy")

    total_benefits_value = tanf_received + snap_received + medicaid_received + ccap_received
    net_resources = gross_monthly_earnings + total_benefits_value
    
    # Track the Bridge Deficit Requirement
    if net_resources < inflated_survival_need:
        bridge_fund_needed = inflated_survival_need - net_resources
        status_msg = "🚨 Income Deficit"
    else:
        bridge_fund_needed = 0.0
        status_msg = "✅ Self-Sustained"
        
    primary_fault = ", ".join(cliffs_hit) if cliffs_hit else "None (Fully Assisted)"
    if status_msg == "✅ Self-Sustained":
        primary_fault = "N/A - Self Sufficient"

    data.append({
        "Year": f"Year {year}",
        "Hourly Wage": f"${wage:.2f}",
        "Gross Monthly Earnings": gross_monthly_earnings,
        "Total Public Assistance Value": total_benefits_value,
        "Total Household Resources": net_resources,
        "Required Cost of Living": inflated_survival_need,
        "Monthly Bridge Fund Needed": bridge_fund_needed,
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
            "Total Public Assistance Value": "${:.2f}",
            "Total Household Resources": "${:.2f}",
            "Required Cost of Living": "${:.2f}",
            "Monthly Bridge Fund Needed": "${:.2f}"
        }),
        use_container_width=True,
        hide_index=True
    )

with col_metrics:
    st.subheader("🏛️ Policy Aggregates")
    cumulative_bridge_cost = df["Monthly Bridge Fund Needed"].sum() * 12
    st.metric(
        label="Total 5-Year Bridge Funding Cost",
        value=f"${cumulative_bridge_cost:,.2f}"
    )
    st.info(f"Target Monthly Self-Sufficiency Needed: ${STARTING_SURVIVAL_NEED:,.2f}")

# --- THE VISUAL LINE CHART ---
st.markdown("---")
st.subheader("📉 The Benefit Cliff Visualization: Total Resources vs. Local Survival Threshold")

wage_axis = np.linspace(12.0, 40.0, 150)
plot_points = []

for w in wage_axis:
    gross = (w * hours_per_week * 52) / 12
    
    t_val = VAL_TANF if gross <= TANF_LIMIT_BASE else 0
    m_val = VAL_MEDICAID if gross <= (MEDICAID_LIMIT_PCT * FPL_MONTHLY_BASE) else 0
    s_val = VAL_SNAP if gross <= (SNAP_LIMIT_PCT * FPL_MONTHLY_BASE) else 0
    c_val = VAL_CCAP if gross <= (CCAP_LIMIT_PCT * FPL_MONTHLY_BASE) else 0
    if c_val > 0 and gross > FPL_MONTHLY_BASE:
        c_val -= (0.07 * gross)
        
    tot_res = gross + t_val + m_val + s_val + c_val
    plot_points.append({
        "Hourly Wage ($)": w,
        "Total Household Resources ($)": tot_res,
        "Baseline Cost of Living ($)": STARTING_SURVIVAL_NEED
    })

chart_df = pd.DataFrame(plot_points)

st.line_chart(
    chart_df, 
    x="Hourly Wage ($)", 
    y=["Total Household Resources ($)", "Baseline Cost of Living ($)"],
    color=["#ff4b4b", "#00c0f2"]
)
st.caption("🔴 Red Line = Total resources available. 🔵 Blue Line = Your customized cost of living threshold. Sharp structural drops indicate active benefit cliff zones.")
