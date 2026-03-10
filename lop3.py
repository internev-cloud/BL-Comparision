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
    common_cols = ['State', 'Centre Name', 'Donor', 'Subject', 'Grade', 'Student ID', 'Total Marks', 'Obtained Marks', 'Category', 'Academic Year']
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
    for col in ['State', 'Centre Name', 'Donor', 'Subject', 'Student ID']:
        if col in df_combined.columns:
            df_combined[col] = df_combined[col].astype(str).str.strip()

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
            
            states = ["All"] + sorted(df['State'].dropna().unique().tolist())
            centres = ["All"] + sorted(df['Centre Name'].dropna().unique().tolist())
            subjects = ["All"] + sorted(df['Subject'].dropna().unique().tolist())
            grades = ["All"] + sorted(df['Grade'].dropna().unique().tolist())

            selected_states = st.selectbox("Select State", states, index=0)
            selected_centres = st.selectbox("Select Centre", centres, index=0)
            selected_subjects = st.selectbox("Select Subject", subjects, index=0)
            selected_grades = st.selectbox("Select Grade", grades, index=0)

            # Apply Filters
            filtered_df = df.copy()
            if selected_states != "All": filtered_df = filtered_df[filtered_df['State'] == selected_states]
            if selected_centres != "All": filtered_df = filtered_df[filtered_df['Centre Name'] == selected_centres]
            if selected_subjects != "All": filtered_df = filtered_df[filtered_df['Subject'] == selected_subjects]
            if selected_grades != "All": filtered_df = filtered_df[filtered_df['Grade'] == selected_grades]

        if filtered_df.empty:
            st.warning("⚠️ No data available for the selected filters. Please adjust your criteria.")
        else:
            # ==========================================
            # DASHBOARD TABS
            # ==========================================
            tab1, tab2, tab3, tab4 = st.tabs([
                "📊 Executive Summary", 
                "📚 Subject Deep-Dive", 
                "🗺️ Geographic View",
                "🧑‍🎓 Student-Level Impact"
            ])

            base_df = filtered_df[filtered_df['Academic Year'] == 'Baseline']
            end_df = filtered_df[filtered_df['Academic Year'] == 'Endline']

            # ------------------------------------------
            # TAB 1: EXECUTIVE SUMMARY
            # ------------------------------------------
            with tab1:
                st.markdown("### 🚀 High-Level Metrics")
                kpi1, kpi2, kpi3, kpi4 = st.columns(4)
                
                total_assessments = len(filtered_df)
                
                avg_base = base_df['Obtained Marks'].mean() if not base_df.empty else None
                avg_end = end_df['Obtained Marks'].mean() if not end_df.empty else None

                kpi1.metric("Total Assessments", f"{total_assessments:,}")
                
                if avg_base is not None and avg_end is not None:
                    kpi2.metric("Baseline Avg Score", f"{avg_base:.2f}")
                    kpi3.metric("Endline Avg Score", f"{avg_end:.2f}", delta=f"{avg_end - avg_base:.2f}")
                    
                    # Calculate % of students in "Evolving" (top category)
                    base_evolve = len(base_df[base_df['Category'] == 'Evolving']) / len(base_df) * 100 if len(base_df) > 0 else 0
                    end_evolve = len(end_df[end_df['Category'] == 'Evolving']) / len(end_df) * 100 if len(end_df) > 0 else 0
                    kpi4.metric("Students in 'Evolving'", f"{end_evolve:.1f}%", delta=f"{end_evolve - base_evolve:.1f}%")
                elif avg_base is not None:
                    kpi2.metric("Baseline Avg Score", f"{avg_base:.2f}")
                    kpi3.metric("Endline Avg Score", "N/A")
                    kpi4.metric("Data Status", "Awaiting Endline")
                else:
                    kpi2.metric("Baseline Avg Score", "N/A")
                    kpi3.metric("Endline Avg Score", f"{avg_end:.2f}")
                    kpi4.metric("Data Status", "Endline Only")

                st.markdown("---")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("#### 📈 Score Distribution (Box Plot)")
                    st.caption("Visualizes the spread of scores, median, and outliers.")
                    fig_box = px.box(filtered_df, x="Academic Year", y="Obtained Marks", color="Academic Year", 
                                     color_discrete_map=COLOR_MAP, points="all")
                    fig_box.update_layout(showlegend=False, margin=dict(l=0, r=0, t=30, b=0))
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
                    fig_rise.update_layout(barmode='group', margin=dict(l=0, r=0, t=30, b=0))
                    st.plotly_chart(fig_rise, use_container_width=True)


            # ------------------------------------------
            # TAB 2: SUBJECT DEEP-DIVE
            # ------------------------------------------
            with tab2:
                st.markdown("### 📚 Subject & Grade Performance")
                
                sub_col1, sub_col2 = st.columns(2)
                
                with sub_col1:
                    st.markdown("#### Average Score by Subject")
                    avg_subj = filtered_df.groupby(['Subject', 'Academic Year'])['Obtained Marks'].mean().reset_index()
                    fig_subj = px.bar(avg_subj, x='Subject', y='Obtained Marks', color='Academic Year', barmode='group',
                                      text_auto='.2f', color_discrete_map=COLOR_MAP)
                    fig_subj.update_layout(yaxis_title="Average Marks", margin=dict(l=0, r=0, t=30, b=0))
                    st.plotly_chart(fig_subj, use_container_width=True)
                    
                with sub_col2:
                    st.markdown("#### Average Score by Grade")
                    if 'Grade' in filtered_df.columns:
                        avg_grade = filtered_df.groupby(['Grade', 'Academic Year'])['Obtained Marks'].mean().reset_index()
                        fig_grade = px.line(avg_grade, x='Grade', y='Obtained Marks', color='Academic Year', markers=True,
                                            color_discrete_map=COLOR_MAP)
                        fig_grade.update_layout(yaxis_title="Average Marks", margin=dict(l=0, r=0, t=30, b=0))
                        st.plotly_chart(fig_grade, use_container_width=True)


            # ------------------------------------------
            # TAB 3: GEOGRAPHIC VIEW
            # ------------------------------------------
            with tab3:
                st.markdown("### 🗺️ Geographic & Centre Analysis")
                
                geo_col1, geo_col2 = st.columns([3, 2])
                
                with geo_col1:
                    st.markdown("#### State-wise Performance Comparison")
                    avg_state = filtered_df.groupby(['State', 'Academic Year'])['Obtained Marks'].mean().reset_index()
                    fig_state = px.bar(avg_state, x='State', y='Obtained Marks', color='Academic Year', barmode='group',
                                       text_auto='.2f', color_discrete_map=COLOR_MAP)
                    fig_state.update_layout(xaxis={'categoryorder': 'total descending'}, yaxis_title="Average Marks")
                    st.plotly_chart(fig_state, use_container_width=True)
                    
                with geo_col2:
                    st.markdown("#### Top 10 Centres (Overall Avg)")
                    top_centres = filtered_df.groupby('Centre Name')['Obtained Marks'].mean().reset_index().sort_values('Obtained Marks', ascending=True).tail(10)
                    fig_top_centres = px.bar(top_centres, x='Obtained Marks', y='Centre Name', orientation='h', text_auto='.2f')
                    fig_top_centres.update_traces(marker_color='#636EFA')
                    fig_top_centres.update_layout(xaxis_title="Avg Marks", yaxis_title="")
                    st.plotly_chart(fig_top_centres, use_container_width=True)


            # ------------------------------------------
            # TAB 4: STUDENT-LEVEL IMPACT (UPDATED)
            # ------------------------------------------
            with tab4:
                st.markdown("### 🧑‍🎓 Student-Level Impact (Matched Cohort)")
                st.markdown("Tracking individual student growth by matching their Baseline and Endline records.")
                
                if not base_df.empty and not end_df.empty and 'Student ID' in df.columns:
                    
                    # Isolate required columns and clean drop missing IDs
                    base_clean = base_df[['Student ID', 'Subject', 'Obtained Marks', 'Category']].dropna(subset=['Student ID'])
                    end_clean = end_df[['Student ID', 'Subject', 'Obtained Marks', 'Category']].dropna(subset=['Student ID'])
                    
                    # Merge on Student ID and Subject
                    paired_df = pd.merge(base_clean, end_clean, on=['Student ID', 'Subject'], suffixes=('_BL', '_EL'))
                    
                    if not paired_df.empty:
                        paired_df['Score Delta'] = paired_df['Obtained Marks_EL'] - paired_df['Obtained Marks_BL']
                        mean_change = paired_df['Score Delta'].mean()
                        improved_pct = (len(paired_df[paired_df['Score Delta'] > 0]) / len(paired_df)) * 100
                        
                        st.markdown("---")
                        met_col1, met_col2, met_col3 = st.columns(3)
                        met_col1.metric("Matched Students", f"{len(paired_df):,}")
                        met_col2.metric("Avg Score Change (EL - BL)", f"{mean_change:+.2f}")
                        met_col3.metric("% of Students Improved", f"{improved_pct:.1f}%")
                        st.markdown("---")
                        
                        viz_col1, viz_col2 = st.columns(2)
                        
                        with viz_col1:
                            st.markdown("#### 🔄 Category Transition Matrix")
                            st.caption("Read rows left-to-right. E.g., 'Of students who started in Reviving, X% moved to...'")
                            
                            # Create transition matrix (row percentages)
                            transition = pd.crosstab(paired_df['Category_BL'], paired_df['Category_EL'], normalize='index') * 100
                            
                            # Plot heatmap
                            fig_heat = px.imshow(transition, 
                                                 labels=dict(x="Endline Category", y="Baseline Category", color="% of Students"),
                                                 x=transition.columns, y=transition.index, text_auto=".1f", color_continuous_scale="Greens")
                            fig_heat.update_layout(margin=dict(l=0, r=0, t=30, b=0))
                            st.plotly_chart(fig_heat, use_container_width=True)

                        with viz_col2:
                            st.markdown("#### 📈 Individual Score Migration")
                            st.caption("Dots above the dashed line indicate improvement.")
                            
                            fig_scatter = px.scatter(paired_df, x="Obtained Marks_BL", y="Obtained Marks_EL", 
                                                     color="Category_EL", hover_data=["Student ID"], 
                                                     color_discrete_map=RISE_COLORS, opacity=0.7)
                            
                            # Add y=x reference line
                            max_val = max(paired_df['Obtained Marks_BL'].max(), paired_df['Obtained Marks_EL'].max())
                            fig_scatter.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val, line=dict(color="black", dash="dash", width=1))
                            fig_scatter.update_layout(xaxis_title="Baseline Marks", yaxis_title="Endline Marks", margin=dict(l=0, r=0, t=30, b=0))
                            st.plotly_chart(fig_scatter, use_container_width=True)
                            
                        # Detailed Paired DataFrame
                        st.markdown("#### 🗄️ Student Data Explorer")
                        st.dataframe(paired_df, use_container_width=True, height=300)

                    else:
                        st.warning("⚠️ Could not find matching 'Student ID' and 'Subject' between the Baseline and Endline datasets.")
                else:
                    st.info("⚠️ Both Baseline and Endline datasets with a valid 'Student ID' column are required for this analysis.")

else:
    # Empty State Graphic/Message
    st.info("👈 Please select your upload method and provide the data files to populate the dashboard.")
    st.image("https://cdn-icons-png.flaticon.com/512/7264/7264168.png", width=150)
