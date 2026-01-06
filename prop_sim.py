import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px

# --- Page Configuration ---
st.set_page_config(page_title="Prop Firm Simulator", layout="wide")

# --- CSS Styling ---
# Adjusted .small-font to be smaller, thinner, and lighter color
st.markdown("""
<style>
    .metric-card { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    .stButton>button { width: 100%; background-color: #007bff; color: white; }
    .small-font { font-size: 11px; color: #999; margin-top: -12px; margin-bottom: 10px; font-weight: 300; font-style: italic; }
    .avg-text { font-size: 13px; color: #888; margin-top: -15px; margin-bottom: 10px; font-weight: 400; }
</style>
""", unsafe_allow_html=True)

# --- Initialize Session State ---
if 'sim_results' not in st.session_state:
    st.session_state.sim_results = None
if 'sim_params' not in st.session_state:
    st.session_state.sim_params = None
if 'deep_dive_data' not in st.session_state:
    st.session_state.deep_dive_data = None

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
    win_rate_input = st.number_input("Win Rate (%)", value=70.0, step=0.1, min_value=1.0, max_value=100.0)
    win_rate = win_rate_input / 100.0
    reward_ratio = st.number_input("Risk/Reward Ratio (1:?)", value=1.0, step=0.1)
    
    st.markdown("**No. of Trades per day**")
    trades_input = st.text_input("No. of Trades Input", "2, 3, 4, 5", label_visibility="collapsed")
    st.markdown('<p class="small-font">integers only, separated by comma</p>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("**Risk Amount ($)**")
    risk_input = st.text_input("Risk Amount Input", "100, 120, 150, 175, 200, 250, 300, 350, 400, 450, 500", label_visibility="collapsed")
    st.markdown('<p class="small-font">separated by comma</p>', unsafe_allow_html=True)

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
    all_max_win_streaks = [] 
    all_max_loss_streaks = []
    all_max_dd_usd = []        
    all_timeout_equity = []    
    all_lowest_equity = []
    
    # New Collection: Loss Streaks ONLY for Passed Scenarios
    passed_max_loss_streaks = [] 
    
    for _ in range(num_simulations):
        equity = account_size
        high_water_mark = account_size
        status = "In Progress"
        current_dd_limit = account_size - max_total_dd
        
        sim_max_win_streak = 0
        sim_max_loss_streak = 0
        current_win_streak = 0
        current_loss_streak = 0
        
        sim_lowest_equity = account_size
        sim_max_dd = 0
        
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
                
                if equity < sim_lowest_equity: sim_lowest_equity = equity
                
                if equity > high_water_mark:
                    high_water_mark = equity
                    if trailing_type == "Trailing from High Water Mark":
                        current_dd_limit = high_water_mark - max_total_dd
                
                current_dd = high_water_mark - equity
                if current_dd > sim_max_dd: sim_max_dd = current_dd

                if equity <= current_dd_limit: status = "Failed"; break
                
                current_daily_loss = daily_start_equity - equity
                if current_daily_loss >= max_daily_dd: status = "Failed"; break
                
                if personal_limit_usd > 0 and current_daily_loss >= personal_limit_usd: break 

                if equity >= (account_size + profit_target): status = "Passed"; break
            
            if status != "In Progress": break
            
        all_max_win_streaks.append(sim_max_win_streak)
        all_max_loss_streaks.append(sim_max_loss_streak)
        all_max_dd_usd.append(sim_max_dd)
        all_lowest_equity.append(sim_lowest_equity)
        
        outcome_status = "Timeout"
        if status == "Passed":
            pass_count += 1
            all_pass_days.append(day + 1)
            passed_max_loss_streaks.append(sim_max_loss_streak) # Store specifically for passed
            outcome_status = "Passed"
        elif status == "Failed": 
            fail_count += 1
            all_fail_days.append(day + 1)
            outcome_status = "Failed"
        else: 
            timeout_count += 1
            all_timeout_equity.append(equity)
            
        all_final_pnl.append({"PnL": equity - account_size, "Status": outcome_status})
            
    # Stats Calculation
    avg_days_pass = sum(all_pass_days) / pass_count if pass_count > 0 else 0
    median_days_pass = np.median(all_pass_days) if pass_count > 0 else 0
    
    avg_days_fail = sum(all_fail_days) / fail_count if fail_count > 0 else 0
    median_days_fail = np.median(all_fail_days) if fail_count > 0 else 0
        
    avg_max_win_streak = sum(all_max_win_streaks) / num_simulations
    median_max_win_streak = np.median(all_max_win_streaks)
    
    avg_max_loss_streak = sum(all_max_loss_streaks) / num_simulations
    median_max_loss_streak = np.median(all_max_loss_streaks)
    
    # 1. Worst Case Loss Streak (All Scenarios)
    worst_case_loss_95 = np.percentile(all_max_loss_streaks, 95)
    
    # 2. Worst Case Loss Streak (Passed Scenarios ONLY)
    if passed_max_loss_streaks:
        passed_worst_case_loss_95 = np.percentile(passed_max_loss_streaks, 95)
    else:
        passed_worst_case_loss_95 = 0
    
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
        "Median Max Win Streak": round(median_max_win_streak, 1),
        "Avg Max Loss Streak": round(avg_max_loss_streak, 1),
        "Median Max Loss Streak": round(median_max_loss_streak, 1),
        "Worst Case Loss Streak (95%)": round(worst_case_loss_95, 1),         # All Scenarios
        "Passed Worst Case Loss (95%)": round(passed_worst_case_loss_95, 1), # Passed Scenarios Only
        "Raw Data": {
            "PnL": all_final_pnl, "Pass Days": all_pass_days, "Fail Days": all_fail_days,
            "Win Streaks": all_max_win_streaks, "Loss Streaks": all_max_loss_streaks,
            "Passed Loss Streaks": passed_max_loss_streaks,
            "Max DD": all_max_dd_usd, "Timeout Equity": all_timeout_equity, "Lowest Equity": all_lowest_equity
        }
    }

