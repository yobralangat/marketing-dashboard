import os
import pandas as pd
import google.generativeai as genai

try:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    gemini_enabled = True
    print("Gemini AI client initialized successfully.")
except Exception as e:
    print(f"WARNING: Gemini AI client could not be initialized. AI insights will be disabled. Error: {e}")
    gemini_enabled = False

def get_ai_summary(prompt_text):
    if not gemini_enabled:
        return "AI insights are currently unavailable. Please check your API key configuration."
    try:
        print("--- INSIGHTS: Sending prompt to Gemini API... ---")
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        safety_settings = [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
        response = model.generate_content(prompt_text, safety_settings=safety_settings)
        print("--- INSIGHTS: Successfully received response from Gemini. ---")
        return response.text
    except Exception as e:
        print(f"--- INSIGHTS ERROR: Gemini API call failed. {e} ---")
        return "An error occurred while generating AI insights. Please check the server logs."

def generate_overview_insights(filtered_df):
    total_reach = filtered_df['audience_reach'].sum()
    total_engagement = filtered_df['engagement_metric'].sum()
    total_conversions = filtered_df.get('conversions', 0).sum()
    reach_to_engagement_rate = (total_engagement / total_reach * 100) if total_reach > 0 else 0
    engagement_to_conversion_rate = (total_conversions / total_engagement * 100) if total_engagement > 0 else 0
    prompt = f"""
    You are a senior marketing analyst interpreting a marketing funnel for a client. Your tone is professional and insightful. Use Markdown for formatting.
    Funnel data: Audience Reached: {total_reach:,}, Engagements: {total_engagement:,}, Final Conversions: {total_conversions:,}.
    Based on this, provide 2-3 bullet points of analysis:
    1. State the conversion rate from Reach to Engagement ({reach_to_engagement_rate:.2f}%).
    2. State the conversion rate from Engagement to Final Conversion ({engagement_to_conversion_rate:.2f}%).
    3. Identify the biggest "drop-off" point and provide one clear, strategic recommendation to improve it.
    """
    return get_ai_summary(prompt)

def generate_channel_insights(filtered_df):
    channel_performance = filtered_df.groupby('marketing_channel').agg(total_spend=('ad_spend', 'sum'), avg_cvr=('conversion_rate', 'mean'), avg_cpe=('cost_per_engagement', 'mean')).round(2)
    if channel_performance.empty or len(channel_performance) < 2: return "Not enough distinct channel data to perform a comparative analysis."
    data_summary_string = channel_performance.to_string()
    prompt = f"""
    You are a senior marketing analyst. Here is channel performance data:
    ```
    {data_summary_string}
    ```
    Provide 2-3 bullet points of actionable advice using Markdown.
    - Identify the top-performing channel and explain WHY (high avg_cvr, low avg_cpe).
    - Identify the worst-performing channel and explain WHY.
    - Provide a clear, strategic recommendation for budget allocation.
    """
    return get_ai_summary(prompt)

def generate_audience_insights(filtered_df):
    if filtered_df.empty: return "Not enough data to analyze audience performance."
    audience_cvr = filtered_df.groupby('target_audience')['conversion_rate'].mean().sort_values(ascending=False)
    device_cvr = filtered_df.groupby('device')['conversion_rate'].mean().sort_values(ascending=False)
    best_audience = audience_cvr.index[0] if not audience_cvr.empty else "N/A"
    best_device = device_cvr.index[0] if not device_cvr.empty else "N/A"
    prompt = f"""
    You are a senior marketing analyst. Here is audience performance data:
    - Best-performing target audience: '{best_audience}' ({audience_cvr.iloc[0]:.2f}% CVR).
    - Best-performing device: '{best_device}' ({device_cvr.iloc[0]:.2f}% CVR).
    Based on this, provide 2-3 bullet points of strategic advice on where to focus targeting efforts.
    """
    return get_ai_summary(prompt)