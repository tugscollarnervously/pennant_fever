import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split

# need to have the ballpark factors match the dimensions more closely
# have a pre-generation  option to make symnmetric ballparks

# Load the data
df = pd.read_csv(r'E:\_totalbaseball\team generation\ballpark_data.csv')

# Filter relevant columns for dimensions, fence heights, and park factors
dimension_columns = ['LL', 'LF', 'LC', 'CF', 'RC', 'RF', 'RL']
fence_height_columns = ['LL_height', 'LF_height', 'LC_height', 'CF_height', 'RC_height', 'RF_height', 'RL_height']
park_factor_columns = ['LBA', 'RBA', '2B', '3B', 'LHR', 'RHR']

# Calculate mean and standard deviation for relevant columns, considering only positive values for fence heights
dimension_means = df[dimension_columns].mean()
dimension_std_devs = df[dimension_columns].std()

# Ensure we only calculate stats for positive fence heights
fence_height_means = df[fence_height_columns][df[fence_height_columns] > 0].mean()
fence_height_std_devs = df[fence_height_columns][df[fence_height_columns] > 0].std()

# Combine the means and standard deviations
means = pd.concat([dimension_means, fence_height_means])
std_devs = pd.concat([dimension_std_devs, fence_height_std_devs])

print("Means:\n", means)
print("Standard Deviations:\n", std_devs)

# Prepare the data for training
X = df[dimension_columns + fence_height_columns]
y = df[park_factor_columns]

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train a linear regression model for each park factor
models = {}
for column in park_factor_columns:
    model = LinearRegression()
    model.fit(X_train, y_train[column])
    models[column] = model

def generate_synthetic_ballpark(means, std_devs, models, num_samples=1):
    synthetic_data = {}
    for column in means.index:
        synthetic_data[column] = np.random.normal(loc=means[column], scale=std_devs[column], size=num_samples)
    
    synthetic_df = pd.DataFrame(synthetic_data)
    
    # Generate correlated fence heights based on dimensions
    for index, row in synthetic_df.iterrows():
        base_height = np.random.randint(8, 15)  # Random base height between observed ranges
        fence_heights = [base_height] * len(fence_height_columns)  # Initialize all fence heights to the base height
        
        # Introduce occasional height changes
        change_points = np.random.choice(len(fence_height_columns), size=np.random.randint(1, 4), replace=False)
        for change_point in change_points:
            new_height = base_height + np.random.choice([-2, -1, 1, 2])  # Change height by +/- 1 or 2
            fence_heights[change_point:] = [max(new_height, 3)] * (len(fence_height_columns) - change_point)
        
        # Occasionally generate higher fence heights
        if np.random.rand() > 0.95:
            high_fence_index = np.random.randint(0, len(fence_height_columns))
            fence_heights[high_fence_index] = np.random.randint(15, 21)
        
        # Rarely generate extreme fence heights (over 20 feet)
        eligible_dimensions = [i for i, dim in enumerate(synthetic_df.loc[index, dimension_columns]) if dim <= 335]
        if eligible_dimensions:
            if np.random.rand() > 0.99:
                extreme_fence_indices = []
                extreme_fence_height = np.random.randint(21, 39)
                
                # Select one or more eligible dimensions for extreme fence heights
                num_extreme_fences = np.random.randint(1, min(3, len(eligible_dimensions) + 1))
                extreme_fence_indices = np.random.choice(eligible_dimensions, size=num_extreme_fences, replace=False)
                
                # Assign extreme fence heights and propagate to neighboring dimensions
                for extreme_index in extreme_fence_indices:
                    fence_heights[extreme_index] = extreme_fence_height
                    if np.random.rand() > 0.5:  # 50% chance to propagate to neighbors
                        neighbors = [extreme_index - 1, extreme_index + 1]
                        for neighbor in neighbors:
                            if 0 <= neighbor < len(fence_heights):
                                fence_heights[neighbor] = extreme_fence_height
        
        for i, col in enumerate(fence_height_columns):
            synthetic_df.at[index, col] = fence_heights[i]
    
    # Predict park factors based on generated dimensions and fence heights
    for column in park_factor_columns:
        synthetic_df[column] = models[column].predict(synthetic_df[dimension_columns + fence_height_columns])
    
    return synthetic_df

# Generate synthetic ballparks
synthetic_ballparks = generate_synthetic_ballpark(means, std_devs, models, num_samples=100)

# Save to Excel for verification
output_file = 'synthetic_ballparks_v7.xlsx'
synthetic_ballparks.to_excel(output_file, index=False)
print(f"Synthetic ballpark data saved to {output_file}")