"""
dashboard/app.py
=================
Executive dashboard for the Fan Engagement Platform. Pulls exclusively
from the metrics/ layer (Phase 2) — no metric is computed inline here,
so the dashboard and any future consumer of metrics/ always agree.

Run with:
    streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from metrics.content import (
    engagement_by_type_and_category,
    engagement_depth_distribution,
    widget_performance,
)
from metrics.engagement import dau_wau_mau, events_and_content_rate, session_stats
from metrics.funnels import funnel_by_channel, funnel_overview
from metrics.growth import weekly_growth
from metrics.retention import (
    cohort_retention_pivot,
    day_n_retention,
    rolling_28d_retention,
    segment_retention,
)

st.set_page_config(
    page_title="Fan Engagement Platform",
    page_icon="📊",
    layout="wide",
)

ACCENT = "#5B8DEF"
ACCENT_SOFT = "#7FA8F0"
PLOTLY_TEMPLATE = "plotly_dark"


@st.cache_data(ttl=300)
def load_dau_wau_mau():
    return dau_wau_mau()


@st.cache_data(ttl=300)
def load_session_stats():
    return session_stats()


@st.cache_data(ttl=300)
def load_events_content_rate():
    return events_and_content_rate()


@st.cache_data(ttl=300)
def load_day_n_retention():
    return day_n_retention()


@st.cache_data(ttl=300)
def load_cohort_pivot():
    return cohort_retention_pivot()


@st.cache_data(ttl=300)
def load_rolling_retention():
    return rolling_28d_retention()


@st.cache_data(ttl=300)
def load_segment_retention():
    return segment_retention()


@st.cache_data(ttl=300)
def load_weekly_growth():
    return weekly_growth()


@st.cache_data(ttl=300)
def load_funnel_overview():
    return funnel_overview()


@st.cache_data(ttl=300)
def load_funnel_by_channel():
    return funnel_by_channel()


@st.cache_data(ttl=300)
def load_content_by_type_category():
    return engagement_by_type_and_category()


@st.cache_data(ttl=300)
def load_content_depth():
    return engagement_depth_distribution()


@st.cache_data(ttl=300)
def load_widget_performance():
    return widget_performance()


def kpi_card(col, label: str, value: str, insight: str | None = None):
    with col:
        st.metric(label, value)
        if insight:
            st.caption(insight)


def insight(text: str):
    st.markdown(f"<div style='color:#9AA5B1;font-size:0.85rem;margin-top:-0.5rem;'>💡 {text}</div>",
                unsafe_allow_html=True)


st.title("📊 Fan Engagement Platform — Executive Dashboard")
st.caption("LiveLike-style gamification widgets (polls, trivia, predictions, leaderboards) · "
           "10,000 users · 12-month simulation window")

tab_overview, tab_retention, tab_funnels, tab_content, tab_growth, tab_experiments, tab_recs = st.tabs(
    ["Overview", "Retention", "Funnels", "Content", "Growth", "Experiments", "Recommendations"]
)

# ============================================================
# OVERVIEW
# ============================================================
with tab_overview:
    dwm = load_dau_wau_mau()
    sstats = load_session_stats()

    latest = dwm.iloc[-2]  # second-to-last row: last row is a partial/in-progress day
    avg_stickiness_30d = dwm["stickiness_dau_mau"].tail(31).head(30).mean()

    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, "DAU (latest full day)", f"{int(latest['dau']):,}")
    kpi_card(c2, "WAU", f"{int(latest['wau']):,}")
    kpi_card(c3, "MAU", f"{int(latest['mau']):,}")
    kpi_card(c4, "Stickiness (DAU/MAU, 30d avg)", f"{avg_stickiness_30d:.1%}")

    insight(
        f"A {avg_stickiness_30d:.0%} stickiness ratio means roughly 1 in "
        f"{round(1/avg_stickiness_30d) if avg_stickiness_30d else 0} monthly active users opens the app on "
        "any given day. Sub-20% is typical for a utility/companion app used around live events, not a daily-habit app — "
        "consistent with a sports companion product where usage clusters around game days."
    )

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Median session duration")
        st.metric("Median", f"{sstats['median_session_duration_sec'].iloc[0]:.0f}s",
                   help="p75 / p95 shown below")
        st.caption(f"p75: {sstats['p75_session_duration_sec'].iloc[0]:.0f}s · "
                   f"p95: {sstats['p95_session_duration_sec'].iloc[0]:.0f}s")
    with c2:
        st.subheader("Sessions per user")
        st.metric("Median", f"{sstats['median_sessions_per_user'].iloc[0]:.0f}")
        st.caption(f"p75: {sstats['p75_sessions_per_user'].iloc[0]:.0f} · "
                   f"p95: {sstats['p95_sessions_per_user'].iloc[0]:.0f}")

    st.divider()
    st.subheader("DAU / WAU / MAU trend")
    plot_df = dwm.iloc[:-1]  # drop partial final day from the trend line
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=plot_df["activity_date"], y=plot_df["mau"], name="MAU",
                              line=dict(color="#3D4F6B", width=2)))
    fig.add_trace(go.Scatter(x=plot_df["activity_date"], y=plot_df["wau"], name="WAU",
                              line=dict(color=ACCENT_SOFT, width=2)))
    fig.add_trace(go.Scatter(x=plot_df["activity_date"], y=plot_df["dau"], name="DAU",
                              line=dict(color=ACCENT, width=2)))
    fig.update_layout(template=PLOTLY_TEMPLATE, height=380, margin=dict(t=10, b=10),
                       legend=dict(orientation="h", y=1.05))
    st.plotly_chart(fig, width='stretch')
    insight("MAU has been declining since the front-loaded signup spike tapered off mid-simulation — "
            "expected for a launch-spike acquisition curve with no resurrection campaigns yet.")

# ============================================================
# RETENTION
# ============================================================
with tab_retention:
    st.subheader("Cohort retention heatmap")
    st.caption("Rows = signup-week cohorts · Columns = weeks since signup · "
               "Blank cells = cohort hasn't lived long enough to measure that week yet (not 0%)")

    pivot = load_cohort_pivot()
    pivot.index = pivot.index.astype(str)
    fig = px.imshow(
        pivot.values,
        x=[f"Wk {c}" for c in pivot.columns],
        y=pivot.index,
        color_continuous_scale="Blues",
        aspect="auto",
        labels=dict(color="Retention %"),
    )
    fig.update_layout(template=PLOTLY_TEMPLATE, height=520, margin=dict(t=10, b=10))
    st.plotly_chart(fig, width='stretch')
    insight("Retention stabilizes in the 25-38% band after week 2 rather than decaying to zero — "
            "a sign the gamification loop creates a returning habit for a meaningful minority, not just one-time curiosity.")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Day-N retention: bounded vs. unbounded")
        dn = load_day_n_retention()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=dn["day_n"], y=dn["bounded_retention_pct"], name="Bounded (returned ON day N)",
                              marker_color="#3D4F6B"))
        fig.add_trace(go.Bar(x=dn["day_n"], y=dn["unbounded_retention_pct"], name="Unbounded (active ON OR AFTER day N)",
                              marker_color=ACCENT))
        fig.update_layout(template=PLOTLY_TEMPLATE, barmode="group", height=360,
                           xaxis_title="Day N", yaxis_title="Retention %", margin=dict(t=10, b=10),
                           legend=dict(orientation="h", y=1.15))
        st.plotly_chart(fig, width='stretch')
        insight("Unbounded retention stays high because sessions are spread across a user's whole active "
                "lifetime — it answers 'ever came back,' not 'still engaged like before.' Bounded is the noisier "
                "but more literal day-N signal.")

    with c2:
        st.subheader("Rolling 28-day retention by cohort")
        rr = load_rolling_retention()
        fig = px.line(rr, x="cohort_week", y="rolling_28d_retention_pct", markers=True,
                       color_discrete_sequence=[ACCENT])
        fig.update_layout(template=PLOTLY_TEMPLATE, height=360, margin=dict(t=10, b=10),
                           yaxis_title="% active in trailing 28 days")
        st.plotly_chart(fig, width='stretch')
        insight("This answers a different question than the cohort matrix above: of users who signed up in "
                "week X, what fraction are active RIGHT NOW — catching cohorts that retained early but have since gone dormant.")

    st.divider()
    st.subheader("Day-7 / Day-30 retention by segment")
    seg = load_segment_retention()
    c1, c2 = st.columns(2)
    with c1:
        chan = seg[seg["breakdown_type"] == "acquisition_channel"]
        fig = px.bar(chan, x="segment", y="retention_pct", color="day_n", barmode="group",
                      color_discrete_sequence=["#3D4F6B", ACCENT])
        fig.update_layout(template=PLOTLY_TEMPLATE, height=340, margin=dict(t=30, b=10),
                           title="By acquisition channel")
        st.plotly_chart(fig, width='stretch')
    with c2:
        dev = seg[seg["breakdown_type"] == "device_type"]
        fig = px.bar(dev, x="segment", y="retention_pct", color="day_n", barmode="group",
                      color_discrete_sequence=["#3D4F6B", ACCENT])
        fig.update_layout(template=PLOTLY_TEMPLATE, height=340, margin=dict(t=30, b=10),
                           title="By device type")
        st.plotly_chart(fig, width='stretch')
    insight("Unbounded retention is nearly flat across channels and devices — acquisition channel mostly drives "
            "engagement VOLUME (see Growth tab), not whether a user ever returns at all.")

# ============================================================
# FUNNELS
# ============================================================
with tab_funnels:
    st.subheader("Core engagement funnel")
    fo = load_funnel_overview()
    fig = go.Figure(go.Funnel(
        y=fo["step"], x=fo["users_reached"],
        textinfo="value+percent initial",
        marker=dict(color=[ACCENT, ACCENT_SOFT, "#7FA8F0", "#A9C2F5", "#D0DFFA"]),
    ))
    fig.update_layout(template=PLOTLY_TEMPLATE, height=420, margin=dict(t=10, b=10))
    st.plotly_chart(fig, width='stretch')

    leak_row = fo.iloc[3]  # repeat_engagement
    insight(f"The real leak is repeat engagement: only {leak_row['pct_of_previous_step']:.0f}% of users who engage "
            "once come back to engage again on a DIFFERENT day. First view and first engagement both convert above "
            "85% — the habit-formation gap, not initial interest, is the bottleneck.")

    st.divider()
    st.subheader("Funnel by acquisition channel")
    fc = load_funnel_by_channel()
    fig = px.bar(fc, x="acquisition_channel",
                 y=["pct_first_view", "pct_first_engagement", "pct_repeat_engagement", "pct_premium_conversion"],
                 barmode="group", color_discrete_sequence=["#3D4F6B", ACCENT_SOFT, ACCENT, "#D0DFFA"])
    fig.update_layout(template=PLOTLY_TEMPLATE, height=400, margin=dict(t=10, b=10),
                       yaxis_title="% of signups reaching step", legend_title="Funnel step")
    st.plotly_chart(fig, width='stretch')
    best = fc.sort_values("pct_premium_conversion", ascending=False).iloc[0]
    worst = fc.sort_values("pct_premium_conversion", ascending=True).iloc[0]
    insight(f"{best['acquisition_channel']} converts to premium at {best['pct_premium_conversion']:.1f}% vs. "
            f"{worst['acquisition_channel']} at {worst['pct_premium_conversion']:.1f}% — channel quality differences "
            "compound through the whole funnel, not just at signup volume.")

# ============================================================
# CONTENT
# ============================================================
with tab_content:
    st.subheader("Engagement rate by widget type")
    tc = load_content_by_type_category()
    by_type = tc.groupby("widget_type", as_index=False).agg(
        impressions=("impressions", "sum"),
        interactions=("interactions", "sum"),
    )
    by_type["engagement_rate_pct"] = (100 * by_type["interactions"] / by_type["impressions"]).round(1)
    by_type = by_type.sort_values("engagement_rate_pct", ascending=False)
    fig = px.bar(by_type, x="widget_type", y="engagement_rate_pct", color="widget_type",
                 color_discrete_sequence=[ACCENT, ACCENT_SOFT, "#7FA8F0", "#A9C2F5"])
    fig.update_layout(template=PLOTLY_TEMPLATE, height=360, margin=dict(t=10, b=10), showlegend=False)
    st.plotly_chart(fig, width='stretch')
    insight(f"{by_type.iloc[0]['widget_type'].title()}s convert impressions to interactions at "
            f"{by_type.iloc[0]['engagement_rate_pct']:.0f}% vs. {by_type.iloc[-1]['widget_type']}s at "
            f"{by_type.iloc[-1]['engagement_rate_pct']:.0f}% — a {by_type.iloc[0]['engagement_rate_pct']/by_type.iloc[-1]['engagement_rate_pct']:.1f}x gap. "
            "Invest in which widget FORMATS to build, not in region/platform-specific optimization.")

    st.divider()
    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("Engagement by type × sport category")
        st.dataframe(tc, width='stretch', hide_index=True)
    with c2:
        st.subheader("Top / bottom performing widgets")
        wp = load_widget_performance()
        st.caption("Filtered to widgets with ≥200 impressions (avoids ranking noise from low-exposure widgets)")
        st.dataframe(
            pd.concat([wp.head(5), wp.tail(5)])[["name", "widget_type", "sport", "engagement_rate_pct", "total_points_generated"]],
            width='stretch', hide_index=True,
        )

    st.divider()
    st.subheader("Engagement depth (interaction → completion latency)")
    depth = load_content_depth()
    fig = px.bar(depth, x="widget_type", y="median_latency_sec", color="widget_type",
                 color_discrete_sequence=[ACCENT, ACCENT_SOFT, "#7FA8F0", "#A9C2F5"])
    fig.update_layout(template=PLOTLY_TEMPLATE, height=320, margin=dict(t=10, b=10), showlegend=False)
    st.plotly_chart(fig, width='stretch')
    st.caption("⚠️ This metric is flat across widget types in the current synthetic data — the generator applies "
               "the same completion-latency distribution to every widget type, so this isn't a real product signal "
               "yet. Flagged honestly rather than presented as a finding.")

# ============================================================
# GROWTH
# ============================================================
with tab_growth:
    st.subheader("New / returning / resurrected users per week")
    wg = load_weekly_growth()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=wg["week"], y=wg["new_users"], name="New", stackgroup="one",
                              line=dict(width=0), fillcolor=ACCENT))
    fig.add_trace(go.Scatter(x=wg["week"], y=wg["returning_users"], name="Returning", stackgroup="one",
                              line=dict(width=0), fillcolor="#3D4F6B"))
    fig.add_trace(go.Scatter(x=wg["week"], y=wg["resurrected_users"], name="Resurrected", stackgroup="one",
                              line=dict(width=0), fillcolor=ACCENT_SOFT))
    fig.update_layout(template=PLOTLY_TEMPLATE, height=380, margin=dict(t=10, b=10),
                       legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, width='stretch')

    st.divider()
    st.subheader("Quick Ratio over time")
    fig = px.line(wg.iloc[1:], x="week", y="quick_ratio", markers=True, color_discrete_sequence=[ACCENT])
    fig.add_hline(y=1.0, line_dash="dash", line_color="#9AA5B1",
                  annotation_text="Quick Ratio = 1.0 (growth = churn)")
    fig.update_layout(template=PLOTLY_TEMPLATE, height=360, margin=dict(t=10, b=10))
    st.plotly_chart(fig, width='stretch')

    latest_qr = wg.iloc[-1]["quick_ratio"]
    trend = "below" if latest_qr < 1 else "above"
    insight(f"Quick Ratio is now {latest_qr:.2f} — {trend} the 1.0 breakeven line, meaning churn is currently "
            "outpacing new + resurrected users. Early weeks show inflated ratios (10x+) purely from the launch "
            "signup spike; the post-launch decline below 1.0 is the metric that actually matters for a mature platform.")

# ============================================================
# EXPERIMENTS (Phase 4)
# ============================================================
with tab_experiments:
    st.info("📍 Coming in Phase 4 — A/B test results, sample size/power calculations, "
            "CUPED variance reduction, and ship/no-ship recommendations for 3 pre-built experiments.")

# ============================================================
# RECOMMENDATIONS (Phase 5)
# ============================================================
with tab_recs:
    st.info("📍 Coming in Phase 5 — collaborative filtering + content-based recommendation engine "
            "with cold-start handling, evaluated on a temporal train/test split.")
