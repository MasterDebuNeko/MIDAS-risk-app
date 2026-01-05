import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px

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

# --- Initialize Session State (Memory) ---
if 'sim_results' not in st.session_state:
    st.session_state.sim_results = None
if 'sim_params' not in st.session_state:
    st.session_state.sim_params = None

# --- Header ---
st.title("🛡️ Prop Firm Simulator")
st.markdown("**Monte Carlo Analysis: Probability, Efficiency, and Risk Metrics.**")

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

with st.sidebar.expander("🎲 Simulation Settings", expanded=True):
    num_simulations = st.number_input("Simulations per Scenario", value=5000, step=100)
    max_days = st.number_input("Max Days to Trade", value=20, step=1)

# --- Logic Functions ---

def run_monte_carlo(risk_val, trades_day_val):
    """Deep simulation for Heatmap & Stats & ALL Histogram Data"""
    reward_per_trade = risk_val * reward_ratio
    personal_limit_usd = (daily_limit_r * risk_val) if daily_limit_r > 0 else 0
    
    pass_count = 0
    fail_count = 0
    timeout_count = 0
    
    # --- Collections for Histograms ---
    all_pass_days = []
    all_fail_days = []
    all_final_pnl = []
    all_max_win_streaks = []  # Added
    all_max_loss_streaks = [] # Added
    
    for _ in range(num_simulations):
        equity = account_size
        high_water_mark = account_size
        status = "In Progress"
        current_dd_limit = account_size - max_total_dd
        
        sim_max_win_streak = 0
        sim_max_loss_streak = 0
        current_win_streak = 0
        current_loss_streak = 0
        
        for day in range(max_days):
            daily_start_equity = equity
            
            for trade in range(trades_day_val):
                is_win = np.random.rand() < win_rate
                
                if is_win:
                    current_win_streak += 1
                    current_loss_streak = 0
                    if current_win_streak > sim_max_win_streak: sim_max_win_streak = current_win_streak
                    equity += reward_per_trade
                else:
                    current_loss_streak += 1
                    current_win_streak = 0
                    if current_loss_streak > sim_max_loss_streak: sim_max_loss_streak = current_loss_streak
                    equity -= risk_val
                
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
            
        # Collect Data
        all_max_win_streaks.append(sim_max_win_streak)
        all_max_loss_streaks.append(sim_max_loss_streak)
        
        outcome_status = "Timeout"
        if status == "Passed":
            pass_count += 1
            all_pass_days.append(day + 1)
            outcome_status = "Passed"
        elif status == "Failed": 
            fail_count += 1
            all_fail_days.append(day + 1)
            outcome_status = "Failed"
        else: 
            timeout_count += 1
            
        all_final_pnl.append({
            "PnL": equity - account_size,
            "Status": outcome_status
        })
            
    # --- Calculate Statistics ---
    
    if pass_count > 0:
        avg_days_pass = sum(all_pass_days) / pass_count
        median_days_pass = np.median(all_pass_days)
    else:
        avg_days_pass = 0
        median_days_pass = 0
    
    if fail_count > 0:
        avg_days_fail = sum(all_fail_days) / fail_count
        median_days_fail = np.median(all_fail_days)
    else:
        avg_days_fail = 0
        median_days_fail = 0
        
    avg_max_win_streak = sum(all_max_win_streaks) / num_simulations
    avg_max_loss_streak = sum(all_max_loss_streaks) / num_simulations
    worst_case_95 = np.percentile(all_max_loss_streaks, 95)
    
    risk_percent = (risk_val / account_size) * 100
    
    return {
        "Risk ($)": risk_val, "Risk (%)": risk_percent, "Trades/Day": trades_day_val,
        "Pass Rate (%)": (pass_count / num_simulations) * 100,
        "Fail Rate (%)": (fail_count / num_simulations) * 100,
        "Timeout Rate (%)": (timeout_count / num_simulations) * 100,
        
        "Avg Days Pass": round(avg_days_pass, 1),
        "Median Days Pass": round(median_days_pass, 1),
        
        "Avg Days Fail": round(avg_days_fail, 1),
        "Median Days Fail": round(median_days_fail, 1),
        
        "Avg Max Win Streak": round(avg_max_win_streak, 1),
        "Avg Max Loss Streak": round(avg_max_loss_streak, 1),
        "Worst Case Streak (95%)": round(worst_case_95, 1),
        
        # ✅ Sending ALL raw data for Histograms
        "Raw Data": {
            "PnL": all_final_pnl,
            "Pass Days": all_pass_days,
            "Fail Days": all_fail_days,
            "Win Streaks": all_max_win_streaks,
            "Loss Streaks": all_max_loss_streaks
        }
    }

