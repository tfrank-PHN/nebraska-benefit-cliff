import streamlit as st
import pandas as pd
import numpy as np

# Set up page and layout
st.set_page_config(page_title="Nebraska Benefit Cliff Simulator", layout="wide")

st.title("🌾 Nebraska Public Benefits & Cliff Trajectory Dashboard")
st.markdown("""
This model illustrates the financial trajectory of a single parent with 2 children in Nebraska over a 5-year career horizon. 
It calculates compounding inflation, tracks the exact program causing a benefit cliff, and visualizes the net resource drops for policy makers.
""")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("📊 Interactive Parameters")
current_wage = st.sidebar.slider("Starting Hourly Wage ($)", min_value=12.0, max_value=35.0, value=16.0, step=0.50)
hours_per_week = st.sidebar.number_input("Hours Worked Per Week", value=40, step=1)
annual_raise = st.sidebar.slider("Annual Wage Increase (%)", min_value=1.0, max_value=5.0, value=2.0, step=0.5) / 100
inflation_rate = st.sidebar.slider("Annual Inflation / Cost of Living Rise (%)", min_value=1.0, max_value=5.0, value=3.0, step=0.5) / 100

# --- POLICY CONSTANTS (2026 Nebraska Frameworks - Family of 3) ---
FPL_MONTHLY_BASE = 2153.00  
MEDICAID_LIMIT_PCT = 1.38
SNAP_LIMIT_PCT = 1.65
CCAP_LIMIT_PCT = 1.85
TANF_LIMIT_BASE = 1525.50  

# Baseline Market Values of Aid / Out-Of-Pocket Protection
VAL_TANF = 500.00
VAL_SNAP = 600.00
VAL_MEDICAID = 650.00  # Reflects out-of-pocket medical exposure/deductibles
VAL_CCAP = 1600.00     # Real-world market rate for 2 kids in NE

# Survival Base Needs
STARTING_SURVIVAL_NEED = 5000.00  

# --- SIMULATION ENGINE ---
data = []
chart_data = []

# Generate sequential rows for the 5-year outlook
for year in range(1, 6):
    # Scale variables by inflation and raises over time
    wage = current_wage * ((1 + annual_raise) ** (year - 1))
    gross_monthly_earnings = (wage * hours_per_week * 52) / 12
    
    # Compound the cost of living baseline by inflation each year
    inflated_survival_need = STARTING_SURVIVAL_NEED * ((1 + inflation_rate) ** (year - 1))
    current_fpl = FPL_MONTHLY_BASE * ((1 + inflation_rate) ** (year - 1))
    
    # Tracking exact cliff triggers
    cliffs_hit = []
    
    # 1. TANF Evaluation
    if gross_monthly_earnings <= TANF_LIMIT_BASE:
        tanf_received = VAL_TANF
    else:
        tanf_received = 0.0
        cliffs_hit.append("TANF/ADC Cash Assist")
        
    # 2. Medicaid Evaluation
    if gross_monthly_earnings <= (MEDICAID_LIMIT_PCT * current_fpl):
        medicaid_received = VAL_MEDICAID
    else:
        medicaid_received = 0.0
        cliffs_hit.append("Medicaid (Heritage Health)")
        
    # 3. SNAP Evaluation
    if gross_monthly_earnings <= (SNAP_LIMIT_PCT * current_fpl):
        snap_received = VAL_SNAP
    else:
        snap_received = 0.0
        cliffs_hit.append("SNAP Food Aid")
        
    # 4. Childcare Evaluation
    if gross_monthly_earnings <= (CCAP_LIMIT_PCT * current_fpl):
        ccap_received = VAL_CCAP
        # Apply Nebraska 7% copay rule if earning over poverty line
        if gross_monthly_earnings > current_fpl:
            ccap_received -= (0.07 * gross_monthly_earnings)
    else:
        ccap_received = 0.0
        cliffs_hit.append("Childcare Subsidy (CCAP)")

    total_benefits_value = tanf_received + snap_received + medicaid_received + ccap_received
    net_resources = gross_monthly_earnings + total_benefits_value
    
    # Calculate the exact resource gap accounting for inflation over time
    if net_resources < inflated_survival_need:
        bridge_fund_needed = inflated_survival_need - net_resources
        status_msg = "🚨 Income Deficit"
    else:
        bridge_fund_needed = 0.0
        status_msg = "✅ Self-Sustained"
        
    # Determine the primary active cliff for reporting
    primary_fault = ", ".join(cliffs_hit) if cliffs_hit else "None (Fully Assisted)"
    if status_msg == "✅ Self-Sustained":
        primary_fault = "N/A - Self Sufficient"

    data.append({
        "Year": f"Year {year}",
        "Hourly Wage": f"${wage:.2f}",
        "Gross Monthly Earnings": gross_monthly_earnings,
        "Total Public Assistance Remaining": total_benefits_value,
        "Total Household Resources": net_resources,
        "Required Cost of Living (With Inflation)": inflated_survival_need,
        "Monthly Bridge Fund Needed": bridge_fund_needed,
        "Active Program Cliffs Triggered": primary_fault
    })

df = pd.DataFrame(data)

# --- USER INTERFACE LAYOUT ---
col_table, col_metrics = st.columns([2.5, 1])

with col_table:
    st.subheader("📊 5-Year Financial Calculation Matrix")
    st.dataframe(
        df.style.format({
            "Gross Monthly Earnings": "${:.2f}",
            "Total Public Assistance Remaining": "${:.2f}",
            "Total Household Resources": "${:.2f}",
            "Required Cost of Living (With Inflation)": "${:.2f}",
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
        value=f"${cumulative_bridge_cost:,.2f}",
        help="The total capital needed to systematically absorb the economic cliffs and keep this household out of an active financial deficit over 5 years."
    )
    st.markdown("""
    **Understanding the Triggers:**
    * Watch the **Active Program Cliffs Triggered** column in the table. 
    * When a program name appears there, it means the worker's earnings crossed that state threshold, stripping away that entire benefit program's financial baseline value.
    """)

# --- THE VISUAL LINE CHART (WHAT LAWMAKERS NEED TO SEE) ---
st.markdown("---")
st.subheader("📉 The Benefit Cliff Visualization: Total Resources vs. Inflation Baseline")

# Create a dense data grid for a smooth line chart plot across varying wages
wage_axis = np.linspace(12.0, 35.0, 150)
plot_points = []

for w in wage_axis:
    gross = (w * hours_per_week * 52) / 12
    
    # Apply baseline rules for standalone chart reference mapping
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

# Render native Streamlit line chart
st.line_chart(
    chart_df, 
    x="Hourly Wage ($)", 
    y=["Total Household Resources ($)", "Baseline Cost of Living ($)"],
    color=["#ff4b4b", "#00c0f2"]
)
st.caption("🔴 Red Line = Total available resources. 🔵 Blue Line = What it actually costs to survive. Notice the sharp drops where the red line plummets below survival needs when a cliff is broken.")
