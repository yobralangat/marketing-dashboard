# insights_generator.py (Final Version with Context-Aware Prompts)
import os
import pandas as pd
import google.generativeai as genai

# Initialization (Unchanged)
try:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    gemini_enabled = True
    print("--- AI Engine: Gemini client initialized successfully. ---")
except Exception as e:
    print(f"--- AI Engine WARNING: Gemini client failed. AI insights disabled. Error: {e}")
    gemini_enabled = False

def get_ai_summary(prompt_text):
    if not gemini_enabled:
        return "AI insights are currently unavailable. Please check API key."
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt_text)
        return response.text
    except Exception as e:
        return f"An error occurred: {e}"

# --- Other prompt functions are unchanged, they are solid ---
def generate_overview_insights(filtered_df):
    if filtered_df.empty: return "Not enough data for an overview analysis."
    total_reach = filtered_df['audience_reach'].sum()
    total_engagement = filtered_df['engagement_metric'].sum()
    total_conversions = filtered_df['conversions'].sum()
    reach_to_engagement_rate = (total_engagement / total_reach * 100) if total_reach > 0 else 0
    engagement_to_conversion_rate = (total_conversions / total_engagement * 100) if total_engagement > 0 else 0
    prompt = f"""
    You are a top-tier marketing strategist providing a concise summary for a busy executive.
    Analyze the following marketing funnel performance. All numbers are totals for the selected period.
    - **Audience Reached:** {total_reach:,.0f}
    - **Engagements:** {total_engagement:,.0f}
    - **Conversions:** {total_conversions:,.0f}
    Based on this data, provide a summary using the following Markdown format:
    **Headline Insight:** (A single, impactful sentence identifying the funnel's primary issue).
    **Key Diagnosis:**
    * **Top-of-Funnel Efficiency:** The conversion rate from Reach to Engagement is **{reach_to_engagement_rate:.2f}%**.
    * **Mid-Funnel Efficiency:** The conversion rate from Engagement to Conversion is **{engagement_to_conversion_rate:.2f}%**.
    * **Primary Bottleneck:** (State which of the two stages above is the biggest problem).
    **Actionable Recommendation:**
    * **Next Step:** (Provide one clear, strategic action to fix the primary bottleneck. Be specific—e.g., "Review ad creative for audience mismatch" or "Optimize landing page to reduce friction").
    """
    return get_ai_summary(prompt)

def generate_channel_insights(filtered_df):
    if filtered_df.empty: return "Not enough channel data to analyze."
    channel_performance = filtered_df.groupby('marketing_channel').agg(total_spend=('ad_spend', 'sum'), avg_cvr=('conversion_rate', 'mean'), avg_cpc=('cost_per_conversion', 'mean')).round(2).sort_values('avg_cpc', ascending=True)
    data_summary = channel_performance.to_string()
    prompt = f"""
    You are a top-tier marketing strategist summarizing channel performance for an executive.
    Here is the data, showing total spend, average conversion rate (CVR), and average cost per conversion (CPC).
    ```
    {data_summary}
    ```
    Provide a summary in the following Markdown format:
    **Performance Summary:**
    * **Top Performer (Workhorse):** Identify the channel with the best combination of low CPC and high CVR. Explain why it's effective.
    * **Top Spender:** Identify the channel with the highest `total_spend`.
    * **Underperformer (Money Pit):** Identify the channel with the worst combination of high CPC and low CVR.
    **Strategic Recommendation:**
    * **Budget Action:** Based on the data, recommend a specific budget shift. For example: "Consider reallocating 15% of the budget from [Underperformer] to [Top Performer] to maximize ROI."
    """
    return get_ai_summary(prompt)

def generate_audience_insights(filtered_df):
    if filtered_df.empty: return "Not enough audience data to analyze."
    audience_cvr = filtered_df.groupby('target_audience')['conversion_rate'].mean().sort_values(ascending=False)
    device_cvr = filtered_df.groupby('device')['conversion_rate'].mean().sort_values(ascending=False)
    top_audience_segment = f"'{audience_cvr.index[0]}'" if not audience_cvr.empty else "N/A"
    top_device_type = f"'{device_cvr.index[0]}'" if not device_cvr.empty else "N/A"
    prompt = f"""
    You are a top-tier marketing strategist identifying the most valuable customer segments for an executive.
    Performance data shows:
    - The highest-converting audience segment is **{top_audience_segment}**.
    - The highest-converting device type is **{top_device_type}**.
    Provide a summary in the following Markdown format:
    **Core Insight:**
    * **Golden Customer Profile:** Our most valuable customers are clearly the **{top_audience_segment}** demographic using a **{top_device_type}** device.
    **Actionable Recommendations:**
    * **Targeting:** Double-down on this profile. Create dedicated campaigns with creative and messaging that speaks directly to the {top_audience_segment} audience.
    * **Optimization:** Investigate why other devices are underperforming for this key audience. Is the user experience on other platforms poor?
    """
    return get_ai_summary(prompt)


# --- THIS IS THE NEW, SMARTER PROMPT LOGIC ---
def generate_geo_insights(filtered_df):
    if filtered_df.empty: return "Not enough geographic data to analyze."
    geo_perf = filtered_df.groupby('region').agg(
        total_spend=('ad_spend', 'sum'), avg_cpc=('cost_per_conversion', 'mean')
    ).round(2)
    
    # Check for empty or all-zero CPCs to avoid errors
    if geo_perf.empty or (geo_perf['avg_cpc'] <= 0).all():
        return "Could not determine an efficient region from the available data."

    # Find the top regions
    highest_spend_region = geo_perf['total_spend'].idxmax()
    most_efficient_region = geo_perf[geo_perf['avg_cpc'] > 0]['avg_cpc'].idxmin()

    # Dynamic prompt creation based on the data
    if highest_spend_region == most_efficient_region:
        # Scenario 1: Budget and efficiency are ALIGNED
        recommendation_prompt = f"""
        **Strategic Alignment:**
        * Our budget is correctly aligned with performance. Our highest spend is in **{highest_spend_region}**, which is also our most efficient region (lowest CPC). This indicates a successful strategy in this market.

        **Action Plan:**
        * **Phase 1 (Capitalize):** Propose a 15% budget increase for **{highest_spend_region}** to determine the point of market saturation. We need to find out how much more we can invest before efficiency drops.
        * **Phase 2 (Replicate):** Task the regional team for **{highest_spend_region}** to create a "success playbook." The goal is to analyze what makes this region so effective and apply those learnings to underperforming regions.
        """
    else:
        # Scenario 2: Budget and efficiency are MISMATCHED
        recommendation_prompt = f"""
        **Strategic Mismatch:**
        * Our budget is currently misaligned with performance. We spend the most in **{highest_spend_region}**, but our best ROI comes from **{most_efficient_region}**.

        **Action Plan:**
        * **Phase 1 (Test):** Immediately pilot a 10% budget reallocation from **{highest_spend_region}** to **{most_efficient_region}**. The goal is to confirm if the lower CPC in {most_efficient_region} can be maintained with an increased spend.
        * **Phase 2 (Scale):** If the pilot is successful, we will develop a plan for a larger-scale budget shift to maximize our global return on investment.
        """
        
    # Final combined prompt
    prompt = f"""
    You are a Chief Marketing Officer (CMO) reporting to your CEO. Be direct, concise, and strategic.
    {recommendation_prompt}
    """
    return get_ai_summary(prompt)