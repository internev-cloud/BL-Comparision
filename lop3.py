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
    st.markdown("<span style='color: gray; font-size: 0.85em;'>Upload your CSV or Excel files.</span>", unsafe_allow_html=True)
    
    file1 = st.file_uploader("Upload Baseline Data", type=["csv", "xlsx"])
    file2 = st.file_uploader("Upload Endline Data", type=["csv", "xlsx"])
    
    st.divider()

@st.cache_data
def load_and_prep_data(file1, file2):
    # Added 'Student ID' to extract deeper insights
    common_cols = ['State', 'Centre Name', 'Donor', 'Subject', 'Grade', 'Student ID', 'Total Marks', 'Obtained Marks', 'Category', 'Academic Year']
    dfs_to_concat = []

    def read_data(f):
        if f.name.endswith('.csv'):
            return pd.read_csv(f)
        return pd.read_excel(f, sheet_name=0)

    if file1:
        df_base = read_data(file1)
        if 'Rubrics' in df_base.columns: df_base.rename(columns={'Rubrics': 'Category'}, inplace=True)
        df_base['Academic Year'] = 'Baseline'
        dfs_to_concat.append(df_base[[c for c in common_cols if c in df_base.columns]])

    if file2:
        df_end = read_data(file2)
        if 'Rubrics' in df_end.columns: df_end.rename(columns={'Rubrics': 'Category'}, inplace=True)
        df_end['Academic Year'] = 'Endline'
        dfs_to_concat.append(df_end[[c for c in common_cols if c in df_end.columns]])

    df_combined = pd.concat(dfs_to_concat, ignore_index=True)

    # Text cleaning
    for col in ['State', 'Centre Name', 'Donor', 'Subject']:
        if col in df_combined.columns:
            df_combined[col] = df_combined[col].astype(str).str.strip()

    if 'Grade' in df_combined.columns:
        df_combined['Grade'] = df_combined['Grade'].astype(str).str.replace(r'\.0$', '', regex=True)

    # Enforce R.I.S.E ordering (UPDATED ORDER)
    if 'Category' in df_combined.columns:
        rise_order = ["Reviving", "Initiating", "Shaping", "Evolving"]
        df_combined['Category'] = pd.Categorical(df_combined['Category'], categories=rise_order, ordered=True)

    # Ensure numeric
    df_combined['Obtained Marks'] = pd.to_numeric(df_combined['Obtained Marks'], errors='coerce')

    return df_combined

# Define color palette for consistency
COLOR_MAP = {'Baseline': '#636EFA', 'Endline': '#00CC96'}
RISE_COLORS = {"Reviving": "#EF553B", "Initiating": "#AB63FA", "Shaping": "#FFA15A", "Evolving": "#00CC96"}

if file1 or file2:
    with st.spinner('Crunching numbers...'):
        df = load_and_prep_data(file1, file2)

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
            "🗄️ Raw Data"
        ])

        # ------------------------------------------
        # TAB 1: EXECUTIVE SUMMARY
        # ------------------------------------------
        with tab1:
            st.markdown("### 🚀 High-Level Metrics")
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            
            total_assessments = len(filtered_df)
            base_df = filtered_df[filtered_df['Academic Year'] == 'Baseline']
            end_df = filtered_df[filtered_df['Academic Year'] == 'Endline']
            
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
                
                # UPDATED CHART: Vertical orientation and new category order
                fig_rise = px.bar(cat_counts, x="Academic Year", y="Percentage", color="Category", 
                                  text=cat_counts['Percentage'].apply(lambda x: f'{x:.1f}%'),
                                  color_discrete_map=RISE_COLORS,
                                  category_orders={"Category": ["Reviving", "Initiating", "Shaping", "Evolving"]})
                fig_rise.update_layout(barmode='stack', margin=dict(l=0, r=0, t=30, b=0))
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
        # TAB 4: RAW DATA & EXPORT
        # ------------------------------------------
        with tab4:
            st.markdown("### 🗄️ Dataset Explorer")
            st.markdown("Review the filtered dataset below. You can also download it for external reporting.")
            
            # Download button
            csv = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Filtered Data as CSV",
                data=csv,
                file_name='filtered_impact_data.csv',
                mime='text/csv',
            )
            
            st.dataframe(filtered_df, use_container_width=True, height=500)

else:
    # Empty State Graphic/Message
    st.info("👈 Please upload your Baseline and/or Endline dataset in the sidebar to populate the dashboard.")
    st.image("https://cdn-icons-png.flaticon.com/512/7264/7264168.png", width=150)
