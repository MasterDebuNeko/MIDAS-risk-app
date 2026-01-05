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
st.markdown("เปรียบเทียบความเสี่ยงหลายระดับ เพื่อหาจุดที่ **โอกาสผ่านสูงสุด** (Optimization)")

# --- Sidebar Inputs ---
st.sidebar.header("⚙️ Settings")

with st.sidebar.expander("📝 Prop Firm Rules", expanded=True):
    # แก้ value เป็น 50000
    account_size = st.number_input("Account Size ($)", value=50000, step=1000)
    
    # แก้ value เป็น 3000
    profit_target = st.number_input("Profit Target ($)", value=3000, step=100)
    
    # แก้ value เป็น 2500
    max_daily_dd = st.number_input("Max Daily Drawdown ($)", value=2500, step=100)
    
    # แก้ value เป็น 2500
    max_total_dd = st.number_input("Max Total Drawdown ($)", value=2500, step=100)
    
    # สลับเอา "Trailing..." ขึ้นมาก่อน เพื่อให้เป็นค่า Default ตามรูป
    trailing_type = st.selectbox("Drawdown Type", ["Trailing from High Water Mark", "Static"])

with st.sidebar.expander("📊 Trading Parameters", expanded=True):
    win_rate = st.slider("Win Rate (%)", 10, 90, 70) / 100.0
    reward_ratio = st.number_input("Risk/Reward Ratio (1:?)", value=1.0, step=0.1)
    trades_per_day = st.number_input("Trades Per Day", value=3, step=1)
    
    # --- New Input: Multi-Risk ---
    st.markdown("---")
    st.markdown("**🎯 Risk Scenarios to Compare**")
    risk_input = st.text_input("Enter Risk amounts (separated by comma)", "100, 150, 250, 350, 500")
    
with st.sidebar.expander("🎲 Simulation Settings", expanded=False):
    num_simulations = st.number_input("Simulations per Scenario", value=500, step=100)
    max_days = st.number_input("Max Days to Trade", value=20, step=1)

run_btn = st.sidebar.button("🚀 Run Comparison Analysis")

# --- Core Logic (Function รับค่า Risk เป็น Argument) ---
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
        daily_start_equity = account_size
        
        for day in range(max_days):
            days_passed += 1
            daily_start_equity = equity
            
            for trade in range(trades_per_day):
                is_win = np.random.rand() < win_rate
                
                if is_win:
                    equity += reward_per_trade
                else:
                    equity -= risk_val
                
                # Check Trailing DD
                if equity > high_water_mark:
                    high_water_mark = equity
                    if trailing_type == "Trailing from High Water Mark":
                        current_dd_limit = high_water_mark - max_total_dd
                
                # Check Fail Conditions
                if equity <= current_dd_limit:
                    status = "Failed"
                    break
                if (daily_start_equity - equity) >= max_daily_dd:
                    status = "Failed"
                    break
                # Check Pass Condition
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
            
    # Calculate stats for this risk level
    pass_rate = (pass_count / num_simulations) * 100
    avg_days = total_days_pass / pass_count if pass_count > 0 else 0
    
    return {
        "Risk ($)": risk_val,
        "Risk (%)": round((risk_val/account_size)*100, 2),
        "Pass Rate (%)": pass_rate,
        "Fail Rate (%)": 100 - pass_rate, # Simplify: Fail + Timeout
        "Avg Days to Pass": round(avg_days, 1)
    }

# --- Main Execution ---
if run_btn:
    try:
        # 1. แปลง Input string เป็น list ของตัวเลข
        risk_list = [float(x.strip()) for x in risk_input.split(',')]
        risk_list.sort()
        
        results_summary = []
        
        # 2. Progress Bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 3. Loop run simulation ทีละค่า Risk
        for i, r_val in enumerate(risk_list):
            status_text.text(f"Simulating Risk: ${r_val}...")
            res = run_monte_carlo(r_val)
            results_summary.append(res)
            progress_bar.progress((i + 1) / len(risk_list))
            
        status_text.text("Analysis Complete!")
        progress_bar.empty()
        
        # 4. สร้าง DataFrame
        df_summary = pd.DataFrame(results_summary)
        
        # --- Display Results ---
        
        # A. Optimal Point Highlight
        best_row = df_summary.loc[df_summary['Pass Rate (%)'].idxmax()]
        st.success(f"🏆 จุดที่โอกาสผ่านสูงสุด (Sweet Spot) คือ Risk: **${best_row['Risk ($)']}** (Pass Rate: **{best_row['Pass Rate (%)']}%**)")

        # B. Comparison Chart
        col_chart, col_table = st.columns([2, 1])
        
        with col_chart:
            st.subheader("📈 Probability vs Risk")
            fig = px.line(df_summary, x="Risk ($)", y="Pass Rate (%)", markers=True,
                          title="Pass Rate at Different Risk Levels",
                          labels={"Pass Rate (%)": "Pass Probability (%)"})
            fig.update_traces(line_color='#007bff', line_width=3)
            fig.add_hline(y=df_summary['Pass Rate (%)'].max(), line_dash="dot", line_color="green", annotation_text="Max Prob")
            st.plotly_chart(fig, use_container_width=True)
            
        with col_table:
            st.subheader("📋 Data Table")
            st.dataframe(df_summary.style.format("{:.1f}"), use_container_width=True)
            
        # C. Detailed Explanation
        st.markdown("### 💡 Analysis Insight")
        st.markdown("""
        * **โซนซ้าย (Low Risk):** ถ้ากราฟต่ำ แสดงว่าเสี่ยงน้อยไป ทำกำไรไม่ทันเวลา หรือจบ 20 วันแล้วยังไม่ถึงเป้า
        * **ยอดดอย (Peak):** คือจุด Risk ที่เหมาะสมที่สุดสำหรับระบบเทรดของท่านพี่
        * **โซนขวา (High Risk):** กราฟจะดิ่งลง เพราะชน Drawdown/พอร์ตแตกง่ายขึ้น
        """)

    except ValueError:
        st.error("⚠️ กรุณาใส่ตัวเลขในช่อง Risk Scenarios ให้ถูกต้อง (เช่น: 100, 200, 300)")

else:

    st.info("👈 ใส่ค่า Risk หลายๆ ค่าคั่นด้วยจุลภาค (,) ในแถบด้านซ้าย แล้วกด Run เพื่อเปรียบเทียบเจ้าค่ะ")
