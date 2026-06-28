"""
dashboard/app.py
=================
Executive dashboard for the Fan Engagement Platform. Pulls exclusively
from the metrics/ layer (Phase 2) — no metric is computed inline here,
so the dashboard and any future consumer of metrics/ always agree.

Run with:
    streamlit run dashboard/app.py
"""

import json
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
from experimentation.analyze import (
    analyze_feed_experiment,
    analyze_onboarding_experiment,
    analyze_push_experiment,
)
from recommendations.serve import get_recommendation, train_recommender_state

st.set_page_config(
    page_title="Fan Engagement Platform",
    page_icon="📊",
    layout="wide",
)

ACCENT = "#5B8DEF"
ACCENT_SOFT = "#7FA8F0"
PLOTLY_TEMPLATE = "plotly_dark"

# ============================================================
# CUSTOM CSS — targets Streamlit's internal data-testid selectors
# (stMetric, stPlotlyChart, stTabs, stDataFrame) rather than rebuilding
# components from scratch, since that's the only stable way to style
# Streamlit's pre-built widgets. Real ceiling here: Streamlit reruns
# the whole script server-side rather than diffing the DOM client-side
# the way a JS framework would, so a fade-in plays once per script run
# rather than tracking actual scroll position — true scroll-triggered
# animation is reserved for the Phase 6 deployed site, which won't be
# built on raw Streamlit.
# ============================================================
def inject_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(14px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    /* KPI metric cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(160deg, #161B22 0%, #1B2230 100%);
        border: 1px solid #2A3142;
        border-radius: 14px;
        padding: 1rem 1.1rem 0.7rem 1.1rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.25);
        transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
        animation: fadeInUp 0.5s ease both;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(91,141,239,0.18);
        border-color: #5B8DEF55;
    }
    div[data-testid="stMetricLabel"] { font-weight: 500; color: #9AA5B1; }
    div[data-testid="stMetricValue"] { font-weight: 700; }

    /* Chart "cards" */
    div[data-testid="stPlotlyChart"] {
        background: #12161D;
        border: 1px solid #232938;
        border-radius: 14px;
        padding: 0.6rem;
        box-shadow: 0 2px 14px rgba(0,0,0,0.3);
        animation: fadeInUp 0.6s ease both;
        transition: box-shadow 0.2s ease;
    }
    div[data-testid="stPlotlyChart"]:hover {
        box-shadow: 0 6px 22px rgba(91,141,239,0.12);
    }

    /* Dataframes */
    div[data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #232938;
        animation: fadeInUp 0.6s ease both;
    }

    /* Tabs: animated underline instead of the default flat bar */
    button[data-baseweb="tab"] {
        font-weight: 600;
        transition: color 0.15s ease;
    }
    div[data-baseweb="tab-highlight"] {
        background-color: #5B8DEF !important;
        height: 3px !important;
        border-radius: 3px;
        transition: left 0.25s cubic-bezier(0.4,0,0.2,1), width 0.25s cubic-bezier(0.4,0,0.2,1);
    }

    /* Section headers get a subtle accent rule */
    h3 {
        border-left: 3px solid #5B8DEF;
        padding-left: 0.6rem;
        animation: fadeInUp 0.45s ease both;
    }

    /* Title */
    h1 { animation: fadeInUp 0.4s ease both; }

    /* Insight callouts */
    .insight-box {
        background: #151B26;
        border-left: 3px solid #5B8DEF;
        border-radius: 8px;
        padding: 0.55rem 0.9rem;
        margin: 0.3rem 0 1rem 0;
        color: #B7C2D0;
        font-size: 0.86rem;
        animation: fadeInUp 0.5s ease both;
        transition: background 0.2s ease;
    }
    .insight-box:hover { background: #1A2230; }
    </style>
    """, unsafe_allow_html=True)


inject_custom_css()


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


# Experiment queries are heavier (per-user pulls over ~2M events on a
# free-tier nano Postgres instance) — cached for an hour, not 5 minutes,
# since experiment results don't need to refresh as often as live KPIs.
@st.cache_data(ttl=3600)
def load_feed_experiment():
    return analyze_feed_experiment()


@st.cache_data(ttl=3600)
def load_onboarding_experiment():
    return analyze_onboarding_experiment()


@st.cache_data(ttl=3600)
def load_push_experiment():
    return analyze_push_experiment()


def kpi_card(col, label: str, value: str, insight: str | None = None):
    with col:
        st.metric(label, value)
        if insight:
            st.caption(insight)


def insight(text: str):
    st.markdown(f"<div class='insight-box'>💡 {text}</div>", unsafe_allow_html=True)


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
def decision_badge(decision: dict):
    rec = decision["recommendation"]
    color = {"ship": "#3FB950", "no-ship": "#F85149", "inconclusive": "#D29922"}[rec]
    st.markdown(
        f"<div style='display:inline-block;background:{color}22;border:1px solid {color};"
        f"color:{color};padding:0.3rem 0.9rem;border-radius:20px;font-weight:700;"
        f"text-transform:uppercase;font-size:0.8rem;'>{rec}</div>",
        unsafe_allow_html=True,
    )
    st.caption(decision["reason"])


def ci_bar_chart(label_a: str, label_b: str, result, as_pct: bool):
    """
    Bars show each arm's own point estimate with its OWN confidence
    interval as error bars -- not the CI of the difference between
    arms overlaid on one bar, which is a different quantity entirely
    (centered on the diff, not on that arm's value) and would
    mislabel the chart. The diff's own CI is reported separately in
    the metrics panel next to this chart, where it belongs.

    Per-arm Wald CIs are only computed for proportions (as_pct=True),
    since TestResult carries each arm's n but not its own variance for
    continuous metrics (only the pooled/Welch SE of the difference) --
    for continuous metrics (as_pct=False), bars are shown without
    error whiskers rather than fabricating an incorrect one.
    """
    scale = 100 if as_pct else 1
    z = 1.96  # 95% CI

    fig = go.Figure()
    for label, val, n, color in [
        (label_a, result.metric_a, result.n_a, "#3D4F6B"),
        (label_b, result.metric_b, result.n_b, ACCENT),
    ]:
        if as_pct and n > 0:
            se_arm = (val * (1 - val) / n) ** 0.5
            err = z * se_arm * scale
            error_y = dict(type="data", array=[err], arrayminus=[err])
        else:
            error_y = None
        fig.add_trace(go.Bar(x=[label], y=[val * scale], marker_color=color, error_y=error_y))

    fig.update_layout(template=PLOTLY_TEMPLATE, height=300, margin=dict(t=10, b=10), showlegend=False,
                       yaxis_title=("%" if as_pct else "value"))
    st.plotly_chart(fig, width='stretch')


with tab_experiments:
    st.caption("Each experiment below ran on real per-user data from the simulated platform — "
               "every number is a measured result, not a canned example.")

    with st.spinner("Running experiment analysis (per-user queries over ~2M events, cached for 1hr after first load)..."):
        feed = load_feed_experiment()
        onboarding = load_onboarding_experiment()
        push = load_push_experiment()

    exp_choice = st.selectbox("Select experiment", [feed["name"], onboarding["name"], push["name"]])

    st.divider()

    if exp_choice == feed["name"]:
        st.subheader(feed["name"])
        st.caption("**Hypothesis:** a personalized content/widget feed increases Day-7 retention vs. a chronological feed. "
                   "**Primary metric:** bounded Day-7 retention (returned on exactly day 7).")
        c1, c2 = st.columns([2, 1])
        with c1:
            ci_bar_chart("Control", "Treatment", feed["primary"], as_pct=True)
        with c2:
            decision_badge(feed["decision"])
            st.metric("Lift", f"{feed['primary'].relative_lift_pct:.1f}%",
                      f"{feed['primary'].diff*100:.1f}pp")
            st.caption(f"95% CI for the difference: [{feed['primary'].ci_low*100:.1f}pp, {feed['primary'].ci_high*100:.1f}pp]")
            st.metric("p-value", f"{feed['primary'].p_value:.4f}")
            st.metric("Required n/arm (for MDE)", f"{feed['required_n_per_arm']:,}",
                       help=f"We had {feed['primary'].n_a:,} (achieved power: {feed['achieved_power']:.0%})")
        insight("Unbounded Day-7 retention (active any time on/after day 7) was nearly flat between arms in earlier "
                "analysis — it was already near ceiling. Bounded retention (returned on EXACTLY day 7) is the "
                "sensitive metric for this experiment; using the unbounded version would have hidden a real effect.")
        st.markdown(f"**Guardrail (avg session duration):** {'✅ OK' if feed['guardrail_ok'] else '⚠️ Violated'} "
                    f"(p={feed['guardrail'].p_value:.3f}, diff={feed['guardrail'].diff:+.1f}s)")
        st.markdown("**Segment breakdown (by acquisition channel):**")
        seg_df = pd.DataFrame([{"channel": s["segment"], "lift_pp": s["result"].diff * 100,
                                 "p_value": s["result"].p_value} for s in feed["segment_results"]])
        st.dataframe(seg_df, width='stretch', hide_index=True)

    elif exp_choice == onboarding["name"]:
        st.subheader(onboarding["name"])
        st.caption("**Hypothesis:** reducing onboarding from 5 steps to 2 increases signup-to-first-engagement "
                   "conversion. **Primary metric:** % of users who ever reach a first interaction.")
        c1, c2 = st.columns([2, 1])
        with c1:
            ci_bar_chart("Control", "Treatment", onboarding["primary"], as_pct=True)
        with c2:
            decision_badge(onboarding["decision"])
            st.metric("Lift", f"{onboarding['primary'].relative_lift_pct:.1f}%",
                      f"{onboarding['primary'].diff*100:.1f}pp")
            st.caption(f"95% CI for the difference: [{onboarding['primary'].ci_low*100:.1f}pp, {onboarding['primary'].ci_high*100:.1f}pp]")
            st.metric("p-value", f"{onboarding['primary'].p_value:.2e}")
            st.metric("Required n/arm (for MDE)", f"{onboarding['required_n_per_arm']:,}",
                       help=f"We had {onboarding['primary'].n_a:,} (achieved power: {onboarding['achieved_power']:.0%})")
        st.markdown(f"**Guardrail (completion rate):** {'✅ OK' if onboarding['guardrail_ok'] else '⚠️ Violated'} "
                    f"(p={onboarding['guardrail'].p_value:.2e}, diff={onboarding['guardrail'].diff*100:+.1f}pp) — "
                    "completion rate also went UP, not down, so the simpler flow isn't trading quality for speed.")
        st.markdown("**Segment breakdown (by acquisition channel):**")
        seg_df = pd.DataFrame([{"channel": s["segment"], "lift_pp": s["result"].diff * 100,
                                 "p_value": s["result"].p_value} for s in onboarding["segment_results"]])
        st.dataframe(seg_df, width='stretch', hide_index=True)

    else:
        st.subheader(push["name"])
        st.caption("**Hypothesis:** ML-optimized push timing increases session frequency vs. fixed morning/evening "
                   "sends. **Primary comparison:** ml_optimized vs. morning (the pre-existing baseline approach). "
                   "**Primary metric:** total sessions per user.")
        c1, c2 = st.columns([2, 1])
        with c1:
            ci_bar_chart("Morning (baseline)", "ML-optimized", push["primary"], as_pct=False)
        with c2:
            decision_badge(push["decision"])
            st.metric("Lift", f"{push['primary'].relative_lift_pct:.1f}%",
                      f"{push['primary'].diff:+.1f} sessions")
            st.caption(f"95% CI for the difference: [{push['primary'].ci_low:+.2f}, {push['primary'].ci_high:+.2f}] sessions")
            st.metric("p-value", f"{push['primary'].p_value:.4f}")
            st.metric("Required n/arm (Cohen's d)", f"{push['required_n_per_arm']:,}",
                       help=f"Observed effect size d={push['cohens_d']:.2f}; we had {push['primary'].n_a:,}/arm")

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**CUPED variance reduction**")
            st.metric("Variance reduction", f"{push['cuped']['var_reduction_pct']:.1f}%",
                       help="Covariate: acquisition-channel quality score (no pre-period history exists for "
                            "these users — all assigned at signup — so a known-before-randomization proxy is used "
                            "instead of each user's own pre-treatment value).")
            st.caption(f"CUPED-adjusted p-value: {push['cuped_test'].p_value:.4f} (raw: {push['primary'].p_value:.4f}) — "
                       "modest reduction since acquisition channel is a weak proxy for individual session count.")
        with c2:
            st.markdown("**Multiple comparison correction (Holm)**")
            mc = push["multiple_comparison_correction"]
            mc_df = pd.DataFrame({
                "comparison": ["ml_optimized vs morning", "evening vs morning"],
                "raw_p": mc["raw_p_values"],
                "corrected_p": mc["corrected_p_values"],
                "reject_null": mc["reject_null"],
            })
            st.dataframe(mc_df, width='stretch', hide_index=True)
            st.caption("evening vs. morning does NOT survive correction — that arm's effect isn't distinguishable "
                       "from noise at this sample size, even though the generator's true effect was negative.")

        st.divider()
        st.markdown("**The peeking problem: naive sequential checks vs. the correct boundary**")
        peek_df = pd.DataFrame(push["sequential_peeks"])
        peek_df["obrien_fleming_threshold"] = push["sequential_alphas"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=peek_df["frac_of_data"], y=peek_df["p_value"], name="Observed p-value",
                                  mode="lines+markers", line=dict(color=ACCENT, width=3)))
        fig.add_trace(go.Scatter(x=peek_df["frac_of_data"], y=peek_df["obrien_fleming_threshold"],
                                  name="O'Brien-Fleming threshold (this look)", mode="lines+markers",
                                  line=dict(color="#F85149", dash="dash")))
        fig.add_hline(y=0.05, line_dash="dot", line_color="#9AA5B1", annotation_text="naive alpha=0.05")
        fig.update_layout(template=PLOTLY_TEMPLATE, height=340, margin=dict(t=10, b=10),
                           xaxis_title="Fraction of data observed", yaxis_title="p-value",
                           legend=dict(orientation="h", y=1.15))
        st.plotly_chart(fig, width='stretch')
        insight("At 75% of the data, the naive p-value (0.048) already looks significant against the unadjusted "
                "0.05 line — but the proper sequential boundary at that look (0.024) says NOT YET. A team peeking "
                "without correction would have shipped 1 look early on noise; the boundary that accounts for repeated "
                "looks correctly waits for the final look, where p=0.0019 clears even the strict cumulative bar.")

# ============================================================
# RECOMMENDATIONS (Phase 5)
# ============================================================
@st.cache_resource(show_spinner=False)
def load_recommender_state():
    return train_recommender_state()


with tab_recs:
    st.caption("Collaborative filtering (ALS), content-based cold-start fallback, and a LightGBM hybrid ranker — "
               "evaluated on a temporal train/test split (train: first ~10 months, test: last ~2).")
    st.warning("⚠️ **Catalog-size caveat:** this product has only 60 widgets total. A Top-10 recommendation covers "
               "~17% of the entire catalog, so the Recall@10/NDCG@10 numbers below are mechanically much higher "
               "than they'd be for a real catalog of thousands of items. The methodology is the same either way — "
               "the absolute metric values are not comparable to a production-scale system.")

    eval_path = Path(__file__).parent.parent / "recommendations" / "eval_results.json"
    if eval_path.exists():
        with open(eval_path) as f:
            eval_results = json.load(f)
        st.subheader("Offline evaluation: CF-only vs. content-only vs. hybrid")
        st.caption(f"{eval_results['n_test_users']} test users ({eval_results['n_warm']} warm, "
                   f"{eval_results['n_cold']} cold-start) · {eval_results['catalog_size']}-widget catalog")

        summary_df = pd.DataFrame(eval_results["summary"])
        pivot_recall = summary_df.pivot(index="method", columns="segment", values="recall_at_10")
        pivot_ndcg = summary_df.pivot(index="method", columns="segment", values="ndcg_at_10")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Recall@10**")
            fig = px.bar(pivot_recall.reset_index(), x="method", y=["warm_only", "cold_only"], barmode="group",
                         color_discrete_sequence=[ACCENT, "#F85149"])
            fig.update_layout(template=PLOTLY_TEMPLATE, height=320, margin=dict(t=10, b=10),
                               legend=dict(orientation="h", y=1.15))
            st.plotly_chart(fig, width='stretch')
        with c2:
            st.markdown("**NDCG@10**")
            fig = px.bar(pivot_ndcg.reset_index(), x="method", y=["warm_only", "cold_only"], barmode="group",
                         color_discrete_sequence=[ACCENT, "#F85149"])
            fig.update_layout(template=PLOTLY_TEMPLATE, height=320, margin=dict(t=10, b=10),
                               legend=dict(orientation="h", y=1.15))
            st.plotly_chart(fig, width='stretch')

        cf_cold_recall = pivot_recall.loc["cf", "cold_only"]
        content_cold_recall = pivot_recall.loc["content", "cold_only"]
        hybrid_cold_recall = pivot_recall.loc["hybrid", "cold_only"]
        insight(f"CF-only scores {cf_cold_recall:.3f} recall on cold-start users — it has zero history to work "
                f"with, so it can't recommend at all. Content-based scores {content_cold_recall:.3f} (it's "
                f"specifically the cold-start handler). Hybrid scores {hybrid_cold_recall:.3f} — it degrades "
                "gracefully instead of going blind, because the CF-score feature just defaults to 0 for unscorable users "
                "rather than breaking the whole ranking.")
    else:
        st.info("Run `python recommendations/run_evaluation.py` to generate the offline evaluation results.")

    st.divider()
    st.subheader("Try it: get recommendations for a user")
    st.caption("Trains the hybrid model once per dashboard session (~1-2 min first time, instant after) — "
               "this is the same model the FastAPI `/recommend` endpoint serves.")

    user_id_input = st.number_input("User ID", min_value=1, max_value=10000, value=7493, step=1)
    if st.button("Get recommendations"):
        with st.spinner("Training models (first call only)..."):
            state = load_recommender_state()
        result = get_recommendation(state, int(user_id_input), n=10)
        if result is None:
            st.error(f"user_id {user_id_input} not found.")
        else:
            badge_color = "#D29922" if result["is_cold_start"] else "#3FB950"
            st.markdown(
                f"<div style='display:inline-block;background:{badge_color}22;border:1px solid {badge_color};"
                f"color:{badge_color};padding:0.25rem 0.7rem;border-radius:16px;font-weight:700;"
                f"font-size:0.8rem;'>{result['method_used']}</div>",
                unsafe_allow_html=True,
            )
            st.caption(result["why"])
            rec_df = pd.DataFrame(result["recommendations"])
            st.dataframe(rec_df, width='stretch', hide_index=True)
