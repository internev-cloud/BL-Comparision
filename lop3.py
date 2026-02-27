import streamlit as st
import pandas as pd
import plotly.express as px

# Set page configuration
st.set_page_config(page_title="Baseline Comparison Dashboard", layout="wide", initial_sidebar_state="expanded")

st.title("📈 Baseline Assessment Comparison")
st.markdown("**Academic Year 24-25 vs Academic Year 25-26**")

# Sidebar for file uploads
st.sidebar.header("1. Upload Data")
file1 = st.sidebar.file_uploader("Upload AY 24-25 (EL-BL-Data-AY-24-25.xlsx)", type=["xlsx"])
file2 = st.sidebar.file_uploader("Upload AY 25-26 (BaseLine_Data_25-26YMR.xlsx)", type=["xlsx"])


@st.cache_data
def load_and_prep_data(file1, file2):
    # Read specifically the Baseline sheets
    df_24_25 = pd.read_excel(file1, sheet_name='BaseLine-AY2425')
    df_25_26 = pd.read_excel(file2, sheet_name='BL-Data')

    # Standardize column names (AY 24-25 uses 'Rubrics', AY 25-26 uses 'Category')
    if 'Rubrics' in df_24_25.columns:
        df_24_25 = df_24_25.rename(columns={'Rubrics': 'Category'})
    if 'Rubrics' in df_25_26.columns:
        df_25_26 = df_25_26.rename(columns={'Rubrics': 'Category'})

    # Tag the academic years
    df_24_25['Academic Year'] = 'AY 24-25'
    df_25_26['Academic Year'] = 'AY 25-26'

    # Define common columns we care about for the comparison
    common_cols = ['State', 'Centre Name', 'Donor', 'Subject', 'Grade', 'Total Marks', 'Obtained Marks', 'Category',
                   'Academic Year']

    # Filter datasets to only include common columns to avoid mismatches, then combine
    df_combined = pd.concat([df_24_25[common_cols], df_25_26[common_cols]], ignore_index=True)

    # Clean up any potential whitespace in string columns and ensure consistent types
    for col in ['State', 'Centre Name', 'Donor', 'Subject']:
        df_combined[col] = df_combined[col].astype(str).str.strip()

    # Ensure Grade is treated as a string for easy filtering
    df_combined['Grade'] = df_combined['Grade'].astype(str).str.replace(r'\.0$', '', regex=True)

    return df_combined


