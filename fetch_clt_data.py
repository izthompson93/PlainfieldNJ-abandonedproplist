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
        print(f"Error: {INPUT_FILE} not found.")
        return

    # Updated headers to capture the new financial data from the JSON + physical data from the HTML
    headers = [
        "Block", "Lot", "Address", "Owner Address", "Taxes", "Last Sale Price", 
        "Square Footage", "Acreage", "Zoning", "Year Built"
    ]
    
    with open(OUTPUT_FILE, mode="w", newline="", encoding="utf-8") as out_file:
        writer = csv.writer(out_file)
        writer.writerow(headers)

        with open(INPUT_FILE, mode="r", encoding="utf-8-sig") as in_file:
            reader = csv.reader(in_file)
            
            for row in reader:
                # Skip empty rows
                if not row or len(row) < 2:
                    continue
                
                block = row[0].strip()
                lot = row[1].strip()
                
                # Skip header row
                if block.lower() == "block" or not block:
                    continue
                
                json_url = f"https://njparcels.com/api/v1.0/property/{MUNICIPALITY_CODE}_{block}_{lot}.json"
                html_url = f"https://njparcels.com/property/{MUNICIPALITY_CODE}/{block}/{lot}"
                
                print(f"Fetching Block {block}, Lot {lot}...")
                
                try:
                    # 1. Pull Owner & Tax Data from the JSON API
                    json_resp = requests.get(json_url, headers={"User-Agent": "Mozilla/5.0"})
                    
                    address = "Unknown"
                    owner_address = "Unknown"
                    taxes = "Unknown"
                    sale_price = "Unknown"
                    
                    if json_resp.status_code == 200:
                        data = json_resp.json()
                        if "features" in data and len(data["features"]) > 0:
                            props = data["features"][0].get("properties", {})
                            address = props.get("property_location", "Unknown")
                            
                            # Combine owner city/zip for a complete mailing address
                            owner_street = props.get("owner_address", "")
                            owner_city = props.get("owner_city", "")
                            owner_address = f"{owner_street}, {owner_city}".strip(', ')
                            
                            taxes = props.get("taxes", "Unknown")
                            sale_price = props.get("sale_price", "Unknown")

                    # 2. Pull Physical Data directly from the HTML page
                    html_resp = requests.get(html_url, headers={"User-Agent": "Mozilla/5.0"})
                    
                    sqft = "Unknown"
                    acreage = "Unknown"
                    zoning = "Unknown"
                    year_built = "Unknown"

                    if html_resp.status_code == 200:
                        html_text = html_resp.text
                        
                        # Use Regular Expressions to hunt down the exact table values in the HTML
                        sqft_match = re.search(r'Interior Space.*?<td>(.*?)</td>', html_text, re.IGNORECASE | re.DOTALL)
                        if sqft_match: sqft = sqft_match.group(1).strip()
                            
                        acre_match = re.search(r'Acreage.*?<td>(.*?)</td>', html_text, re.IGNORECASE | re.DOTALL)
                        if acre_match: acreage = acre_match.group(1).strip()
                            
                        year_match = re.search(r'Year Constructed.*?<td>(.*?)</td>', html_text, re.IGNORECASE | re.DOTALL)
                        if year_match: year_built = year_match.group(1).strip()
                            
                        zone_match = re.search(r'within the <b>(.*?)</b> zone', html_text, re.IGNORECASE)
                        if zone_match: zoning = zone_match.group(1).strip()

                    # Write the fully compiled row to the CSV
                    writer.writerow([block, lot, address, owner_address, taxes, sale_price, sqft, acreage, zoning, year_built])
                        
                except Exception as e:
                    print(f"Error parsing Block {block}, Lot {lot}: {e}")
                    writer.writerow([block, lot, "Error", "Error", "Error", "Error", "Error", "Error", "Error", "Error"])
                
                # 1.5 second delay to avoid getting IP blocked by the server
                time.sleep(1.5)

if __name__ == "__main__":
    fetch_property_data()
