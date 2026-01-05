# --- PLOTS ---
            with st.spinner(f"Simulating..."):
                df_viz = run_visualization_sim(sel_risk, sel_trades, n_viz=sel_sim_count)
                raw_data = stats["Raw Data"]
                color_map = {"Passed": "#0072B2", "Failed": "#D55E00", "Timeout": "#B6B6B6"}
                
                # --- VISUALIZATION PREP (Original Pure Data) ---
                df_viz['SimID'] = df_viz['SimID'].astype(str) # Force discrete lines

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

                def plot_pnl_hist(data_pnl, title):
                    df = pd.DataFrame(data_pnl)
                    if df.empty: st.info(f"No data for {title}"); return
                    mean_val = df["PnL"].mean(); median_val = df["PnL"].median()
                    fig = px.histogram(df, x="PnL", color="Status", nbins=50, color_discrete_map=color_map, title=title)
                    fig.add_vline(x=median_val, line_width=3, line_dash="solid", line_color="#333333") 
                    fig.add_vline(x=mean_val, line_width=3, line_dash="dash", line_color="#000000")   
                    fig.add_annotation(x=median_val, y=1.05, yref="paper", text=f"Med:{median_val:.0f}", showarrow=False, font=dict(color="#333333", size=11))
                    
                    # ✅ Fixed Margin for Title Alignment
                    fig.update_layout(height=450, showlegend=False, margin=dict(l=20, r=20, t=60, b=20), bargap=0.1)
                    st.plotly_chart(fig, use_container_width=True)

                st.markdown("### 📊 Distribution Analysis")

                # --- 4x2 GRID (PnL Left, Curve Right - Fixed Margins) ---
                r1_left, r1_right = st.columns([1, 2])
                
                with r1_left: 
                    plot_pnl_hist(raw_data["PnL"], "Final PnL Distribution")
                
                with r1_right: 
                    # Plot using ORIGINAL Equity (No Jitter)
                    fig_curve = px.line(df_viz, x="Day", y="Equity", color="Status", line_group="SimID", 
                                        color_discrete_map=color_map, 
                                        title=f"Equity Curves: {sel_sim_count} Sample Paths") 
                    
                    fig_curve.add_hline(y=account_size, line_dash="dash", line_color="black", annotation_text="Start")
                    fig_curve.add_hline(y=account_size + profit_target, line_dash="dot", line_color="#009E73", annotation_text="Target")
                    fig_curve.update_traces(opacity=0.5, line=dict(width=1))
                    
                    # ✅ Fixed Margin for Title Alignment
                    fig_curve.update_layout(height=450, margin=dict(l=20, r=20, t=60, b=20))
                    st.plotly_chart(fig_curve, use_container_width=True)

                r2_1, r2_2 = st.columns(2)
                with r2_1: plot_hist_with_stats(raw_data["Pass Days"], "Days to Pass Distribution", "#6A0DAD", "Days", 20) 
                with r2_2: plot_hist_with_stats(raw_data["Fail Days"], "Days to Fail Distribution", "#009E73", "Days", 20) 

                r3_1, r3_2 = st.columns(2)
                with r3_1: plot_hist_with_stats(raw_data["Win Streaks"], "Max Win Streaks", "#2CA02C", "Streak Count", 15) 
                with r3_2: plot_hist_with_stats(raw_data["Loss Streaks"], "Max Loss Streaks", "#FF7F0E", "Streak Count", 15) 

                st.caption(f"Distributions from {num_simulations} runs. Black Solid Line = Median, Blue Dashed Line = Average.")