def run_visualization_sim(risk_val, trades_day_val, n_viz=100):
    """Detailed simulation for Equity Curve"""
    reward_per_trade = risk_val * reward_ratio
    personal_limit_usd = (daily_limit_r * risk_val) if daily_limit_r > 0 else 0
    
    all_curves = []
    
    for sim_id in range(n_viz):
        equity = account_size
        high_water_mark = account_size
        status = "Timeout" 
        current_dd_limit = account_size - max_total_dd
        
        curve = [{"Day": 0, "Equity": account_size, "SimID": sim_id, "Status": "In Progress"}]
        
        for day in range(1, max_days + 1):
            daily_start_equity = equity
            day_status = "In Progress"
            
            for trade in range(trades_day_val):
                is_win = np.random.rand() < win_rate
                if is_win: equity += reward_per_trade
                else: equity -= risk_val
                
                if equity > high_water_mark:
                    high_water_mark = equity
                    if trailing_type == "Trailing from High Water Mark":
                        current_dd_limit = high_water_mark - max_total_dd
                
                if equity <= current_dd_limit:
                    status = "Failed"; day_status = "Failed"; break
                
                current_daily_loss = daily_start_equity - equity
                if current_daily_loss >= max_daily_dd:
                    status = "Failed"; day_status = "Failed"; break
                
                if personal_limit_usd > 0 and current_daily_loss >= personal_limit_usd:
                    break 

                if equity >= (account_size + profit_target):
                    status = "Passed"; day_status = "Passed"; break
            
            curve.append({"Day": day, "Equity": equity, "SimID": sim_id, "Status": status})
            
            if day_status != "In Progress":
                break
        
        final_status = curve[-1]["Status"]
        for point in curve:
            point["Status"] = final_status
            
        all_curves.extend(curve)
        
    return pd.DataFrame(all_curves)

# --- TABS LAYOUT ---
tab1, tab2 = st.tabs(["🗺️ Global Strategy Map", "🔬 Single Scenario Deep Dive"])

