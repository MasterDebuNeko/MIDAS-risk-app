import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- Page Configuration ---
st.set_page_config(page_title="Prop Firm Simulator", layout="wide")

# --- CSS Styling ---
st.markdown("""
<style>
    .metric-card { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    .stButton>button { width: 100%; background-color: #007bff; color: white; }
    .small-font { font-size: 12px; color: #666; margin-top: -10px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.title("🛡️ Prop Firm Simulator")
st.markdown("Analyze **Pass**, **Time**, **Failure**, and **Timeout** probabilities.")

# --- Sidebar Inputs ---
st.sidebar.header("⚙️ Settings")

with st.sidebar.expander("📝 Prop Firm Rules", expanded=True):
    account_size = st.number_input("Account Size ($)", value=50000, step=1000)
    profit_target = st.number_input("Profit Target ($)", value=3000, step=100)
    max_daily_dd = st.number_input("Max Daily Drawdown ($)", value=2500, step=100)
    max_total_dd = st.number_input("Max Total Drawdown ($)", value=2500, step=100)
    trailing_type = st.selectbox("Drawdown Type", ["Trailing from High Water Mark", "Static"])

with st.sidebar.expander("📊 Trading Parameters", expanded=True):
    # 1. Win Rate
    win_rate_input = st.number_input("Win Rate (%)", value=70.0, step=0.1, min_value=1.0, max_value=100.0)
    win_rate = win_rate_input / 100.0
    
    reward_ratio = st.number_input("Risk/Reward Ratio (1:?)", value=1.0, step=0.1)
    
    # 2. Trades Per Day
    st.markdown("**No. of Trades per day**")
    trades_input = st.text_input("No. of Trades Input", "2, 3, 4, 5", label_visibility="collapsed")
    st.markdown('<p class="small-font">integers only, separated by comma</p>', unsafe_allow_html=True)
    
    # 3. Risk Scenarios
    st.markdown("---")
    st.markdown("**Risk Amount ($)**")
    risk_input = st.text_input("Risk Amount Input", "100, 120, 150, 175, 200, 250, 300, 350, 400, 450, 500", label_visibility="collapsed")
    st.markdown('<p class="small-font">separated by comma</p>', unsafe_allow_html=True)

    # 4. Personal Risk Management
    st.markdown("---")
    st.markdown("🛡️ **Personal Risk Management**")
    daily_limit_r = st.number_input("Daily Loss Limit (R) (0 = Disabled)", value=2, step=1, help="Ex: Enter 2 means stop trading for the day if loss reaches 2R.")

with st.sidebar.expander("🎲 Simulation Settings", expanded=False):
    num_simulations = st.number_input("Simulations per Scenario", value=5000, step=100)
    max_days = st.number_input("Max Days to Trade", value=20, step=1)

# --- Logic Functions ---

def run_monte_carlo(risk_val, trades_day_val):
    """Fast simulation for Heatmap (returns stats only)"""
    reward_per_trade = risk_val * reward_ratio
    personal_limit_usd = (daily_limit_r * risk_val) if daily_limit_r > 0 else 0
    
    pass_count = 0
    fail_count = 0
    timeout_count = 0
    total_days_pass = 0
    
    for _ in range(num_simulations):
        equity = account_size
        high_water_mark = account_size
        status = "In Progress"
        current_dd_limit = account_size - max_total_dd
        
        for day in range(max_days):
            daily_start_equity = equity
            for trade in range(trades_day_val):
                is_win = np.random.rand() < win_rate
                if is_win: equity += reward_per_trade
                else: equity -= risk_val
                
                if equity > high_water_mark:
                    high_water_mark = equity
                    if trailing_type == "Trailing from High Water Mark":
                        current_dd_limit = high_water_mark - max_total_dd
                
                if equity <= current_dd_limit:
                    status = "Failed"; break
                
                current_daily_loss = daily_start_equity - equity
                if current_daily_loss >= max_daily_dd:
                    status = "Failed"; break
                
                if personal_limit_usd > 0 and current_daily_loss >= personal_limit_usd:
                    break 

                if equity >= (account_size + profit_target):
                    status = "Passed"; break
            
            if status != "In Progress": break
            
        if status == "Passed":
            pass_count += 1
            total_days_pass += (day + 1)
        elif status == "Failed": fail_count += 1
        else: timeout_count += 1
            
    avg_days = total_days_pass / pass_count if pass_count > 0 else 0
    risk_percent = (risk_val / account_size) * 100
    
    return {
        "Risk ($)": risk_val, "Risk (%)": risk_percent, "Trades/Day": trades_day_val,
        "Pass Rate (%)": (pass_count / num_simulations) * 100,
        "Failed Rate (%)": (fail_count / num_simulations) * 100,
        "Timeout Rate (%)": (timeout_count / num_simulations) * 100,
        "Avg Days": round(avg_days, 1)
    }

def run_visualization_sim(risk_val, trades_day_val, n_viz=100):
    """Detailed simulation for Equity Curve (returns daily data)"""
    reward_per_trade = risk_val * reward_ratio
    personal_limit_usd = (daily_limit_r * risk_val) if daily_limit_r > 0 else 0
    
    all_curves = []
    
    for sim_id in range(n_viz):
        equity = account_size
        high_water_mark = account_size
        status = "Timeout" # Default if ends without pass/fail
        current_dd_limit = account_size - max_total_dd
        
        # Start with Day 0
        curve = [{"Day": 0, "Equity": account_size, "SimID": sim_id, "Status": "In Progress"}]
        
        for day in range(1, max_days + 1):
            daily_start_equity = equity
            day_status = "In Progress"
            
            for trade in range(trades_day_val):
                is_win = np.random.rand() < win_rate
                if is_win: equity += reward_per_trade
                else: equity -= risk_val
                
                # Trailing DD Update
                if equity > high_water_mark:
                    high_water_mark = equity
                    if trailing_type == "Trailing from High Water Mark":
                        current_dd_limit = high_water_mark - max_total_dd
                
                # Check Fails
                if equity <= current_dd_limit:
                    status = "Failed"; day_status = "Failed"; break
                
                current_daily_loss = daily_start_equity - equity
                if current_daily_loss >= max_daily_dd:
                    status = "Failed"; day_status = "Failed"; break
                
                # Check Personal Limit
                if personal_limit_usd > 0 and current_daily_loss >= personal_limit_usd:
                    break 

                # Check Pass
                if equity >= (account_size + profit_target):
                    status = "Passed"; day_status = "Passed"; break
            
            # Record Day End
            curve.append({"Day": day, "Equity": equity, "SimID": sim_id, "Status": status})
            
            if day_status != "In Progress":
                break
        
        # Update status for the whole curve based on final outcome
        final_status = curve[-1]["Status"]
        for point in curve:
            point["Status"] = final_status
            
        all_curves.extend(curve)
        
    return pd.DataFrame(all_curves)

# --- TABS LAYOUT ---
tab1, tab2 = st.tabs(["📊 Heatmap Analysis", "📈 Equity Curve Inspector"])

# ================= TAB 1: HEATMAP =================
with tab1:
    run_btn = st.button("🚀 Run Full Analysis", key="btn_heatmap")
    
    if run_btn:
        try:
            risk_list = [float(x.strip()) for x in risk_input.split(',')]
            trades_list = [int(x.strip()) for x in trades_input.split(',')]
            risk_list.sort(); trades_list.sort()
            
            results_summary = []
            total_steps = len(risk_list) * len(trades_list)
            current_step = 0
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for r_val in risk_list:
                for t_val in trades_list:
                    current_step += 1
                    status_text.text(f"Simulating... Risk: ${r_val} | Trades: {t_val}/day")
                    res = run_monte_carlo(r_val, t_val)
                    results_summary.append(res)
                    progress_bar.progress(current_step / total_steps)
            
            status_text.empty(); progress_bar.empty()
            df_summary = pd.DataFrame(results_summary)
            cols = ["Risk ($)", "Risk (%)", "Trades/Day", "Pass Rate (%)", "Failed Rate (%)", "Timeout Rate (%)", "Avg Days"]
            df_summary = df_summary[cols]

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🔥 1. Pass Rate (%)")
                heatmap_pass = df_summary.pivot(index="Trades/Day", columns="Risk ($)", values="Pass Rate (%)")
                fig_pass = px.imshow(heatmap_pass, labels=dict(x="Risk ($)", y="Trades/Day", color="Pass %"),
                                     x=heatmap_pass.columns, y=heatmap_pass.index, text_auto=".1f", aspect="auto", color_continuous_scale="Blues")
                fig_pass.update_yaxes(dtick=1)
                st.plotly_chart(fig_pass, use_container_width=True)

                st.subheader("💥 3. Failed Rate (%)")
                heatmap_fail = df_summary.pivot(index="Trades/Day", columns="Risk ($)", values="Failed Rate (%)")
                fig_fail = px.imshow(heatmap_fail, labels=dict(x="Risk ($)", y="Trades/Day", color="Fail %"),
                                     x=heatmap_fail.columns, y=heatmap_fail.index, text_auto=".1f", aspect="auto", color_continuous_scale="Reds")
                fig_fail.update_yaxes(dtick=1)
                st.plotly_chart(fig_fail, use_container_width=True)

            with col2:
                st.subheader("⏳ 2. Avg Days to Pass")
                heatmap_days = df_summary.pivot(index="Trades/Day", columns="Risk ($)", values="Avg Days")
                fig_days = px.imshow(heatmap_days, labels=dict(x="Risk ($)", y="Trades/Day", color="Days"),
                                     x=heatmap_days.columns, y=heatmap_days.index, text_auto=".1f", aspect="auto", color_continuous_scale="Purples")
                fig_days.update_yaxes(dtick=1)
                st.plotly_chart(fig_days, use_container_width=True)

                st.subheader("🐢 4. Timeout Rate (%)")
                heatmap_timeout = df_summary.pivot(index="Trades/Day", columns="Risk ($)", values="Timeout Rate (%)")
                fig_timeout = px.imshow(heatmap_timeout, labels=dict(x="Risk ($)", y="Trades/Day", color="Timeout %"),
                                        x=heatmap_timeout.columns, y=heatmap_timeout.index, text_auto=".1f", aspect="auto", color_continuous_scale="Greys")
                fig_timeout.update_yaxes(dtick=1)
                st.plotly_chart(fig_timeout, use_container_width=True)

            st.divider()
            st.subheader("📋 Comprehensive Performance Metrics")
            st.dataframe(df_summary.style.format({
                "Risk ($)": "${:.0f}", "Risk (%)": "{:.2f}%", "Pass Rate (%)": "{:.1f}%",
                "Failed Rate (%)": "{:.1f}%", "Timeout Rate (%)": "{:.1f}%", "Avg Days": "{:.1f} Days"
            }).background_gradient(subset=["Pass Rate (%)"], cmap="Blues"), use_container_width=True)
            
            # Footer
            st.markdown("---")
            st.subheader("⚙️ Simulation Settings Reference")
            c1, c2, c3 = st.columns(3)
            with c1:
                 st.write(f"- Account: **${account_size:,.0f}**")
                 st.write(f"- Profit Target: **${profit_target:,.0f}**")
                 st.write(f"- Max Daily Drawdown: **${max_daily_dd:,.0f}**")
            with c2:
                 st.write(f"- Win Rate: **{win_rate_input:.1f}%**")
                 st.write(f"- Risk/Reward: **1:{reward_ratio}**")
                 st.write(f"- Personal Daily Limit: **{daily_limit_r}R**")
            with c3:
                 st.write(f"- Simulations: **{num_simulations:,}** runs")
                 st.write(f"- Max Days: **{max_days}** days")

        except ValueError:
            st.error("⚠️ Data Error: Please ensure inputs are correct.")

# ================= TAB 2: EQUITY CURVES =================
with tab2:
    st.markdown("### 📈 Visualize Specific Scenario")
    st.info("Select a combination to see 100 random equity curves.")
    
    try:
        # Parse inputs again for dropdowns
        r_options = [float(x.strip()) for x in risk_input.split(',')]
        t_options = [int(x.strip()) for x in trades_input.split(',')]
        r_options.sort(); t_options.sort()
        
        c1, c2, c3 = st.columns([1,1,2])
        with c1:
            sel_risk = st.selectbox("Select Risk Amount ($)", r_options)
        with c2:
            sel_trades = st.selectbox("Select Trades/Day", t_options)
        with c3:
            st.write("") # Spacer
            st.write("")
            viz_btn = st.button("📸 Generate Equity Curves", key="btn_viz")
            
        if viz_btn:
            with st.spinner(f"Simulating 100 runs for Risk ${sel_risk}, Trades {sel_trades}..."):
                df_viz = run_visualization_sim(sel_risk, sel_trades, n_viz=100)
                
                # Define Colors
                color_map = {"Passed": "#28a745", "Failed": "#dc3545", "Timeout": "#6c757d"}
                
                # Plot
                fig = px.line(df_viz, x="Day", y="Equity", color="Status", line_group="SimID",
                              color_discrete_map=color_map,
                              title=f"Equity Curves: Risk ${sel_risk} | {sel_trades} Trades/Day (100 Samples)")
                
                # Add Lines (Initial, Target, Max Loss estimate)
                fig.add_hline(y=account_size, line_dash="dash", line_color="black", annotation_text="Start")
                fig.add_hline(y=account_size + profit_target, line_dash="dot", line_color="green", annotation_text="Target")
                # Note: Drawdown line is dynamic, so we just show start level
                
                fig.update_traces(opacity=0.4, line=dict(width=1))
                fig.update_layout(height=600)
                st.plotly_chart(fig, use_container_width=True)
                
                # Stats for this batch
                batch_pass = len(df_viz[df_viz['Status'] == 'Passed']['SimID'].unique())
                st.caption(f"In this sample batch: Passed {batch_pass}%")

    except ValueError:
        st.error("⚠️ Please check your input format in the sidebar first.")
