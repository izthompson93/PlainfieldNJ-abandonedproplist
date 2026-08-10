import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import os

# Collapse the sidebar by default in case Streamlit tries to render it empty
st.set_page_config(page_title="Plainfield CLT Property Tracker", layout="wide", initial_sidebar_state="collapsed")

st.title("Community Land Trust Parcel Tracker")
st.markdown("Live spatial data on vacant and abandoned properties targeted for community acquisition in Plainfield, NJ.")

def clean_id(col):
    """Helper to clean Block/Lot numbers for accurate cross-referencing."""
    return col.astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.lstrip('0')

def load_data():
    try:
        df = pd.read_csv("master_combined_database.csv")
        if 'lat' in df.columns and 'lon' in df.columns:
            df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
            df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
            
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
        if row['On City List'] == "Yes": score += 2
        
        zoning = str(row.get('Zoning', '')).upper()
        if 'R' in zoning or 'RES' in zoning or 'MU' in zoning: score += 1
            
        price = pd.to_numeric(row.get('Last Sale Price', np.nan), errors='coerce')
        if pd.notna(price):
            if price <= 1000: score += 2 
            elif price <= 150000: score += 1
            
        if score >= 4: return "High Potential", "green"
        elif score >= 2: return "Medium Potential", "orange"
        else: return "Low Potential", "red"

    grades = df.apply(grade_target, axis=1)
    df['Target Level'] = [g[0] for g in grades]
    df['Color'] = [g[1] for g in grades]

    if 'Zoning' in df.columns:
        df['Zoning'] = df['Zoning'].fillna("Unzoned / Unknown")
        zoning_options = sorted(df['Zoning'].astype(str).unique().tolist())
    else:
        zoning_options = []
        
    target_options = ["High Potential", "Medium Potential", "Low Potential"]

    # Sleeker, collapsed horizontal filter row instead of the bulky sidebar
    with st.expander("🔍 Filter & Search Properties", expanded=False):
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            selected_targets = st.multiselect("Acquisition Priority", options=target_options, default=target_options)
        with f_col2:
            selected_zoning = st.multiselect("Zoning District", options=zoning_options, default=zoning_options) if zoning_options else []
        with f_col3:
            search = st.text_input("Text Search (Address, Owner, Block):")

    # Apply filters
    filtered_df = df[df['Target Level'].isin(selected_targets)] if selected_targets else df
    if selected_zoning:
        filtered_df = filtered_df[filtered_df['Zoning'].isin(selected_zoning)]
    if search:
        search_mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
        filtered_df = filtered_df[search_mask]

    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.markdown("🟢 **High** | 🟠 **Medium** | 🔴 **Low**")
        
        if 'lat' in filtered_df.columns and 'lon' in filtered_df.columns:
            map_df = filtered_df.dropna(subset=['lat', 'lon'])
            
            if not map_df.empty:
                m = folium.Map(location=[40.6180, -74.4168], zoom_start=13, tiles="CartoDB positron")
                
                api_key = st.secrets.get("STREETVIEW_API_KEY", "")
                
                for _, row in map_df.iterrows():
                    address = row.get('Address', 'Unknown Address')
                    price = row.get('Last Sale Price', 'N/A')
                    color = row.get('Color', 'gray')
                    lat = row['lat']
                    lon = row['lon']
                    
                    if api_key:
                        image_url = f"https://maps.googleapis.com/maps/api/streetview?size=250x150&location={lat},{lon}&key={api_key}"
                        image_html = f'<img src="{image_url}" width="250" style="border-radius: 5px; margin-bottom: 8px;">'
                    else:
                        image_html = f'<img src="https://placehold.co/250x150/e2e8f0/475569?text=Street+View\\nImage" width="250" style="border-radius: 5px; margin-bottom: 8px;">'
                    
                    popup_html = f"""
                    <div style="width: 250px; font-family: sans-serif;">
                        {image_html}
                        <h4 style="margin: 0 0 5px 0; color: #1e293b; font-size: 16px;">{address}</h4>
                        <b>Block/Lot:</b> {row.get('Block')} / {row.get('Lot')}<br>
                        <b>Zoning:</b> {row.get('Zoning')}<br>
                        <b>Sale Price:</b> ${price}<br>
                        <b>City VA List:</b> {"✅ Yes" if row['On City List'] == "Yes" else "❌ No"}<br>
                        <br>
                        <a href="https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat},{lon}" target="_blank" style="background-color: #2563eb; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; display: inline-block; font-size: 12px;">Open in Street View</a>
                    </div>
                    """
                    
                    folium.CircleMarker(
                        location=[lat, lon],
                        radius=4, # Smaller, cleaner dots
                        color=color,
                        weight=1.5,
                        fill=True,
                        fill_color=color,
                        fill_opacity=0.8,
                        popup=folium.Popup(popup_html, max_width=260), # Narrower max_width to prevent cutoff
                        tooltip=f"{address} ({row['Target Level']})"
                    ).add_to(m)
                
                # returned_objects=[] completely stops the map from greying out when clicked
                st_folium(m, use_container_width=True, height=600, returned_objects=[])
            else:
                st.info("No properties found based on current filters.")
        else:
            st.info("Latitude and longitude coordinates are missing from the dataset.")

    with col2:
        # Pushing the table down slightly to align with the map
        st.markdown("<br>", unsafe_allow_html=True)
        display_df = filtered_df[['Block', 'Lot', 'Address', 'Target Level', 'On City List', 'Owner Address', 'Zoning', 'Last Sale Price']]
        
        st.dataframe(display_df, use_container_width=True, height=600)
