import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# PAGE CONFIGURATION & CUSTOM CSS
# ==========================================
st.set_page_config(page_title="Impact Analytics Dashboard", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for better KPI cards and UI polishing
st.markdown("""
<style>
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📈 Impact Analytics Dashboard")
st.markdown("<p style='color: gray; font-size: 1.1em;'>Comprehensive Baseline vs. Endline Performance Assessment</p>", unsafe_allow_html=True)

# ==========================================
# SIDEBAR: DATA INTAKE & FILTERS
# ==========================================
with st.sidebar:
    st.header("📁 1. Data Intake")
    
    upload_mode = st.radio("Upload Method:", ["Two Separate Files", "Single File (Multiple Sheets)"])
    st.markdown("<span style='color: gray; font-size: 0.85em;'>Select your data structure and upload below.</span>", unsafe_allow_html=True)
    
    base_file, end_file = None, None
    base_sheet, end_sheet = 0, 0

    if upload_mode == "Two Separate Files":
        base_file = st.file_uploader("Upload Baseline Data", type=["csv", "xlsx"])
        end_file = st.file_uploader("Upload Endline Data", type=["csv", "xlsx"])
    else:
        single_file = st.file_uploader("Upload Master Workbook", type=["xlsx"])
        if single_file:
            # Read sheet names to populate dropdowns
            xls = pd.ExcelFile(single_file)
            sheet_names = xls.sheet_names
            
            # Smart defaults (auto-detect if named appropriately)
            def_base = sheet_names.index('Baseline') if 'Baseline' in sheet_names else 0
            def_end = sheet_names.index('Endline') if 'Endline' in sheet_names else (1 if len(sheet_names) > 1 else 0)
            
            base_sheet = st.selectbox("Select Baseline Sheet", sheet_names, index=def_base)
            end_sheet = st.selectbox("Select Endline Sheet", sheet_names, index=def_end)
            
            base_file = single_file
            end_file = single_file

    st.divider()

@st.cache_data
def load_and_prep_data(base_file, end_file, base_sheet=0, end_sheet=0):
    common_cols = ['State', 'Centre Name', 'Donor', 'Subject', 'Grade', 'Student ID', 'Gender', 'Total Marks', 'Obtained Marks', 'Category', 'Academic Year']
    dfs_to_concat = []

    def read_data(f, sheet):
        f.seek(0) # Reset file pointer in case the same file object is read twice
        if f.name.endswith('.csv'):
            return pd.read_csv(f)
        return pd.read_excel(f, sheet_name=sheet)

    if base_file is not None:
        df_base = read_data(base_file, base_sheet)
        if 'Rubrics' in df_base.columns: df_base.rename(columns={'Rubrics': 'Category'}, inplace=True)
        df_base['Academic Year'] = 'Baseline'
        dfs_to_concat.append(df_base[[c for c in common_cols if c in df_base.columns]])

    if end_file is not None:
        df_end = read_data(end_file, end_sheet)
        if 'Rubrics' in df_end.columns: df_end.rename(columns={'Rubrics': 'Category'}, inplace=True)
        df_end['Academic Year'] = 'Endline'
        dfs_to_concat.append(df_end[[c for c in common_cols if c in df_end.columns]])

    if not dfs_to_concat:
        return pd.DataFrame()

    df_combined = pd.concat(dfs_to_concat, ignore_index=True)

    # Text cleaning
    for col in ['State', 'Centre Name', 'Donor', 'Subject', 'Student ID', 'Gender']:
        if col in df_combined.columns:
            df_combined[col] = df_combined[col].astype(str).str.strip()

    # Standardize Gender formatting to catch ALL variations (boy, BOY, bOy -> Boy)
    if 'Gender' in df_combined.columns:
        df_combined['Gender'] = df_combined['Gender'].astype(str).str.strip().str.title()

    if 'Grade' in df_combined.columns:
        df_combined['Grade'] = df_combined['Grade'].astype(str).str.replace(r'\.0$', '', regex=True)

    # Enforce R.I.S.E ordering
    if 'Category' in df_combined.columns:
        rise_order = ["Reviving", "Initiating", "Shaping", "Evolving"]
        df_combined['Category'] = pd.Categorical(df_combined['Category'], categories=rise_order, ordered=True)

    # Ensure numeric
    df_combined['Obtained Marks'] = pd.to_numeric(df_combined['Obtained Marks'], errors='coerce')

    return df_combined

# Define color palette for consistency
COLOR_MAP = {'Baseline': '#636EFA', 'Endline': '#00CC96'}
RISE_COLORS = {"Reviving": "#EF553B", "Initiating": "#AB63FA", "Shaping": "#FFA15A", "Evolving": "#00CC96"}

if base_file or end_file:
    with st.spinner('Crunching numbers...'):
        df = load_and_prep_data(base_file, end_file, base_sheet, end_sheet)

    if not df.empty:
        with st.sidebar:
            st.header("🎯 2. Global Filters")
            
            # 1. State Filter
            states = ["All"] + sorted(df['State'].dropna().unique().tolist())
            selected_states = st.selectbox("Select State", states, index=0)
            
            # Pre-filter for next dropdown
            df_state_filtered = df.copy()
            if selected_states != "All": 
                df_state_filtered = df_state_filtered[df_state_filtered['State'] == selected_states]

            # 2. Donor Filter (Dependent on State)
            donors = ["All"] + sorted(df_state_filtered['Donor'].dropna().unique().tolist())
            selected_donors = st.selectbox("Select Donor", donors, index=0)
            
            # Pre-filter for next dropdown
            df_donor_filtered = df_state_filtered.copy()
            if selected_donors != "All":
                df_donor_filtered = df_donor_filtered[df_donor_filtered['Donor'] == selected_donors]

            # 3. Centre Filter (Dependent on State & Donor)
            centres = ["All"] + sorted(df_donor_filtered['Centre Name'].dropna().unique().tolist())
            selected_centres = st.selectbox("Select Centre", centres, index=0)
            
            # Pre-filter for next dropdown
            df_centre_filtered = df_donor_filtered.copy()
            if selected_centres != "All":
                df_centre_filtered = df_centre_filtered[df_centre_filtered['Centre Name'] == selected_centres]

            # 4. Subject Filter (Dependent on Centre)
            subjects = ["All"] + sorted(df_centre_filtered['Subject'].dropna().unique().tolist())
            selected_subjects = st.selectbox("Select Subject", subjects, index=0)

            # Pre-filter for next dropdown
            df_subject_filtered = df_centre_filtered.copy()
            if selected_subjects != "All":
                df_subject_filtered = df_subject_filtered[df_subject_filtered['Subject'] == selected_subjects]

            # 5. Grade Filter (Dependent on Subject, Multi-select)
            grades = sorted(df_subject_filtered['Grade'].dropna().unique().tolist())
            selected_grades = st.multiselect("Select Grade(s)", options=grades, default=grades)

            # Pre-filter for next dropdown
            df_grade_filtered = df_subject_filtered.copy()
            if selected_grades:
                df_grade_filtered = df_grade_filtered[df_grade_filtered['Grade'].isin(selected_grades)]
            else:
                df_grade_filtered = df_grade_filtered.iloc[0:0] 

            # 6. Gender Filter (Dependent on Grade, Multi-select)
            if 'Gender' in df_grade_filtered.columns:
                valid_genders = df_grade_filtered[~df_grade_filtered['Gender'].str.lower().isin(['nan', 'none', 'null', ''])]
                genders = sorted(valid_genders['Gender'].unique().tolist())
                if genders:
                    selected_genders = st.multiselect("Select Gender(s)", options=genders, default=genders)
                    filtered_df = df_grade_filtered[df_grade_filtered['Gender'].isin(selected_genders)].copy()
                else:
                    filtered_df = df_grade_filtered.copy()
            else:
                filtered_df = df_grade_filtered.copy()

        if filtered_df.empty:
            st.warning("⚠️ No data available for the selected filters. Please adjust your criteria.")
        else:
            # ==========================================
            # DASHBOARD TABS
            # ==========================================
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "📊 Executive Summary", 
                "📚 Subject Deep-Dive", 
                "🗺️ Geographic View",
                "🧑‍🎓 Student-Level Impact",
                "🚻 Gender Analysis"
            ])

            base_df = filtered_df[filtered_df['Academic Year'] == 'Baseline']
            end_df = filtered_df[filtered_df['Academic Year'] == 'Endline']

            # ------------------------------------------
            # TAB 1: EXECUTIVE SUMMARY
            # ------------------------------------------
            with tab1:
                st.markdown("### 🚀 High-Level Metrics")
                
                # Expanded to 5 columns to fit SD
                kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
                
                total_assessments = len(filtered_df)
                
                avg_base = base_df['Obtained Marks'].mean() if not base_df.empty else None
                avg_end = end_df['Obtained Marks'].mean() if not end_df.empty else None
                
                sd_base = base_df['Obtained Marks'].std() if not base_df.empty and len(base_df) > 1 else None
                sd_end = end_df['Obtained Marks'].std() if not end_df.empty and len(end_df) > 1 else None

                kpi1.metric("Total Assessments", f"{total_assessments:,}")
                
                if avg_base is not None and avg_end is not None:
                    kpi2.metric("Baseline Mean Score", f"{avg_base:.2f}")
                    kpi3.metric("Endline Mean Score", f"{avg_end:.2f}", delta=f"{avg_end - avg_base:.2f}")
                    
                    if sd_base is not None and sd_end is not None:
                        kpi4.metric("Endline Score SD", f"{sd_end:.2f}", delta=f"{sd_end - sd_base:.2f}", delta_color="inverse")
                    else:
                        kpi4.metric("Endline Score SD", "N/A")
                    
                    # Calculate % of students in "Evolving" (top category)
                    base_evolve = len(base_df[base_df['Category'] == 'Evolving']) / len(base_df) * 100 if len(base_df) > 0 else 0
                    end_evolve = len(end_df[end_df['Category'] == 'Evolving']) / len(end_df) * 100 if len(end_df) > 0 else 0
                    kpi5.metric("Students in 'Evolving'", f"{end_evolve:.1f}%", delta=f"{end_evolve - base_evolve:.1f}%")
                elif avg_base is not None:
                    kpi2.metric("Baseline Mean Score", f"{avg_base:.2f}")
                    kpi3.metric("Endline Mean Score", "N/A")
                    kpi4.metric("Endline Score SD", "N/A")
                    kpi5.metric("Data Status", "Awaiting Endline")
                else:
                    kpi2.metric("Baseline Mean Score", "N/A")
                    kpi3.metric("Endline Mean Score", f"{avg_end:.2f}")
                    kpi4.metric("Endline Score SD", f"{sd_end:.2f}" if sd_end else "N/A")
                    kpi5.metric("Data Status", "Endline Only")
                    
                st.info("**💡 Understanding Standard Deviation (SD):** SD measures the spread of student scores. A **decrease** (green delta) in SD means scores are becoming more clustered and consistent, indicating that the learning gap between high and low performers is closing. An **increase** (red delta) means the gap is widening.")

                st.markdown("---")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("#### 📈 Score Distribution (Box Plot)")
                    st.caption("Visualizes the spread of scores, median, and outliers.")
                    fig_box = px.box(filtered_df, x="Academic Year", y="Obtained Marks", color="Academic Year", 
                                     color_discrete_map=COLOR_MAP, points="all")
                    fig_box.update_layout(showlegend=False, margin=dict(l=0, r=0, t=30))
                    st.plotly_chart(fig_box, use_container_width=True)

                with col_b:
                    st.markdown("#### 🧬 R.I.S.E Category Shift")
                    st.caption("Proportional breakdown of performance categories.")
                    cat_counts = filtered_df.groupby(['Academic Year', 'Category']).size().reset_index(name='Count')
                    cat_counts['Percentage'] = cat_counts.groupby('Academic Year')['Count'].transform(lambda x: x / x.sum() * 100)
                    cat_counts = cat_counts.sort_values(['Academic Year', 'Category'])
                    
                    # Grouped side-by-side bar chart
                    fig_rise = px.bar(cat_counts, x="Category", y="Percentage", color="Academic Year", 
                                      text=cat_counts['Percentage'].apply(lambda x: f'{x:.1f}%' if not pd.isna(x) else ''),
                                      color_discrete_map=COLOR_MAP,
                                      category_orders={"Category": ["Reviving", "Initiating", "Shaping", "Evolving"]})
                    fig_rise.update_layout(barmode='group', margin=dict(l=0, r=0, t=30),
                                           legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5, title=""))
                    st.plotly_chart(fig_rise, use_container_width=True)


            # ------------------------------------------
            # TAB 2: SUBJECT DEEP-DIVE
            # ------------------------------------------
            with tab2:
                st.markdown("### 📚 Subject & Grade Performance (R.I.S.E. Distribution)")
                
                def get_stacked_data(df_subset):
                    if df_subset.empty or 'Grade' not in df_subset.columns:
                        return pd.DataFrame()
                    grouped = df_subset.groupby(['Grade', 'Category']).size().reset_index(name='Count')
                    grouped['Percentage'] = grouped.groupby('Grade')['Count'].transform(lambda x: x / x.sum() * 100)
                    return grouped
                
                base_stacked = get_stacked_data(base_df)
                end_stacked = get_stacked_data(end_df)
                
                sub_col1, sub_col2 = st.columns(2)
                
                with sub_col1:
                    st.markdown("#### Baseline R.I.S.E by Grade")
                    if not base_stacked.empty:
                        fig_base_grade = px.bar(base_stacked, x="Grade", y="Percentage", color="Category",
                                                color_discrete_map=RISE_COLORS, 
                                                text=base_stacked['Percentage'].apply(lambda x: f'{x:.1f}%' if x > 5 else ''),
                                                category_orders={"Category": ["Reviving", "Initiating", "Shaping", "Evolving"]})
                        fig_base_grade.update_layout(barmode='stack', yaxis_title="% of Students", margin=dict(l=0, r=0, t=30),
                                                     legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5, title=""))
                        st.plotly_chart(fig_base_grade, use_container_width=True)
                    else:
                        st.info("No Baseline data available.")
                        
                with sub_col2:
                    st.markdown("#### Endline R.I.S.E by Grade")
                    if not end_stacked.empty:
                        fig_end_grade = px.bar(end_stacked, x="Grade", y="Percentage", color="Category",
                                               color_discrete_map=RISE_COLORS, 
                                               text=end_stacked['Percentage'].apply(lambda x: f'{x:.1f}%' if x > 5 else ''),
                                               category_orders={"Category": ["Reviving", "Initiating", "Shaping", "Evolving"]})
                        fig_end_grade.update_layout(barmode='stack', yaxis_title="% of Students", margin=dict(l=0, r=0, t=30),
                                                    legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5, title=""))
                        st.plotly_chart(fig_end_grade, use_container_width=True)
                    else:
                        st.info("No Endline data available.")
                
                st.markdown("---")
                st.markdown("#### 🧠 Automated Insights")
                
                if not base_stacked.empty and not end_stacked.empty:
                    try:
                        base_piv = base_stacked.pivot(index='Grade', columns='Category', values='Percentage').fillna(0)
                        end_piv = end_stacked.pivot(index='Grade', columns='Category', values='Percentage').fillna(0)
                        
                        for cat in ["Reviving", "Initiating", "Shaping", "Evolving"]:
                            if cat not in base_piv.columns: base_piv[cat] = 0
                            if cat not in end_piv.columns: end_piv[cat] = 0
                            
                        common_grades = base_piv.index.intersection(end_piv.index)
                        
                        if len(common_grades) > 0:
                            diff_piv = end_piv.loc[common_grades] - base_piv.loc[common_grades]
                            
                            best_evo_grade = diff_piv['Evolving'].idxmax()
                            best_evo_val = diff_piv['Evolving'].max()
                            
                            best_rev_grade = diff_piv['Reviving'].idxmin()
                            best_rev_val = diff_piv['Reviving'].min()
                            
                            if best_evo_val > 0:
                                st.success(f"📈 **Top Excellence Growth:** Grade **{best_evo_grade}** saw the highest shift into the 'Evolving' category, increasing its top-tier share by **{best_evo_val:+.1f}** percentage points from Baseline to Endline.")
                            else:
                                st.warning("⚠️ **Excellence Alert:** No grade saw an increase in the 'Evolving' category percentage.")
                            
                            if best_rev_val < 0:
                                st.success(f"📉 **Highest Risk Reduction:** Grade **{best_rev_grade}** had the most successful intervention for struggling students, reducing its 'Reviving' (lowest tier) population by **{abs(best_rev_val):.1f}** percentage points.")
                            else:
                                st.warning("⚠️ **Risk Alert:** No grade successfully reduced their share of students in the 'Reviving' category.")
                        else:
                            st.info("Insufficient overlapping grades between Baseline and Endline to generate comparative insights.")
                    except Exception as e:
                        st.info("Not enough data variance to generate automated insights.")
                else:
                    st.info("Awaiting both Baseline and Endline data to generate comparative insights.")


            # ------------------------------------------
            # TAB 3: GEOGRAPHIC VIEW
            # ------------------------------------------
            with tab3:
                st.markdown("### 🗺️ Geographic & Centre Analysis")
                
                geo_col1, geo_col2 = st.columns([3, 2])
                
                with geo_col1:
                    st.markdown("#### State-wise Performance Comparison (R.I.S.E %)")
                    
                    if not filtered_df.empty:
                        state_cat = filtered_df.groupby(['State', 'Academic Year', 'Category']).size().reset_index(name='Count')
                        state_cat['Percentage'] = state_cat.groupby(['State', 'Academic Year'])['Count'].transform(lambda x: x / x.sum() * 100)
                        
                        # Apply Abbreviation to the Academic Year column for this specific chart
                        state_cat['Period'] = state_cat['Academic Year'].map({'Baseline': 'B', 'Endline': 'E'})
                        
                        # NEW: Dynamic State Abbreviation (Initials for multi-word, first 3 letters for single-word)
                        def abbreviate_state(state_name):
                            words = str(state_name).split()
                            if len(words) > 1:
                                return "".join([w[0].upper() for w in words])
                            return str(state_name)[:3].upper()
                            
                        state_cat['State'] = state_cat['State'].apply(abbreviate_state)
                        
                        fig_state = px.bar(state_cat, x="Period", y="Percentage", color="Category", facet_col="State",
                                           color_discrete_map=RISE_COLORS,
                                           text=state_cat['Percentage'].apply(lambda x: f'{x:.1f}%' if not pd.isna(x) and x > 5 else ''),
                                           category_orders={"Category": ["Reviving", "Initiating", "Shaping", "Evolving"],
                                                            "Period": ["B", "E"]})
                        
                        fig_state.update_layout(barmode='stack', yaxis_title="% of Students", margin=dict(l=0, r=0, t=40),
                                                legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5, title=""))
                        fig_state.update_xaxes(title_text='')
                        fig_state.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
                        
                        st.plotly_chart(fig_state, use_container_width=True)
                    else:
                        st.info("No data available for State comparison.")
                    
                with geo_col2:
                    st.markdown("#### Top 10 Centres (Sorted by % Evolving)")
                    
                    if not filtered_df.empty:
                        center_cat = filtered_df.groupby(['Centre Name', 'Category']).size().reset_index(name='Count')
                        center_cat['Percentage'] = center_cat.groupby('Centre Name')['Count'].transform(lambda x: x / x.sum() * 100)
                        
                        center_piv = center_cat.pivot(index='Centre Name', columns='Category', values='Percentage').fillna(0)
                        
                        for cat in ["Reviving", "Initiating", "Shaping", "Evolving"]:
                            if cat not in center_piv.columns:
                                center_piv[cat] = 0
                                
                        center_piv_sorted = center_piv.sort_values(
                            by=['Evolving', 'Shaping', 'Initiating', 'Reviving'], 
                            ascending=[False, False, False, False]
                        ).head(10)
                        
                        center_piv_sorted = center_piv_sorted.iloc[::-1]
                        
                        top_centres_long = center_piv_sorted.reset_index().melt(
                            id_vars='Centre Name', 
                            value_vars=["Reviving", "Initiating", "Shaping", "Evolving"], 
                            var_name='Category', 
                            value_name='Percentage'
                        )
                        
                        fig_top_centres = px.bar(top_centres_long, x="Percentage", y="Centre Name", color="Category", 
                                                 orientation='h', color_discrete_map=RISE_COLORS,
                                                 text=top_centres_long['Percentage'].apply(lambda x: f'{x:.1f}%' if x > 5 else ''),
                                                 category_orders={"Category": ["Reviving", "Initiating", "Shaping", "Evolving"]})
                        
                        fig_top_centres.update_layout(barmode='stack', xaxis_title="% of Students", yaxis_title="", margin=dict(l=0, r=0, t=30),
                                                      legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5, title=""))
                        st.plotly_chart(fig_top_centres, use_container_width=True)
                    else:
                        st.info("No data available for Top Centres.")


            # ------------------------------------------
            # TAB 4: STUDENT-LEVEL IMPACT
            # ------------------------------------------
            with tab4:
                st.markdown("### 🧑‍🎓 Student-Level Impact (Matched Cohort)")
                st.markdown("Tracking individual student growth by matching their Baseline and Endline records.")
                
                if not base_df.empty and not end_df.empty and 'Student ID' in df.columns:
                    base_clean = base_df[['Student ID', 'Subject', 'Obtained Marks', 'Category']].dropna(subset=['Student ID'])
                    end_clean = end_df[['Student ID', 'Subject', 'Obtained Marks', 'Category']].dropna(subset=['Student ID'])
                    
                    paired_df = pd.merge(base_clean, end_clean, on=['Student ID', 'Subject'], suffixes=('_BL', '_EL'))
                    
                    if not paired_df.empty:
                        paired_df['Score Delta'] = paired_df['Obtained Marks_EL'] - paired_df['Obtained Marks_BL']
                        mean_change = paired_df['Score Delta'].mean()
                        
                        total_paired = len(paired_df)
                        positive_pct = (len(paired_df[paired_df['Score Delta'] > 0]) / total_paired) * 100
                        neutral_pct = (len(paired_df[paired_df['Score Delta'] == 0]) / total_paired) * 100
                        negative_pct = (len(paired_df[paired_df['Score Delta'] < 0]) / total_paired) * 100
                        
                        st.markdown("---")
                        met_col1, met_col2, met_col3, met_col4, met_col5 = st.columns(5)
                        met_col1.metric("Matched Students", f"{total_paired:,}")
                        met_col2.metric("Avg Score Change", f"{mean_change:+.2f}")
                        met_col3.metric("Students (+ Score)", f"{positive_pct:.1f}%")
                        met_col4.metric("Students (No Change)", f"{neutral_pct:.1f}%")
                        met_col5.metric("Students (- Score)", f"{negative_pct:.1f}%")
                        st.markdown("---")
                        
                        st.markdown("#### 🔄 Category Transition Matrix")
                        st.caption("Read rows left-to-right to see student mobility. **Background colors represent transition status:** <span style='color:#82E0AA; font-weight:bold;'>Green (Upward Transition)</span>, <span style='color:#A9A9A9; font-weight:bold;'>Grey (No Transition)</span>, and <span style='color:#FF7F7F; font-weight:bold;'>Red (Downward Transition)</span>.", unsafe_allow_html=True)
                        
                        transition = pd.crosstab(paired_df['Category_BL'], paired_df['Category_EL'], normalize='index') * 100
                        
                        cat_order = ["Reviving", "Initiating", "Shaping", "Evolving"]
                        transition = transition.reindex(index=cat_order, columns=cat_order, fill_value=0)
                        
                        direction_matrix = pd.DataFrame(index=cat_order, columns=cat_order)
                        for i, bl in enumerate(cat_order):
                            for j, el in enumerate(cat_order):
                                if i == j: direction_matrix.loc[bl, el] = 0
                                elif j > i: direction_matrix.loc[bl, el] = 1
                                else: direction_matrix.loc[bl, el] = -1
                                    
                        direction_matrix = direction_matrix.astype(float)
                        
                        fig_heat = px.imshow(direction_matrix, 
                                             labels=dict(x="Endline Category", y="Baseline Category", color="Transition Type"),
                                             x=transition.columns, y=transition.index,
                                             color_continuous_scale=["#FF7F7F", "#F2F4F7", "#82E0AA"]) 
                        
                        text_matrix = transition.applymap(lambda x: f"{x:.1f}%")
                        fig_heat.update_traces(text=text_matrix, texttemplate="%{text}", 
                                               hovertemplate="Baseline: %{y}<br>Endline: %{x}<br>Students: %{text}<extra></extra>")
                        
                        fig_heat.update_coloraxes(showscale=False)
                        fig_heat.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=500)
                        
                        col1, col2, col3 = st.columns([1, 4, 1])
                        with col2:
                            st.plotly_chart(fig_heat, use_container_width=True)

                    else:
                        st.warning("⚠️ Could not find matching 'Student ID' and 'Subject' between the Baseline and Endline datasets.")
                else:
                    st.info("⚠️ Both Baseline and Endline datasets with a valid 'Student ID' column are required for this analysis.")

            # ------------------------------------------
            # TAB 5: GENDER-WISE ANALYSIS
            # ------------------------------------------
            with tab5:
                st.markdown("### 🚻 Gender-Wise Performance")
                
                if 'Gender' in filtered_df.columns:
                    # Filter out any lingering null/blank string artifacts
                    gdf = filtered_df[~filtered_df['Gender'].str.lower().isin(['nan', 'none', 'null', ''])].copy()
                    
                    if not gdf.empty:
                        # 1. High-Level Metrics
                        st.markdown("#### 🏆 Endline Average Score Snapshot")
                        
                        g_base = gdf[gdf['Academic Year'] == 'Baseline']
                        g_end = gdf[gdf['Academic Year'] == 'Endline']
                        
                        genders_present = sorted(gdf['Gender'].unique())
                        cols = st.columns(max(len(genders_present), 2)) # Ensure at least 2 columns for layout
                        
                        for i, g in enumerate(genders_present):
                            with cols[i]:
                                b_mean = g_base[g_base['Gender'] == g]['Obtained Marks'].mean() if not g_base.empty else None
                                e_mean = g_end[g_end['Gender'] == g]['Obtained Marks'].mean() if not g_end.empty else None
                                
                                if b_mean is not None and e_mean is not None:
                                    st.metric(f"{g} - Endline Avg", f"{e_mean:.2f}", delta=f"{e_mean - b_mean:.2f}")
                                elif e_mean is not None:
                                    st.metric(f"{g} - Endline Avg", f"{e_mean:.2f}")
                                elif b_mean is not None:
                                    st.metric(f"{g} - Baseline Avg", f"{b_mean:.2f}")
                                    
                        st.markdown("---")
                        
                        # 2. Charts
                        gen_col1, gen_col2 = st.columns(2)
                        
                        with gen_col1:
                            st.markdown("#### 📈 Average Score Trend")
                            st.caption("Direct comparison of mean scores by gender.")
                            
                            avg_gen = gdf.groupby(['Gender', 'Academic Year'])['Obtained Marks'].mean().reset_index()
                            fig_gen_avg = px.bar(avg_gen, x="Gender", y="Obtained Marks", color="Academic Year", barmode="group",
                                                 color_discrete_map=COLOR_MAP, text_auto='.2f')
                            fig_gen_avg.update_layout(yaxis_title="Average Marks", margin=dict(l=0, r=0, t=30),
                                                      legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5, title=""))
                            st.plotly_chart(fig_gen_avg, use_container_width=True)
                            
                        with gen_col2:
                            st.markdown("#### 🧬 R.I.S.E Category Shift")
                            st.caption("Proportional breakdown of performance tiers by gender.")
                            
                            gen_cat = gdf.groupby(['Gender', 'Academic Year', 'Category']).size().reset_index(name='Count')
                            gen_cat['Percentage'] = gen_cat.groupby(['Gender', 'Academic Year'])['Count'].transform(lambda x: x / x.sum() * 100)
                            
                            fig_gen_rise = px.bar(gen_cat, x="Academic Year", y="Percentage", color="Category", facet_col="Gender",
                                                  color_discrete_map=RISE_COLORS,
                                                  text=gen_cat['Percentage'].apply(lambda x: f'{x:.1f}%' if not pd.isna(x) and x > 5 else ''),
                                                  category_orders={"Category": ["Reviving", "Initiating", "Shaping", "Evolving"],
                                                                   "Academic Year": ["Baseline", "Endline"]})
                            fig_gen_rise.update_layout(barmode='stack', yaxis_title="% of Students", margin=dict(l=0, r=0, t=40),
                                                       legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5, title=""))
                            fig_gen_rise.update_xaxes(title_text='')
                            fig_gen_rise.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
                            st.plotly_chart(fig_gen_rise, use_container_width=True)
                            
                    else:
                        st.info("No valid gender data available in the current filtered selection.")
                else:
                    st.warning("⚠️ 'Gender' column is missing from the uploaded dataset. Please ensure your files include a column labeled 'Gender' with values like 'Boy' or 'Girl'.")

else:
    # Empty State Graphic/Message
    st.info("👈 Please select your upload method and provide the data files to populate the dashboard.")
    st.image("https://cdn-icons-png.flaticon.com/512/7264/7264168.png", width=150)