def run_visualization_sim(risk_val, trades_day_val, n_viz=100):
    """
    Original logic - Pure Simulation (Jitter added later for plotting)
    """
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
            df_summary = pd.DataFrame(results_summary)
            
            cols = ["Risk ($)", "Risk (%)", "Trades/Day", 
                    "Pass Rate (%)", "Median Days Pass", 
                    "Fail Rate (%)", "Timeout Rate (%)",
                    "Median Max Loss Streak", "Worst Case Loss Streak (95%)",
                    "Median Max Win Streak", "Passed Worst Case Loss (95%)"]
            
            st.session_state.sim_results = df_summary[cols]
            
            st.session_state.sim_params = {
                "acc": account_size, "tgt": profit_target, "mdd": max_daily_dd, "mtd": max_total_dd, "type": trailing_type,
                "win": win_rate_input, "rr": reward_ratio, "r_lim": daily_limit_r, "sims": num_simulations, "days": max_days,
                "r_in": risk_input, "t_in": trades_input
            }
        except ValueError: st.error("⚠️ Error in inputs.")

    if st.session_state.sim_results is not None:
        df_summary = st.session_state.sim_results
        
        def draw_heatmap(val_col, color_scale, title, caption):
            heatmap_data = df_summary.pivot(index="Trades/Day", columns="Risk ($)", values=val_col)
            fig = px.imshow(heatmap_data, labels=dict(x="Risk ($)", y="Trades/Day", color=val_col),
                            x=heatmap_data.columns, y=heatmap_data.index, text_auto=".1f", aspect="auto", color_continuous_scale=color_scale)
            fig.update_yaxes(dtick=1)
            st.subheader(title); st.plotly_chart(fig, use_container_width=True); st.caption(caption)

        # 1. Pass Rate (%)
        col1, col2 = st.columns(2)
        with col1: draw_heatmap("Pass Rate (%)", "Blues", "🔥 1. Pass Rate (%)", "🟦 **Goal: Maximize.** Darker Blue = Higher probability.")
        # 2. Median Days to Pass
        with col2: draw_heatmap("Median Days Pass", "Purples", "⏳ 2. Median Days to Pass", "🟪 **Efficiency.** Median duration.")

        # 3. Fail Rate (%)
        col3, col4 = st.columns(2)
        with col3: draw_heatmap("Fail Rate (%)", "Reds", "💥 3. Fail Rate (%)", "🟥 **Goal: Minimize.** Darker Red = High Risk.")
        # 4. Timeout Rate (%)
        with col4: draw_heatmap("Timeout Rate (%)", "Greys", "🐢 4. Timeout Rate (%)", "⬜ **Goal: Minimize.** High Grey = Too passive.")

        # 5. Median Max Loss Streak
        col5, col6 = st.columns(2)
        with col5: draw_heatmap("Median Max Loss Streak", "Reds", "🥶 5. Median Max Loss Streak", "🟥 **Pain Index.** Median consecutive losses (Strong Red).")
        # 6. Worst Case Loss Streak (All Scenarios)
        with col6: draw_heatmap("Worst Case Loss Streak (95%)", "YlOrRd", "💀 6. All: Worst Case Loss (95%)", "🟥 **Extreme Risk.** 95% chance loss streak won't exceed this (All Scenarios).")

        # 7. Median Max Win Streak
        col7, col8 = st.columns(2)
        with col7: draw_heatmap("Median Max Win Streak", "Greens", "🍀 7. Median Max Win Streak", "🟩 **Momentum.** Median consecutive wins.")
        
        # 8. Passed Worst Case Loss (Pass Scenarios Only)
        with col8: draw_heatmap("Passed Worst Case Loss (95%)", "Oranges", "🥵 8. Passed: Worst Case Loss (95%)", "🟧 **Survivor Pain.** Worst case streak even for those who passed.")

        st.divider(); st.subheader("📋 Comprehensive Performance Metrics")
        
        st.dataframe(
            df_summary.style.format({
                "Risk ($)": "${:.0f}", "Risk (%)": "{:.2f}%", 
                "Pass Rate (%)": "{:.1f}%", "Fail Rate (%)": "{:.1f}%", "Timeout Rate (%)": "{:.1f}%",
                "Median Days Pass": "{:.1f}",
                "Median Max Loss Streak": "{:.1f}", 
                "Worst Case Loss Streak (95%)": "{:.1f}",
                "Median Max Win Streak": "{:.1f}",
                "Passed Worst Case Loss (95%)": "{:.1f}"
            })
            .background_gradient(subset=["Pass Rate (%)"], cmap="Blues")
            .background_gradient(subset=["Fail Rate (%)"], cmap="Reds")
            .background_gradient(subset=["Timeout Rate (%)"], cmap="Greys")
            .background_gradient(subset=["Median Days Pass"], cmap="Purples")
            .background_gradient(subset=["Median Max Loss Streak"], cmap="Reds")   
            .background_gradient(subset=["Worst Case Loss Streak (95%)"], cmap="YlOrRd")
            .background_gradient(subset=["Median Max Win Streak"], cmap="Greens")
            .background_gradient(subset=["Passed Worst Case Loss (95%)"], cmap="Oranges"),
            use_container_width=True
        )

