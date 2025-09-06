# app.py (Final Version with Markdown Fix)
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.express as px
from dotenv import load_dotenv
import uuid
from flask_caching import Cache
import dash_ag_grid as dag

from insights_generator import (
    generate_overview_insights, generate_channel_insights,
    generate_audience_insights, generate_geo_insights
)

# --- App Initialization, Caching, and Data Loading (Unchanged) ---
load_dotenv()
APP_THEME = dbc.themes.FLATLY
app = dash.Dash(__name__, external_stylesheets=[APP_THEME], suppress_callback_exceptions=True)
server = app.server

cache = Cache(app.server, config={'CACHE_TYPE': 'filesystem', 'CACHE_DIR': 'cache-directory'})
CACHE_TIMEOUT = 3600

try:
    df = pd.read_parquet('assets/marketing_data.parquet')
except FileNotFoundError:
    print("FATAL ERROR: Run 'preprocess.py' first.")
    exit()

size_order = ['1-10', '11-50', '51-100', '100+']
df['company_size'] = pd.Categorical(df['company_size'], categories=size_order, ordered=True)

# --- App Layout (Unchanged) ---
app.layout = html.Div(className="bg-light", style={'minHeight': '100vh'}, children=[
    dcc.Store(id='session-id-store'),
    dcc.Store(id='ai-trigger-store'),
    dbc.Container([
        dbc.Row(html.H1("SME Marketing Strategy Dashboard", className="text-primary text-center my-4"), align="center"),
        dbc.Card(dbc.CardBody([dbc.Row([
            dbc.Col([dbc.Label("Filter by Industry", className="fw-bold"), dcc.Dropdown(id='industry-filter', options=[{'label': i, 'value': i} for i in sorted(df['industry'].unique())], value=df['industry'].unique()[0])], width=12, md=6),
            dbc.Col([dbc.Label("Filter by Company Size", className="fw-bold"), dcc.Dropdown(id='size-filter', options=[{'label': i, 'value': i} for i in df['company_size'].cat.categories], value=df['company_size'].cat.categories[0])], width=12, md=6, className="mt-3 mt-md-0"),
        ])]), className="mb-4"),
        dbc.Tabs(id="dashboard-tabs", active_tab="tab-overview", children=[
            dbc.Tab(label="🚀 Executive Overview", tab_id="tab-overview"), dbc.Tab(label="📊 Channel Performance", tab_id="tab-channel"),
            dbc.Tab(label="👥 Audience Deep-Dive", tab_id="tab-audience"), dbc.Tab(label="🌍 Geographic Performance", tab_id="tab-geo"),
        ]),
        html.Div(id="tab-content", className="mt-4")
    ], fluid=True, className="dbc")
])

# --- Callbacks ---
# (Session ID callback is unchanged)
@app.callback(Output('session-id-store', 'data'), Input('industry-filter', 'value'), Input('size-filter', 'value'))
def update_data_and_get_session_id(selected_industry, selected_size):
    session_id = str(uuid.uuid4())
    filtered_df = df[(df['industry'] == selected_industry) & (df['company_size'] == selected_size)]
    cache.set(session_id, filtered_df, timeout=CACHE_TIMEOUT)
    return session_id

