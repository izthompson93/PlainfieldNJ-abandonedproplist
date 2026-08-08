import os
import csv
import time
import requests
import re

MUNICIPALITY_CODE = "2012"
INPUT_FILE = "properties.csv"
OUTPUT_FILE = "clt_property_database.csv"

def fetch_property_data():
    if not os.path.exists(INPUT_FILE):
        return

    headers = [
        "Block", "Lot", "Address", "Owner Address", "Taxes", "Last Sale Price", 
        "Square Footage", "Acreage", "Zoning", "Year Built", "lat", "lon"
    ]
    
    with open(OUTPUT_FILE, mode="w", newline="", encoding="utf-8") as out_file:
        writer = csv.writer(out_file)
        writer.writerow(headers)

        with open(INPUT_FILE, mode="r", encoding="utf-8-sig") as in_file:
            reader = csv.reader(in_file)
            
            for row in reader:
                if not row or len(row) < 2:
                    continue
                
                block = row[0].strip()
                lot = row[1].strip()
                if block.lower() == "block" or not block:
                    continue
                
                json_url = f"https://njparcels.com/api/v1.0/property/{MUNICIPALITY_CODE}_{block}_{lot}.json"
                html_url = f"https://njparcels.com/property/{MUNICIPALITY_CODE}/{block}/{lot}"
                print(f"Fetching Block {block}, Lot {lot}...")
                
                try:
                    json_resp = requests.get(json_url, headers={"User-Agent": "Mozilla/5.0"})
                    address, owner_address, taxes, sale_price, lat, lon = ["Unknown"] * 6
                    
                    if json_resp.status_code == 200:
                        data = json_resp.json()
                        if "features" in data and len(data["features"]) > 0:
                            feature = data["features"][0]
                            props = feature.get("properties", {})
                            address = props.get("property_location", "Unknown")
                            
                            owner_street = props.get("owner_address", "")
                            owner_city = props.get("owner_city", "")
                            owner_address = f"{owner_street}, {owner_city}".strip(', ')
                            taxes = props.get("taxes", "Unknown")
                            sale_price = props.get("sale_price", "Unknown")
                            
                            # Calculate the center lat/lon from the property polygon
                            geom = feature.get("geometry", {})
                            if geom and geom.get("type") == "MultiPolygon":
                                try:
                                    coords = geom["coordinates"][0][0]
                                    lon_val = sum(p[0] for p in coords) / len(coords)
                                    lat_val = sum(p[1] for p in coords) / len(coords)
                                    lon = str(round(lon_val, 6))
                                    lat = str(round(lat_val, 6))
                                except Exception:
                                    pass

                    html_resp = requests.get(html_url, headers={"User-Agent": "Mozilla/5.0"})
                    sqft, acreage, zoning, year_built = ["Unknown"] * 4

                    if html_resp.status_code == 200:
                        html_text = html_resp.text
                        sqft_match = re.search(r'Interior Space.*?<td>(.*?)</td>', html_text, re.IGNORECASE | re.DOTALL)
                        if sqft_match: sqft = sqft_match.group(1).strip()
                        acre_match = re.search(r'Acreage.*?<td>(.*?)</td>', html_text, re.IGNORECASE | re.DOTALL)
                        if acre_match: acreage = acre_match.group(1).strip()
                        year_match = re.search(r'Year Constructed.*?<td>(.*?)</td>', html_text, re.IGNORECASE | re.DOTALL)
                        if year_match: year_built = year_match.group(1).strip()
                        zone_match = re.search(r'within the <b>(.*?)</b> zone', html_text, re.IGNORECASE)
                        if zone_match: zoning = zone_match.group(1).strip()

                    writer.writerow([block, lot, address, owner_address, taxes, sale_price, sqft, acreage, zoning, year_built, lat, lon])
                        
                except Exception as e:
                    writer.writerow([block, lot, "Error"] + [""] * 9)
                
                time.sleep(1.5)

if __name__ == "__main__":
    fetch_property_data()
