import pandas as pd
import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
from dotenv import load_dotenv

# Import the AI insight generator functions
from insights_generator import generate_overview_insights, generate_channel_insights, generate_audience_insights

# --- Configuration & Setup ---
load_dotenv()
APP_THEME = dbc.themes.LUX

# --- Load the FAST Pre-processed Data ---
try:
    df = pd.read_parquet('assets/marketing_data.parquet')
    print("--- APP: Pre-processed Parquet file loaded successfully. ---")
except FileNotFoundError:
    print("--- APP FATAL ERROR: Processed data file not found. Please run 'preprocess.py' first. ---")
    exit()

# --- Initialize the Dash App ---
app = dash.Dash(__name__, external_stylesheets=[APP_THEME], suppress_callback_exceptions=True)
server = app.server
print("--- APP: Dash app initialized. ---")

# --- App Layout ---
app.layout = html.Div(className="bg-light", style={'minHeight': '100vh'}, children=[
    dbc.Container([
        # Header
        dbc.Row([
            dbc.Col(html.H1("Marketing Strategy Dashboard", className="text-primary"), md=6),
            dbc.Col([
                dbc.Label("Filter by Industry"),
                dcc.Dropdown(
                    id='industry-filter',
                    options=[{'label': i, 'value': i} for i in sorted(df['industry'].unique())],
                    value=df['industry'].unique()[0]
                )
            ], md=3),
            dbc.Col([
                dbc.Label("Filter by Company Size"),
                dcc.Dropdown(
                    id='size-filter',
                    options=[{'label': i, 'value': i} for i in df['company_size'].cat.categories],
                    value=df['company_size'].cat.categories[0]
                )
            ], md=3)
        ], align="center", className="py-4"),

        # Main Tabbed Interface
        dbc.Tabs(id="dashboard-tabs", active_tab="tab-overview", children=[
            dbc.Tab(label="Executive Overview", tab_id="tab-overview"),
            dbc.Tab(label="Channel Performance", tab_id="tab-channel"),
            dbc.Tab(label="Audience Deep-Dive", tab_id="tab-audience"),
        ]),
        
        # Content area for the active tab, wrapped in a Loading component
        dcc.Loading(
            id="loading-spinner",
            type="circle",
            children=html.Div(id="tab-content", className="mt-4")
        )
    ], fluid=False)
])
print("--- APP: Layout created successfully. ---")

