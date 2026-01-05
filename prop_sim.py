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

# --- Header ---
st.title("🛡️ Prop Firm Simulator: 4-Dimensional Analysis")
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
    daily_limit_r = st.number_input("Daily Loss Limit (R) (0 = Disabled)", value=0, step=1, help="Ex: Enter 2 means stop trading for the day if loss reaches 2R.")

with st.sidebar.expander("🎲 Simulation Settings", expanded=False):
    num_simulations = st.number_input("Simulations per Scenario", value=500, step=100)
    max_days = st.number_input("Max Days to Trade", value=20, step=1)

run_btn = st.sidebar.button("🚀 Run Full Analysis")

# --- Core Logic ---
def run_monte_carlo(risk_val, trades_day_val):
    reward_per_trade = risk_val * reward_ratio
    personal_limit_usd = (daily_limit_r * risk_val) if daily_limit_r > 0 else 0
    
    pass_count = 0
    fail_count = 0
    timeout_count = 0
    total_days_pass = 0
    
    for _ in range(num_simulations):
        equity = account_size
        high_water_mark = account_size
        days_passed = 0
        status = "In Progress"
        current_dd_limit = account_size - max_total_dd
        
        for day in range(max_days):
            days_passed += 1
            daily_start_equity = equity
            
            for trade in range(trades_day_val):
                # Trade Execution
                is_win = np.random.rand() < win_rate
                if is_win:
                    equity += reward_per_trade
                else:
                    equity -= risk_val
                
                # Update Trailing Drawdown
                if equity > high_water_mark:
                    high_water_mark = equity
                    if trailing_type == "Trailing from High Water Mark":
                        current_dd_limit = high_water_mark - max_total_dd
                
                # Check Failure
                if equity <= current_dd_limit:
                    status = "Failed"
                    break
                
                current_daily_loss = daily_start_equity - equity
                if current_daily_loss >= max_daily_dd:
                    status = "Failed"
                    break
                
                # Check Personal Limit
                if personal_limit_usd > 0 and current_daily_loss >= personal_limit_usd:
                    break 

                # Check Success
                if equity >= (account_size + profit_target):
                    status = "Passed"
                    break
            
            if status != "In Progress":
                break
        
        # Tally Results
        if status == "Passed":
            pass_count += 1
            total_days_pass += days_passed
        elif status == "Failed":
            fail_count += 1
        else:
            timeout_count += 1 # Timed Out
            
    # Calculate Rates
    pass_rate = (pass_count / num_simulations) * 100
    fail_rate = (fail_count / num_simulations) * 100
    timeout_rate = (timeout_count / num_simulations) * 100
    avg_days = total_days_pass / pass_count if pass_count > 0 else 0
    
    return {
        "Risk ($)": risk_val,
        "Trades/Day": trades_day_val,
        "Pass Rate (%)": pass_rate,
        "Failed Rate (%)": fail_rate,
        "Timeout Rate (%)": timeout_rate,
        "Avg Days": round(avg_days, 1)
    }

# --- Main Execution ---
if run_btn:
    try:
        risk_list = [float(x.strip()) for x in risk_input.split(',')]
        trades_list = [int(x.strip()) for x in trades_input.split(',')]
        
        risk_list.sort()
        trades_list.sort()
        
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
            
        status_text.text("Analysis Complete!")
        progress_bar.empty()
        
        df_summary = pd.DataFrame(results_summary)
        
        # --- Visualization Section (Heatmaps) ---
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 1. Pass Rate (Blues)
            st.subheader("🔥 1. Pass Rate (%)")
            heatmap_pass = df_summary.pivot(index="Trades/Day", columns="Risk ($)", values="Pass Rate (%)")
            fig_pass = px.imshow(heatmap_pass, labels=dict(x="Risk ($)", y="Trades/Day", color="Pass %"),
                                 x=heatmap_pass.columns, y=heatmap_pass.index, text_auto=".1f", aspect="auto", color_continuous_scale="Blues")
            fig_pass.update_yaxes(dtick=1)
            st.plotly_chart(fig_pass, use_container_width=True)
            st.caption("🟦 **Maximize this.** Darker Blue = Higher Probability.")

            # 3. Failed Rate (Reds)
            st.subheader("💥 3. Failed Rate (%)")
            heatmap_fail = df_summary.pivot(index="Trades/Day", columns="Risk ($)", values="Failed Rate (%)")
            fig_fail = px.imshow(heatmap_fail, labels=dict(x="Risk ($)", y="Trades/Day", color="Fail %"),
                                 x=heatmap_fail.columns, y=heatmap_fail.index, text_auto=".1f", aspect="auto", color_continuous_scale="Reds")
            fig_fail.update_yaxes(dtick=1)
            st.plotly_chart(fig_fail, use_container_width=True)
            st.caption("🟥 **Minimize this.** High Red = Risk is too high.")

        with col2:
            # 2. Avg Days (Purples)
            st.subheader("⏳ 2. Avg Days to Pass")
            heatmap_days = df_summary.pivot(index="Trades/Day", columns="Risk ($)", values="Avg Days")
            fig_days = px.imshow(heatmap_days, labels=dict(x="Risk ($)", y="Trades/Day", color="Days"),
                                 x=heatmap_days.columns, y=heatmap_days.index, text_auto=".1f", aspect="auto", color_continuous_scale="Purples")
            fig_days.update_yaxes(dtick=1)
            st.plotly_chart(fig_days, use_container_width=True)
            st.caption("🟪 **Lower is Faster.** Lighter Purple = Efficiency.")

            # 4. Timeout Rate (Greys)
            st.subheader("🐢 4. Timeout Rate (%)")
            heatmap_timeout = df_summary.pivot(index="Trades/Day", columns="Risk ($)", values="Timeout Rate (%)")
            fig_timeout = px.imshow(heatmap_timeout, labels=dict(x="Risk ($)", y="Trades/Day", color="Timeout %"),
                                    x=heatmap_timeout.columns, y=heatmap_timeout.index, text_auto=".1f", aspect="auto", color_continuous_scale="Greys")
            fig_timeout.update_yaxes(dtick=1)
            st.plotly_chart(fig_timeout, use_container_width=True)
            st.caption("⬜ **Too Slow.** High Grey = Playing too safe.")

        st.divider()

        # --- Detailed Table ---
        st.subheader("📋 Comprehensive Performance Metrics")
        st.dataframe(
            df_summary.style.format({
                "Risk ($)": "${:.0f}",
                "Pass Rate (%)": "{:.1f}%",
                "Failed Rate (%)": "{:.1f}%",
                "Timeout Rate (%)": "{:.1f}%",
                "Avg Days": "{:.1f} Days"
            }).background_gradient(subset=["Pass Rate (%)"], cmap="Blues"),
            use_container_width=True
        )

    except ValueError:
        st.error("⚠️ Data Error: Please ensure inputs are correct.")

else:
    st.info("👈 Click 'Run Full Analysis' to start.")
