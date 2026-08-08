import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Plainfield CLT Property Tracker", layout="wide")

st.title("Community Land Trust Parcel Tracker")
st.markdown("Live spatial data on vacant and abandoned properties targeted for community acquisition in Plainfield, NJ.")

# Removed the @st.cache_data completely so it ALWAYS reads the freshest data
def load_data():
    try:
        df = pd.read_csv("master_combined_database.csv")
        # Ensure coordinates exist and are numeric for mapping
        if 'lat' in df.columns and 'lon' in df.columns:
            df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
            df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        return df
    except FileNotFoundError:
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("Data is currently updating or unavailable. Please check back later.")
else:
    st.sidebar.header("Filter Properties")
    
    # Fill missing zoning with "Unzoned / Unknown" so they don't disappear from the map
    if 'Zoning' in df.columns:
        df['Zoning'] = df['Zoning'].fillna("Unzoned / Unknown")
        zoning_options = df['Zoning'].unique().tolist()
        selected_zoning = st.sidebar.multiselect("Zoning District", options=zoning_options, default=zoning_options)
        filtered_df = df[df['Zoning'].isin(selected_zoning)] if selected_zoning else df
    else:
        filtered_df = df

    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.subheader("Property Locations")
        if 'lat' in filtered_df.columns and 'lon' in filtered_df.columns:
            map_df = filtered_df.dropna(subset=['lat', 'lon'])
            
            if not map_df.empty:
                m = folium.Map(location=[40.6180, -74.4168], zoom_start=13, tiles="CartoDB positron")
                
                for _, row in map_df.iterrows():
                    address = row.get('Address', 'Unknown Address')
                    block = row.get('Block', 'N/A')
                    lot = row.get('Lot', 'N/A')
                    owner = row.get('Owner Address', 'N/A')
                    
                    popup_html = f"""
                    <div style="width: 200px;">
                        <b>{address}</b><br>
                        <b>Block/Lot:</b> {block} / {lot}<br>
                        <b>Tax Billing:</b> {owner}
                    </div>
                    """
                    folium.Marker(
                        location=[row['lat'], row['lon']],
                        popup=folium.Popup(popup_html, max_width=250),
                        tooltip=str(address),
                        icon=folium.Icon(color="darkblue", icon="home")
                    ).add_to(m)
                    
                st_folium(m, width=650, height=550)
            else:
                st.info("No properties with valid coordinates found based on current filters.")
        else:
            st.info("Latitude and longitude coordinates are missing from the dataset.")

    with col2:
        st.subheader("Property Registry")
        search = st.text_input("Search by address, owner, or block:")
        
        if search:
            search_mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
            display_df = filtered_df[search_mask]
        else:
            display_df = filtered_df
            
        st.dataframe(display_df, use_container_width=True, height=500)
