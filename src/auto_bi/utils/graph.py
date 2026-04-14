from collections import defaultdict
from datetime import datetime
import plotly.graph_objects as go

DATE_FORMAT = "%Y-%m-%d"

# Define Theme Palettes
DARK_THEME = {
    "name": "dark",
    "bg_color": "rgba(0,0,0,0)",
    "text_color": "#F9FAFB",
    "grid_color": "#374151",
    "palette": ["#818CF8", "#34D399", "#FBBF24", "#F87171", "#60A5FA", "#A78BFA", "#F472B6", "#2DD4BF"]
}

def get_theme():
    return DARK_THEME

def _parse_date(value: str):
    try:
        return datetime.strptime(value, DATE_FORMAT).date()
    except (TypeError, ValueError):
        return None

def _base_layout(theme: dict, xaxis_title=None, yaxis_title=None):
    return go.Layout(
        paper_bgcolor=theme["bg_color"],
        plot_bgcolor=theme["bg_color"],
        font=dict(color=theme["text_color"], family="Inter, sans-serif"),
        xaxis=dict(
            title=xaxis_title, 
            gridcolor=theme["grid_color"], 
            zerolinecolor=theme["grid_color"],
            color=theme["text_color"],
            automargin=True
        ),
        yaxis=dict(
            title=yaxis_title, 
            gridcolor=theme["grid_color"], 
            zerolinecolor=theme["grid_color"],
            color=theme["text_color"],
            automargin=True
        ),
        margin=dict(l=40, r=40, t=80, b=80)
    )

def plot_category_totals(data):
    theme = get_theme()
    totals = defaultdict(float)
    for row in data:
        amount = row.get("amount")
        category = row.get("category")
        if category and isinstance(amount, (int, float)):
            totals[category] += abs(amount)

    if not totals:
        fig = go.Figure()
        fig.update_layout(_base_layout(theme, xaxis_title="No data available"))
        return fig

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
    
    max_val = max(values) if values else 100
    fig.update_layout(
        _base_layout(theme, yaxis_title="Amount (€)"),
        xaxis_tickangle=-30,
        yaxis=dict(range=[0, max_val * 1.2])  # 20% headroom
    )
    return fig


def plot_category_pie(data):
    theme = get_theme()
    totals = defaultdict(float)
    for row in data:
        amount = row.get("amount")
        category = row.get("category")
        if category and isinstance(amount, (int, float)):
            totals[category] += abs(amount)

    if not totals:
        fig = go.Figure()
        fig.update_layout(_base_layout(theme, xaxis_title="No data available"))
        return fig

    labels, values = zip(*sorted(totals.items(), key=lambda item: item[1], reverse=True))
    
    fig = go.Figure(
        data=go.Pie(
            labels=labels, 
            values=values, 
            textinfo="percent+label",
            textposition="outside",
            marker=dict(colors=theme["palette"], line=dict(color=theme["bg_color"], width=2)),
            hovertemplate="<b>%{label}</b><br>Amount: %{value:.2f} €<br>Percentage: %{percent}<extra></extra>"
        )
    )
    
    fig.update_layout(_base_layout(theme), height=600)
    fig.update_traces(hole=.4, hoverinfo="label+percent+name")
    return fig


def plot_amount_over_time(data, freq="D"):
    theme = get_theme()
    daily_incoming = defaultdict(float)
    daily_outgoing = defaultdict(float)
    import datetime
    
    for row in data:
        amount = row.get("amount")
        tipology = row.get("tipology", row.get("direction"))
        date_value = row.get("date")
        parsed = _parse_date(date_value)
        if parsed and isinstance(amount, (int, float)):
            if freq == "W":
                parsed = parsed - datetime.timedelta(days=parsed.weekday())
            elif freq == "M":
                parsed = parsed.replace(day=1)
                
            # New logic: Incoming vs Outgoing (with backward compat)
            if tipology == "Incoming" or tipology == "Salary":
                daily_incoming[parsed] += abs(amount)
            else:  # Outgoing, Expense, Refund, or any other
                daily_outgoing[parsed] += abs(amount)

    all_dates = sorted(set(list(daily_incoming.keys()) + list(daily_outgoing.keys())))

    if not all_dates:
        return go.Figure(layout=_base_layout(theme))

    if freq == "W":
        x_labels = [d.strftime("%Y-W%W") for d in all_dates]
    elif freq == "M":
        x_labels = [d.strftime("%B %Y") for d in all_dates]
    else:
        x_labels = all_dates

    y_incoming = [float(daily_incoming.get(d, 0.0)) for d in all_dates]
    y_outgoing = [float(daily_outgoing.get(d, 0.0)) for d in all_dates]

    fig = go.Figure()
    
    has_incoming = any(y > 0 for y in y_incoming)
    
    if has_incoming:
        fig.add_trace(go.Scatter(
            x=x_labels, 
            y=y_incoming, 
            name="Incoming",
            mode="lines+markers", 
            line=dict(color=theme["palette"][1], width=3, shape='spline'),
            marker=dict(size=8, color=theme["palette"][1], line=dict(width=1, color=theme["bg_color"])),
            hovertemplate="<b>%{x}</b><br>Incoming: %{y:.2f} €<extra></extra>"
        ))
        
    fig.add_trace(go.Scatter(
        x=x_labels, 
        y=y_outgoing, 
        name="Outgoing",
        mode="lines+markers", 
        line=dict(color=theme["palette"][3], width=3, shape='spline'),
        marker=dict(size=8, color=theme["palette"][3], line=dict(width=1, color=theme["bg_color"])),
        hovertemplate="<b>%{x}</b><br>Outgoing: %{y:.2f} €<extra></extra>"
    ))
    
    fig.update_layout(
        _base_layout(theme, xaxis_title="Date", yaxis_title="Amount (€)"),
        hovermode="x unified"
    )
    return fig

