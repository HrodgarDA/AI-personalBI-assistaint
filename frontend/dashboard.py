import streamlit as st
from collections import defaultdict
from backend.services.visualization import plot_amount_over_time, plot_category_pie, plot_category_totals

def render_dashboard(data):
    st.markdown("<h2 style='text-align: center;'>📈 Dashboard</h2>", unsafe_allow_html=True)
    
    # Financial Configuration
    SAVINGS_CAT = "Savings & Investments"
    REFUND_CAT = "Refund"

    # Group records by transaction_type
    incoming_records = [r for r in data if r.get("transaction_type") == "Incoming"]
    outgoing_records = [r for r in data if r.get("transaction_type") == "Outgoing"]

    # --- 1. SAVINGS LOGIC ---
    deposits_to_savings = sum(abs(r.get("amount", 0)) for r in outgoing_records if r.get("category_id") == SAVINGS_CAT)
    withdrawals_from_savings = sum(abs(r.get("amount", 0)) for r in incoming_records if r.get("category_id") == SAVINGS_CAT)
    net_savings_val = deposits_to_savings - withdrawals_from_savings

    # --- 2. PURE INCOME ---
    real_income_val = sum(abs(r.get("amount", 0)) for r in incoming_records if r.get("category_id") not in [SAVINGS_CAT, REFUND_CAT])
    
    # --- 3. REAL EXPENSES ---
    gross_expenses_val = sum(abs(r.get("amount", 0)) for r in outgoing_records if r.get("category_id") != SAVINGS_CAT)
    refunds_val = sum(abs(r.get("amount", 0)) for r in incoming_records if r.get("category_id") == REFUND_CAT)
    real_expenses_val = gross_expenses_val - refunds_val

    # --- 4. NET BALANCE ---
    total_balance = sum(r.get("amount", 0) for r in data)
    num_tx = len(data)

    # Determine context for charts
    active_types = {row.get("transaction_type") for row in data if row.get("transaction_type")}
    is_mostly_income = all(t in ["Incoming", "Salary", "Refund"] for t in active_types) if active_types else False
    is_mostly_expense = all(t in ["Outgoing", "Expense"] for t in active_types) if active_types else False
    
    if is_mostly_income:
        chart_title_prefix = "Income"
    elif is_mostly_expense:
        chart_title_prefix = "Expenses"
    else:
        chart_title_prefix = "Transactions"

    # Top Category calculation
    cat_totals = defaultdict(float)
    for row in data:
        amount = row.get("amount")
        cat = row.get("category_id")
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
        col2.metric("Real Income", f"€ {real_income_val:,.2f}", help="Real income (excluding savings transfers or internal refunds)")
        col3.metric("Real Expenses (Net)", f"€ {real_expenses_val:,.2f}", help="Actual expenses (Outgoing - Refunds)", delta_color="inverse")
        col4.metric("Top Category", top_cat)

    # Low Confidence Warning
    try:
        low_conf_count = len([row for row in data if float(row.get("confidence", 1.0)) < 0.7])
    except (ValueError, TypeError):
        low_conf_count = 0
        
    if low_conf_count > 0:
        st.warning(f"⚠️ **{low_conf_count} transactions** require your review (Confidence < 70%). Switch to the **Data Explorer** and use the 'Needs Review' filter.")

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

    st.markdown("<h3 style='text-align: center;'>Performance over Time</h3>", unsafe_allow_html=True)
    
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
            use_container_width=True, 
            key="chart_over_time"
        )

    st.markdown(f"<h3 style='text-align: center;'>{chart_title_prefix} by Category</h3>", unsafe_allow_html=True)
    with st.container(border=True):
        pie_data = [r for r in data if r.get("category_id") not in [SAVINGS_CAT, REFUND_CAT]]
        st.plotly_chart(plot_category_pie(pie_data), use_container_width=True, key="chart_category_pie")

    st.markdown(f"<h3 style='text-align: center;'>Total {chart_title_prefix} by Category</h3>", unsafe_allow_html=True)
    with st.container(border=True):
        st.plotly_chart(plot_category_totals(data), use_container_width=True, key="chart_category_totals")

    st.caption("Insights generated by AI Personal BI Assistant.")
