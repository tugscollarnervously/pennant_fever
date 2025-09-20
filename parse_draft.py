import pandas as pd

# Load the Excel file
file_path = r'C:\Users\vadim\Documents\Code\_pennant_race\draft.xlsx'  # Replace with the actual path to your file
df = pd.read_excel(file_path, sheet_name='Sheet1')

# Group by 'schoolDivision', 'school', and 'highLevel', then pivot to reshape the data
school_counts = df.groupby(['schoolDivision', 'school', 'highLevel']).size().reset_index(name='count')
pivot_table = school_counts.pivot(index=['schoolDivision', 'school'], columns='highLevel', values='count').fillna(0)

# Optionally, reorder columns based on the provided levels
pivot_table = pivot_table[['MLB', 'Indy', 'Intl', 'AAA', 'AA', 'A', 'A+', 'A-', 'Rk', 'NCAA', 'NAIA', 'JrCollege']]

# Reset index to turn multi-index columns into regular columns
pivot_table.reset_index(inplace=True)

# Save the result to a new Excel file or CSV (you can choose based on preference)
output_file =  r'C:\Users\vadim\Documents\Code\_pennant_race\school_highlevel_counts.xlsx'  # You can also save as CSV by changing the extension to .csv
pivot_table.to_excel(output_file)

print(f"Pivoted table of schools and high levels has been saved to {output_file}")
