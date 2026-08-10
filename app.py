import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import os

st.set_page_config(page_title="Plainfield CLT Property Tracker", layout="wide")

st.title("Community Land Trust Parcel Tracker")
st.markdown("Live spatial data on vacant and abandoned properties targeted for community acquisition in Plainfield, NJ.")

def clean_id(col):
    """Helper to clean Block/Lot numbers for accurate cross-referencing."""
    return col.astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.lstrip('0')

def load_data():
    try:
        # Load the master database
        df = pd.read_csv("master_combined_database.csv")
        if 'lat' in df.columns and 'lon' in df.columns:
            df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
            df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
            
        # Load the City list to cross-reference which properties are officially on the city's radar
        city_set = set()
        if os.path.exists("clt_property_database.csv"):
            city_df = pd.read_csv("clt_property_database.csv")
            city_df['join_idx'] = clean_id(city_df['Block']) + "_" + clean_id(city_df['Lot'])
            city_set = set(city_df['join_idx'])
            
        return df, city_set
    except FileNotFoundError:
        return pd.DataFrame(), set()

df, city_set = load_data()

if df.empty:
    st.warning("Data is currently updating or unavailable. Please check back later.")
else:
    # Build the Scoring Logic
    df['join_idx'] = clean_id(df['Block']) + "_" + clean_id(df['Lot'])
    df['On City List'] = df['join_idx'].apply(lambda x: "Yes" if x in city_set else "No")
    
    def grade_target(row):
        score = 0
        # Point 1: On the City VA List?
        if row['On City List'] == "Yes": score += 2
        
        # Point 2: Residential Zoning? (Plainfield uses R-2, R-3, R-4, etc.)
        zoning = str(row.get('Zoning', '')).upper()
        if 'R' in zoning or 'RES' in zoning or 'MU' in zoning: score += 1
            
        # Point 3: Distressed Pricing? (Nominal transfers like $1, $100, or < $100k)
        price = pd.to_numeric(row.get('Last Sale Price', np.nan), errors='coerce')
        if pd.notna(price):
            if price <= 1000: score += 2  # Likely a nominal deed transfer or foreclosure
            elif price <= 150000: score += 1
            
        if score >= 4: return "High Potential", "green"
        elif score >= 2: return "Medium Potential", "orange"
        else: return "Low Potential", "red"

    # Apply grading to the dataframe
    grades = df.apply(grade_target, axis=1)
    df['Target Level'] = [g[0] for g in grades]
    df['Color'] = [g[1] for g in grades]

    # Sidebar Filtering
    st.sidebar.header("Filter Properties")
    
    target_options = ["High Potential", "Medium Potential", "Low Potential"]
    selected_targets = st.sidebar.multiselect("Acquisition Priority", options=target_options, default=target_options)
    
    if 'Zoning' in df.columns:
        df['Zoning'] = df['Zoning'].fillna("Unzoned / Unknown")
        zoning_options = sorted(df['Zoning'].astype(str).unique().tolist())
        selected_zoning = st.sidebar.multiselect("Zoning District", options=zoning_options, default=zoning_options)
    else:
        selected_zoning = []

    # Apply filters
    filtered_df = df[df['Target Level'].isin(selected_targets)] if selected_targets else df
    if selected_zoning:
        filtered_df = filtered_df[filtered_df['Zoning'].isin(selected_zoning)]

    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.subheader("Target Map")
        st.markdown("🟢 **High** | 🟠 **Medium** | 🔴 **Low**")
        
        if 'lat' in filtered_df.columns and 'lon' in filtered_df.columns:
            map_df = filtered_df.dropna(subset=['lat', 'lon'])
            
            if not map_df.empty:
                m = folium.Map(location=[40.6180, -74.4168], zoom_start=13, tiles="CartoDB positron")
                
                # Fetch API key safely from Streamlit Secrets
                api_key = st.secrets.get("STREETVIEW_API_KEY", "")
                
                for _, row in map_df.iterrows():
                    address = row.get('Address', 'Unknown Address')
                    price = row.get('Last Sale Price', 'N/A')
                    color = row.get('Color', 'gray')
                    lat = row['lat']
                    lon = row['lon']
                    
                    # Generate the image HTML based on API key presence
                    if api_key:
                        image_url = f"https://maps.googleapis.com/maps/api/streetview?size=250x150&location={lat},{lon}&key={api_key}"
                        image_html = f'<img src="{image_url}" width="250" style="border-radius: 5px; margin-bottom: 8px;">'
                    else:
                        image_html = f'<img src="https://placehold.co/250x150/e2e8f0/475569?text=Street+View\\nImage" width="250" style="border-radius: 5px; margin-bottom: 8px;">'
                    
                    popup_html = f"""
                    <div style="width: 260px; font-family: sans-serif;">
                        {image_html}
                        <h4 style="margin: 0 0 5px 0; color: #1e293b;">{address}</h4>
                        <b>Block/Lot:</b> {row.get('Block')} / {row.get('Lot')}<br>
                        <b>Zoning:</b> {row.get('Zoning')}<br>
                        <b>Last Sale Price:</b> ${price}<br>
                        <b>City VA List:</b> {"✅ Yes" if row['On City List'] == "Yes" else "❌ No"}<br>
                        <b>Owner:</b> {row.get('Owner Address', 'N/A')}<br>
                        <br>
                        <a href="https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat},{lon}" target="_blank" style="background-color: #2563eb; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; display: inline-block;">Explore in Street View</a>
                    </div>
                    """
                    
                    folium.CircleMarker(
                        location=[lat, lon],
                        radius=7,
                        color=color,
                        weight=1.5,
                        fill=True,
                        fill_color=color,
                        fill_opacity=0.7,
                        popup=folium.Popup(popup_html, max_width=300),
                        tooltip=f"{address} ({row['Target Level']})"
                    ).add_to(m)
                    
                st_folium(m, width=650, height=600)
            else:
                st.info("No properties found based on current filters.")
        else:
            st.info("Latitude and longitude coordinates are missing from the dataset.")

    with col2:
        st.subheader("Property Registry")
        search = st.text_input("Search by address, owner, or block:")
        
        display_df = filtered_df[['Block', 'Lot', 'Address', 'Target Level', 'On City List', 'Owner Address', 'Zoning', 'Last Sale Price']]
        
        if search:
            search_mask = display_df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
            display_df = display_df[search_mask]
            
        st.dataframe(display_df, use_container_width=True, height=550)
