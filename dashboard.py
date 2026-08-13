import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State, MATCH, ALL
from dash_extensions import WebSocket
import plotly.graph_objects as go
import json
import requests
from collections import deque
import datetime
import random
from flask_compress import Compress

# Initialize Dash App
app = dash.Dash(__name__, title="HealthTrack Clinical Monitor", suppress_callback_exceptions=True)

compress = Compress()
compress.init_app(app.server)

API_URL = "http://127.0.0.1:8000"
AUTH_HEADER = {"Authorization": "Bearer fake-super-secret-token"}

# In-memory storage for time-series data
MAX_DATAPOINTS = 30
time_queue = deque(maxlen=MAX_DATAPOINTS)
hr_queue = deque(maxlen=MAX_DATAPOINTS)
sys_queue = deque(maxlen=MAX_DATAPOINTS)
dia_queue = deque(maxlen=MAX_DATAPOINTS)
bg_queue = deque(maxlen=MAX_DATAPOINTS)

# Define initial default figures
default_gauge = go.Figure(go.Indicator(mode="gauge+number", value=0, title={'text': "Awaiting Data..."}))
default_gauge.update_layout(margin=dict(l=20, r=20, t=30, b=20), height=200, paper_bgcolor='rgba(0,0,0,0)')

default_line = go.Figure()
default_line.update_layout(title="Awaiting Telemetry Stream...", xaxis_title="Time", yaxis_title="Value", height=250, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(240, 244, 248, 0.5)')

def fetch_patient_options():
    try:
        response = requests.get(f"{API_URL}/patients/", headers=AUTH_HEADER)
        if response.status_code == 200:
            patients = response.json()
            return [{'label': f"{p['first_name']} {p['last_name']} (ID: {p['id']})", 'value': p['id']} for p in patients]
    except Exception as e:
        print(f"Error fetching patients: {e}")
    return []

# --- Premium UI Layout ---
app.layout = html.Div(style={'fontFamily': 'Segoe UI, Roboto, Helvetica, Arial, sans-serif', 'padding': '30px', 'backgroundColor': '#f0f4f8', 'minHeight': '100vh'}, children=[
    
    # Download Component
    dcc.Download(id="download-dataframe-csv"),

    # Header Module
    html.Div([
        html.Div([
            html.H1("HealthTrack ICU Telemetry", style={'color': '#102a43', 'margin': '0 0 5px 0', 'fontSize': '28px'}),
            html.P("Real-Time Multi-Metric Monitoring Workspace", style={'color': '#627d98', 'margin': '0', 'fontSize': '16px'})
        ]),
        
        html.Div([
            dcc.Dropdown(
                id='patient-dropdown',
                options=fetch_patient_options(),
                placeholder="--- Select Patient to Initiate Stream ---",
                style={'width': '350px', 'fontSize': '15px'}
            ),
            # New Demographics Panel
            html.Div(id="patient-demographics", style={'marginTop': '10px', 'fontSize': '13px', 'color': '#486581', 'textAlign': 'right'})
        ], style={'backgroundColor': '#ffffff', 'padding': '15px', 'borderRadius': '8px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.05)', 'border': '1px solid #d9e2ec'})
    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'flex-start', 'marginBottom': '25px'}),

    # Hidden WebSocket Container
    html.Div(id="ws-container"),

    # Clinical Parameters & Export Control Module
    
    # Clinical Parameters & Export Control Module
    html.Div([
        html.Div([
            html.H4("Active Threshold Parameters", style={'margin': '0 15px 0 0', 'color': '#334e68', 'fontSize': '15px', 'textTransform': 'uppercase', 'letterSpacing': '1px'}),
            html.Div([
                html.Label("HR Min:", style={'fontWeight': '600', 'color': '#486581', 'marginRight': '5px'}),
                dcc.Input(id='min-hr', type='number', value=60, step=1, style={'width': '60px', 'padding': '4px', 'borderRadius': '4px', 'border': '1px solid #bcccdc', 'marginRight': '20px'}),
                
                html.Label("HR Max:", style={'fontWeight': '600', 'color': '#486581', 'marginRight': '5px'}),
                dcc.Input(id='max-hr', type='number', value=100, step=1, style={'width': '60px', 'padding': '4px', 'borderRadius': '4px', 'border': '1px solid #bcccdc', 'marginRight': '20px'}),

                html.Label("Sys Max:", style={'fontWeight': '600', 'color': '#486581', 'marginRight': '5px'}),
                dcc.Input(id='max-sys', type='number', value=130, step=1, style={'width': '60px', 'padding': '4px', 'borderRadius': '4px', 'border': '1px solid #bcccdc', 'marginRight': '20px'}),

                html.Label("Dia Max:", style={'fontWeight': '600', 'color': '#486581', 'marginRight': '5px'}),
                dcc.Input(id='max-dia', type='number', value=85, step=1, style={'width': '60px', 'padding': '4px', 'borderRadius': '4px', 'border': '1px solid #bcccdc'}),
            ], style={'display': 'flex', 'alignItems': 'center'})
        ], style={'display': 'flex', 'alignItems': 'center'}),
        
        html.Div([
            html.Button("🧠 Generate Risk Report", id="btn-risk", style={'backgroundColor': '#8b5cf6', 'color': 'white', 'border': 'none', 'padding': '8px 15px', 'borderRadius': '6px', 'fontWeight': 'bold', 'cursor': 'pointer', 'marginRight': '10px', 'boxShadow': '0 2px 4px rgba(139, 92, 246, 0.3)'}),
            html.Button("📥 Download Session", id="btn-download", style={'backgroundColor': '#3b82f6', 'color': 'white', 'border': 'none', 'padding': '8px 15px', 'borderRadius': '6px', 'fontWeight': 'bold', 'cursor': 'pointer', 'boxShadow': '0 2px 4px rgba(59, 130, 246, 0.3)'})
        ])
    ], style={'backgroundColor': '#ffffff', 'padding': '15px', 'borderRadius': '10px', 'boxShadow': '0 4px 6px rgba(0,0,0,0.04)', 'marginBottom': '15px', 'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'}),

    # New Risk Assessment Container
    dcc.Loading(
        id="loading-risk-report",
        type="circle",
        color="#8b5cf6",
        children=html.Div(id="risk-assessment-container", style={'marginBottom': '25px', 'minHeight': '50px'})
    ),

    # Main Visualizations Grid
    html.Div([
        # Left Column: Gauges, Widgets & Alerts
        html.Div([
            html.Div([
                html.H4("Current Heart Rate", style={'textAlign': 'center', 'color': '#334e68', 'margin': '0 0 5px 0'}),
                dcc.Graph(id="live-hr-gauge", figure=default_gauge, animate=True)
            ], style={'backgroundColor': '#ffffff', 'padding': '15px', 'borderRadius': '10px', 'boxShadow': '0 4px 6px rgba(0,0,0,0.04)', 'marginBottom': '15px'}),
            
            # New Blood Glucose Widget
            html.Div([
                html.H4("Blood Glucose", style={'color': '#334e68', 'margin': '0 0 5px 0'}),
                html.Div([
                    html.Span(id="live-bg-value", children="--", style={'fontSize': '36px', 'fontWeight': 'bold', 'color': '#8b5cf6'}),
                    html.Span(" mg/dL", style={'fontSize': '16px', 'color': '#627d98', 'marginLeft': '5px'})
                ], style={'textAlign': 'center'})
            ], style={'backgroundColor': '#ffffff', 'padding': '15px', 'borderRadius': '10px', 'boxShadow': '0 4px 6px rgba(0,0,0,0.04)', 'marginBottom': '15px'}),

            html.Div([
                html.H4("Incident & Alert Log", style={'margin': '0 0 10px 0', 'color': '#d64545'}),
                html.Div(id="alert-log", children=[], style={'height': '170px', 'overflowY': 'auto', 'backgroundColor': '#fff5f5', 'border': '1px solid #ffcccc', 'padding': '10px', 'borderRadius': '6px', 'fontFamily': 'Consolas, monospace', 'fontSize': '13px'})
            ], style={'backgroundColor': '#ffffff', 'padding': '15px', 'borderRadius': '10px', 'boxShadow': '0 4px 6px rgba(0,0,0,0.04)'})
        ], style={'width': '32%', 'display': 'flex', 'flexDirection': 'column'}),

        # Right Column: Time Series Trends
        html.Div([
            html.Div([
                dcc.Graph(id="live-hr-trend", figure=default_line, animate=True)
            ], style={'backgroundColor': '#ffffff', 'padding': '20px', 'borderRadius': '10px', 'boxShadow': '0 4px 6px rgba(0,0,0,0.04)', 'marginBottom': '20px'}),

            html.Div([
                dcc.Graph(id="live-bp-trend", figure=default_line, animate=True)
            ], style={'backgroundColor': '#ffffff', 'padding': '20px', 'borderRadius': '10px', 'boxShadow': '0 4px 6px rgba(0,0,0,0.04)'})
        ], style={'width': '66%', 'display': 'flex', 'flexDirection': 'column'})
    ], style={'display': 'flex', 'justifyContent': 'space-between'})
])

# Feature 2: Fetch and display Demographics
@app.callback(
    [Output("ws-container", "children"), Output("patient-demographics", "children")],
    Input("patient-dropdown", "value")
)
def update_connection_and_demographics(patient_id):
    if not patient_id:
        return None, ""
    
    # Clear session history
    time_queue.clear()
    hr_queue.clear()
    sys_queue.clear()
    dia_queue.clear()
    bg_queue.clear()
    
    demographics_ui = ""
    try:
        res = requests.get(f"{API_URL}/patients/{patient_id}", headers=AUTH_HEADER)
        if res.status_code == 200:
            p = res.json()
            # Calculate age safely
            dob_str = p.get('date_of_birth', '')
            if dob_str:
                dob = datetime.datetime.strptime(dob_str, "%Y-%m-%dT%H:%M:%SZ")
                age = (datetime.datetime.now() - dob).days // 365
                demographics_ui = f"Age: {age} | DOB: {dob.strftime('%Y-%m-%d')} | Provider: {p.get('provider_id', 'Unassigned')}"
    except Exception as e:
        demographics_ui = "Demographics unavailable"

    return WebSocket(id="ws-vitals", url=f"ws://127.0.0.1:8000/ws/vitals/{patient_id}"), demographics_ui

# Feature 4: Download Session Data to CSV
@app.callback(
    Output("download-dataframe-csv", "data"),
    Input("btn-download", "n_clicks"),
    prevent_initial_call=True
)
def download_session_report(n_clicks):
    csv_string = "Timestamp,HeartRate_BPM,Systolic_BP,Diastolic_BP,BloodGlucose_mgdL\n"
    for t, hr, sys, dia, bg in zip(time_queue, hr_queue, sys_queue, dia_queue, bg_queue):
        csv_string += f"{t},{hr},{sys},{dia},{bg}\n"
    return dict(content=csv_string, filename=f"telemetry_session_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv")

# Feature 1 & 3: Advanced UI Updates & Alert Acknowledgement
@app.callback(
    [Output("live-hr-gauge", "figure"), 
     Output("live-hr-trend", "figure"),
     Output("live-bp-trend", "figure"),
     Output("alert-log", "children"),
     Output("live-bg-value", "children")],
    [Input("ws-vitals", "message"), 
     Input({'type': 'ack-btn', 'index': ALL}, 'n_clicks')],
    [State("min-hr", "value"), State("max-hr", "value"),
     State("max-sys", "value"), State("max-dia", "value"),
     State("alert-log", "children")]
)
def update_dashboard(msg, ack_clicks, min_hr, max_hr, max_sys, max_dia, existing_alerts):
    ctx = dash.callback_context
    existing_alerts = existing_alerts or []
    
    # Check if the callback was triggered by an Acknowledgement button
    if ctx.triggered and 'ack-btn' in ctx.triggered[0]['prop_id']:
        triggered_id = json.loads(ctx.triggered[0]['prop_id'].split('.')[0])
        alert_index = triggered_id['index']
        
        # Remove the acknowledged alert from the UI list
        filtered_alerts = [
            alert for alert in existing_alerts 
            if alert['props']['id']['index'] != alert_index
        ]
        
        # Fire off the mock API request to the backend to update the database
        # (Silently fails if ID is mocked/invalid, keeping the frontend robust)
        try:
            requests.patch(f"{API_URL}/alerts/{alert_index}/acknowledge", headers=AUTH_HEADER)
        except:
            pass

        return dash.no_update, dash.no_update, dash.no_update, filtered_alerts, dash.no_update

    # Otherwise, process the standard WebSocket vital stream
    min_hr, max_hr = min_hr or 60, max_hr or 100
    max_sys, max_dia = max_sys or 130, max_dia or 85

    if not msg:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    data = json.loads(msg['data'])
    current_hr = data['heart_rate']
    current_sys = data['blood_pressure_systolic']
    current_dia = data['blood_pressure_diastolic']
    # Fallback simulation if blood_glucose is not yet streamed by backend
    current_bg = data.get('blood_glucose', random.randint(90, 110)) 
    current_time = data['recorded_at']

    time_queue.append(current_time)
    hr_queue.append(current_hr)
    sys_queue.append(current_sys)
    dia_queue.append(current_dia)
    bg_queue.append(current_bg)

    hr_color = "#10b981" 
    new_alerts = []

    def create_alert_element(message, color, border_color, alert_id):
        return html.Div([
            html.Span(message, style={'flex': '1', 'fontWeight': '500'}),
            html.Button("Ack", id={'type': 'ack-btn', 'index': alert_id}, style={'backgroundColor': color, 'color': 'white', 'border': 'none', 'padding': '2px 8px', 'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '11px', 'fontWeight': 'bold'})
        ], id={'type': 'alert-div', 'index': alert_id}, style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'color': color, 'borderBottom': f'1px solid {border_color}', 'padding': '6px 0'})

    # Evaluate Clinical Thresholds
    if current_hr > max_hr:
        hr_color = "#ef4444"
        new_alerts.append(create_alert_element(f"[{current_time}] CRITICAL: Tachycardia - HR {current_hr}", hr_color, "#fee2e2", f"hr-high-{current_time}"))
    elif current_hr < min_hr:
        hr_color = "#f59e0b"
        new_alerts.append(create_alert_element(f"[{current_time}] WARNING: Bradycardia - HR {current_hr}", hr_color, "#fef3c7", f"hr-low-{current_time}"))

    if current_sys > max_sys or current_dia > max_dia:
        new_alerts.append(create_alert_element(f"[{current_time}] RISK: Hypertension - BP {current_sys}/{current_dia}", "#c2410c", "#ffedd5", f"bp-high-{current_time}"))

    if new_alerts:
        existing_alerts = new_alerts + existing_alerts
        existing_alerts = existing_alerts[:15] 

    # 1. HR Gauge
    gauge_fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=current_hr,
        number={'font': {'size': 36, 'color': '#102a43'}},
        gauge={
            'axis': {'range': [None, 200], 'tickwidth': 1, 'tickcolor': "#334e68"},
            'bar': {'color': hr_color},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#e2e8f0",
            'steps': [
                {'range': [0, min_hr], 'color': '#fef3c7'},
                {'range': [min_hr, max_hr], 'color': '#d1fae5'},
                {'range': [max_hr, 200], 'color': '#fee2e2'}
            ],
            'threshold': {'line': {'color': "red", 'width': 3}, 'thickness': 0.75, 'value': current_hr}
        }
    ))
    gauge_fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=200, paper_bgcolor='rgba(0,0,0,0)')

    # 2. HR Trend
    hr_line = go.Figure()
    hr_line.add_trace(go.Scatter(x=list(time_queue), y=list(hr_queue), mode='lines+markers', line=dict(color='#3b82f6', width=3, shape='spline'), marker=dict(size=6, color=hr_color), name="HR", fill='tozeroy', fillcolor='rgba(59, 130, 246, 0.1)'))
    hr_line.add_hline(y=max_hr, line_dash="dash", line_color="#ef4444", annotation_text="Max HR")
    hr_line.add_hline(y=min_hr, line_dash="dash", line_color="#f59e0b", annotation_text="Min HR")
    hr_line.update_layout(title="Heart Rate History", xaxis_title="Timestamp", yaxis_title="BPM", yaxis=dict(range=[40, 160]), margin=dict(l=20, r=20, t=40, b=20), height=250, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(240, 244, 248, 0.5)')

    # 3. BP Trend
    bp_line = go.Figure()
    bp_line.add_trace(go.Scatter(x=list(time_queue), y=list(sys_queue), mode='lines+markers', line=dict(color='#8b5cf6', width=3, shape='spline'), marker=dict(size=6), name="Systolic"))
    bp_line.add_trace(go.Scatter(x=list(time_queue), y=list(dia_queue), mode='lines+markers', line=dict(color='#14b8a6', width=3, shape='spline'), marker=dict(size=6), name="Diastolic"))
    bp_line.add_hline(y=max_sys, line_dash="dot", line_color="#ef4444", annotation_text="Sys Max")
    bp_line.add_hline(y=max_dia, line_dash="dot", line_color="#ef4444", annotation_text="Dia Max")
    bp_line.update_layout(title="Continuous Blood Pressure Monitoring", xaxis_title="Timestamp", yaxis_title="mmHg", yaxis=dict(range=[50, 160]), margin=dict(l=20, r=20, t=40, b=20), height=250, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(240, 244, 248, 0.5)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))

    return gauge_fig, hr_line, bp_line, existing_alerts, str(current_bg)

