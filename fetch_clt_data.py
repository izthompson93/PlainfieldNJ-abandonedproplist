import os
import csv
import time
import requests

MUNICIPALITY_CODE = "2012"  # Plainfield City Code
INPUT_FILE = "properties.csv"
OUTPUT_FILE = "clt_property_database.csv"

def fetch_property_data():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    headers = [
        "Block", "Lot", "Address", "Property Class", 
        "Square Footage", "Acreage", "Zoning District", "Year Built"
    ]
    
    with open(OUTPUT_FILE, mode="w", newline="", encoding="utf-8") as out_file:
        writer = csv.writer(out_file)
        writer.writerow(headers)

        # 'utf-8-sig' safely handles invisible formatting characters from Excel/Windows
        with open(INPUT_FILE, mode="r", encoding="utf-8-sig") as in_file:
            reader = csv.reader(in_file)
            
            for row in reader:
                # Skip completely empty rows
                if not row or len(row) < 2:
                    continue
                
                block = row[0].strip()
                lot = row[1].strip()
                
                # Skip the header row if it exists in the CSV
                if block.lower() == "block" or not block:
                    continue
                
                url = f"https://njparcels.com/api/v1.0/property/{MUNICIPALITY_CODE}_{block}_{lot}.json"
                print(f"Fetching Block {block}, Lot {lot}...")
                
                try:
                    response = requests.get(url, headers={"User-Agent": "CLTDataBot/1.0"})
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Handle potential structural variations in JSON payloads
                        if "properties" in data:
                            props = data["properties"]
                        elif "features" in data and len(data["features"]) > 0:
                            props = data["features"][0].get("properties", {})
                        else:
                            props = data
                        
                        # Extract metrics
                        address = props.get("address", props.get("addr1", "Unknown"))
                        prop_class = props.get("class", "Unknown")
                        sqft = props.get("sqft", props.get("inside_space", "Unknown"))
                        acres = props.get("acres", props.get("acreage", "Unknown"))
                        zoning = props.get("zoning", "Unknown")
                        year_built = props.get("year_built", props.get("year_constructed", "Unknown"))
                        
                        writer.writerow([block, lot, address, prop_class, sqft, acres, zoning, year_built])
                    else:
                        print(f"Skipped Block {block}, Lot {lot} (HTTP Status {response.status_code})")
                        writer.writerow([block, lot, f"API Error {response.status_code}", "", "", "", "", ""])
                        
                except Exception as e:
                    print(f"Error parsing Block {block}, Lot {lot}: {e}")
                    writer.writerow([block, lot, "Error Parsing", "", "", "", "", ""])
                
                # Respect server rate limits
                time.sleep(1.5)

if __name__ == "__main__":
    fetch_property_data()