@app.callback(Output('tab-content', 'children'), Input('dashboard-tabs', 'active_tab'), Input('session-id-store', 'data'))
def render_tab_content(active_tab, session_id):
    if not session_id: raise PreventUpdate
    filtered_df = cache.get(session_id)
    if filtered_df is None or filtered_df.empty: return dbc.Alert("No data available for the selected filters.", color="warning")
    
    ai_section = html.Div([
        html.Hr(className="my-5"),
        dbc.Row([dbc.Col(html.H4("Automated Insights"), width="auto"), dbc.Col(dbc.Button("✨ Generate AI Summary", id="generate-ai-button", n_clicks=0, color="primary"), width="auto")], justify="between", align="center"),
        dbc.Spinner(dcc.Markdown(id="ai-output-div", className="text-body-secondary border rounded p-3 mt-3", style={"whiteSpace": "pre-wrap"}))
    ])

    template = "plotly_white"
    if active_tab == "tab-overview":
        total_spend = filtered_df['ad_spend'].sum()
        total_reach = filtered_df['audience_reach'].sum()
        total_conversions = filtered_df['conversions'].sum()
        valid_cpc = filtered_df['cost_per_conversion'][filtered_df['cost_per_conversion'] > 0]
        avg_cpc = valid_cpc.mean() if not valid_cpc.empty else 0
        kpi_cards = dbc.Row([dbc.Col(dbc.Card(dbc.CardBody([html.H3(f"${total_spend:,.0f}"), html.P("Total Ad Spend")])), md=3), dbc.Col(dbc.Card(dbc.CardBody([html.H3(f"{total_reach:,}"), html.P("Total Audience Reach")])), md=3), dbc.Col(dbc.Card(dbc.CardBody([html.H3(f"{total_conversions:,}"), html.P("Total Conversions")])), md=3), dbc.Col(dbc.Card(dbc.CardBody([html.H3(f"${avg_cpc:,.2f}"), html.P("Avg. Cost Per Conversion")]))), ], className="text-center text-primary mt-2 g-4")
        total_engagement = filtered_df['engagement_metric'].sum()
        funnel_data = dict(number=[total_reach, total_engagement, total_conversions], stage=["Reach", "Engagement", "Conversion"])
        fig_funnel = px.funnel(funnel_data, x='number', y='stage', title="The Customer Journey", template=template, labels={'number':'Count'})
        spend_dist = filtered_df.groupby('marketing_channel', as_index=False)['ad_spend'].sum()
        fig_pie_spend = px.pie(spend_dist, names='marketing_channel', values='ad_spend', title="Budget Allocation", hole=0.4, template=template)
        return html.Div([kpi_cards, dbc.Row([dbc.Col(dcc.Graph(figure=fig_funnel), lg=7), dbc.Col(dcc.Graph(figure=fig_pie_spend), lg=5), ], className="mt-4", align="center"), ai_section])

    elif active_tab == "tab-channel":
        channel_perf = filtered_df.groupby('marketing_channel', as_index=False).agg(total_spend=('ad_spend', 'sum'), avg_cvr=('conversion_rate', 'mean'), avg_cpc=('cost_per_conversion', 'mean')).round(2)
        most_efficient = channel_perf.loc[channel_perf['avg_cpc'][channel_perf['avg_cpc']>0].idxmin()] if not channel_perf.empty and (channel_perf['avg_cpc']>0).any() else None
        highest_cvr = channel_perf.loc[channel_perf['avg_cvr'].idxmax()] if not channel_perf.empty else None
        kpi_cards = dbc.Row([dbc.Col(dbc.Card(dbc.CardBody([html.H3(most_efficient['marketing_channel']), html.P("Most Efficient Channel (CPC)")])) if most_efficient is not None else "", md=6), dbc.Col(dbc.Card(dbc.CardBody([html.H3(highest_cvr['marketing_channel']), html.P("Highest Converting Channel (CVR)")])) if highest_cvr is not None else "", md=6), ], className="text-center text-primary mt-2 mb-4 g-4")
        fig_bubble = px.scatter(channel_perf, x='avg_cpc', y='avg_cvr', size='total_spend', color='marketing_channel', title="Channel Efficiency vs. Conversion Rate", template=template, size_max=60, hover_name='marketing_channel', labels={"avg_cpc": "Avg. Cost Per Conversion ($)", "avg_cvr": "Avg. Conversion Rate (%)", "total_spend": "Total Spend ($)"})
        table = dag.AgGrid(rowData=channel_perf.to_dict("records"), columnDefs=[{"headerName": "Channel", "field": "marketing_channel"}, {"headerName": "Total Spend ($)", "field": "total_spend"}, {"headerName": "Avg. CVR (%)", "field": "avg_cvr"}, {"headerName": "Avg. CPC ($)", "field": "avg_cpc"}, ], defaultColDef={"sortable": True, "filter": True, "resizable": True}, dashGridOptions={"domLayout": "autoHeight"}, )
        return html.Div([kpi_cards, dbc.Row([dbc.Col(dcc.Graph(figure=fig_bubble), lg=7), dbc.Col([html.H4("Detailed Channel Data", className="mt-4 mt-lg-0"), table], lg=5), ], align="center", className="mt-4"), ai_section])

    elif active_tab == "tab-audience":
        # --- THIS IS THE FIX ---
        # We now group by the SUM of conversions, not the average of a rate.
        # This aligns the KPIs with the chart and business reality.
        audience_conversions = filtered_df.groupby('target_audience')['conversions'].sum()
        top_audience = audience_conversions.idxmax() if not audience_conversions.empty else "N/A"

        device_conversions = filtered_df.groupby('device')['conversions'].sum()
        top_device = device_conversions.idxmax() if not device_conversions.empty else "N/A"
        # --- END OF FIX ---

        kpi_cards = dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([html.H3(top_audience), html.P("Top Audience by Total Conversions")])), md=6),
            dbc.Col(dbc.Card(dbc.CardBody([html.H3(top_device), html.P("Top Device by Total Conversions")])) if top_device is not None else "", md=6),
        ], className="text-center text-primary mt-2 mb-4 g-4")
        
        # The sunburst chart logic was already correct, so it remains unchanged.
        sunburst_df = filtered_df.groupby(['target_audience', 'device'], as_index=False)['conversions'].sum()
        fig_sunburst = px.sunburst(sunburst_df, path=['target_audience', 'device'], values='conversions', title="Conversions by Audience and Device", template=template)
        return html.Div([kpi_cards, dcc.Graph(figure=fig_sunburst), ai_section])

    elif active_tab == "tab-geo":
        geo_perf = filtered_df.groupby('region', as_index=False).agg(total_spend=('ad_spend', 'sum'), avg_cpc=('cost_per_conversion', 'mean')).round(2)
        highest_spend = geo_perf.loc[geo_perf['total_spend'].idxmax()] if not geo_perf.empty else None
        most_efficient = geo_perf.loc[geo_perf['avg_cpc'][geo_perf['avg_cpc']>0].idxmin()] if not geo_perf.empty and (geo_perf['avg_cpc']>0).any() else None
        kpi_cards = dbc.Row([dbc.Col(dbc.Card(dbc.CardBody([html.H3(highest_spend['region']), html.P("Highest Spend Region")])) if highest_spend is not None else "", md=6), dbc.Col(dbc.Card(dbc.CardBody([html.H3(most_efficient['region']), html.P("Most Efficient Region (CPC)")])) if most_efficient is not None else "", md=6), ], className="text-center text-primary mt-2 mb-4 g-4")
        fig_geo_spend = px.bar(geo_perf.sort_values('total_spend', ascending=False), x='region', y='total_spend', color='region', title="Ad Spend by Region", template=template, labels={"total_spend": "Total Ad Spend ($)", "region": "Region"})
        fig_geo_cpc = px.bar(geo_perf.sort_values('avg_cpc', ascending=True), x='region', y='avg_cpc', color='region', title="Efficiency (CPC) by Region", template=template, labels={"avg_cpc": "Avg. Cost Per Conversion ($)", "region": "Region"})
        return html.Div([kpi_cards, dbc.Row([dbc.Col(dcc.Graph(figure=fig_geo_spend), width=12, lg=6), dbc.Col(dcc.Graph(figure=fig_geo_cpc), width=12, lg=6)], className="mt-4"), ai_section])
