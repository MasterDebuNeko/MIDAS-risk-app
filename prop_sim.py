st.divider(); st.subheader("📋 Comprehensive Performance Metrics")
        
        # --- Layout: Header (Left) | Checkbox (Right) ---
        col_head, col_opt = st.columns([0.85, 0.15]) 
        
        with col_head:
            st.write("") # Spacer to align
        
        with col_opt:
            st.write("") 
            st.write("") 
            show_all_rows = st.checkbox("Show Full Table", value=False)
        
        # --- SMART HEIGHT CALCULATION ---
        # 1. Calculate the 'natural' height based on data rows
        # (Rows + 1 for Header) * 35px per row + 3px buffer
        natural_height = (len(df_summary) + 1) * 35 + 3
        
        if show_all_rows:
            # Case A: Expand to show everything
            table_height = natural_height
        else:
            # Case B: Shrink to fit content, BUT cap at 400px (Scroll if larger)
            table_height = min(natural_height, 400)

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
            .background_gradient(subset=["Worst Case Loss Streak (95%)"], cmap="Reds")
            .background_gradient(subset=["Median Max Win Streak"], cmap="Greens")
            .background_gradient(subset=["Passed Worst Case Loss (95%)"], cmap="Oranges"),
            use_container_width=True,
            height=table_height # Apply smart height
        )