# Feature 5: Machine Learning Risk Assessment Generation
@app.callback(
    Output("risk-assessment-container", "children"),
    Input("btn-risk", "n_clicks"),
    State("patient-dropdown", "value"),
    prevent_initial_call=True
)
def generate_risk_report(n_clicks, patient_id):
    if not patient_id:
        return html.Div("⚠️ Please select a patient first.", style={'color': '#ef4444', 'fontWeight': 'bold'})
    
    try:
        response = requests.get(f"{API_URL}/patients/{patient_id}/risk-assessment", headers=AUTH_HEADER)
        if response.status_code != 200:
            return html.Div(f"Error fetching report: {response.text}", style={'color': '#ef4444'})
        
        data = response.json()
        
        # Color Mapping Logic
        risk_level = data.get("risk_level", "Unknown")
        color_map = {
            "Low": {"bg": "#d1fae5", "text": "#065f46", "border": "#34d399"},
            "Moderate": {"bg": "#fef3c7", "text": "#92400e", "border": "#fbbf24"},
            "High": {"bg": "#ffedd5", "text": "#9a3412", "border": "#fb923c"},
            "Critical": {"bg": "#fee2e2", "text": "#991b1b", "border": "#f87171"}
        }
        style = color_map.get(risk_level, {"bg": "#f3f4f6", "text": "#374151", "border": "#d1d5db"})

        # Format Contributing Factors
        factors_ui = [html.Li(f) for f in data.get("contributing_factors", [])]
        
        # Format Recommendations
        recs_ui = [html.Li(r) for r in data.get("system_recommendations", [])]

        return html.Div([
            html.Div([
                html.H3("AI Clinical Risk Assessment", style={'margin': '0 0 10px 0', 'color': style['text']}),
                html.Div([
                    html.Span("Overall Risk Level: ", style={'fontWeight': 'bold', 'fontSize': '18px'}),
                    html.Span(risk_level.upper(), style={'fontWeight': '900', 'fontSize': '20px', 'backgroundColor': style['text'], 'color': 'white', 'padding': '3px 10px', 'borderRadius': '4px'})
                ], style={'marginBottom': '15px'}),
            ], style={'borderBottom': f'2px solid {style["border"]}', 'marginBottom': '15px', 'paddingBottom': '10px'}),
            
            html.Div([
                html.Div([
                    html.H4("Identified Contributing Factors:", style={'margin': '0 0 10px 0', 'color': style['text']}),
                    html.Ul(factors_ui, style={'margin': '0', 'paddingLeft': '20px', 'color': '#1f2937'})
                ], style={'flex': '1'}),
                html.Div([
                    html.H4("System-Generated Recommendations:", style={'margin': '0 0 10px 0', 'color': style['text']}),
                    html.Ul(recs_ui, style={'margin': '0', 'paddingLeft': '20px', 'color': '#1f2937', 'fontWeight': '500'})
                ], style={'flex': '1'})
            ], style={'display': 'flex', 'gap': '20px'})
            
        ], style={
            'backgroundColor': style['bg'], 
            'border': f'1px solid {style["border"]}', 
            'borderRadius': '8px', 
            'padding': '20px',
            'boxShadow': '0 4px 6px rgba(0,0,0,0.05)'
        })

    except Exception as e:
        return html.Div(f"Connection Error: {str(e)}", style={'color': '#ef4444'})

if __name__ == '__main__':
    app.run(debug=True, port=8050)