# ================= TAB 1: STRATEGY MAP =================
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
            
            # Save Results to Session State
            df_summary = pd.DataFrame(results_summary)
            cols = ["Risk ($)", "Risk (%)", "Trades/Day", 
                    "Pass Rate (%)", "Avg Days Pass", "Median Days Pass", 
                    "Fail Rate (%)", "Avg Days Fail", "Median Days Fail", 
                    "Timeout Rate (%)", "Avg Max Win Streak",
                    "Avg Max Loss Streak", "Worst Case Streak (95%)"]
            st.session_state.sim_results = df_summary[cols]
            
            # Save Parameters Snapshot
            st.session_state.sim_params = {
                "acc": account_size, "tgt": profit_target, "mdd": max_daily_dd, "mtd": max_total_dd, "type": trailing_type,
                "win": win_rate_input, "rr": reward_ratio, "r_lim": daily_limit_r, "sims": num_simulations, "days": max_days,
                "r_in": risk_input, "t_in": trades_input
            }
            
        except ValueError:
            st.error("⚠️ Data Error: Please ensure inputs are correct.")

    # --- Render Logic ---
    if st.session_state.sim_results is not None:
        df_summary = st.session_state.sim_results
        params = st.session_state.sim_params
        
        col1, col2 = st.columns(2)
        
        # ROW 1: Success Zone
        with col1:
            st.subheader("🔥 1. Pass Rate (%)")
            heatmap_pass = df_summary.pivot(index="Trades/Day", columns="Risk ($)", values="Pass Rate (%)")
            fig_pass = px.imshow(heatmap_pass, labels=dict(x="Risk ($)", y="Trades/Day", color="Pass %"),
                                    x=heatmap_pass.columns, y=heatmap_pass.index, text_auto=".1f", aspect="auto", color_continuous_scale="Blues")
            fig_pass.update_yaxes(dtick=1)
            st.plotly_chart(fig_pass, use_container_width=True)
            st.caption("🟦 **Goal: Maximize.** Darker Blue = Higher probability of success.")

        with col2:
            st.subheader("⏳ 2. Median Days to Pass")
            heatmap_days = df_summary.pivot(index="Trades/Day", columns="Risk ($)", values="Median Days Pass")
            fig_days = px.imshow(heatmap_days, labels=dict(x="Risk ($)", y="Trades/Day", color="Days"),
                                    x=heatmap_days.columns, y=heatmap_days.index, text_auto=".1f", aspect="auto", color_continuous_scale="Purples")
            fig_days.update_yaxes(dtick=1)
            st.plotly_chart(fig_days, use_container_width=True)
            st.caption("🟪 **Efficiency.** Median duration. 50% of successful runs pass within this time.")

        # ROW 2: Failure Zone
        col3, col4 = st.columns(2)
        with col3:
            st.subheader("💥 3. Fail Rate (%)")
            heatmap_fail = df_summary.pivot(index="Trades/Day", columns="Risk ($)", values="Fail Rate (%)")
            fig_fail = px.imshow(heatmap_fail, labels=dict(x="Risk ($)", y="Trades/Day", color="Fail %"),
                                    x=heatmap_fail.columns, y=heatmap_fail.index, text_auto=".1f", aspect="auto", color_continuous_scale="Reds")
            fig_fail.update_yaxes(dtick=1)
            st.plotly_chart(fig_fail, use_container_width=True)
            st.caption("🟥 **Goal: Minimize.** Darker Red = High Risk. (0% = Safe/No failures).")

        with col4:
            st.subheader("📉 4. Median Days to Fail")
            heatmap_dfail = df_summary.pivot(index="Trades/Day", columns="Risk ($)", values="Median Days Fail")
            fig_dfail = px.imshow(heatmap_dfail, labels=dict(x="Risk ($)", y="Trades/Day", color="Days"),
                                    x=heatmap_dfail.columns, y=heatmap_dfail.index, text_auto=".1f", aspect="auto", color_continuous_scale="BuGn")
            fig_dfail.update_yaxes(dtick=1)
            st.plotly_chart(fig_dfail, use_container_width=True)
            st.caption("🟩 **Survival.** Low = Fast Ruin, High = Slow Bleed. (0 = No failures occurred).")

        # ROW 3: Stagnation & Momentum
        col5, col6 = st.columns(2)
        with col5:
            st.subheader("🐢 5. Timeout Rate (%)")
            heatmap_timeout = df_summary.pivot(index="Trades/Day", columns="Risk ($)", values="Timeout Rate (%)")
            fig_timeout = px.imshow(heatmap_timeout, labels=dict(x="Risk ($)", y="Trades/Day", color="Timeout %"),
                                    x=heatmap_timeout.columns, y=heatmap_timeout.index, text_auto=".1f", aspect="auto", color_continuous_scale="Greys")
            fig_timeout.update_yaxes(dtick=1)
            st.plotly_chart(fig_timeout, use_container_width=True)
            st.caption("⬜ **Goal: Minimize.** High Grey = Strategy is too passive/slow.")

        with col6:
            st.subheader("🍀 6. Avg Max Win Streak")
            heatmap_wstreak = df_summary.pivot(index="Trades/Day", columns="Risk ($)", values="Avg Max Win Streak")
            fig_wstreak = px.imshow(heatmap_wstreak, labels=dict(x="Risk ($)", y="Trades/Day", color="Wins"),
                                    x=heatmap_wstreak.columns, y=heatmap_wstreak.index, text_auto=".1f", aspect="auto", color_continuous_scale="Greens")
            fig_wstreak.update_yaxes(dtick=1)
            st.plotly_chart(fig_wstreak, use_container_width=True)
            st.caption("🟩 **Momentum.** Higher indicates better consecutive performance.")

        # ROW 4: Pain Zone
        col7, col8 = st.columns(2)
        with col7:
            st.subheader("🥶 7. Avg Max Loss Streak")
            heatmap_streak = df_summary.pivot(index="Trades/Day", columns="Risk ($)", values="Avg Max Loss Streak")
            fig_streak = px.imshow(heatmap_streak, labels=dict(x="Risk ($)", y="Trades/Day", color="Losses"),
                                    x=heatmap_streak.columns, y=heatmap_streak.index, text_auto=".1f", aspect="auto", color_continuous_scale="Oranges")
            fig_streak.update_yaxes(dtick=1)
            st.plotly_chart(fig_streak, use_container_width=True)
            st.caption("🟧 **Pain Index.** Average max consecutive losses.")

        with col8:
            st.subheader("💀 8. Worst Case Streak (95%)")
            heatmap_worst = df_summary.pivot(index="Trades/Day", columns="Risk ($)", values="Worst Case Streak (95%)")
            fig_worst = px.imshow(heatmap_worst, labels=dict(x="Risk ($)", y="Trades/Day", color="Losses"),
                                    x=heatmap_worst.columns, y=heatmap_worst.index, text_auto=".1f", aspect="auto", color_continuous_scale="YlOrRd")
            fig_worst.update_yaxes(dtick=1)
            st.plotly_chart(fig_worst, use_container_width=True)
            st.caption("🟥 **Extreme Risk.** 95% chance loss streak won't exceed this.")

        st.divider()
        st.subheader("📋 Comprehensive Performance Metrics")
        
        st.dataframe(
            df_summary.style.format({
                "Risk ($)": "${:.0f}", "Risk (%)": "{:.2f}%", 
                "Pass Rate (%)": "{:.1f}%", "Fail Rate (%)": "{:.1f}%", "Timeout Rate (%)": "{:.1f}%",
                "Avg Days Pass": "{:.1f}", "Median Days Pass": "{:.1f}",
                "Avg Days Fail": "{:.1f}", "Median Days Fail": "{:.1f}",
                "Avg Max Win Streak": "{:.1f}", "Avg Max Loss Streak": "{:.1f}", "Worst Case Streak (95%)": "{:.1f}"
            })
            .background_gradient(subset=["Pass Rate (%)"], cmap="Blues")
            .background_gradient(subset=["Fail Rate (%)"], cmap="Reds")
            .background_gradient(subset=["Timeout Rate (%)"], cmap="Greys")
            .background_gradient(subset=["Avg Days Pass"], cmap="Purples")
            .background_gradient(subset=["Median Days Pass"], cmap="Purples") 
            .background_gradient(subset=["Avg Days Fail"], cmap="BuGn")      
            .background_gradient(subset=["Median Days Fail"], cmap="BuGn")  
            .background_gradient(subset=["Avg Max Win Streak"], cmap="Greens") 
            .background_gradient(subset=["Avg Max Loss Streak"], cmap="Oranges")
            .background_gradient(subset=["Worst Case Streak (95%)"], cmap="YlOrRd"),
            use_container_width=True
        )
        
        # Footer
        st.markdown("---")
        st.subheader("⚙️ Simulation Settings Reference")
        if params:
            c1, c2, c3 = st.columns(3)
            with c1:
                    st.write(f"- Account: **${params['acc']:,.0f}**")
                    st.write(f"- Profit Target: **${params['tgt']:,.0f}**")
                    st.write(f"- Max Daily Drawdown: **${params['mdd']:,.0f}**")
            with c2:
                    st.write(f"- Win Rate: **{params['win']:.1f}%**")
                    st.write(f"- Risk/Reward: **1:{params['rr']}**")
                    st.write(f"- Personal Daily Limit: **{params['r_lim']}R**")
            with c3:
                    st.write(f"- Simulations: **{params['sims']:,}** runs")
                    st.write(f"- Max Days: **{params['days']}** days")

    else:
        st.info("👈 Click 'Run Full Analysis' to start.")

