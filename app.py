import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import os

st.set_page_config(page_title="Plainfield CLT Property Tracker", layout="wide", initial_sidebar_state="collapsed")

st.title("Community Land Trust Parcel Tracker")
st.markdown("Live spatial data on vacant and abandoned properties targeted for community acquisition in Plainfield, NJ.")

def clean_id(col):
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

    with st.expander("🔍 Filter & Search Properties", expanded=False):
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            selected_targets = st.multiselect("Acquisition Priority", options=target_options, default=target_options)
        with f_col2:
            selected_zoning = st.multiselect("Zoning District", options=zoning_options, default=zoning_options) if zoning_options else []
        with f_col3:
            search = st.text_input("Text Search (Address, Owner, Block):")
            
        # The new Empty Lot filter toggle
        empty_lot_filter = st.checkbox("🌳 Show Only Truly Empty Lots (Grass, Dirt, or Parking Lots)")

    # Apply base filters
    filtered_df = df[df['Target Level'].isin(selected_targets)] if selected_targets else df
    if selected_zoning:
        filtered_df = filtered_df[filtered_df['Zoning'].isin(selected_zoning)]
    if search:
        search_mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
        filtered_df = filtered_df[search_mask]
        
    # Apply the Empty Lot logic if checked
    if empty_lot_filter:
        # Check if the columns exist to prevent errors
        usecode_col = 'usecode' if 'usecode' in filtered_df.columns else ''
        desc_col = 'building_desc' if 'building_desc' in filtered_df.columns else ''
        
        if usecode_col and desc_col:
            # Class 1 = Vacant Land in NJ, or descriptions containing parking/vacant
            is_class_1 = filtered_df[usecode_col].astype(str).str.strip() == '1'
            is_vacant_desc = filtered_df[desc_col].astype(str).str.contains('VACANT|PARKING|PAV', case=False, na=False)
            filtered_df = filtered_df[is_class_1 | is_vacant_desc]
        else:
            st.warning("Cannot filter by empty lots: missing 'usecode' or 'building_desc' columns from Regrid data.")

    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.markdown("🟢 **High** | 🟠 **Medium** | 🔴 **Low**")
        
        if 'lat' in filtered_df.columns and 'lon' in filtered_df.columns:
            map_df = filtered_df.dropna(subset=['lat', 'lon'])
            
            if not map_df.empty:
                m = folium.Map(location=[40.6180, -74.4168], zoom_start=14, tiles="CartoDB positron")
                
                api_key = st.secrets.get("STREETVIEW_API_KEY", "")
                
                for _, row in map_df.iterrows():
                    address = row.get('Address', 'Unknown Address')
                    price = row.get('Last Sale Price', 'N/A')
                    color = row.get('Color', 'gray')
                    lat = row['lat']
                    lon = row['lon']
                    
                    # Fetch structure description if available to show in popup
                    struct_desc = str(row.get('building_desc', 'N/A')).title()
                    if struct_desc == 'Nan': struct_desc = 'Unknown'
                    
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
                        <b>Status:</b> {struct_desc}<br>
                        <b>Zoning:</b> {row.get('Zoning')}<br>
                        <b>Sale Price:</b> ${price}<br>
                        <b>City VA List:</b> {"✅ Yes" if row['On City List'] == "Yes" else "❌ No"}<br>
                        <br>
                        <a href="https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat},{lon}" target="_blank" style="background-color: #2563eb; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; display: inline-block; font-size: 12px;">Open in Street View</a>
                    </div>
                    """
                    
                    folium.CircleMarker(
                        location=[lat, lon],
                        radius=4,
                        color=color,
                        weight=1.5,
                        fill=True,
                        fill_color=color,
                        fill_opacity=0.8,
                        popup=folium.Popup(popup_html, max_width=260),
                        tooltip=f"{address} ({row['Target Level']})"
                    ).add_to(m)
                
                st_folium(m, use_container_width=True, height=600, returned_objects=[])
            else:
                st.info("No properties found based on current filters.")
        else:
            st.info("Latitude and longitude coordinates are missing from the dataset.")

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        # Added building_desc to the table view so you can see if it's parking, grass, etc.
        display_cols = ['Block', 'Lot', 'Address', 'Target Level', 'On City List', 'Owner Address', 'Zoning', 'Last Sale Price']
        if 'building_desc' in filtered_df.columns:
            display_cols.insert(3, 'building_desc')
            
        display_df = filtered_df[display_cols].copy()
        if 'building_desc' in display_df.columns:
            display_df = display_df.rename(columns={'building_desc': 'Property Type'})
            
        st.dataframe(display_df, use_container_width=True, height=600)
