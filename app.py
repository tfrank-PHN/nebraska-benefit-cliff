import streamlit as st
import pandas as pd

# Set page title and layout
st.set_page_config(page_title="Nebraska Benefit Cliff Simulator", layout="wide")

st.title("🌾 Nebraska Benefit Cliff & Trajectory Simulator")
st.markdown("""
This interactive simulation shows how wage increases can paradoxically throw a single parent with 2 children into a deep financial gap, 
and calculates the exact 'Bridge Fund' required to keep them financially stable until they reach self-sufficiency.
""")

# Sidebar - User Inputs
st.sidebar.header("📊 Household Parameters")
current_wage = st.sidebar.slider("Starting Hourly Wage ($)", min_value=12.0, max_value=35.0, value=16.0, step=0.50)
hours_per_week = st.sidebar.number_input("Hours Worked Per Week", value=40, step=1)
annual_raise = st.sidebar.slider("Annual Wage Increase (%)", min_value=1.0, max_value=5.0, value=2.0, step=0.5) / 100

# Constants based on Nebraska 2026 Policy Frameworks (Family of 3)
FPL_MONTHLY = 2153.00  # 2026 Federal Poverty Level for Family of 3 estimate
MEDICAID_LIMIT = 1.38 * FPL_MONTHLY
SNAP_LIMIT = 1.65 * FPL_MONTHLY
CCAP_LIMIT = 1.85 * FPL_MONTHLY
TANF_LIMIT = 1525.50  # Updated Standard of Need base

# Market Value of Subsidies (Real-World Out of Pocket Risk)
VAL_TANF = 500.00
VAL_SNAP = 600.00
VAL_MEDICAID = 650.00  # Includes average out-of-pocket medical risk / copays
VAL_CCAP = 1600.00     # Private market cost for 2 children in Nebraska

# Self-Sustained Target Baseline
SELF_SUSTAINED_THRESHOLD = 5000.00  # Total required monthly take-home to survive without assistance

# Calculations over a 5-Year Horizon
data = []
for year in range(1, 6):
    # Apply cumulative annual raises
    wage = current_wage * ((1 + annual_raise) ** (year - 1))
    gross_monthly_earnings = (wage * hours_per_week * 52) / 12
    
    # Evaluate benefits based on strict Nebraska caps
    tanf_received = VAL_TANF if gross_monthly_earnings <= TANF_LIMIT else 0.0
    snap_received = VAL_SNAP if gross_monthly_earnings <= SNAP_LIMIT else 0.0
    medicaid_received = VAL_MEDICAID if gross_monthly_earnings <= MEDICAID_LIMIT else 0.0
    ccap_received = VAL_CCAP if gross_monthly_earnings <= CCAP_LIMIT else 0.0
    
    # Subtract 7% CCAP family fee if they still qualify for childcare aid
    if ccap_received > 0 and gross_monthly_earnings > FPL_MONTHLY:
        ccap_received -= (0x07 * gross_monthly_earnings) / 100
        
    total_benefits = tanf_received + snap_received + medicaid_received + ccap_received
    net_resources = gross_monthly_earnings + total_benefits
    
    # Calculate Cliff Cost / Bridge Fund needed to keep family at a stable baseline
    if net_resources < SELF_SUSTAINED_THRESHOLD:
        bridge_fund_needed = SELF_SUSTAINED_THRESHOLD - net_resources
        status = "In the Cliff Gap"
    else:
        bridge_fund_needed = 0.0
        status = "Self-Sustained"
        
    data.append({
        "Year": f"Year {year}",
        "Hourly Wage": f"${wage:.2f}",
        "Gross Monthly Wages": gross_monthly_earnings,
        "Total Public Assistance Value": total_benefits,
        "Total Resources": net_resources,
        "Monthly Bridge Subsidy Cost": bridge_fund_needed,
        "Status": status
    })

df = pd.DataFrame(data)

# Layout Split into Data Columns
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📈 5-Year Trajectory and Cliff Impact")
    # Display the primary calculation matrix
    st.dataframe(
        df.style.format({
            "Gross Monthly Wages": "${:.2f}",
            "Total Public Assistance Value": "${:.2f}",
            "Total Resources": "${:.2f}",
            "Monthly Bridge Subsidy Cost": "${:.2f}"
        }),
        use_container_width=True
    )

with col2:
    st.subheader("📉 Policy Insights for Lawmakers")
    total_bridge_cost = df["Monthly Bridge Subsidy Cost"].map(float).sum() * 12
    
    st.metric(
        label="Total 5-Year Bridge Funding Required", 
        value=f"${total_bridge_cost:,.2f}",
        help="The total financial support needed over 5 years to smoothly transition this single household off public aid without facing a resource crash."
    )
    
    # Dynamic text warning based on cliff event
    if any(df["Status"] == "In the Cliff Gap"):
        st.error("⚠️ Warning: The worker enters a benefit cliff gap during this 5-year timeline. A raise results in an overall loss of household stability.")
    else:
        st.success("✅ The current starting wage allows the household to cleanly scale past cliffs over the 5-year period.")
