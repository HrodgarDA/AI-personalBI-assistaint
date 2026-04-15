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

CATEGORY_EMOJI = {
    "Dining": "🍽️",
    "Financial": "🏦",
    "Gifts": "🎁",
    "Groceries": "🛒",
    "Health": "💊",
    "Home": "🏠",
    "Other": "📦",
    "Shopping": "🛍️",
    "Subscriptions": "🔄",
    "Transport": "🚗",
    "Utilities": "⚡",
    "Salary": "💰",
    "Refund": "↩️",
}

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

    # Sort ascending so largest category is at the top in horizontal layout
    sorted_items = sorted(totals.items(), key=lambda item: item[1])
    labels = [f"{CATEGORY_EMOJI.get(cat, '📌')} {cat}" for cat, _ in sorted_items]
    values = [float(val) for _, val in sorted_items]
    
    # Generate a color per bar from the palette
    bar_colors = [theme["palette"][i % len(theme["palette"])] for i in range(len(labels))]

    fig = go.Figure(
        data=go.Bar(
            y=labels, 
            x=values,
            orientation='h',
            marker_color=bar_colors,
            marker_line_width=0,
            texttemplate="%{x:,.2f} €",
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Amount: %{x:,.2f} €<extra></extra>"
        )
    )
    
    max_val = max(values) if values else 100
    fig.update_layout(
        _base_layout(theme, xaxis_title="Amount (€)"),
        xaxis=dict(range=[0, max_val * 1.25]),
        height=max(400, len(labels) * 45 + 100),
        yaxis=dict(automargin=True),
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
                
            if tipology == "Incoming" or tipology == "Salary":
                daily_incoming[parsed] += abs(amount)
            else:
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

    # Build cumulative sums
    cum_incoming = []
    cum_outgoing = []
    running_in = 0.0
    running_out = 0.0
    for d in all_dates:
        running_in += float(daily_incoming.get(d, 0.0))
        running_out += float(daily_outgoing.get(d, 0.0))
        cum_incoming.append(running_in)
        cum_outgoing.append(running_out)

    fig = go.Figure()
    
    has_incoming = any(y > 0 for y in cum_incoming)
    
    if has_incoming:
        fig.add_trace(go.Scatter(
            x=x_labels, 
            y=cum_incoming, 
            name="Cumulative Incoming",
            mode="lines+markers", 
            line=dict(color=theme["palette"][1], width=3, shape='spline'),
            marker=dict(size=6, color=theme["palette"][1], line=dict(width=1, color=theme["bg_color"])),
            fill='tozeroy',
            fillcolor='rgba(52, 211, 153, 0.1)',
            hovertemplate="<b>%{x}</b><br>Cumulative Incoming: %{y:.2f} €<extra></extra>"
        ))
        
    fig.add_trace(go.Scatter(
        x=x_labels, 
        y=cum_outgoing, 
        name="Cumulative Outgoing",
        mode="lines+markers", 
        line=dict(color=theme["palette"][3], width=3, shape='spline'),
        marker=dict(size=6, color=theme["palette"][3], line=dict(width=1, color=theme["bg_color"])),
        fill='tozeroy',
        fillcolor='rgba(248, 113, 113, 0.1)',
        hovertemplate="<b>%{x}</b><br>Cumulative Outgoing: %{y:.2f} €<extra></extra>"
    ))
    
    fig.update_layout(
        _base_layout(theme, xaxis_title="Date", yaxis_title="Cumulative Amount (€)"),
        hovermode="x unified"
    )
    return fig