if file1 and file2:
    try:
        with st.spinner('Loading and merging baseline data...'):
            df = load_and_prep_data(file1, file2)

        st.sidebar.success("Baseline Data Merged Successfully!")
        st.sidebar.markdown("---")

        # --- Local Filters with "All" Option ---
        st.sidebar.header("2. Filter Data")

        # Get unique values and prepend "All"
        states = ["All"] + sorted(df['State'].dropna().unique().tolist())
        centres = ["All"] + sorted(df['Centre Name'].dropna().unique().tolist())
        donors = ["All"] + sorted(df['Donor'].dropna().unique().tolist())
        subjects = ["All"] + sorted(df['Subject'].dropna().unique().tolist())
        grades = ["All"] + sorted(df['Grade'].dropna().unique().tolist())

        # Create multiselects in the sidebar
        selected_states = st.sidebar.multiselect("Select State(s)", states, default=["All"])
        selected_centres = st.sidebar.multiselect("Select Centre Name(s)", centres, default=["All"])
        selected_donors = st.sidebar.multiselect("Select Donor(s)", donors, default=["All"])
        selected_subjects = st.sidebar.multiselect("Select Subject(s)", subjects, default=["All"])
        selected_grades = st.sidebar.multiselect("Select Class/Grade(s)", grades, default=["All"])

        # Apply Filters iteratively based on "All" logic
        filtered_df = df.copy()

        if "All" not in selected_states:
            filtered_df = filtered_df[filtered_df['State'].isin(selected_states)]

        if "All" not in selected_centres:
            filtered_df = filtered_df[filtered_df['Centre Name'].isin(selected_centres)]

        if "All" not in selected_donors:
            filtered_df = filtered_df[filtered_df['Donor'].isin(selected_donors)]

        if "All" not in selected_subjects:
            filtered_df = filtered_df[filtered_df['Subject'].isin(selected_subjects)]

        if "All" not in selected_grades:
            filtered_df = filtered_df[filtered_df['Grade'].isin(selected_grades)]

        if filtered_df.empty:
            st.warning("No data available for the selected filters. Please adjust your selection.")
        else:
            # --- Key Performance Indicators (KPIs) ---
            st.markdown("### Quick Metrics")
            col1, col2, col3 = st.columns(3)

            total_students = len(filtered_df)
            avg_marks_24 = filtered_df[filtered_df['Academic Year'] == 'AY 24-25']['Obtained Marks'].mean()
            avg_marks_25 = filtered_df[filtered_df['Academic Year'] == 'AY 25-26']['Obtained Marks'].mean()

            col1.metric("Total Assessments (Filtered)", f"{total_students:,}")
            col2.metric("Avg Baseline Score (AY 24-25)", f"{avg_marks_24:.2f}" if pd.notna(avg_marks_24) else "N/A")
            col3.metric("Avg Baseline Score (AY 25-26)", f"{avg_marks_25:.2f}" if pd.notna(avg_marks_25) else "N/A",
                        delta=f"{avg_marks_25 - avg_marks_24:.2f}" if pd.notna(avg_marks_24) and pd.notna(
                            avg_marks_25) else None)

            st.markdown("---")

            # --- Visualizations ---
            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                # 1. Average Marks by Subject
                st.markdown("#### Average Marks by Subject")
                if not filtered_df.empty:
                    avg_subj = filtered_df.groupby(['Subject', 'Academic Year'])['Obtained Marks'].mean().reset_index()
                    fig_subj = px.bar(avg_subj, x='Subject', y='Obtained Marks', color='Academic Year', barmode='group',
                                      text_auto='.2f',
                                      color_discrete_map={'AY 24-25': '#1f77b4', 'AY 25-26': '#ff7f0e'})
                    fig_subj.update_layout(yaxis_title="Avg Obtained Marks")
                    st.plotly_chart(fig_subj, use_container_width=True)

            with col_chart2:
                # 2. Performance Category Breakdown
                st.markdown("#### Performance Category Distribution")
                if not filtered_df.empty:
                    # Group by to get percentages
                    cat_counts = filtered_df.groupby(['Academic Year', 'Category']).size().reset_index(name='Count')
                    cat_counts['Percentage'] = cat_counts.groupby('Academic Year')['Count'].transform(
                        lambda x: x / x.sum() * 100)

                    fig_cat = px.bar(cat_counts, x='Academic Year', y='Percentage', color='Category', barmode='stack',
                                     text=cat_counts['Percentage'].apply(lambda x: f'{x:.1f}%'))
                    fig_cat.update_layout(yaxis_title="% of Students")
                    st.plotly_chart(fig_cat, use_container_width=True)

            st.markdown("#### Average Marks by State")
            if not filtered_df.empty:
                avg_state = filtered_df.groupby(['State', 'Academic Year'])['Obtained Marks'].mean().reset_index()
                fig_state = px.bar(avg_state, x='State', y='Obtained Marks', color='Academic Year', barmode='group',
                                   text_auto='.2f', color_discrete_map={'AY 24-25': '#1f77b4', 'AY 25-26': '#ff7f0e'})
                fig_state.update_layout(xaxis={'categoryorder': 'total descending'}, yaxis_title="Avg Obtained Marks")
                st.plotly_chart(fig_state, use_container_width=True)

            # --- Raw Data Expander ---
            with st.expander("View Filtered Raw Data"):
                st.dataframe(filtered_df, use_container_width=True)

    except Exception as e:
        st.error(f"An error occurred while processing the data: {e}")
else:
    st.info("👈 Please upload both Excel files in the sidebar to generate the baseline comparison dashboard.")