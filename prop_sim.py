import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Midas Model - Heatmap Edition", layout="wide")

# --- CSS ---
st.markdown("""
<style>
    .metric-card { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    .stButton>button { width: 100%; background-color: #007bff; color: white; }
    .small-font { font-size: 12px; color: #666; margin-top: -10px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Midas Model: Scenario Heatmap")
st.markdown("ค้นหา **Sweet Spot** ด้วยแผนภาพความร้อน (Heatmap) ระหว่าง Risk และ Frequency")

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
    
    # 2. Trades Per Day (Variation)
    st.markdown("**Trades Per Day**")
    trades_input = st.text_input("Trades Input", "1, 2, 3, 4, 5", label_visibility="collapsed")
    st.markdown('<p class="small-font">separated by comma (e.g. 2, 3, 4)</p>', unsafe_allow_html=True)
    
    # 3. Risk Scenarios (Variation)
    st.markdown("---")
    st.markdown("**Risk Amount ($)**")
    risk_input = st.text_input("Risk Amount Input", "100, 200, 300, 400, 500, 600", label_visibility="collapsed")
    st.markdown('<p class="small-font">separated by comma (e.g. 100, 250)</p>', unsafe_allow_html=True)

    # 4. Personal Risk Management
    st.markdown("---")
    st.markdown("🛡️ **Personal Risk Management**")
    daily_limit_r = st.number_input("Daily Loss Limit (R) (0 = No limit)", value=0.0, step=0.5, help="Ex: ใส่ 2 แปลว่า ถ้าวันนั้นเสีย 2 ไม้ (2R) จะหยุดเทรดทันที")

with st.sidebar.expander("🎲 Simulation Settings", expanded=False):
    num_simulations = st.number_input("Simulations per Scenario", value=2000, step=100)
    max_days = st.number_input("Max Days to Trade", value=20, step=1)

run_btn = st.sidebar.button("🚀 Run Heatmap Analysis")

# --- Core Logic ---
def run_monte_carlo(risk_val, trades_day_val):
    reward_per_trade = risk_val * reward_ratio
    personal_limit_usd = (daily_limit_r * risk_val) if daily_limit_r > 0 else 0
    
    pass_count = 0
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
                is_win = np.random.rand() < win_rate
                if is_win:
                    equity += reward_per_trade
                else:
                    equity -= risk_val
                
                if equity > high_water_mark:
                    high_water_mark = equity
                    if trailing_type == "Trailing from High Water Mark":
                        current_dd_limit = high_water_mark - max_total_dd
                
                if equity <= current_dd_limit:
                    status = "Failed"
                    break
                
                current_daily_loss = daily_start_equity - equity
                if current_daily_loss >= max_daily_dd:
                    status = "Failed"
                    break
                
                if personal_limit_usd > 0 and current_daily_loss >= personal_limit_usd:
                    break 

                if equity >= (account_size + profit_target):
                    status = "Passed"
                    break
            
            if status != "In Progress":
                break
        
        if status == "Passed":
            pass_count += 1
            total_days_pass += days_passed
            
    pass_rate = (pass_count / num_simulations) * 100
    avg_days = total_days_pass / pass_count if pass_count > 0 else 0
    
    return {
        "Risk ($)": risk_val,
        "Trades/Day": trades_day_val,
        "Pass Rate (%)": pass_rate,
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
        
        # --- 1. HEATMAP SECTION (NEW!) ---
        st.subheader("🔥 Probability Heatmap (Sweet Spot)")
        
        # Prepare Data for Heatmap
        heatmap_data = df_summary.pivot(index="Trades/Day", columns="Risk ($)", values="Pass Rate (%)")
        
        # Create Heatmap
        fig_heat = px.imshow(
            heatmap_data,
            labels=dict(x="Risk Amount ($)", y="Trades Per Day", color="Pass Rate (%)"),
            x=heatmap_data.columns,
            y=heatmap_data.index,
            text_auto=".1f", # Show numbers on heatmap
            aspect="auto",
            color_continuous_scale="Blues" # Colorblind friendly (Light to Dark Blue)
        )
        
        fig_heat.update_layout(
            title="Pass Rate Heatmap (Darker Blue = Better)",
            xaxis_title="Risk Amount ($)",
            yaxis_title="Trades Per Day"
        )
        st.plotly_chart(fig_heat, use_container_width=True)

        st.markdown("""
        **วิธีอ่าน Heatmap:**
        * **สีน้ำเงินเข้ม:** โอกาสผ่านสูง (Recommended Zone)
        * **สีน้ำเงินจาง/ขาว:** โอกาสผ่านต่ำ (Danger Zone)
        """)

        st.divider()

        # --- 2. Line Chart Section ---
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📈 Trend Lines")
            fig_line = px.line(df_summary, x="Risk ($)", y="Pass Rate (%)", color="Trades/Day", markers=True)
            st.plotly_chart(fig_line, use_container_width=True)
            
        with col2:
            st.subheader("📋 Data Table")
            st.dataframe(heatmap_data.style.format("{:.1f}%").background_gradient(cmap="Blues"), use_container_width=True)

    except ValueError:
        st.error("⚠️ กรุณาตรวจสอบการกรอกข้อมูล: ใช้เครื่องหมายจุลภาค (,) คั่นตัวเลขเท่านั้น")

else:
    st.info("👈 กด Run เพื่อสร้าง Heatmap เจ้าค่ะ")
