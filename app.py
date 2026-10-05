import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

st.set_page_config(page_title="Advanced Nebraska Benefit Cliff Simulator", layout="wide")

st.title("🌾 Comprehensive Nebraska Public Benefits & Cliff Trajectory Dashboard")
st.markdown("""
This advanced model illustrates the 5-year financial trajectory of a single parent in Nebraska. 
Configure realistic cost frameworks, simulate custom employer incentives, and visualize stacked resource allocation.
""")

household_defaults = {
    1: {"fpl": 1718.00, "rent": 1000, "childcare_per_kid": 800, "food": 450, "medical": 400, "misc": 350},
    2: {"fpl": 2153.00, "rent": 1200, "childcare_per_kid": 800, "food": 700, "medical": 550, "misc": 450},
    3: {"fpl": 2588.00, "rent": 1400, "childcare_per_kid": 750, "food": 950, "medical": 650, "misc": 500},
    4: {"fpl": 3023.00, "rent": 1600, "childcare_per_kid": 700, "food": 1150, "medical": 700, "misc": 550},
    5: {"fpl": 3458.00, "rent": 1800, "childcare_per_kid": 650, "food": 1350, "medical": 750, "misc": 600},
    6: {"fpl": 3893.00, "rent": 2000, "childcare_per_kid": 600, "food": 1550, "medical": 800, "misc": 650}
}

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

st.sidebar.header("👪 Household Profile")
num_children = st.sidebar.slider(
    "Number of Dependent Children", 
    min_value=1, max_value=6, value=2, step=1,
    key="num_kids_key", on_change=apply_family_size_defaults
)

defaults = household_defaults[num_children]

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

st.sidebar.markdown("---")
st.sidebar.header("🏠 Monthly Private-Market Costs")
st.sidebar.button("🔄 Reset Costs to Selected Family Size Defaults", on_click=apply_family_size_defaults)

rent_val = st.sidebar.slider("Housing & Utilities ($/mo)", 500, 5000, key="rent_key", step=50)
childcare_val = st.sidebar.slider("Childcare Cost Per Child ($/mo)", 200, 2000, key="childcare_key", step=50)
food_val = st.sidebar.slider("Food & Groceries ($/mo)", 200, 3000, key="food_key", step=50)
medical_val = st.sidebar.slider("Private Health Insurance Risk ($/mo)", 100, 2500, key="medical_key", step=25)
misc_val = st.sidebar.slider("Other Basic Needs / Transport ($/mo)", 100, 2000, key="misc_key", step=25)

st.sidebar.header("💼 Employer Voluntary Incentives")
st.sidebar.markdown("*Simulate non-taxable fringe benefits that bypass standard public benefit arithmetic rules.*")
emp_childcare_subsidy = st.sidebar.slider("Direct Childcare Support (Sec. 129) ($/mo)", 0, 1000, 0, 50)
emp_tuition = st.sidebar.slider("Tuition Reimbursement Allowance (Sec. 127) ($/mo)", 0, 437, 0, 25)
emp_transit = st.sidebar.slider("Transit / Gas Card Commuter Benefit ($/mo)", 0, 300, 0, 25)
emp_bridge = st.sidebar.slider("Private Transition 'Bridge Fund' Stipend ($/mo)", 0, 1000, 0, 50)

FPL_MONTHLY_BASE = defaults["fpl"]
MEDICAID_LIMIT_PCT, SNAP_LIMIT_PCT, CCAP_LIMIT_PCT = 1.38, 1.65, 1.85
TANF_LIMIT_BASE = 1132.50 + (393.00 * num_children)

total_childcare_market = childcare_val * num_children
STARTING_SURVIVAL_NEED = rent_val + total_childcare_market + food_val + medical_val + misc_val

medicaid_cutoff_val = MEDICAID_LIMIT_PCT * FPL_MONTHLY_BASE
snap_cutoff_val = SNAP_LIMIT_PCT * FPL_MONTHLY_BASE
ccap_cutoff_val = CCAP_LIMIT_PCT * FPL_MONTHLY_BASE

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

st.markdown("---")
st.subheader("📋 Context Matrix: Dynamic Nebraska Program Limits & Thresholds")
st.markdown(f"""
Based on a household size of **1 Adult and {num_children} Children**, the active legal limits determining whether a family hits a cliff drop include:
*   **TANF/ADC Cash Assistance Cutoff:** **\\${TANF_LIMIT_BASE:,.2f} / month** gross income limit.
*   **Medicaid Expansion Threshold (138% FPL):** **\\${medicaid_cutoff_val:,.2f} / month** gross income limit.
*   **SNAP Food Assistance Eligibility Line (165% FPL):** **\\${snap_cutoff_val:,.2f} / month** gross income limit.
*   **Childcare Subsidy Entry Threshold (185% FPL via LB 304):** **\\${ccap_cutoff_val:,.2f} / month** gross income limit.
""")

st.markdown("---")
st.subheader("📉 The Benefit Cliff Visualization: Total Resources vs. Local Survival Threshold")

