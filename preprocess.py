# preprocess.py
import pandas as pd
import os

def preprocess_marketing_data(input_file='data/digital_marketing_campaigns_smes.csv'): # Assuming the CSV is in the root
    if not os.path.exists('assets'):
        os.makedirs('assets')
    
    print("Loading raw marketing data...")
    try:
        # --- POLISHED: Changed the default path for simplicity. ---
        # Make sure your raw CSV is named 'digital_marketing_campaign_smes.csv' in the project root.
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"ERROR: The file was not found at '{input_file}'. Please place it in the project's root directory.")
        return

    print("Cleaning and enriching data...")
    df.columns = [col.replace(' ', '_').replace('(', '').replace(')', '').lower() for col in df.columns]

    if 'company_size' in df.columns:
        print("Standardizing 'company_size' values...")
        # --- POLISHED: Made this mapping more robust and explicit. ---
        size_map = {
            'jan': '1-10',  # Catches the 'Jan' typo from the source data
            '10-jan': '1-10',
            'nov': '11-50', # Catches the 'Nov' typo
            '11-50': '11-50',
            '51-100': '51-100',
            '100+': '100+'
        }
        # Standardize by extracting known keys from the text
        df['company_size'] = df['company_size'].astype(str).str.lower().str.strip()
        df['company_size'] = df['company_size'].map(size_map)
        
        size_order = ['1-10', '11-50', '51-100', '100+']
        df['company_size'] = pd.Categorical(df['company_size'], categories=size_order, ordered=True)

    numeric_cols = ['ad_spend', 'duration_days', 'engagement_metric', 'conversion_rate', 'audience_reach']
    # Correcting column name based on typical CSV file. If your file has 'duration', change it back.
    if 'duration' in df.columns:
        df.rename(columns={'duration': 'duration_days'}, inplace=True)
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    if 'audience_reach' in df.columns:
        df['audience_reach'] = df['audience_reach'].round(0).astype(int)

    if 'audience_reach' in df.columns and 'conversion_rate' in df.columns:
        df['conversions'] = (df['audience_reach'] * (df['conversion_rate'] / 100)).round(0).astype(int)

    # --- CRITICAL FIX: Calculate Cost Per Engagement ---
    # We use .where() to avoid dividing by zero. If engagement is 0, cost is 0.
    if 'ad_spend' in df.columns and 'engagement_metric' in df.columns:
        print("Calculating 'cost_per_engagement'...")
        df['cost_per_engagement'] = (df['ad_spend'] / df['engagement_metric']).where(df['engagement_metric'] > 0, 0)

    output_path = 'assets/marketing_data.parquet'
    print(f"Saving processed data to '{output_path}'...")
    df.to_parquet(output_path, index=False)
    print("Pre-processing complete!")

if __name__ == '__main__':
    # Make sure you have your CSV file named correctly and in the right place.
    preprocess_marketing_data('data/digital_marketing_campaigns_smes.CSV')