# ================= TAB 2: DEEP DIVE =================
with tab2:
    st.markdown("### 📈 Visualize Specific Scenario")
    
    # --- 1. Helper Functions ---
    def plot_hist_with_stats(data, title, color_hex, label="Count", nbins=50, percentile=None):
        if not data: st.info(f"No data for {title}"); return
        mean_val = np.mean(data); median_val = np.median(data)
        fig = px.histogram(x=data, nbins=nbins, title=title, labels={'x': label}, color_discrete_sequence=[color_hex])
        
        # Make histogram bars slightly transparent so lines behind/inside are visible
        fig.update_traces(marker_opacity=0.7)

        # Median - Solid Line (Consistent Color)
        fig.add_vline(x=median_val, line_width=3, line_dash="solid", line_color=color_hex) 
        # Average - Dash Line (Consistent Color)
        fig.add_vline(x=mean_val, line_width=3, line_dash="dash", line_color=color_hex)   
        
        # Annotations (Color matches histogram, bold for visibility)
        fig.add_annotation(x=median_val, y=1.05, yref="paper", text=f"Med:{median_val:.1f}", showarrow=False, font=dict(color=color_hex, size=11, weight="bold"), xanchor="right")
        fig.add_annotation(x=mean_val, y=1.12, yref="paper", text=f"Avg:{mean_val:.1f}", showarrow=False, font=dict(color=color_hex, size=11, weight="bold"), xanchor="left")
        
        if percentile:
            p_val = np.percentile(data, percentile)
            # 95% Line - Dotted (Consistent Color)
            fig.add_vline(x=p_val, line_width=2, line_dash="dot", line_color=color_hex) 
            fig.add_annotation(x=p_val, y=0.95, yref="paper", text=f"{percentile}%:{p_val:.1f}", showarrow=False, font=dict(color=color_hex, size=10, weight="bold"), xanchor="left")

        fig.update_layout(height=350, showlegend=False, margin=dict(l=20, r=20, t=50, b=20), bargap=0.1)
        st.plotly_chart(fig, use_container_width=True)

    def plot_pnl_hist(data_pnl, title, color_map):
        df = pd.DataFrame(data_pnl)
        if df.empty: st.info(f"No data for {title}"); return
        mean_val = df["PnL"].mean(); median_val = df["PnL"].median()
        fig = px.histogram(df, x="PnL", color="Status", nbins=50, color_discrete_map=color_map, title=title)
        fig.add_vline(x=median_val, line_width=3, line_dash="solid", line_color="#333333") 
        fig.add_vline(x=mean_val, line_width=3, line_dash="dash", line_color="#000000")   
        fig.add_annotation(x=median_val, y=1.05, yref="paper", text=f"Med:{median_val:.0f}", showarrow=False, font=dict(color="#333333", size=11))
        fig.update_layout(height=450, showlegend=False, margin=dict(l=20, r=20, t=60, b=20), bargap=0.1)
        st.plotly_chart(fig, use_container_width=True)

    # --- 2. Input Section ---
    try:
        r_options = [float(x.strip()) for x in risk_input.split(',')]
        t_options = [int(x.strip()) for x in trades_input.split(',')]
        r_options.sort(); t_options.sort()
        
        c1, c2, c3, c4 = st.columns([1, 1, 1, 1.5])
        with c1: sel_risk = st.selectbox("Select Risk ($)", r_options)
        with c2: sel_trades = st.selectbox("Select Trades/Day", t_options)
        with c3: sel_sim_count = st.number_input("No. of Lines", value=1000, min_value=100, step=500)
        with c4: 
            st.write(""); st.write("")
            viz_btn = st.button("📸 Generate Curves & Stats", key="btn_viz", use_container_width=True)

        # --- 3. Calculation Logic (Run Only When Clicked) ---
        if viz_btn:
            with st.spinner("Calculating Statistics..."):
                stats = run_monte_carlo(sel_risk, sel_trades)
                df_viz = run_visualization_sim(sel_risk, sel_trades, n_viz=sel_sim_count)
                
                # Convert to Profit
                df_viz['Profit'] = df_viz['Equity'] - account_size
                
                # Pre-calculate Jitter on PROFIT
                df_viz['SimID'] = df_viz['SimID'].astype(str)
                jitter_amount = sel_risk * 0.1 
                df_viz['Profit_Plot'] = df_viz['Profit'] + np.random.uniform(-jitter_amount, jitter_amount, size=len(df_viz))
                
                # Save to Session State (PERSISTENCE)
                st.session_state.deep_dive_data = {
                    "stats": stats,
                    "df_viz": df_viz,
                    "sim_count": sel_sim_count
                }

        # --- 4. Display Logic (Run Always if Data Exists) ---
        if "deep_dive_data" in st.session_state and st.session_state.deep_dive_data is not None:
            
            data = st.session_state.deep_dive_data
            stats = data["stats"]
            df_viz = data["df_viz"]
            sim_count_disp = data["sim_count"]
            
            # METRICS
            st.markdown("#### 📊 Scenario Statistics & Probabilities")
            def metric_card(label, main_val, sub_val=None):
                st.metric(label, main_val)
                if sub_val: st.markdown(f"<div class='avg-text'>Avg: {sub_val}</div>", unsafe_allow_html=True)

            k1, k2, k3, k4 = st.columns(4)
            with k1: metric_card("🔥 Pass Rate", f"{stats['Pass Rate (%)']:.1f}%")
            with k2: metric_card("💥 Fail Rate", f"{stats['Fail Rate (%)']:.1f}%")
            with k3: metric_card("🐢 Timeout Rate", f"{stats['Timeout Rate (%)']:.1f}%")
            with k4: metric_card("⏳ Median Days to Pass", f"{stats['Median Days Pass']}", f"{stats['Avg Days Pass']}")

            m1, m2, m3, m4 = st.columns(4)
            with m1: metric_card("🍀 Median Win Streak", f"{stats['Median Max Win Streak']}", f"{stats['Avg Max Win Streak']}")
            with m2: metric_card("🥶 Median Loss Streak", f"{stats['Median Max Loss Streak']}", f"{stats['Avg Max Loss Streak']}")
            with m3: metric_card("🥵 Passed: Worst Case Loss (95%)", f"{stats['Passed Worst Case Loss (95%)']}")
            with m4: metric_card("💀 All: Worst Case Loss (95%)", f"{stats['Worst Case Loss Streak (95%)']}")
            
            st.divider()

            # PLOTS
            raw_data = stats["Raw Data"]
            color_map = {"Passed": "#0072B2", "Failed": "#D55E00", "Timeout": "#B6B6B6"}
            
            st.markdown("### 📊 Distribution Analysis")

            r1_left, r1_right = st.columns([1, 2])
            with r1_left: 
                plot_pnl_hist(raw_data["PnL"], "Final PnL Distribution", color_map)
            
            with r1_right: 
                # Plotting PROFIT instead of Equity
                fig_curve = px.line(df_viz, x="Day", y="Profit_Plot", color="Status", line_group="SimID", 
                                    color_discrete_map=color_map, 
                                    title=f"Profit Curves: {sim_count_disp} Sample Paths",
                                    hover_data={"Profit": True, "Profit_Plot": False}) 
                
                # Start Line (0 Profit)
                fig_curve.add_hline(y=0, line_dash="dash", line_color="black", annotation_text="Start ($0)")
                # Target Line (Profit Target)
                fig_curve.add_hline(y=profit_target, line_dash="dot", line_color="#009E73", annotation_text=f"Target (+${profit_target})")
                
                fig_curve.update_traces(opacity=0.5, line=dict(width=1))
                fig_curve.update_layout(height=450, margin=dict(l=20, r=20, t=60, b=20), yaxis_title="Profit ($)")
                st.plotly_chart(fig_curve, use_container_width=True)

            r2_1, r2_2 = st.columns(2)
            with r2_1: plot_hist_with_stats(raw_data["Pass Days"], "Days to Pass Distribution", "#6A0DAD", "Days", 20, percentile=95) 
            # Changed color to #FF7F50 (Coral) to be visible on white but soft
            with r2_2: plot_hist_with_stats(raw_data["Passed Loss Streaks"], "Passed : Max Loss Streaks", "#FF7F50", "Streak Count", 15, percentile=95) 

            r3_1, r3_2 = st.columns(2)
            with r3_1: plot_hist_with_stats(raw_data["Win Streaks"], "Max Win Streaks", "#2CA02C", "Streak Count", 15, percentile=95) 
            with r3_2: plot_hist_with_stats(raw_data["Loss Streaks"], "All : Max Loss Streaks", "#D62728", "Streak Count", 15, percentile=95) 

            st.caption(f"Distributions from {num_simulations} runs. Black Solid Line = Median, Blue Dashed Line = Average.")

    except ValueError: st.error("⚠️ Error in inputs.")
