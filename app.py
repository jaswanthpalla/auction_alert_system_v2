import streamlit as st
import pandas as pd
import glob
import os

st.set_page_config(layout="wide")
st.title("Auction Notices")

# Find the latest combined CSV file
csv_files = glob.glob("auction_exports/combined_auctions_*.csv")
if not csv_files:
    st.error("No combined auction data found.")
else:
    latest_csv = max(csv_files, key=lambda x: x.split('_')[-1].split('.')[0])
    st.write(f"Displaying data from: {latest_csv}")
    df = pd.read_csv(latest_csv)

    st.write("### Data Preview")
    st.dataframe(df.head())

    # Filter by Source
    st.write("### Filter Auctions by Source")
    sources = ['All'] + sorted(df['Source'].unique().tolist())
    selected_source = st.selectbox("Select Source:", sources, index=0)
    if selected_source != 'All':
        df = df[df['Source'] == selected_source]

    # Filter by Days Until Submission
    st.write("### Filter Auctions by Days Until Submission")
    if 'days_until_submission' in df.columns:
        df['days_until_submission'] = pd.to_numeric(df['days_until_submission'], errors='coerce')
        min_days = df['days_until_submission'].min()
        max_days = df['days_until_submission'].max()

        if pd.isna(min_days) or pd.isna(max_days):
            st.warning("No valid 'days_until_submission' data available for filtering.")
            filtered_df = df
        else:
            min_days = int(max(min_days, 0))
            max_days = int(max(max_days, min_days + 1))

            days_range = st.slider(
                "Select range of days until submission:",
                min_value=min_days,
                max_value=max_days,
                value=(min_days, max_days),
                step=1
            )

            if st.button("Apply"):
                filtered_df = df[
                    (df['days_until_submission'] >= days_range[0]) &
                    (df['days_until_submission'] <= days_range[1])
                ]
                st.session_state['filtered_df'] = filtered_df
    else:
        st.error("Column 'days_until_submission' not found in the data.")
        filtered_df = df

    # Use filtered data if available
    if 'filtered_df' in st.session_state:
        filtered_df = st.session_state['filtered_df']
    else:
        filtered_df = df

    # Display the filtered auction listings
    st.write("### Auction Listings")
    st.dataframe(filtered_df)

    # ✅ Download button
    st.download_button(
        label="Download Filtered CSV",
        data=filtered_df.to_csv(index=False).encode('utf-8'),
        file_name=f"combined_auctions_filtered_{os.path.basename(latest_csv).split('_')[-1]}",
        mime="text/csv"
    )
