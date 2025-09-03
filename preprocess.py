import pandas as pd
import os

def preprocess_marketing_data(input_file='data/digital_marketing_campaigns_smes.CSV'):
    if not os.path.exists('assets'):
        os.makedirs('assets')
    
    print("Loading raw marketing data...")
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"ERROR: The file was not found at '{input_file}'. Please check the path.")
        return

    print("Cleaning and enriching data...")
    df.columns = [col.replace(' ', '_').replace('(', '').replace(')', '').lower() for col in df.columns]

    if 'company_size' in df.columns:
        print("Standardizing 'company_size' values...")
        size_col = df['company_size'].astype(str).str.lower().str.strip()
        cond_1_10 = size_col.str.contains('jan', na=False)
        cond_11_50 = size_col.str.contains('nov', na=False) | size_col.str.contains('11-50', na=False)
        cond_51_100 = size_col.str.contains('51-100', na=False)
        cond_100_plus = size_col.str.contains('100\+', na=False)
        
        df.loc[cond_1_10, 'company_size'] = '1-10'
        df.loc[cond_11_50, 'company_size'] = '11-50'
        df.loc[cond_51_100, 'company_size'] = '51-100'
        df.loc[cond_100_plus, 'company_size'] = '100+'
        
        size_order = ['1-10', '11-50', '51-100', '100+']
        df['company_size'] = pd.Categorical(df['company_size'], categories=size_order, ordered=True)

    if 'success' in df.columns:
        df['success_status'] = df['success'].apply(lambda x: 'Successful' if x == 1 else 'Unsuccessful')

    numeric_cols = ['ad_spend', 'duration', 'engagement_metric', 'conversion_rate', 'audience_reach']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    if 'audience_reach' in df.columns:
        df['audience_reach'] = df['audience_reach'].round(0).astype(int)

    if 'audience_reach' in df.columns and 'conversion_rate' in df.columns:
        df['conversions'] = (df['audience_reach'] * (df['conversion_rate'] / 100)).astype(int)

    output_path = 'assets/marketing_data.parquet'
    print(f"Saving processed data to '{output_path}'...")
    df.to_parquet(output_path)
    print("Pre-processing complete!")

if __name__ == '__main__':
    preprocess_marketing_data()