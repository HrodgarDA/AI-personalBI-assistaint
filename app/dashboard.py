import streamlit as st
from collections import defaultdict
from auto_bi.utils.graph import plot_amount_over_time, plot_category_pie, plot_category_totals

def render_dashboard(data):
    st.markdown("<h2 style='text-align: center;'>📈 Dashboard</h2>", unsafe_allow_html=True)
    
    # Financial Configuration
    SAVINGS_CAT = "Savings & Investments"
    REFUND_CAT = "Refund"

    # Group records by category and tipology
    incoming_records = [r for r in data if r.get("tipology") == "Incoming"]
    outgoing_records = [r for r in data if r.get("tipology") == "Outgoing"]

    # --- 1. SAVINGS LOGIC (Netting deposits and withdrawals) ---
    deposits_to_savings = sum(abs(r.get("amount", 0)) for r in outgoing_records if r.get("category") == SAVINGS_CAT)
    withdrawals_from_savings = sum(abs(r.get("amount", 0)) for r in incoming_records if r.get("category") == SAVINGS_CAT)
    net_savings_val = deposits_to_savings - withdrawals_from_savings

    # --- 2. PURE INCOME: Total incoming excluding internal transfers from savings ---
    real_income_val = sum(abs(r.get("amount", 0)) for r in incoming_records if r.get("category") not in [SAVINGS_CAT, REFUND_CAT])
    
    # --- 3. REAL EXPENSES: Total outgoing (non-investment) minus Refunds ---
    gross_expenses_val = sum(abs(r.get("amount", 0)) for r in outgoing_records if r.get("category") != SAVINGS_CAT)
    refunds_val = sum(abs(r.get("amount", 0)) for r in incoming_records if r.get("category") == REFUND_CAT)
    real_expenses_val = gross_expenses_val - refunds_val

    # --- 4. NET BALANCE ---
    total_balance = sum(r.get("amount", 0) for r in data)
    num_tx = len(data)

    # Determine context for charts
    active_tips = {row.get("tipology", row.get("direction")) for row in data}
    is_mostly_income = all(t in ["Incoming", "Salary", "Refund"] for t in active_tips) if active_tips else False
    is_mostly_expense = all(t in ["Outgoing", "Expense"] for t in active_tips) if active_tips else False
    
    if is_mostly_income:
        chart_title_prefix = "Income"
    elif is_mostly_expense:
        chart_title_prefix = "Expenses"
    else:
        chart_title_prefix = "Transactions"

    # Top Category calculation (excluding internal movements)
    cat_totals = defaultdict(float)
    for row in data:
        amount = row.get("amount")
        cat = row.get("category")
        if cat and cat not in [SAVINGS_CAT, REFUND_CAT] and isinstance(amount, (int, float)):
             cat_totals[cat] += abs(amount)
    
    top_cat = max(cat_totals.items(), key=lambda x: x[1])[0] if cat_totals else "N/A"

    # Net Balance Widget
    st.markdown(f"""
        <div style='background-color: #1F2937; padding: 6px 15px; border-radius: 12px; border: 1px solid #374151; margin-bottom: 24px; display: flex; align-items: center; justify-content: space-around; gap: 20px;'>
            <div style='text-align: center;'>
                <span style='margin: 0; font-size: 0.7rem; color: #9CA3AF; text-transform: uppercase; font-weight: 600;'>Net Balance</span><br>
                <span style='margin: 0; color: {"#10B981" if total_balance >=0 else "#EF4444"}; font-size: 1.5rem; font-weight: bold;'>€ {total_balance:,.2f}</span>
            </div>
            <div style='width: 1px; height: 40px; background-color: #374151;'></div>
            <div style='text-align: center;'>
                <span style='margin: 0; font-size: 0.7rem; color: #9CA3AF; text-transform: uppercase; font-weight: 600;'>Monthly Net Savings</span><br>
                <span style='margin: 0; color: #60A5FA; font-size: 1.5rem; font-weight: bold;'>€ {net_savings_val:,.2f}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Transactions", num_tx)
        col2.metric("Real Income", f"€ {real_income_val:,.2f}", help="Reddito reale (escluse entrate da risparmi o rimborsi)")
        col3.metric("Real Expenses (Net)", f"€ {real_expenses_val:,.2f}", help="Spese effettive (Uscite - Rimborsi)", delta_color="inverse")
        col4.metric("Top Category", top_cat)


    # Low Confidence Warning
    try:
        low_conf_count = len([row for row in data if float(row.get("confidence", 1.0)) < 0.7])
    except (ValueError, TypeError):
        low_conf_count = 0
        
    if low_conf_count > 0:
        st.warning(f"⚠️ **{low_conf_count} transactions** require your review (Confidence < 70%). Switch to the **Table** view and use the 'Needs Review' filter.")

    st.markdown("<br>", unsafe_allow_html=True)

    g_col1, g_col2, g_col3 = st.columns([1,1,1])
    if "time_freq" not in st.session_state:
        st.session_state["time_freq"] = "M"
        
    freq = st.session_state["time_freq"]
    with g_col1:
        if st.button("Daily", width="stretch", type="primary" if freq=="D" else "secondary"):
            st.session_state["time_freq"] = "D"
            st.rerun()
    with g_col2:
        if st.button("Weekly", width="stretch", type="primary" if freq=="W" else "secondary"):
            st.session_state["time_freq"] = "W"
            st.rerun()
    with g_col3:
        if st.button("Monthly", width="stretch", type="primary" if freq=="M" else "secondary"):
            st.session_state["time_freq"] = "M"
            st.rerun()

    st.markdown("<h3 style='text-align: center;'>Total Performance over Time</h3>", unsafe_allow_html=True)
    
    # Mode selector
    if "chart_is_cumulative" not in st.session_state:
        st.session_state["chart_is_cumulative"] = True

    c_col1, c_col2 = st.columns([1, 1])
    with c_col1:
        if st.button("📈 Cumulative", width="stretch", type="primary" if st.session_state["chart_is_cumulative"] else "secondary"):
            st.session_state["chart_is_cumulative"] = True
            st.rerun()
    with c_col2:
        if st.button("📊 Periodical", width="stretch", type="primary" if not st.session_state["chart_is_cumulative"] else "secondary"):
            st.session_state["chart_is_cumulative"] = False
            st.rerun()

    with st.container(border=True):
        st.plotly_chart(
            plot_amount_over_time(
                data, 
                freq=st.session_state["time_freq"], 
                cumulative=st.session_state["chart_is_cumulative"]
            ), 
            width="stretch", 
            key="chart_over_time"
        )

    st.markdown(f"<h3 style='text-align: center;'>{chart_title_prefix} by Category</h3>", unsafe_allow_html=True)
    with st.container(border=True):
        # Exclude internal transfers and refunds from pie chart to avoid distortion
        pie_data = [r for r in data if r.get("category") not in [SAVINGS_CAT, REFUND_CAT]]
        st.plotly_chart(plot_category_pie(pie_data), width="stretch", key="chart_category_pie")

    st.markdown(f"<h3 style='text-align: center;'>Total {chart_title_prefix} by Category</h3>", unsafe_allow_html=True)
    with st.container(border=True):
        st.plotly_chart(plot_category_totals(data), width="stretch", key="chart_category_totals")

    st.caption("Insights generated by Auto-BI Assistant.")
