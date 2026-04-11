from collections import defaultdict
from datetime import datetime
import plotly.graph_objects as go

DATE_FORMAT = "%Y-%m-%d"

# Define Theme Palettes
LIGHT_THEME = {
    "name": "light",
    "bg_color": "rgba(0,0,0,0)",
    "text_color": "#111827",
    "grid_color": "#E5E7EB",
    "palette": ["#4F46E5", "#10B981", "#F59E0B", "#EF4444", "#3B82F6", "#8B5CF6", "#EC4899", "#14B8A6"]
}

DARK_THEME = {
    "name": "dark",
    "bg_color": "rgba(0,0,0,0)",
    "text_color": "#F9FAFB",
    "grid_color": "#374151",
    "palette": ["#818CF8", "#34D399", "#FBBF24", "#F87171", "#60A5FA", "#A78BFA", "#F472B6", "#2DD4BF"]
}

def get_theme(is_dark: bool):
    return DARK_THEME if is_dark else LIGHT_THEME

def _parse_date(value: str):
    try:
        return datetime.strptime(value, DATE_FORMAT).date()
    except (TypeError, ValueError):
        return None

def _base_layout(title: str, theme: dict, xaxis_title=None, yaxis_title=None):
    return go.Layout(
        title=dict(text=title, font=dict(color=theme["text_color"], size=18, family="Inter, sans-serif")),
        paper_bgcolor=theme["bg_color"],
        plot_bgcolor=theme["bg_color"],
        font=dict(color=theme["text_color"], family="Inter, sans-serif"),
        xaxis=dict(
            title=xaxis_title, 
            gridcolor=theme["grid_color"], 
            zerolinecolor=theme["grid_color"],
            color=theme["text_color"]
        ),
        yaxis=dict(
            title=yaxis_title, 
            gridcolor=theme["grid_color"], 
            zerolinecolor=theme["grid_color"],
            color=theme["text_color"]
        ),
        margin=dict(l=40, r=40, t=60, b=40),
        hoverlabel=dict(bgcolor=theme["text_color"], font_color=theme["bg_color"]),
    )

def plot_category_totals(data, is_dark=False):
    theme = get_theme(is_dark)
    totals = defaultdict(float)
    for row in data:
        amount = row.get("amount")
        category = row.get("category")
        if category and isinstance(amount, (int, float)):
            totals[category] += amount

    if not totals:
        return go.Figure(layout=_base_layout("No data available", theme))

    labels, values = zip(*sorted(totals.items(), key=lambda item: item[1], reverse=True))
    labels = [str(label) for label in labels]
    values = [float(value) for value in values]
    
    fig = go.Figure(
        data=go.Bar(
            x=labels, 
            y=values, 
            marker_color=theme["palette"][0],
            marker_line_width=0,
            texttemplate="%{y:.2f} €",
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Amount: %{y:.2f} €<extra></extra>"
        )
    )
    
    fig.update_layout(
        _base_layout("Total Amount by Category", theme, yaxis_title="Amount (€)"),
        xaxis_tickangle=-45,
    )
    return fig


def plot_category_pie(data, is_dark=False):
    theme = get_theme(is_dark)
    totals = defaultdict(float)
    for row in data:
        amount = row.get("amount")
        category = row.get("category")
        if category and isinstance(amount, (int, float)):
            totals[category] += amount

    if not totals:
        return go.Figure(layout=_base_layout("No data available", theme))

    labels, values = zip(*sorted(totals.items(), key=lambda item: item[1], reverse=True))
    
    fig = go.Figure(
        data=go.Pie(
            labels=labels, 
            values=values, 
            textinfo="percent+label",
            marker=dict(colors=theme["palette"], line=dict(color=theme["bg_color"], width=2)),
            hovertemplate="<b>%{label}</b><br>Amount: %{value:.2f} €<br>Percentage: %{percent}<extra></extra>"
        )
    )
    
    fig.update_layout(_base_layout("Distribution by Category", theme))
    fig.update_traces(hole=.4, hoverinfo="label+percent+name") # Donut chart for premium look
    return fig


def plot_amount_over_time(data, is_dark=False):
    theme = get_theme(is_dark)
    daily = defaultdict(float)
    for row in data:
        amount = row.get("amount")
        date_value = row.get("date")
        parsed = _parse_date(date_value)
        if parsed and isinstance(amount, (int, float)):
            daily[parsed] += amount

    if not daily:
        return go.Figure(layout=_base_layout("No data available", theme))

    dates = sorted(daily)
    values = [float(daily[date]) for date in dates]

    fig = go.Figure(
        data=go.Scatter(
            x=dates, 
            y=values, 
            mode="lines+markers", 
            line=dict(color=theme["palette"][1], width=3, shape='spline'),
            marker=dict(size=8, color=theme["palette"][1], line=dict(width=1, color=theme["bg_color"])),
            fill='tozeroy',
            fillcolor=theme["palette"][1].replace(")", ", 0.1)").replace("HEX", ""), # rudimentary opacity logic
            hovertemplate="<b>%{x}</b><br>Amount: %{y:.2f} €<extra></extra>"
        )
    )
    
    fig.update_layout(_base_layout("Total Amount over Time", theme, xaxis_title="Date", yaxis_title="Amount (€)"))
    return fig
