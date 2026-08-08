import pandas as pd
import os

CITY_FILE = 'clt_property_database.csv'
REGRID_FILE = 'plainfield-vacancy_2.csv'
OUTPUT_FILE = 'master_combined_database.csv'

def clean_id(col):
    """Removes decimals, strips whitespace, and drops leading zeros for accurate matching."""
    return col.astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.lstrip('0')

def combine_data():
    if not os.path.exists(CITY_FILE) or not os.path.exists(REGRID_FILE):
        print("Missing one of the input files.")
        return

    city_df = pd.read_csv(CITY_FILE)
    regrid_df = pd.read_csv(REGRID_FILE, low_memory=False)

    # 1. Rename the Regrid columns to perfectly match the City headers so they combine seamlessly
    regrid_df = regrid_df.rename(columns={
        'block': 'Block',
        'lot': 'Lot',
        'address': 'Address',
        'owner': 'Owner Address',
        'zoning': 'Zoning',
        'saleprice': 'Last Sale Price',
        'sqft': 'Square Footage',
        'gisacre': 'Acreage',
        'yearbuilt': 'Year Built'
    })

    # 2. Create the unified index key for both dataframes
    city_df['join_idx'] = clean_id(city_df['Block']) + "_" + clean_id(city_df['Lot'])
    regrid_df['join_idx'] = clean_id(regrid_df['Block']) + "_" + clean_id(regrid_df['Lot'])

    city_df = city_df.set_index('join_idx')
    regrid_df = regrid_df.set_index('join_idx')

    # 3. Combine them! This fills missing City data with Regrid data without creating duplicate columns.
    master_df = city_df.combine_first(regrid_df).reset_index(drop=True)

    # 4. Save to a new master file
    master_df.to_csv(OUTPUT_FILE, index=False)
    print("Successfully created master_combined_database.csv")

if __name__ == "__main__":
    combine_data()
