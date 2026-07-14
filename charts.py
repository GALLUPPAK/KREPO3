"""
Generic, data-driven Plotly chart builders. Every chart is produced from the
XLSForm catalogue + current data — nothing is hardcoded to a specific wave of
data, so tomorrow's larger file renders the same way with no code changes.
"""
import re
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

NAVY = "#002147"
RED = "#e4002b"
GOLD = "#c9a227"
TEAL = "#0f7d8c"
SLATE = "#5b7083"
PALETTE = [NAVY, RED, GOLD, TEAL, SLATE, "#8a5a44", "#3f6b3f", "#7a5c99", "#b0793a", "#446e91"]

BASE_LAYOUT = dict(
    font=dict(family="Segoe UI, Arial", size=13, color="#1c1c1c"),
    paper_bgcolor="white",
    plot_bgcolor="white",
    margin=dict(l=10, r=10, t=48, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=-0.25, x=0),
)


def _short_label(text, n=64):
    if not isinstance(text, str):
        return text
    text = re.sub(r"^[A-Za-z0-9_\-]{1,10}\.\s*", "", text)  # strip leading "WB1." style code
    text = text.split("\n")[0].strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def clean_title(row):
    lab = row.get("label") or row.get("var_key")
    return _short_label(lab)


def bar_select_one(data: pd.DataFrame, col: str, list_name: str, label_maps: dict, title: str, min_n=1):
    if col not in data.columns:
        return None, 0
    s = data[col].dropna()
    if len(s) < min_n:
        return None, 0
    lm = label_maps.get(list_name, {})
    decoded = s.apply(lambda v: lm.get(str(v).strip(), str(v)))
    counts = decoded.value_counts()
    if counts.empty:
        return None, 0
    counts = counts.sort_values(ascending=True)
    pct = (counts / counts.sum() * 100).round(1)
    fig = go.Figure(go.Bar(
        x=counts.values, y=[_short_label(str(i), 40) for i in counts.index], orientation="h",
        marker_color=NAVY, text=[f"{v} ({p}%)" for v, p in zip(counts.values, pct.values)],
        textposition="outside",
    ))
    fig.update_layout(title=title, height=max(220, 34 * len(counts) + 90), **BASE_LAYOUT)
    fig.update_xaxes(title="Respondents (n)")
    return fig, len(s)


def bar_select_multiple(sm_frame: pd.DataFrame, title: str, min_n=1):
    if sm_frame is None or sm_frame.empty:
        return None, 0
    n = len(sm_frame)
    if n < min_n:
        return None, 0
    rates = (sm_frame.sum() / n * 100).round(1).sort_values(ascending=True)
    fig = go.Figure(go.Bar(
        x=rates.values, y=[_short_label(str(i), 40) for i in rates.index], orientation="h",
        marker_color=TEAL, text=[f"{v}%" for v in rates.values], textposition="outside",
    ))
    fig.update_layout(title=title, height=max(220, 34 * len(rates) + 90), **BASE_LAYOUT)
    fig.update_xaxes(title="% of respondents selecting", range=[0, max(rates.values.tolist() + [10]) * 1.25])
    return fig, n


def histogram_numeric(data: pd.DataFrame, col: str, title: str, min_n=3, nbins=12):
    if col not in data.columns:
        return None, 0
    s = pd.to_numeric(data[col], errors="coerce").dropna()
    s = s[(s < 9000)]  # drop don't-know / NA sentinel codes like 98, 9998
    if len(s) < min_n:
        return None, 0
    fig = px.histogram(s, nbins=min(nbins, max(3, s.nunique())), color_discrete_sequence=[RED])
    fig.update_layout(title=title, showlegend=False, **BASE_LAYOUT)
    fig.update_xaxes(title=_short_label(title, 40))
    fig.update_yaxes(title="Respondents (n)")
    mean, med = round(s.mean(), 1), round(s.median(), 1)
    fig.add_annotation(text=f"mean={mean}  median={med}  n={len(s)}", xref="paper", yref="paper",
                        x=1, y=1.08, showarrow=False, font=dict(size=11, color=SLATE))
    return fig, len(s)


def bar_select_one_merged(data: pd.DataFrame, col: str, merged_map: dict, title: str, min_n=1):
    if col not in data.columns:
        return None, 0
    s = data[col].dropna()
    if len(s) < min_n:
        return None, 0
    decoded = s.apply(lambda v: merged_map.get(str(v).strip(), str(v)))
    counts = decoded.value_counts()
    if counts.empty:
        return None, 0
    counts = counts.sort_values(ascending=True)
    pct = (counts / counts.sum() * 100).round(1)
    fig = go.Figure(go.Bar(
        x=counts.values, y=[_short_label(str(i), 40) for i in counts.index], orientation="h",
        marker_color=NAVY, text=[f"{v} ({p}%)" for v, p in zip(counts.values, pct.values)],
        textposition="outside",
    ))
    fig.update_layout(title=title, height=max(220, 34 * len(counts) + 90), **BASE_LAYOUT)
    fig.update_xaxes(title="Respondents (n)")
    return fig, len(s)