# --- Callback for FAST Components ---
@app.callback(
    Output('tab-content', 'children'),
    Input('dashboard-tabs', 'active_tab'),
    Input('industry-filter', 'value'),
    Input('size-filter', 'value')
)
def render_charts_and_kpis(active_tab, selected_industry, selected_size):
    # --- DEBUGGING PROBES START HERE ---
    print("\n--- DEBUG: Main callback triggered. ---")
    print(f"    - Active Tab: {active_tab}")
    print(f"    - Selected Industry: {selected_industry}")
    print(f"    - Selected Size: {selected_size}")

    if not all([active_tab, selected_industry, selected_size]):
        print("--- DEBUG: Callback exiting early because an input is missing. ---")
        return dash.no_update

    print("--- DEBUG: Starting data filtering. ---")
    filtered_df = df[(df['industry'] == selected_industry) & (df['company_size'] == selected_size)]
    
    if filtered_df.empty:
        print("--- DEBUG: Filtered dataframe is empty. Returning alert. ---")
        return dbc.Alert("No data available for the selected filters.", color="warning")

    print(f"--- DEBUG: Data filtering complete. Shape of filtered data: {filtered_df.shape} ---")
    template = "plotly_white"
    
    ai_button_and_output = html.Div([
        html.Hr(className="my-4"),
        dbc.Row([
            dbc.Col(dbc.Button("Generate AI Insights", id="generate-ai-summary-button", n_clicks=0, color="primary"), width="auto"),
        ], justify="center", className="mb-4"),
        dcc.Loading(type="circle", children=html.Div(id="ai-summary-content"))
    ])

    if active_tab == "tab-overview":
        print("--- DEBUG: Building 'Overview' tab components... ---")
        total_spend = filtered_df['ad_spend'].sum()
        total_reach = filtered_df['audience_reach'].sum()
        total_conversions = filtered_df.get('conversions', 0).sum()
        avg_conversion_rate = (total_conversions / total_reach * 100) if total_reach > 0 else 0
        
        spend_by_channel = filtered_df.groupby('marketing_channel')['ad_spend'].sum().reset_index()
        fig_spend_dist = px.pie(spend_by_channel, names='marketing_channel', values='ad_spend', title="Ad Spend by Channel", hole=0.4, template=template)
        
        total_engagement = filtered_df['engagement_metric'].sum()
        funnel_data = dict(number=[total_reach, total_engagement, total_conversions], stage=["Audience Reached", "Engagements", "Conversions"])
        fig_funnel = px.funnel(funnel_data, x='number', y='stage', title=f"Marketing Funnel", template=template)
        fig_funnel.update_layout(title_x=0.5)
        
        print("--- DEBUG: 'Overview' tab layout built. Returning content. ---")
        return html.Div([
            dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody([html.P("Total Ad Spend", className="text-muted"), html.H3(f"${total_spend:,.0f}")])), md=3),
                dbc.Col(dbc.Card(dbc.CardBody([html.P("Total Audience Reach", className="text-muted"), html.H3(f"{total_reach:,}")])), md=3),
                dbc.Col(dbc.Card(dbc.CardBody([html.P("Total Conversions", className="text-muted"), html.H3(f"{total_conversions:,}")])), md=3),
                dbc.Col(dbc.Card(dbc.CardBody([html.P("Overall Conversion Rate", className="text-muted"), html.H3(f"{avg_conversion_rate:.2f}%")])), md=3),
            ], className="mb-4"),
            dbc.Row([
                dbc.Col(dbc.Card(dcc.Graph(figure=fig_spend_dist)), md=5, className="mb-4"),
                dbc.Col(dbc.Card(dcc.Graph(figure=fig_funnel)), md=7, className="mb-4"),
            ]),
            ai_button_and_output
        ])

    elif active_tab == "tab-channel":
        print("--- DEBUG: Building 'Channel' tab components... ---")
        channel_performance = filtered_df.groupby('marketing_channel').agg(total_spend=('ad_spend', 'sum'), avg_cvr=('conversion_rate', 'mean'), avg_cpe=('cost_per_engagement', 'mean')).reset_index()
        fig_channel_roi = px.scatter(
            channel_performance, x='avg_cpe', y='avg_cvr', size='total_spend', color='marketing_channel',
            title="Channel Performance: Cost vs. Conversion Rate",
            labels={'avg_cpe': 'Average Cost Per Engagement ($)', 'avg_cvr': 'Average Conversion Rate (%)'},
            template=template, size_max=50
        )
        print("--- DEBUG: 'Channel' tab layout built. Returning content. ---")
        return html.Div([
            dbc.Row([dbc.Col(dbc.Card(dcc.Graph(figure=fig_channel_roi)), width=12, className="mb-4")]),
            ai_button_and_output
        ])

    elif active_tab == "tab-audience":
        print("--- DEBUG: Building 'Audience' tab components... ---")
        fig_audience_cvr = px.bar(filtered_df.groupby('target_audience')['conversion_rate'].mean().sort_values().reset_index(), x='conversion_rate', y='target_audience', orientation='h', title='Average Conversion Rate by Target Audience', labels={'conversion_rate': 'Avg. Conversion Rate (%)', 'target_audience': 'Audience Segment'}, template=template)
        fig_device_cvr = px.bar(filtered_df.groupby('device')['conversion_rate'].mean().sort_values(ascending=False).reset_index(), x='device', y='conversion_rate', title='Average Conversion Rate by Device', labels={'conversion_rate': 'Avg. Conversion Rate (%)', 'device': 'Device Type'}, color='device', template=template)
        print("--- DEBUG: 'Audience' tab layout built. Returning content. ---")
        return html.Div([
            dbc.Row([
                dbc.Col(dbc.Card(dcc.Graph(figure=fig_audience_cvr)), md=6, className="mb-4"),
                dbc.Col(dbc.Card(dcc.Graph(figure=fig_device_cvr)), md=6, className="mb-4"),
            ]),
            ai_button_and_output
        ])

    print("--- DEBUG: Callback finished without returning content from a tab. This is an error. ---")
    return "Error: No matching tab found."


# --- Callback for SLOW AI Summary ---
@app.callback(
    Output('ai-summary-content', 'children'),
    Input('generate-ai-summary-button', 'n_clicks'),
    State('dashboard-tabs', 'active_tab'),
    State('industry-filter', 'value'),
    State('size-filter', 'value'),
    prevent_initial_call=True
)
def generate_ai_summary(n_clicks, active_tab, selected_industry, selected_size):
    if n_clicks == 0:
        return ""

    filtered_df = df[(df['industry'] == selected_industry) & (df['company_size'] == selected_size)]
    ai_generated_text = ""

    if active_tab == "tab-overview":
        total_reach = filtered_df['audience_reach'].sum()
        total_engagement = filtered_df['engagement_metric'].sum()
        total_conversions = filtered_df.get('conversions', 0).sum()
        ai_generated_text = generate_overview_insights(total_reach, total_engagement, total_conversions)
    elif active_tab == "tab-channel":
        ai_generated_text = generate_channel_insights(filtered_df)
    elif active_tab == "tab-audience":
        ai_generated_text = generate_audience_insights(filtered_df)
    
    return dbc.Alert([
        html.H5("AI Analyst Summary", className="alert-heading"), 
        html.Hr(), 
        dcc.Markdown(ai_generated_text)
    ], color="info", className="mt-4")


if __name__ == '__main__':
    app.run(debug=True)