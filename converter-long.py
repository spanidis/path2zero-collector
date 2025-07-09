import streamlit as st
import pandas as pd
import os
import time
import pycountry


def create_breadcrumbs(from_df: pd.DataFrame, in_label_series: list):
    breadcrumb_df = pd.Series([''] * len(from_df), index=from_df.index)
    for label in in_label_series:
        breadcrumb_df = breadcrumb_df + from_df[label].astype(str) + '|'
    return breadcrumb_df.str[:-1]


def map_input(label, available_columns):
    use_static = st.checkbox(f"Use static text for '{label}'", key=f"{label}_checkbox")
    if use_static:
        static_text = st.text_input(f"Enter static text for '{label}'", placeholder=f"{label} Name", key=f"{label}_text", value="")
        return None, static_text
    else:
        selected_cols = st.multiselect(f"Select columns for '{label}'", available_columns, key=f"{label}_cols")
        return selected_cols, None


def convert_iso_to_country_name(iso_code):
    try:
        if len(iso_code) == 2:
            country = pycountry.countries.get(alpha_2=iso_code.upper())
        elif len(iso_code) == 3:
            country = pycountry.countries.get(alpha_3=iso_code.upper())
        elif iso_code.isdigit() or iso_code.isnumeric():
            country = pycountry.countries.get(numeric=iso_code.zfill(3))
        else:
            return iso_code
        return country.name if country else iso_code
    except:
        return iso_code


st.set_page_config(
    page_title="Data Harmonizer",
    page_icon="🧮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Initialize Session State ---
if "last_selected_file" not in st.session_state:
    st.session_state.last_selected_file = None

if "year_transformed" not in st.session_state:
    st.session_state.year_transformed = False
    st.session_state.year_df = None
    st.session_state.rest_labels = None

if "mapping_transformed" not in st.session_state:
    st.session_state.mapping_transformed = False
    st.session_state.mapping_df = None

# --- Data Folder ---
user_folder = os.path.join("data", "default_user")
os.makedirs(user_folder, exist_ok=True)

st.title("DataFrame Uploader & Transformer")

# --- Upload Section ---
st.subheader("Upload a New CSV File")
uploaded_file = st.file_uploader("Upload CSV", type=['csv'])

if uploaded_file is not None:
    save_path = os.path.join(user_folder, uploaded_file.name)

    if os.path.exists(save_path):
        st.warning(f"The file '{uploaded_file.name}' already exists in your folder.")
    else:
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"Saved file: {uploaded_file.name} to your folder!")

# --- File Selection Section ---
st.subheader("Select a CSV File to Load")
csv_files = [f for f in os.listdir(user_folder) if f.endswith('.csv')]