def bar_select_multiple_merged(data: pd.DataFrame, base_name: str, merged_map: dict, title: str, min_n=1):
    import re as _re
    opt_cols = [c for c in data.columns if _re.match(rf"^{_re.escape(base_name)}_\d+$", c)]
    if not opt_cols:
        return None, 0
    n = len(data)
    if n < min_n:
        return None, 0
    rename = {c: merged_map.get(c.split("_")[-1], c.split("_")[-1]) for c in opt_cols}
    sub = data[opt_cols].apply(pd.to_numeric, errors="coerce").fillna(0).rename(columns=rename)
    rates = (sub.sum() / n * 100).round(1).sort_values(ascending=True)
    fig = go.Figure(go.Bar(
        x=rates.values, y=[_short_label(str(i), 40) for i in rates.index], orientation="h",
        marker_color=TEAL, text=[f"{v}%" for v in rates.values], textposition="outside",
    ))
    fig.update_layout(title=title, height=max(220, 34 * len(rates) + 90), **BASE_LAYOUT)
    fig.update_xaxes(title="% of respondents selecting", range=[0, max(rates.values.tolist() + [10]) * 1.25])
    return fig, n


def grouped_bar_by_protocol(data: pd.DataFrame, col: str, list_name: str, label_maps: dict, title: str, min_n=3):
    if col not in data.columns or "protocol" not in data.columns:
        return None, 0
    sub = data[[col, "protocol"]].dropna()
    if len(sub) < min_n:
        return None, 0
    lm = label_maps.get(list_name, {})
    sub = sub.copy()
    sub[col] = sub[col].apply(lambda v: lm.get(str(v).strip(), str(v)))
    ct = pd.crosstab(sub[col], sub["protocol"], normalize="columns") * 100
    fig = go.Figure()
    for i, proto in enumerate(ct.columns):
        fig.add_bar(name=proto, x=[_short_label(str(i), 30) for i in ct.index], y=ct[proto].round(1),
                    marker_color=[NAVY, RED, GOLD][i % 3])
    fig.update_layout(title=title, barmode="group", **BASE_LAYOUT)
    fig.update_yaxes(title="% within pathway")
    return fig, len(sub)


def donut(series_counts: dict, title: str, colors=None):
    labels = list(series_counts.keys())
    values = list(series_counts.values())
    fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.55,
                            marker=dict(colors=colors or PALETTE)))
    fig.update_layout(title=title, **BASE_LAYOUT)
    return fig


def kpi_gauge(value, title, max_val=100, color=NAVY):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        title={"text": title, "font": {"size": 14}},
        gauge={"axis": {"range": [0, max_val]}, "bar": {"color": color},
               "bgcolor": "white", "borderwidth": 1, "bordercolor": "#ddd"},
    ))
    fig.update_layout(height=220, **{k: v for k, v in BASE_LAYOUT.items() if k != "margin"},
                       margin=dict(l=20, r=20, t=50, b=10))
    return fig


def map_scatter(data: pd.DataFrame, title="Fieldwork Locations"):
    lat = pd.to_numeric(data.get("hidd_GPS-Latitude"), errors="coerce")
    lon = pd.to_numeric(data.get("hidd_GPS-Longitude"), errors="coerce")
    sub = pd.DataFrame({"lat": lat, "lon": lon, "protocol": data.get("protocol")}).dropna()
    if sub.empty:
        return None
    fig = px.scatter_mapbox(sub, lat="lat", lon="lon", color="protocol",
                             color_discrete_map={"EDP": RED, "NDP": NAVY},
                             zoom=5.2, height=480, mapbox_style="carto-positron")
    fig.update_layout(title=title, **{k: v for k, v in BASE_LAYOUT.items() if k != "margin"},
                       margin=dict(l=0, r=0, t=48, b=0))
    return fig


def timeline_submissions(data: pd.DataFrame, title="Daily Submissions"):
    if "SubmissionDate" not in data.columns:
        return None
    d = pd.to_datetime(data["SubmissionDate"], errors="coerce", dayfirst=True)
    if d.isna().all():
        return None
    day_counts = d.dt.date.value_counts().sort_index()
    fig = go.Figure(go.Bar(x=[str(x) for x in day_counts.index], y=day_counts.values, marker_color=NAVY))
    fig.update_layout(title=title, **BASE_LAYOUT)
    fig.update_yaxes(title="Interviews completed")
    return fig