# ================= TAB 2: DEEP DIVE =================
with tab2:
    st.markdown("### 📈 Visualize Specific Scenario")
    st.info("Select parameters to visualize random equity curves and detailed stats.")
    
    try:
        # Parse inputs
        r_options = [float(x.strip()) for x in risk_input.split(',')]
        t_options = [int(x.strip()) for x in trades_input.split(',')]
        r_options.sort(); t_options.sort()
        
        c1, c2, c3, c4 = st.columns([1, 1, 1, 1.5])
        
        with c1:
            sel_risk = st.selectbox("Select Risk ($)", r_options)
        with c2:
            sel_trades = st.selectbox("Select Trades/Day", t_options)
        with c3:
            default_lines = int(num_simulations * 0.25)
            if default_lines < 1: default_lines = 1
            sel_sim_count = st.number_input("No. of Lines", value=default_lines, min_value=1, step=50, help="Default is 25% of Total Simulations")

        with c4:
            st.write("")
            st.write("")
            viz_btn = st.button("📸 Generate Curves & Stats", key="btn_viz", use_container_width=True)
            
        if viz_btn:
            with st.spinner("Calculating Statistics..."):
                stats = run_monte_carlo(sel_risk, sel_trades)
            
            # --- TOP ROW (PROBABILITIES) ---
            st.markdown("#### 🎲 Scenario Probabilities")
            k1, k2, k3 = st.columns(3)
            with k1:
                st.metric(label="🔥 Pass Rate", value=f"{stats['Pass Rate (%)']:.1f}%")
            with k2:
                st.metric(label="💥 Fail Rate", value=f"{stats['Fail Rate (%)']:.1f}%")
            with k3:
                st.metric(label="🐢 Timeout Rate", value=f"{stats['Timeout Rate (%)']:.1f}%")
            
            st.divider()

            # --- BOTTOM ROW (DEEP DIVE) ---
            st.markdown("#### 📊 Deep Dive Statistics")
            m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
            with m1:
                st.metric(label="Avg Days Pass", value=f"{stats['Avg Days Pass']}")
            with m2:
                st.metric(label="Median Days Pass", value=f"{stats['Median Days Pass']}")
            with m3:
                st.metric(label="Avg Days Fail", value=f"{stats['Avg Days Fail']}")
            with m4:
                st.metric(label="Median Days Fail", value=f"{stats['Median Days Fail']}")
            with m5:
                st.metric(label="Avg Max Win Streak", value=f"{stats['Avg Max Win Streak']}")
            with m6:
                st.metric(label="Avg Max Loss Streak", value=f"{stats['Avg Max Loss Streak']}")
            with m7:
                st.metric(label="Worst Case Streak (95%)", value=f"{stats['Worst Case Streak (95%)']}")
            
            st.divider()

            # --- PLOTS ROW ---
            # 3. Generate Curves (Left) & Histogram (Right)
            with st.spinner(f"Simulating..."):
                # Simulation for Lines
                df_viz = run_visualization_sim(sel_risk, sel_trades, n_viz=sel_sim_count)
                
                # Colors
                color_map = {"Passed": "#0072B2", "Failed": "#D55E00", "Timeout": "#B6B6B6"}
                
                # Layout Side-by-Side
                p1, p2 = st.columns(2)
                
                with p1:
                    # --- Plot 1: Equity Curves ---
                    fig_curve = px.line(df_viz, x="Day", y="Equity", color="Status", line_group="SimID",
                                  color_discrete_map=color_map,
                                  title=f"Equity Curves: {sel_sim_count} Sample Paths")
                    
                    fig_curve.add_hline(y=account_size, line_dash="dash", line_color="black", annotation_text="Start")
                    fig_curve.add_hline(y=account_size + profit_target, line_dash="dot", line_color="#009E73", annotation_text="Target")
                    fig_curve.update_traces(opacity=0.3, line=dict(width=1))
                    fig_curve.update_layout(height=500)
                    st.plotly_chart(fig_curve, use_container_width=True)

                with p2:
                    # --- Plot 2: Interactive Histograms ---
                    raw_data = stats["Raw Data"]
                    
                    # 🔹 Dropdown for Metric Selection
                    metric_choice = st.selectbox(
                        "📊 Select Distribution Metric:",
                        ["Final Profit/Loss (PnL)", "Days to Pass", "Days to Fail", "Max Win Streak", "Max Loss Streak"]
                    )
                    
                    # 🔹 Logic for Plotting based on selection
                    if metric_choice == "Final Profit/Loss (PnL)":
                        df_hist = pd.DataFrame(raw_data["PnL"])
                        fig_hist = px.histogram(df_hist, x="PnL", color="Status", nbins=50,
                                                color_discrete_map=color_map,
                                                title="Distribution of Final Outcomes (PnL)")
                    
                    elif metric_choice == "Days to Pass":
                        data = raw_data["Pass Days"]
                        if data:
                            fig_hist = px.histogram(x=data, nbins=20, title="Distribution: Days to Pass",
                                                    labels={'x': 'Days'}, color_discrete_sequence=['#0072B2']) # Blue
                        else:
                            st.warning("No Pass data available (0% Pass Rate).")
                            fig_hist = None

                    elif metric_choice == "Days to Fail":
                        data = raw_data["Fail Days"]
                        if data:
                            fig_hist = px.histogram(x=data, nbins=20, title="Distribution: Days to Fail",
                                                    labels={'x': 'Days'}, color_discrete_sequence=['#D55E00']) # Red/Orange
                        else:
                            st.warning("No Failure data available (0% Fail Rate).")
                            fig_hist = None

                    elif metric_choice == "Max Win Streak":
                        data = raw_data["Win Streaks"]
                        fig_hist = px.histogram(x=data, nbins=20, title="Distribution: Max Win Streaks",
                                                labels={'x': 'Streak Count'}, color_discrete_sequence=['#009E73']) # Greenish

                    elif metric_choice == "Max Loss Streak":
                        data = raw_data["Loss Streaks"]
                        fig_hist = px.histogram(x=data, nbins=20, title="Distribution: Max Loss Streaks",
                                                labels={'x': 'Streak Count'}, color_discrete_sequence=['#E69F00']) # Orange

                    if fig_hist:
                        fig_hist.update_layout(height=450)
                        st.plotly_chart(fig_hist, use_container_width=True)
                
                unique_sims = df_viz.groupby('SimID')['Status'].first()
                st.caption(f"Visualizing {sel_sim_count} paths (Left) vs. Statistical Distribution of {num_simulations} runs (Right).")

    except ValueError:
        st.error("⚠️ Please check your input format in the sidebar first.")
