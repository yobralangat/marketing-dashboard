# preprocess.py (Final Version with Integer Reach)
import pandas as pd
import os

def preprocess_marketing_data(input_file='data/digital_marketing_campaigns_smes.CSV'):
    """
    Loads raw data, robustly cleans all columns, enriches the data with KPIs,
    and saves a clean file with correct data types for the dashboard.
    """
    if not os.path.exists('assets'):
        os.makedirs('assets')
    
    print("-> Loading raw marketing data...")
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"FATAL ERROR: Raw data file not found at '{input_file}'. Please place it in the project root.")
        return

    print("-> Standardizing all column names to lowercase with underscores...")
    df.columns = [col.replace(' ', '_').replace('(', '').replace(')', '').lower() for col in df.columns]

    print("-> Cleaning 'company_size' column based on actual raw values...")
    raw_size_col = df['company_size'].astype(str).str.lower()
    cond_1_10   = raw_size_col.str.contains('jan', na=False)
    cond_11_50  = raw_size_col.str.contains('nov', na=False)
    cond_51_100 = raw_size_col.str.contains('51-100', na=False)
    cond_100_plus = raw_size_col.str.contains('100\+', na=False)
    df.loc[cond_1_10, 'company_size_clean'] = '1-10'
    df.loc[cond_11_50, 'company_size_clean'] = '11-50'
    df.loc[cond_51_100, 'company_size_clean'] = '51-100'
    df.loc[cond_100_plus, 'company_size_clean'] = '100+'
    df = df.drop(columns=['company_size'])
    df = df.rename(columns={'company_size_clean': 'company_size'})
    size_order = ['1-10', '11-50', '51-100', '100+']
    df['company_size'] = pd.Categorical(df['company_size'], categories=size_order, ordered=True)
    print("-> 'company_size' column has been successfully cleaned and standardized.")

    print("-> Cleaning and typing other columns...")
    numeric_cols = ['ad_spend', 'duration_days', 'engagement_metric', 'conversion_rate', 'audience_reach']
    if 'duration' in df.columns:
         df.rename(columns={'duration': 'duration_days'}, inplace=True)
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # --- THIS IS THE FIX ---
    # After all cleaning, we explicitly cast 'audience_reach' to a whole number (integer).
    if 'audience_reach' in df.columns:
        df['audience_reach'] = df['audience_reach'].astype(int)
        print("-> Confirmed 'audience_reach' is now an integer.")

    print("-> Engineering new KPIs...")
    df['conversions'] = (df['audience_reach'] * (df['conversion_rate'] / 100)).round(0).astype(int)
    df['cost_per_engagement'] = (df['ad_spend'] / df['engagement_metric']).where(df['engagement_metric'] > 0, 0).round(2)
    df['cost_per_conversion'] = (df['ad_spend'] / df['conversions']).where(df['conversions'] > 0, 0).round(2)

    output_path = 'assets/marketing_data.parquet'
    print(f"-> Saving final, clean data to '{output_path}'...")
    df.to_parquet(output_path, index=False)
    print("\nPre-processing is complete and your data is ready for the dashboard!")

if __name__ == '__main__':
    preprocess_marketing_data()