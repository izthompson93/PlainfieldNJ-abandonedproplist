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

    # Load both datasets
    city_df = pd.read_csv(CITY_FILE)
    regrid_df = pd.read_csv(REGRID_FILE, low_memory=False)

    # Clean the Block and Lot columns in both files to create a unified matching key
    city_df['join_block'] = clean_id(city_df['Block'])
    city_df['join_lot'] = clean_id(city_df['Lot'])
    
    # Regrid typically uses lowercase column headers for block and lot
    if 'block' in regrid_df.columns and 'lot' in regrid_df.columns:
        regrid_df['join_block'] = clean_id(regrid_df['block'])
        regrid_df['join_lot'] = clean_id(regrid_df['lot'])
    else:
        print("Error: Regrid file is missing 'block' and 'lot' columns.")
        return

    # Perform a FULL OUTER JOIN to keep everything from both files
    master_df = pd.merge(
        city_df, 
        regrid_df, 
        on=['join_block', 'join_lot'], 
        how='outer', 
        suffixes=('_city', '_regrid')
    )

    # Drop the temporary join columns
    master_df = master_df.drop(columns=['join_block', 'join_lot'])

    # Save to a new master file
    master_df.to_csv(OUTPUT_FILE, index=False)
    print("Successfully created master_combined_database.csv")

if __name__ == "__main__":
    combine_data()