if csv_files:
    selected_file = st.selectbox("Choose a CSV file", ["-- Select a file --"] + csv_files)

    if selected_file != st.session_state.last_selected_file:
        st.session_state.last_selected_file = selected_file
        st.session_state.year_transformed = False
        st.session_state.year_df = None
        st.session_state.rest_labels = None
        st.session_state.mapping_transformed = False
        st.session_state.mapping_df = None
        st.rerun()

    if selected_file and selected_file != "-- Select a file --":
        file_path = os.path.join(user_folder, selected_file)
        df = pd.read_csv(file_path)
        available_columns = df.columns.tolist()

        st.subheader("Original DataFrame")
        st.dataframe(df, use_container_width=True)

        # --- Year Mapping Section ---
        st.subheader("Year Configuration")
        years_in_rows = st.checkbox("Are years stored in rows?", value=False)

        if years_in_rows:
            year_column = st.selectbox("Select the column that contains the Year values", available_columns)
            value_column = st.selectbox("Select the column that contains the Values", available_columns)
        else:
            year_columns = st.multiselect("Select the Year columns", available_columns)

        if st.button("Transform Year Columns") and not st.session_state.year_transformed:
            st.subheader("Transformed Year DataFrame (Preview)")
            if years_in_rows:
                rest_labels = [col for col in available_columns if col not in [year_column, value_column]]
                year_df = df.pivot(index=rest_labels, columns=year_column, values=value_column)
                year_df.reset_index(drop=True, inplace=True)
            else:
                rest_labels = [col for col in available_columns if col not in year_columns]
                year_df = df[year_columns]

            st.session_state.year_df = year_df
            st.session_state.year_transformed = True
            st.session_state.rest_labels = rest_labels
            st.rerun()

        elif st.session_state.year_transformed:
            st.dataframe(st.session_state.year_df, use_container_width=True)
            if st.button("Clear Year Transformation"):
                st.session_state.year_transformed = False
                st.session_state.year_df = None
                st.session_state.rest_labels = None
                st.rerun()

        # --- Mapping Section ---
        if st.session_state.year_transformed:
            st.subheader("Map Columns for Transformation")

            available_columns = st.session_state.rest_labels
            transformed_df = pd.DataFrame(columns=['Model', 'Scenario', 'Region', 'Variable', 'Unit'])
            transformed_df = transformed_df.reindex(st.session_state.year_df.index)

            model_cols, model_text = map_input("Model", available_columns)
            scenario_cols, scenario_text = map_input("Scenario", available_columns)
            region_cols, region_text = map_input("Region", available_columns)
            st.caption("ℹ️ ISO 3166 codes will be converted to full country names.")
            variable_cols, variable_text = map_input("Variable", available_columns)
            unit_cols, unit_text = map_input("Unit", available_columns)

            if st.button("Transform DataFrame"):
                st.subheader("Transformed DataFrame (Preview)")

                if model_text:
                    transformed_df['Model'] = model_text
                elif model_cols:
                    transformed_df['Model'] = create_breadcrumbs(df, model_cols)

                if scenario_text:
                    transformed_df['Scenario'] = scenario_text
                elif scenario_cols:
                    transformed_df['Scenario'] = create_breadcrumbs(df, scenario_cols)

                if region_text:
                    transformed_df['Region'] = region_text
                elif region_cols:
                    transformed_df['Region'] = create_breadcrumbs(df, region_cols)
                transformed_df['Region'] = transformed_df['Region'].apply(convert_iso_to_country_name)

                if variable_text:
                    transformed_df['Variable'] = variable_text
                elif variable_cols:
                    transformed_df['Variable'] = create_breadcrumbs(df, variable_cols)

                if unit_text:
                    transformed_df['Unit'] = unit_text
                elif unit_cols:
                    transformed_df['Unit'] = create_breadcrumbs(df, unit_cols)

                st.session_state.mapping_df = transformed_df
                st.session_state.mapping_transformed = True
                st.rerun()

            elif st.session_state.mapping_transformed:
                st.dataframe(st.session_state.mapping_df, use_container_width=True)
                if st.button("Clear Mapping Transformation"):
                    st.session_state.mapping_transformed = False
                    st.session_state.mapping_df = None
                    st.rerun()

            # --- Final IAMC Format Output ---
            if st.session_state.mapping_transformed:
    st.subheader("IAMC Transformation")
    if st.button("Transform to IAMC Format"):
        final_df = pd.concat([st.session_state.mapping_df, st.session_state.year_df], axis=1).reset_index(drop=True)
        st.dataframe(final_df, use_container_width=True)

        # Add new button for long-format transformation:
        if st.button("Create IAMC Long Format for Postgres"):
            # Identify year columns in the year_df (these are wide columns)
            year_cols = st.session_state.year_df.columns.tolist()
            
            # Combine fixed columns + year columns for melting
            fixed_cols = st.session_state.mapping_df.columns.tolist()
            
            # Combine both dataframes again for melting
            combined_df = pd.concat([st.session_state.mapping_df.reset_index(drop=True),
                                     st.session_state.year_df.reset_index(drop=True)], axis=1)
            
            # Melt wide year columns to long format
            long_df = combined_df.melt(id_vars=fixed_cols, 
                                       value_vars=year_cols,
                                       var_name='Year',
                                       value_name='Value')

            # Convert Year to int if possible
            try:
                long_df['Year'] = long_df['Year'].astype(int)
            except:
                pass
            
            # Show the long format DataFrame
            st.subheader("IAMC Long Format Table for Postgres")
            st.dataframe(long_df, use_container_width=True)


else:
    st.info("No CSV files in your folder. Upload one to get started!")
    if st.button("🔄 Reload Files"):
        st.rerun()
