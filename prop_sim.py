# ================= TAB 2: DEEP DIVE =================
with tab2:
    st.markdown("### 📈 Visualize Specific Scenario")
    st.info("Select parameters to visualize random equity curves and detailed stats.")
    
    # --- 1. Helper Functions (Defined once) ---
    def plot_hist_with_stats(data, title, color_hex, label="Count", nbins=50):
        if not data: st.info(f"No data for {title}"); return
        mean_val = np.mean(data); median_val = np.median(data)
        fig = px.histogram(x=data, nbins=nbins, title=title, labels={'x': label}, color_discrete_sequence=[color_hex])
        fig.add_vline(x=median_val, line_width=2, line_dash="solid", line_color="#333333") 
        fig.add_vline(x=mean_val, line_width=2, line_dash="dash", line_color="#0072B2")   
        fig.add_annotation(x=median_val, y=1.05, yref="paper", text=f"Med:{median_val:.1f}", showarrow=False, font=dict(color="#333333", size=10), xanchor="right")
        fig.add_annotation(x=mean_val, y=1.12, yref="paper", text=f"Avg:{mean_val:.1f}", showarrow=False, font=dict(color="#0072B2", size=10), xanchor="left")
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
        with c3: sel_sim_count = st.number_input("No. of Lines", value=int(num_simulations*0.25), min_value=1, step=50)
        with c4: 
            st.write(""); st.write("")
            viz_btn = st.button("📸 Generate Curves & Stats", key="btn_viz", use_container_width=True)

        # --- 3. Calculation Logic (Run Only When Clicked) ---
        if viz_btn:
            with st.spinner("Calculating Statistics..."):
                stats = run_monte_carlo(sel_risk, sel_trades)
                df_viz = run_visualization_sim(sel_risk, sel_trades, n_viz=sel_sim_count)
                
                # Pre-calculate Jitter here and store it
                df_viz['SimID'] = df_viz['SimID'].astype(str)
                jitter_amount = sel_risk * 0.1 
                df_viz['Equity_Plot'] = df_viz['Equity'] + np.random.uniform(-jitter_amount, jitter_amount, size=len(df_viz))
                
                # Save to Session State (PERSISTENCE)
                st.session_state.deep_dive_data = {
                    "stats": stats,
                    "df_viz": df_viz,
                    "sim_count": sel_sim_count
                }

        # --- 4. Display Logic (Run Always if Data Exists) ---
        if "deep_dive_data" in st.session_state and st.session_state.deep_dive_data is not None:
            
            data = st.session_state.deep_dive_data # Retrieve data
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
            with k4: metric_card("💀 Worst Case (95%)", f"{stats['Worst Case Streak (95%)']}")

            m1, m2, m3, m4 = st.columns(4)
            with m1: metric_card("Median Days Pass", f"{stats['Median Days Pass']}", f"{stats['Avg Days Pass']}")
            with m2: metric_card("Median Days Fail", f"{stats['Median Days Fail']}", f"{stats['Avg Days Fail']}")
            with m3: metric_card("Median Win Streak", f"{stats['Median Max Win Streak']}", f"{stats['Avg Max Win Streak']}")
            with m4: metric_card("Median Loss Streak", f"{stats['Median Max Loss Streak']}", f"{stats['Avg Max Loss Streak']}")
            
            st.divider()

            # PLOTS
            raw_data = stats["Raw Data"]
            color_map = {"Passed": "#0072B2", "Failed": "#D55E00", "Timeout": "#B6B6B6"}
            
            st.markdown("### 📊 Distribution Analysis")

            r1_left, r1_right = st.columns([1, 2])
            with r1_left: 
                plot_pnl_hist(raw_data["PnL"], "Final PnL Distribution", color_map)
            
            with r1_right: 
                fig_curve = px.line(df_viz, x="Day", y="Equity_Plot", color="Status", line_group="SimID", 
                                    color_discrete_map=color_map, 
                                    title=f"Equity Curves: {sim_count_disp} Sample Paths",
                                    hover_data={"Equity": True, "Equity_Plot": False}) 
                fig_curve.add_hline(y=account_size, line_dash="dash", line_color="black", annotation_text="Start")
                fig_curve.add_hline(y=account_size + profit_target, line_dash="dot", line_color="#009E73", annotation_text="Target")
                fig_curve.update_traces(opacity=0.5, line=dict(width=1))
                fig_curve.update_layout(height=450, margin=dict(l=20, r=20, t=60, b=20))
                st.plotly_chart(fig_curve, use_container_width=True)

            r2_1, r2_2 = st.columns(2)
            with r2_1: plot_hist_with_stats(raw_data["Pass Days"], "Days to Pass Distribution", "#6A0DAD", "Days", 20) 
            with r2_2: plot_hist_with_stats(raw_data["Fail Days"], "Days to Fail Distribution", "#009E73", "Days", 20) 

            r3_1, r3_2 = st.columns(2)
            with r3_1: plot_hist_with_stats(raw_data["Win Streaks"], "Max Win Streaks", "#2CA02C", "Streak Count", 15) 
            with r3_2: plot_hist_with_stats(raw_data["Loss Streaks"], "Max Loss Streaks", "#FF7F0E", "Streak Count", 15) 

            st.caption(f"Distributions from {num_simulations} runs. Black Solid Line = Median, Blue Dashed Line = Average.")

    except ValueError: st.error("⚠️ Error in inputs.")
