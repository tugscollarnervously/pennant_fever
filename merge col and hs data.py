import pandas as pd
import re

# Load the data from your Excel file
xls = pd.ExcelFile('school_highlevel_counts_new.xlsx')

# Load the sheets
hs_df = pd.read_excel(xls, sheet_name='HS')
counts_hs_df = pd.read_excel(xls, sheet_name='counts_hs')
col_df = pd.read_excel(xls, sheet_name='COL')
counts_col_df = pd.read_excel(xls, sheet_name='counts_col')

# Helper function to extract school name, city, and state from 'School (City, State)' format
def extract_school_city_state(school_name):
    match = re.match(r'(.+?)\s*\((.+),([A-Z]{2})\)', school_name)
    if match:
        return match.group(1).strip(), match.group(2).strip(), match.group(3).strip()
    return None, None, None

# Apply extraction to the counts_hs data
counts_hs_df['parsed_school'], counts_hs_df['parsed_city'], counts_hs_df['parsed_state'] = zip(
    *counts_hs_df['school_name'].apply(extract_school_city_state))

# Function to merge counts data into HS
def merge_hs_counts(hs_df, counts_hs_df):
    merged_hs_df = hs_df.copy()
    
    for idx, counts_row in counts_hs_df.iterrows():
        counts_school = counts_row['parsed_school']
        counts_city = counts_row['parsed_city']
        counts_state = counts_row['parsed_state']
        
        # Ensure the school name is a string
        if isinstance(counts_school, str):
            # Find matching rows in HS based on city, state, and partial school name
            matched_rows = merged_hs_df[
                (merged_hs_df['city'] == counts_city) &
                (merged_hs_df['state'] == counts_state) &
                (merged_hs_df['school_name'].str.contains(counts_school, case=False, na=False))
            ]
            
            # Append the counts_hs data to the matched HS rows
            if not matched_rows.empty:
                for match_idx in matched_rows.index:
                    # Append counts data to HS row
                    merged_hs_df.loc[match_idx, 'MLB':'Total'] = counts_row['MLB':'Total']
                    merged_hs_df.loc[match_idx, 'matched_school_name'] = counts_row['school_name']
    
    return merged_hs_df

# Merge high school data
merged_hs_df = merge_hs_counts(hs_df, counts_hs_df)

# Function to merge counts data into COL
def merge_col_counts(col_df, counts_col_df):
    merged_col_df = pd.merge(col_df, counts_col_df, how='left', on='school_name', suffixes=('', '_counts'))
    return merged_col_df

# Merge college data
merged_col_df = merge_col_counts(col_df, counts_col_df)

# Save the results to new Excel files
with pd.ExcelWriter('merged_school_data.xlsx') as writer:
    merged_col_df.to_excel(writer, sheet_name='COL', index=False)
    merged_hs_df.to_excel(writer, sheet_name='HS', index=False)

print("Merging complete! Results saved to 'merged_school_data.xlsx'")