wage_axis = np.linspace(12.0, 30.0, 35)
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
    
    plot_points.append({"Hourly Wage": w, "Resource Value": gross, "Type": "A. Gross Earned Wages"})
    plot_points.append({"Hourly Wage": w, "Resource Value": tot_public, "Type": "B. Public Assistance"})
    plot_points.append({"Hourly Wage": w, "Resource Value": tot_employer, "Type": "C. Employer Fringe"})

chart_df = pd.DataFrame(plot_points)

line_df = pd.DataFrame({
    "Hourly Wage": wage_axis,
    "Cost Value": [STARTING_SURVIVAL_NEED] * len(wage_axis)
})

bars = alt.Chart(chart_df).mark_bar(size=14).encode(
x=alt.X("Hourly Wage:Q", title="Hourly Wage ($)"),
y=alt.Y("Resource Value:Q", title="Total Monthly Resources ($)", stack=True),
color=alt.Color("Type:N", scale=alt.Scale(
domain=["A. Gross Earned Wages", "B. Public Assistance", "C. Employer Fringe"],
range=["#2ecc71", "#ff4b4b", "#f1c40f"]
), title="Resource Layer"),
order=alt.Order("Type:N", sort="ascending")
)
line = alt.Chart(line_df).mark_line(color="#00c0f2", strokeWidth=3.5).encode(
x="Hourly Wage:Q",
y="Cost Value:Q"
)
st.altair_chart(bars + line, use_container_width=True)
st.caption("""
🟩 Green Bars = Gross Wages. 🟥 Red Bars = Public Assistance Value. 🟨 Yellow Bars = Employer Incentives. 🔵 Solid Blue Line = Real Out-Of-Pocket Cost of Living Baseline.
""")# --- OPTIONAL BACKEND EXTENSION: EMPLOYER TURNOVER COST CALCULATOR ---

st.markdown("---")
st.subheader("🏢 Corporate Financial Impact: The Cost of Worker Turnover")
st.markdown("""
When a valued worker turns down a promotion or leaves your company due to a benefit cliff, your business incurs 
substantial friction costs to replace them. Use this tool to calculate your company's hidden baseline losses.
""")

# Split the layout into interactive slider controls and calculation summaries
col_calc_inputs, col_calc_outputs = st.columns([1.5, 1])

with col_calc_inputs:
    worker_role_type = st.selectbox(
        "Select the General Position Tier:",
        ["Entry-Level / Frontline Worker", "Mid-Level Specialist / Shift Supervisor", "Advanced Technical Role"]
    )
    
    # Establish dynamic replacement baselines based on national SHRM workforce standards
    if worker_role_type == "Entry-Level / Frontline Worker":
        default_separation_cost = 4000.00
    elif worker_role_type == "Mid-Level Specialist / Shift Supervisor":
        default_separation_cost = 9500.00
    else:
        default_separation_cost = 15000.00
        
    custom_replacement_cost = st.slider(
        "Estimated Total Cost to Replace One Worker ($):", 
        min_value=1000, max_value=25000, value=int(default_separation_cost), step=500,
        help="Includes recruiting ads, background checks, temporary agency fees, overtime for remaining staff, and manager training hours."
    )
    
    annual_cliff_turnover_count = st.slider(
        "Number of Employees Lost to Cliff Events Per Year:",
        min_value=1, max_value=50, value=3, step=1,
        help="How many workers quit, scale back hours, or decline promotions annually at your firm to protect their public benefits?"
    )

# Calculate corporate metrics based on user slider adjustments
total_annual_turnover_loss = custom_replacement_cost * annual_cliff_turnover_count
monthly_employer_fringe_total = emp_childcare_subsidy + emp_tuition + emp_transit + emp_bridge
annual_employer_incentive_investment = monthly_employer_fringe_total * 12

with col_calc_outputs:
    st.markdown("#### 📉 Financial Summary Pass")
    st.metric(
        label="Your Annual Capital Lost to Turnover Friction",
        value=f"${total_annual_turnover_loss:,.2f}",
        delta="- Net Revenue Drag",
        delta_color="inverse"
    )
    
    st.metric(
        label="Your Current Annual Investment in Fringe Benefits",
        value=f"${annual_employer_incentive_investment:,.2f}",
        help="The total annual cost of the voluntary employer incentives currently configured in your sidebar controls."
    )
    
    # Render dynamic strategic guidance comparing losses to potential solutions
    if annual_employer_incentive_investment < total_annual_turnover_loss:
        st.success(f"""
        💡 **Strategic ROI Insight:** Investing in non-taxable fringe benefits is highly cost-effective for your business. 
        Your current benefit allocation costs **${annual_employer_incentive_investment:,.2f}/year**, which is significantly 
        less than the **${total_annual_turnover_loss:,.2f}** you lose to turnover. By stabilizing your worker's benefits, 
        you prevent them from quitting and save your business money.
        """)
    else:
        st.warning("""
        ⚠️ **Optimization Insight:** Your configured employer benefits currently exceed your baseline turnover costs. 
        Consider optimizing your voluntary support levels or targeting these incentives specifically toward high-risk 
        retention positions to maximize your corporate return on investment.
        """)
