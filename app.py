import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date
import os
from utils.redfin import load_redfin_data, get_market_metrics, get_price_history, get_dom_history
from utils.freddie import load_freddie_rates, get_latest_rates, get_rate_history
from utils.derived import calc_absorption_rate, calc_price_reductions, calc_funnel, calc_affordability

ZIP_CODE = "33301"
CITY_LABEL = "Fort Lauderdale · Las Olas"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

st.set_page_config(
    page_title=f"Market Dashboard · {ZIP_CODE}",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .metric-card {
        background: #f8f8f7;
        border-radius: 8px;
        padding: 14px 16px;
        height: 100%;
    }
    .metric-label {
        font-size: 11px;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 22px;
        font-weight: 600;
        font-family: monospace;
        color: #111;
        line-height: 1.1;
    }
    .metric-delta-up   { font-size: 12px; color: #0ca30c; margin-top: 3px; }
    .metric-delta-down { font-size: 12px; color: #d03b3b; margin-top: 3px; }
    .metric-delta-flat { font-size: 12px; color: #888;    margin-top: 3px; }
    .section-label {
        font-size: 10px;
        color: #aaa;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        margin: 20px 0 8px;
    }
    .ins-note {
        background: #faeeda;
        border: 1px solid #f5c87a;
        border-radius: 6px;
        padding: 10px 14px;
        font-size: 12px;
        color: #6b4a00;
        margin-top: 10px;
    }
    [data-testid="stMetric"] { background: #f8f8f7; border-radius: 8px; padding: 12px; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=86400)
def load_all_data():
    redfin = load_redfin_data(DATA_DIR, ZIP_CODE)
    freddie = load_freddie_rates(DATA_DIR)
    return redfin, freddie


def metric_card(label, value, delta_text, direction):
    delta_class = {"up": "metric-delta-up", "down": "metric-delta-down", "flat": "metric-delta-flat"}[direction]
    arrow = {"up": "▲", "down": "▼", "flat": "—"}[direction]
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        <div class="{delta_class}">{arrow} {delta_text}</div>
    </div>
    """, unsafe_allow_html=True)


def plotly_theme():
    return dict(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="sans-serif", size=11, color="#888"),
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(showgrid=False, tickfont=dict(size=10, color="#aaa")),
        yaxis=dict(gridcolor="#eee", tickfont=dict(size=10, color="#aaa")),
    )


# ── Load data ──────────────────────────────────────────────────────────────────
redfin_df, freddie_df = load_all_data()
metrics = get_market_metrics(redfin_df)
price_hist = get_price_history(redfin_df)
dom_hist = get_dom_history(redfin_df)
rates = get_latest_rates(freddie_df)
rate_hist = get_rate_history(freddie_df)
absorption = calc_absorption_rate(redfin_df)
reductions = calc_price_reductions(redfin_df)
funnel = calc_funnel(redfin_df)
afford = calc_affordability(metrics["median_price"], rates["rate_30yr"])

# ── Header ─────────────────────────────────────────────────────────────────────
col_title, col_badge = st.columns([4, 1])
with col_title:
    st.markdown(f"""
    <span style="font-size:13px;font-family:monospace;font-weight:600;
                 color:#185FA5;background:#E6F1FB;border:1px solid #B5D4F4;
                 border-radius:6px;padding:3px 10px;">
        📍 {ZIP_CODE}
    </span>
    <h2 style="margin:6px 0 2px;font-size:22px;">{CITY_LABEL}</h2>
    <p style="color:#aaa;font-size:12px;margin:0;">Residential · single-family & condos · Fort Lauderdale, FL</p>
    """, unsafe_allow_html=True)
with col_badge:
    st.markdown(f"""
    <div style="text-align:right;padding-top:8px;">
        <span style="font-size:11px;color:#aaa;background:#f4f4f2;border:1px solid #e0e0e0;
                     border-radius:6px;padding:4px 10px;">
            🟢 Updated {date.today().strftime('%b %d, %Y')} · 6:00 AM
        </span>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── Market overview KPIs ───────────────────────────────────────────────────────
st.markdown('<div class="section-label">Market overview</div>', unsafe_allow_html=True)
k1, k2, k3, k4, k5, k6 = st.columns(6)
with k1:
    metric_card("Median price", f"${metrics['median_price']/1000:.0f}k",
                f"{metrics['median_price_chg']:+.1f}% vs last mo",
                "up" if metrics["median_price_chg"] > 0 else "down")
with k2:
    metric_card("Active listings", str(metrics["active_listings"]),
                f"{metrics['active_listings_chg']:+.0f} vs last wk",
                "down" if metrics["active_listings_chg"] < 0 else "up")
with k3:
    metric_card("Avg days on market", str(metrics["avg_dom"]),
                f"{metrics['dom_chg']:+.0f} days vs last mo",
                "down" if metrics["dom_chg"] < 0 else "up")
with k4:
    metric_card("Price per sq ft", f"${metrics['price_per_sqft']:.0f}",
                f"{metrics['ppsf_chg']:+.1f}% vs last mo",
                "up" if metrics["ppsf_chg"] > 0 else "down")
with k5:
    metric_card("Absorption rate", f"{absorption['months']:.1f} mo",
                absorption["label"], "flat")
with k6:
    metric_card("List-to-sale ratio", f"{metrics['list_to_sale']:.1f}%",
                f"{metrics['list_to_sale_chg']:+.1f}pts vs last mo",
                "up" if metrics["list_to_sale_chg"] > 0 else "down")

# ── Market pulse ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Market pulse</div>', unsafe_allow_html=True)
p1, p2, p3 = st.columns(3)

with p1:
    with st.container(border=True):
        st.markdown("**Absorption rate**")
        st.markdown(f"<span style='font-size:32px;font-family:monospace;font-weight:600;'>{absorption['months']:.1f}</span> <span style='color:#aaa'>months</span>", unsafe_allow_html=True)
        pct = min(absorption["months"] / 12, 1.0)
        if absorption["months"] < 4:
            bar_color = "#0ca30c"
            tag = "🟢 Seller's market"
        elif absorption["months"] < 7:
            bar_color = "#eda100"
            tag = "🟡 Balanced market"
        else:
            bar_color = "#d03b3b"
            tag = "🔴 Buyer's market"
        fig = go.Figure(go.Bar(
            x=[absorption["months"]], y=[""], orientation="h",
            marker_color=bar_color, width=0.4
        ))
        fig.add_vline(x=6, line_dash="dot", line_color="#aaa", line_width=1)
     theme = plotly_theme()
theme["xaxis"] = dict(range=[0, 12], showgrid=False, tickfont=dict(size=9, color="#aaa"))
theme["yaxis"] = dict(showticklabels=False)
theme["height"] = 50
fig.update_layout(**theme)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.caption(f"{tag} · {absorption['sales_30d']} sales in last 30 days vs {metrics['active_listings']} active")

with p2:
    with st.container(border=True):
        st.markdown("**Price reductions · this week**")
        st.markdown(f"<span style='font-size:32px;font-family:monospace;font-weight:600;color:#d03b3b;'>{reductions['total']}</span> <span style='color:#aaa;font-size:13px;'>of {metrics['active_listings']} listings ({reductions['pct']:.0f}%)</span>", unsafe_allow_html=True)
        red_df = pd.DataFrame({
            "Type": ["Condos", "Single-family"],
            "Count": [reductions["condos_count"], reductions["sf_count"]],
            "Avg cut": [f"-${reductions['condos_avg_cut']:,.0f}", f"-${reductions['sf_avg_cut']:,.0f}"]
        })
        st.dataframe(red_df, hide_index=True, use_container_width=True)
        st.caption(f"Avg days before first cut: {reductions['avg_days_before_cut']:.0f} days")

with p3:
    with st.container(border=True):
        st.markdown("**New · pending · closed · last 5 weeks**")
        fig = go.Figure()
        weeks = funnel["weeks"]
        fig.add_trace(go.Bar(name="New", x=weeks, y=funnel["new"], marker_color="#2a78d6", width=0.25))
        fig.add_trace(go.Bar(name="Pending", x=weeks, y=funnel["pending"], marker_color="#eda100", width=0.25))
        fig.add_trace(go.Bar(name="Closed", x=weeks, y=funnel["closed"], marker_color="#1baf7a", width=0.25))
        fig.update_layout(**plotly_theme(), height=180, barmode="group",
            legend=dict(orientation="h", y=1.15, x=0, font=dict(size=10)),
            yaxis=dict(gridcolor="#eee", tickfont=dict(size=10, color="#aaa"), title=None))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        latest = {"New": funnel["new"][-1], "Pending": funnel["pending"][-1], "Closed": funnel["closed"][-1]}
        c1, c2, c3 = st.columns(3)
        for col, (k, v) in zip([c1, c2, c3], latest.items()):
            col.metric(k, v)

# ── Trend charts ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">12-month trends</div>', unsafe_allow_html=True)
ch1, ch2 = st.columns(2)

with ch1:
    with st.container(border=True):
        st.markdown("**Median sale price · 33301**")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=price_hist["month"], y=price_hist["median_price"],
            mode="lines+markers", line=dict(color="#2a78d6", width=2),
            fill="tozeroy", fillcolor="rgba(42,120,214,0.07)",
            marker=dict(size=5, color="#2a78d6"),
            hovertemplate="$%{y:,.0f}<extra></extra>"
        ))
        fig.update_layout(**plotly_theme(), height=200,
            yaxis=dict(tickprefix="$", tickformat=",.0f", gridcolor="#eee",
                       tickfont=dict(size=10, color="#aaa")))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with ch2:
    with st.container(border=True):
        st.markdown("**Avg days on market · 33301**")
        fig = go.Figure()
        colors = ["#2a78d6" if i == len(dom_hist) - 1 else "rgba(42,120,214,0.35)"
                  for i in range(len(dom_hist))]
        fig.add_trace(go.Bar(
            x=dom_hist["month"], y=dom_hist["avg_dom"],
            marker_color=colors,
            hovertemplate="%{y} days<extra></extra>"
        ))
        fig.update_layout(**plotly_theme(), height=200,
            yaxis=dict(gridcolor="#eee", tickfont=dict(size=10, color="#aaa")))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ── Florida insurance tracker ──────────────────────────────────────────────────
st.markdown('<div class="section-label">Florida insurance tracker</div>', unsafe_allow_html=True)
with st.container(border=True):
    st.markdown("**Property insurance · Broward County**")
    st.caption("Source: FLOIR · OIR rate filings · NFIP")
    i1, i2, i3, i4, i5, i6 = st.columns(6)
    ins_tiles = [
        (i1, "Avg annual premium", "$6,840", "+11.2% yr/yr", "down"),
        (i2, "Avg per $1k coverage", "$10.90", "+8.4% yr/yr", "down"),
        (i3, "Citizens policies", "148k", "−9% (depopulating)", "up"),
        (i4, "Condo assess. risk", "High", "Post-Surfside SB 4-D", "down"),
        (i5, "Flood zone · 33301", "AE / VE", "FEMA high-risk", "flat"),
        (i6, "Avg flood premium", "$2,210", "+14.1% yr/yr", "down"),
    ]
    for col, label, val, delta, direction in ins_tiles:
        with col:
            metric_card(label, val, delta, direction)

    st.markdown("")
    ins_years = [2020, 2021, 2022, 2023, 2024, 2025]
    ins_home  = [3840, 4210, 4890, 5540, 6150, 6840]
    ins_flood = [890,  970, 1180, 1540, 1940, 2210]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ins_years, y=ins_home, name="Homeowners", mode="lines+markers",
        line=dict(color="#e34948", width=2), fill="tozeroy", fillcolor="rgba(227,73,72,0.07)",
        marker=dict(size=5), hovertemplate="Homeowners: $%{y:,}<extra></extra>"))
    fig.add_trace(go.Scatter(x=ins_years, y=ins_flood, name="Flood (NFIP)", mode="lines+markers",
        line=dict(color="#eda100", width=1.5, dash="dot"),
        marker=dict(size=4), hovertemplate="Flood: $%{y:,}<extra></extra>"))
    fig.update_layout(**plotly_theme(), height=180,
        legend=dict(orientation="h", y=1.15, x=0, font=dict(size=10)),
        yaxis=dict(tickprefix="$", tickformat=",", gridcolor="#eee", tickfont=dict(size=10, color="#aaa")))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown("""
    <div class="ins-note">
    ⚠️ <strong>Agent note:</strong> Insurance costs in 33301 now add an avg <strong>$570/mo</strong>
    to buyer carrying costs. Condo buyers face additional exposure from Milestone Inspection
    requirements under <strong>SB 4-D</strong>. Disclose early and factor into affordability conversations.
    </div>
    """, unsafe_allow_html=True)

# ── Mortgage rates ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Mortgage rates</div>', unsafe_allow_html=True)
with st.container(border=True):
    st.markdown("**Current rates &nbsp;·&nbsp;** <span style='font-size:11px;color:#aaa'>Source: Freddie Mac PMMS · weekly</span>", unsafe_allow_html=True)
    r1, r2, r3, r4 = st.columns(4)
    rate_tiles = [
        (r1, "30-yr fixed",  f"{rates['rate_30yr']:.2f}%",  f"{rates['chg_30yr']:+.2f}pts wk/wk", "up" if rates["chg_30yr"] < 0 else "down"),
        (r2, "15-yr fixed",  f"{rates['rate_15yr']:.2f}%",  f"{rates['chg_15yr']:+.2f}pts wk/wk", "up" if rates["chg_15yr"] < 0 else "down"),
        (r3, "5/1 ARM",      f"{rates['rate_arm']:.2f}%",   f"{rates['chg_arm']:+.2f}pts wk/wk",  "up" if rates["chg_arm"]  < 0 else "down"),
        (r4, "FHA 30-yr",    f"{rates['rate_fha']:.2f}%",   f"{rates['chg_fha']:+.2f}pts wk/wk",  "up" if rates["chg_fha"]  < 0 else "down"),
    ]
    for col, label, val, delta, direction in rate_tiles:
        with col:
            metric_card(label, val, delta, direction)

    st.markdown("")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=rate_hist["week"], y=rate_hist["rate_30yr"], name="30-yr fixed",
        mode="lines+markers", line=dict(color="#2a78d6", width=2),
        fill="tozeroy", fillcolor="rgba(42,120,214,0.07)", marker=dict(size=4),
        hovertemplate="30-yr: %{y:.2f}%<extra></extra>"))
    fig.add_trace(go.Scatter(x=rate_hist["week"], y=rate_hist["rate_15yr"], name="15-yr fixed",
        mode="lines+markers", line=dict(color="#1baf7a", width=1.5, dash="dot"),
        marker=dict(size=3), hovertemplate="15-yr: %{y:.2f}%<extra></extra>"))
    fig.update_layout(**plotly_theme(), height=180,
        legend=dict(orientation="h", y=1.15, x=0, font=dict(size=10)),
        yaxis=dict(ticksuffix="%", range=[5.5, 8.0], gridcolor="#eee",
                   tickfont=dict(size=10, color="#aaa")))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown("**Affordability at 33301 median price &nbsp;·&nbsp;** <span style='font-size:11px;color:#aaa'>20% down · 30-yr fixed</span>", unsafe_allow_html=True)
    a1, a2, a3 = st.columns(3)
    with a1:
        metric_card("Loan amount", f"${afford['loan']:,.0f}", f"${metrics['median_price']:,.0f} − 20% down", "flat")
    with a2:
        metric_card("Est. P&I payment", f"${afford['monthly_pi']:,.0f}/mo", f"At {rates['rate_30yr']:.2f}%", "flat")
    with a3:
        metric_card("True monthly cost", f"${afford['monthly_total']:,.0f}/mo", "P&I + avg insurance", "flat")

# ── Listings ───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Recent listings · 33301</div>', unsafe_allow_html=True)
with st.container(border=True):
    listings_df = redfin_df[redfin_df["type"] == "listing"].copy() if "type" in redfin_df.columns else pd.DataFrame()
    if listings_df.empty:
        st.caption("No listing data loaded — add Redfin CSV to data/ folder.")
    else:
        display_cols = ["address", "list_price", "beds", "baths", "sqft", "dom", "price_change", "status"]
        st.dataframe(
            listings_df[display_cols].rename(columns={
                "address": "Address", "list_price": "List price", "beds": "Beds",
                "baths": "Baths", "sqft": "Sqft", "dom": "DOM",
                "price_change": "Change", "status": "Status"
            }),
            use_container_width=True, hide_index=True
        )

st.divider()
st.caption(f"Data sources: Redfin market data · Freddie Mac PMMS · FLOIR · FEMA NFIP &nbsp;·&nbsp; ZIP {ZIP_CODE} &nbsp;·&nbsp; Last refresh: {datetime.now().strftime('%b %d, %Y %H:%M')}")
