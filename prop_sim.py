import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Midas Model - Risk Analysis", layout="wide")

# --- CSS ---
st.markdown("""
<style>
    .metric-card { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    .stButton>button { width: 100%; background-color: #007bff; color: white; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Midas Model: Risk Sensitivity Analysis")
st.markdown("เปรียบเทียบความเสี่ยง และทดสอบ **Personal Daily Limit** เพื่อรักษาพอร์ต")

# --- Sidebar Inputs ---
st.sidebar.header("⚙️ Settings")

with st.sidebar.expander("📝 Prop Firm Rules", expanded=True):
    # Default values updated to Apex 50k
    account_size = st.number_input("Account Size ($)", value=50000, step=1000)
    profit_target = st.number_input("Profit Target ($)", value=3000, step=100)
    max_daily_dd = st.number_input("Max Daily Drawdown ($)", value=2500, step=100)
    max_total_dd = st.number_input("Max Total Drawdown ($)", value=2500, step=100)
    trailing_type = st.selectbox("Drawdown Type", ["Trailing from High Water Mark", "Static"])

with st.sidebar.expander("🛡️ Personal Risk Management", expanded=True):
    # NEW: ช่องใส่ Daily Loss Limit ส่วนตัว
    st.markdown("**Stop Trading for the day if loss reaches:**")
    personal_daily_limit = st.number_input("Daily Loss Limit ($) (0 = No limit)", value=0, step=100, help="ถ้าขาดทุนในวันนั้นถึงยอดนี้ จะหยุดเทรดทันทีแล้วไปเริ่มวันใหม่")

with st.sidebar.expander("📊 Trading Parameters", expanded=True):
    win_rate = st.slider("Win Rate (%)", 10, 90, 70) / 100.0
    reward_ratio = st.number_input("Risk/Reward Ratio (1:?)", value=1.0, step=0.1)
    trades_per_day = st.number_input("Trades Per Day", value=3, step=1)
    
    st.markdown("---")
    st.markdown("**🎯 Risk Scenarios to Compare**")
    risk_input = st.text_input("Enter Risk amounts (separated by comma)", "100, 150, 250, 350, 500")
    
with st.sidebar.expander("🎲 Simulation Settings", expanded=False):
    num_simulations = st.number_input("Simulations per Scenario", value=500, step=100)
    max_days = st.number_input("Max Days to Trade", value=20, step=1)

run_btn = st.sidebar.button("🚀 Run Comparison Analysis")

# --- Core Logic ---
def run_monte_carlo(risk_val):
    reward_per_trade = risk_val * reward_ratio
    pass_count = 0
    fail_count = 0
    total_days_pass = 0
    
    for _ in range(num_simulations):
        equity = account_size
        high_water_mark = account_size
        days_passed = 0
        status = "In Progress"
        current_dd_limit = account_size - max_total_dd
        
        for day in range(max_days):
            days_passed += 1
            daily_start_equity = equity # จดเงินต้นวัน
            
            for trade in range(trades_per_day):
                # 1. เทรด
                is_win = np.random.rand() < win_rate
                
                if is_win:
                    equity += reward_per_trade
                else:
                    equity -= risk_val
                
                # 2. Update Trailing DD Logic
                if equity > high_water_mark:
                    high_water_mark = equity
                    if trailing_type == "Trailing from High Water Mark":
                        current_dd_limit = high_water_mark - max_total_dd
                
                # 3. Check กฎกองทุน (Fail Conditions)
                # 3.1 Total Drawdown (พอร์ตแตก)
                if equity <= current_dd_limit:
                    status = "Failed"
                    break
                
                # 3.2 Daily Drawdown (พอร์ตแตก)
                current_daily_loss = daily_start_equity - equity
                if current_daily_loss >= max_daily_dd:
                    status = "Failed"
                    break
                
                # 4. Check กฎส่วนตัว (Personal Daily Stop)
                # ถ้าตั้งค่าไว้ (>0) และ ขาดทุนวันนี้เกินลิมิต -> หยุดเทรดวันนี้ (Break loop เทรด)
                if personal_daily_limit > 0 and current_daily_loss >= personal_daily_limit:
                    # หยุดเทรดวันนั้น แต่สถานะยังไม่ Failed (แค่ข้ามไปวันถัดไป)
                    break 

                # 5. Check Pass Condition
                if equity >= (account_size + profit_target):
                    status = "Passed"
                    break
            
            if status != "In Progress":
                break
        
        if status == "Passed":
            pass_count += 1
            total_days_pass += days_passed
        elif status == "Failed":
            fail_count += 1
            
    # Calculate stats
    pass_rate = (pass_count / num_simulations) * 100
    avg_days = total_days_pass / pass_count if pass_count > 0 else 0
    
    return {
        "Risk ($)": risk_val,
        "Risk (%)": round((risk_val/account_size)*100, 2),
        "Pass Rate (%)": pass_rate,
        "Fail Rate (%)": 100 - pass_rate,
        "Avg Days to Pass": round(avg_days, 1)
    }

# --- Main Execution ---
if run_btn:
    try:
        risk_list = [float(x.strip()) for x in risk_input.split(',')]
        risk_list.sort()
        
        results_summary = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, r_val in enumerate(risk_list):
            status_text.text(f"Simulating Risk: ${r_val}...")
            res = run_monte_carlo(r_val)
            results_summary.append(res)
            progress_bar.progress((i + 1) / len(risk_list))
            
        status_text.text("Analysis Complete!")
        progress_bar.empty()
        
        df_summary = pd.DataFrame(results_summary)
        
        # Display Results
        best_row = df_summary.loc[df_summary['Pass Rate (%)'].idxmax()]
        st.success(f"🏆 จุดที่ดีที่สุด (Sweet Spot) คือ Risk: **${best_row['Risk ($)']}** (Pass Rate: **{best_row['Pass Rate (%)']}%**)")

        if personal_daily_limit > 0:
            st.info(f"ℹ️ เปิดใช้งาน Personal Daily Stop ที่ ${personal_daily_limit} (ช่วยรักษาพอร์ตไม่ให้แตกในวันที่เทรดแย่)")

        col_chart, col_table = st.columns([2, 1])
        
        with col_chart:
            st.subheader("📈 Probability vs Risk")
            fig = px.line(df_summary, x="Risk ($)", y="Pass Rate (%)", markers=True,
                          title="Pass Rate at Different Risk Levels",
                          labels={"Pass Rate (%)": "Pass Probability (%)"})
            fig.update_traces(line_color='#007bff', line_width=3)
            st.plotly_chart(fig, use_container_width=True)
            
        with col_table:
            st.subheader("📋 Data Table")
            st.dataframe(df_summary.style.format("{:.1f}"), use_container_width=True)

    except ValueError:
        st.error("⚠️ กรุณาใส่ตัวเลขในช่อง Risk Scenarios ให้ถูกต้อง")

else:
    st.info("👈 กด Run เพื่อเริ่มการจำลองเจ้าค่ะ")
