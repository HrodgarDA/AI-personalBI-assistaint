from collections import defaultdict
from datetime import datetime

import plotly.graph_objects as go


DATE_FORMAT = "%Y-%m-%d"


def _parse_date(value: str):
    try:
        return datetime.strptime(value, DATE_FORMAT).date()
    except (TypeError, ValueError):
        return None


def plot_category_totals(data):
    totals = defaultdict(float)
    for row in data:
        amount = row.get("amount")
        category = row.get("category")
        if category and isinstance(amount, float):
            totals[category] += amount

    if not totals:
        return go.Figure(
            layout=go.Layout(
                title="No data available for charts",
                template="plotly_white",
            )
        )

    labels, values = zip(*sorted(totals.items(), key=lambda item: item[1], reverse=True))
    labels = [str(label) for label in labels]
    values = [float(value) for value in values]
    fig = go.Figure(
        data=go.Bar(x=labels, y=values, marker_color="#4c78a8")
    )
    fig.update_layout(
        title="Total amount by category",
        xaxis_title="Category",
        yaxis_title="Euro",
        xaxis_tickangle=-45,
        template="plotly_white",
        margin=dict(l=40, r=40, t=60, b=80),
    )
    return fig


def plot_category_pie(data):
    totals = defaultdict(float)
    for row in data:
        amount = row.get("amount")
        category = row.get("category")
        if category and isinstance(amount, float):
            totals[category] += amount

    if not totals:
        return go.Figure(
            layout=go.Layout(
                title="No data available for charts",
                template="plotly_white",
            )
        )

    labels, values = zip(*sorted(totals.items(), key=lambda item: item[1], reverse=True))
    labels = [str(label) for label in labels]
    values = [float(value) for value in values]
    fig = go.Figure(
        data=go.Pie(labels=labels, values=values, textinfo="percent+label")
    )
    fig.update_layout(
        title="Percentage distribution by category",
        template="plotly_white",
        margin=dict(l=40, r=40, t=60, b=60),
    )
    return fig


def plot_amount_over_time(data):
    daily = defaultdict(float)
    for row in data:
        amount = row.get("amount")
        date_value = row.get("date")
        parsed = _parse_date(date_value)
        if parsed and isinstance(amount, float):
            daily[parsed] += amount

    if not daily:
        return go.Figure(
            layout=go.Layout(
                title="No data available for charts",
                template="plotly_white",
            )
        )

    dates = sorted(daily)
    values = [float(daily[date]) for date in dates]

    fig = go.Figure(
        data=go.Scatter(x=dates, y=values, mode="lines+markers", line=dict(color="#f28e2b"))
    )
    fig.update_layout(
        title="Total amount by day",
        xaxis_title="Date",
        yaxis_title="Euro",
        template="plotly_white",
        margin=dict(l=40, r=40, t=60, b=60),
    )
    return fig
