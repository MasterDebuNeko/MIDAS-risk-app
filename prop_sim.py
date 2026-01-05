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
st.markdown("Analyze **Pass**, **Time**, **Failure**, **Streaks**, and **Risk of Ruin**.")

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
    """Deep simulation for Heatmap & Stats (Includes Streak Analysis & 95% Worst Case)"""
    reward_per_trade = risk_val * reward_ratio
    personal_limit_usd = (daily_limit_r * risk_val) if daily_limit_r > 0 else 0
    
    pass_count = 0
    fail_count = 0
    timeout_count = 0
    
    total_days_pass = 0
    total_days_fail = 0
    
    total_max_con_wins = 0
    total_max_con_losses = 0
    
    # Store max loss streak of EACH simulation to calculate percentile later
    all_max_loss_streaks = []
    
    for _ in range(num_simulations):
        equity = account_size
        high_water_mark = account_size
        status = "In Progress"
        current_dd_limit = account_size - max_total_dd
        
        # Streak Tracking per Sim
        sim_max_win_streak = 0
        sim_max_loss_streak = 0
        current_win_streak = 0
        current_loss_streak = 0
        
        for day in range(max_days):
            daily_start_equity = equity
            
            for trade in range(trades_day_val):
                is_win = np.random.rand() < win_rate
                
                # Update Streaks
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
                
                # Update Trailing DD
                if equity > high_water_mark:
                    high_water_mark = equity
                    if trailing_type == "Trailing from High Water Mark":
                        current_dd_limit = high_water_mark - max_total_dd
                
                # Check Fails
                if equity <= current_dd_limit:
                    status = "Failed"; break
                
                current_daily_loss = daily_start_equity - equity
                if current_daily_loss >= max_daily_dd:
                    status = "Failed"; break
                
                if personal_limit_usd > 0 and current_daily_loss >= personal_limit_usd:
                    break 

                # Check Pass
                if equity >= (account_size + profit_target):
                    status = "Passed"; break
            
            if status != "In Progress": break
            
        # Collect Stats
        total_max_con_wins += sim_max_win_streak
        total_max_con_losses += sim_max_loss_streak
        all_max_loss_streaks.append(sim_max_loss_streak)
        
        if status == "Passed":
            pass_count += 1
            total_days_pass += (day + 1)
        elif status == "Failed": 
            fail_count += 1
            total_days_fail += (day + 1)
        else: 
            timeout_count += 1
            
    # Calculate Statistics
    avg_days_pass = total_days_pass / pass_count if pass_count > 0 else 0
    avg_days_fail = total_days_fail / fail_count if fail_count > 0 else 0
    avg_max_win_streak = total_max_con_wins / num_simulations
    avg_max_loss_streak = total_max_con_losses / num_simulations
    
    # Calculate 95th Percentile for Worst Case Loss Streak
    worst_case_95 = np.percentile(all_max_loss_streaks, 95)
    
    risk_percent = (risk_val / account_size) * 100
    
    return {
        "Risk ($)": risk_val, "Risk (%)": risk_percent, "Trades/Day": trades_day_val,
        "Pass Rate (%)": (pass_count / num_simulations) * 100,
        "Failed Rate (%)": (fail_count / num_simulations) * 100,
        "Timeout Rate (%)": (timeout_count / num_simulations) * 100,
        "Avg Days Pass": round(avg_days_pass, 1),
        "Avg Days Fail": round(avg_days_fail, 1),
        "Avg Max Win Streak": round(avg_max_win_streak, 1),
        "Avg Max Loss Streak": round(avg_max_loss_streak, 1),
        "Worst Case Streak (95%)": round(worst_case_95, 1)
    }