# (The fast AI trigger callback is unchanged)
@app.callback(
    Output('ai-trigger-store', 'data'),
    Output('generate-ai-button', 'disabled'),
    Output('ai-output-div', 'children'),
    Input('generate-ai-button', 'n_clicks'),
    State('session-id-store', 'data'),
    prevent_initial_call=True
)
def trigger_ai_computation(n_clicks, session_id):
    if n_clicks is None or n_clicks == 0:
        raise PreventUpdate
    thinking_message = "🤖 Thinking... Please wait while I analyze the data."
    return session_id, True, thinking_message

# (The slow AI worker callback is unchanged)
@app.callback(
    Output('ai-output-div', 'children', allow_duplicate=True),
    Output('generate-ai-button', 'disabled', allow_duplicate=True),
    Input('ai-trigger-store', 'data'),
    State('dashboard-tabs', 'active_tab'),
    prevent_initial_call=True
)
def run_ai_computation(session_id, active_tab):
    if not session_id:
        raise PreventUpdate
    filtered_df = cache.get(session_id)
    if filtered_df is None or filtered_df.empty:
        return "No data to analyze.", False
    ai_text = ""
    if active_tab == "tab-overview":    ai_text = generate_overview_insights(filtered_df)
    elif active_tab == "tab-channel":   ai_text = generate_channel_insights(filtered_df)
    elif active_tab == "tab-audience":  ai_text = generate_audience_insights(filtered_df)
    elif active_tab == "tab-geo":       ai_text = generate_geo_insights(filtered_df)
    else:                               ai_text = "Error: Could not determine active tab."
    return ai_text, False

if __name__ == '__main__':
    app.run(debug=True)