def run_visualization_sim(risk_val, trades_day_val, n_viz=100):
    """Detailed simulation for Equity Curve (returns daily data)"""
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
            
            # Save Results to Session State
            df_summary = pd.DataFrame(results_summary)
            # Reorder cols for logic
            cols = ["Risk ($)", "Risk (%)", "Trades/Day", 
                    "Pass Rate (%)", "Avg Days Pass", 
                    "Failed Rate (%)", "Avg Days Fail",
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
            st.caption("🟦 **Maximize this.** Darker Blue = Higher Probability.")

        with col2:
            st.subheader("⏳ 2. Avg Days to Pass")
            heatmap_days = df_summary.pivot(index="Trades/Day", columns="Risk ($)", values="Avg Days Pass")
            fig_days = px.imshow(heatmap_days, labels=dict(x="Risk ($)", y="Trades/Day", color="Days"),
                                    x=heatmap_days.columns, y=heatmap_days.index, text_auto=".1f", aspect="auto", color_continuous_scale="Purples")
            fig_days.update_yaxes(dtick=1)
            st.plotly_chart(fig_days, use_container_width=True)
            st.caption("🟪 **Lower is Faster.** Lighter Purple = Efficiency.")

        # ROW 2: Failure Zone
        col3, col4 = st.columns(2)
        with col3:
            st.subheader("💥 3. Failed Rate (%)")
            heatmap_fail = df_summary.pivot(index="Trades/Day", columns="Risk ($)", values="Failed Rate (%)")
            fig_fail = px.imshow(heatmap_fail, labels=dict(x="Risk ($)", y="Trades/Day", color="Fail %"),
                                    x=heatmap_fail.columns, y=heatmap_fail.index, text_auto=".1f", aspect="auto", color_continuous_scale="Reds")
            fig_fail.update_yaxes(dtick=1)
            st.plotly_chart(fig_fail, use_container_width=True)
            st.caption("🟥 **Minimize this.** High Red = Risk is too high.")

        with col4:
            st.subheader("📉 4. Avg Days to Fail")
            heatmap_dfail = df_summary.pivot(index="Trades/Day", columns="Risk ($)", values="Avg Days Fail")
            fig_dfail = px.imshow(heatmap_dfail, labels=dict(x="Risk ($)", y="Trades/Day", color="Days"),
                                    x=heatmap_dfail.columns, y=heatmap_dfail.index, text_auto=".1f", aspect="auto", color_continuous_scale="BuGn")
            fig_dfail.update_yaxes(dtick=1)
            st.plotly_chart(fig_dfail, use_container_width=True)
            st.caption("🟩 **Survival Time:** Low days = Fast Ruin. High days = Slow Bleed.")

        # ROW 3: Stagnation & Momentum
        col5, col6 = st.columns(2)
        with col5:
            st.subheader("🐢 5. Timeout Rate (%)")
            heatmap_timeout = df_summary.pivot(index="Trades/Day", columns="Risk ($)", values="Timeout Rate (%)")
            fig_timeout = px.imshow(heatmap_timeout, labels=dict(x="Risk ($)", y="Trades/Day", color="Timeout %"),
                                    x=heatmap_timeout.columns, y=heatmap_timeout.index, text_auto=".1f", aspect="auto", color_continuous_scale="Greys")
            fig_timeout.update_yaxes(dtick=1)
            st.plotly_chart(fig_timeout, use_container_width=True)
            st.caption("⬜ **Too Slow.** High Grey = Playing too safe.")

        with col6:
            st.subheader("🍀 6. Avg Max Win Streak")
            heatmap_wstreak = df_summary.pivot(index="Trades/Day", columns="Risk ($)", values="Avg Max Win Streak")
            fig_wstreak = px.imshow(heatmap_wstreak, labels=dict(x="Risk ($)", y="Trades/Day", color="Wins"),
                                    x=heatmap_wstreak.columns, y=heatmap_wstreak.index, text_auto=".1f", aspect="auto", color_continuous_scale="Greens")
            fig_wstreak.update_yaxes(dtick=1)
            st.plotly_chart(fig_wstreak, use_container_width=True)
            st.caption("🟩 **Momentum.** Higher is better for morale.")

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
            st.caption("🟥 **Extreme Pain.** 95% of the time, streaks won't exceed this.")

        st.divider()
        st.subheader("📋 Comprehensive Performance Metrics")
        
        # Format table with ALL 8 metrics & Correct Colors
        st.dataframe(
            df_summary.style.format({
                "Risk ($)": "${:.0f}", "Risk (%)": "{:.2f}%", 
                "Pass Rate (%)": "{:.1f}%", "Failed Rate (%)": "{:.1f}%", "Timeout Rate (%)": "{:.1f}%",
                "Avg Days Pass": "{:.1f}", "Avg Days Fail": "{:.1f}",
                "Avg Max Win Streak": "{:.1f}", "Avg Max Loss Streak": "{:.1f}", "Worst Case Streak (95%)": "{:.1f}"
            })
            .background_gradient(subset=["Pass Rate (%)"], cmap="Blues")
            .background_gradient(subset=["Failed Rate (%)"], cmap="Reds")
            .background_gradient(subset=["Timeout Rate (%)"], cmap="Greys")
            .background_gradient(subset=["Avg Days Pass"], cmap="Purples")
            .background_gradient(subset=["Avg Days Fail"], cmap="BuGn")      # Matching Heatmap 4
            .background_gradient(subset=["Avg Max Win Streak"], cmap="Greens") # Matching Heatmap 6
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

# ================= TAB 2: EQUITY CURVES =================
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
            # 1. Calculate Stats (Run Monte Carlo for this single scenario)
            with st.spinner("Calculating Statistics..."):
                stats = run_monte_carlo(sel_risk, sel_trades)
            
            # --- TOP ROW (PROBABILITIES - Heatmaps 1, 3, 5) ---
            st.markdown("#### 🎲 Scenario Probabilities")
            k1, k2, k3 = st.columns(3)
            with k1:
                st.metric(label="🔥 Pass Probability", value=f"{stats['Pass Rate (%)']:.1f}%")
            with k2:
                st.metric(label="💥 Failure Probability", value=f"{stats['Failed Rate (%)']:.1f}%")
            with k3:
                st.metric(label="🐢 Timeout Probability", value=f"{stats['Timeout Rate (%)']:.1f}%")
            
            st.divider()

            # --- BOTTOM ROW (DEEP DIVE - Heatmaps 2, 4, 6, 7, 8) ---
            # Ordered exactly like the remaining heatmaps
            st.markdown("#### 📊 Deep Dive Statistics")
            m1, m2, m3, m4, m5 = st.columns(5)
            with m1:
                st.metric(label="Avg Days to Pass", value=f"{stats['Avg Days Pass']} Days")
            with m2:
                st.metric(label="Avg Days to Fail", value=f"{stats['Avg Days Fail']} Days")
            with m3:
                st.metric(label="Avg Max Win Streak", value=f"{stats['Avg Max Win Streak']} Wins")
            with m4:
                st.metric(label="Avg Max Loss Streak", value=f"{stats['Avg Max Loss Streak']} Losses")
            with m5:
                st.metric(label="Worst Case (95%)", value=f"{stats['Worst Case Streak (95%)']} Losses")
            
            st.divider()

            # 3. Generate Curves
            with st.spinner(f"Simulating {sel_sim_count} runs..."):
                df_viz = run_visualization_sim(sel_risk, sel_trades, n_viz=sel_sim_count)
                
                color_map = {
                    "Passed": "#0072B2",  # Blue
                    "Failed": "#D55E00",  # Vermilion
                    "Timeout": "#B6B6B6"  # Light Grey
                }
                
                fig = px.line(df_viz, x="Day", y="Equity", color="Status", line_group="SimID",
                              color_discrete_map=color_map,
                              title=f"Equity Curves: Risk ${sel_risk} | {sel_trades} Trades/Day ({sel_sim_count} Samples)")
                
                fig.add_hline(y=account_size, line_dash="dash", line_color="black", annotation_text="Start")
                fig.add_hline(y=account_size + profit_target, line_dash="dot", line_color="#009E73", annotation_text="Target")
                
                fig.update_traces(opacity=0.5, line=dict(width=1))
                fig.update_layout(height=600)
                st.plotly_chart(fig, use_container_width=True)
                
                unique_sims = df_viz.groupby('SimID')['Status'].first()
                batch_pass = (unique_sims == 'Passed').sum()
                batch_pass_rate = (batch_pass / len(unique_sims)) * 100
                st.caption(f"In this sample batch of {sel_sim_count} runs: Passed {batch_pass_rate:.1f}%")

    except ValueError:
        st.error("⚠️ Please check your input format in the sidebar first.")
