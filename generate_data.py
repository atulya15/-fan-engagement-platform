"""
generate_data.py
=================
Generates realistic synthetic data for the Fan Engagement Platform
(a sports/media gamification product: polls, trivia, predictions,
leaderboards — modeled after LiveLike-style engagement widgets).

DESIGN PRINCIPLES
------------------
1. Power-law engagement: ~20% of users drive ~78% of all activity,
   modeled with a Pareto-weighted rank transform (not uniform random).
   This mirrors real mobile/media app engagement curves.
2. Signups are front-loaded (launch spike, then a tapering trickle)
   rather than spread flat across the window.
3. Funnel realism: impressions > interactions > completions, with
   conversion rates that vary slightly by widget_type (polls convert
   higher than trivia, for example — polls take one tap).
4. All inserts use execute_values for fast batch loading. The large
   widget_events insert is chunked with retry/reconnect logic since
   free-tier pooled Postgres connections can drop on long-running
   batch operations.
5. Day-offsets for signups/sessions use resampling (not clipping) to
   stay within the simulation window — clipping piles every overflow
   value onto the single boundary day, producing an artificial spike
   on the last day of the window. Resampling preserves the natural
   shape of the exponential tail instead.
6. Script is idempotent — truncates and reseeds on every run.

USAGE
-----
    python generate_data.py
"""

import os
import random
from datetime import datetime, timedelta, timezone

import hashlib
import numpy as np
import psycopg2
from psycopg2.extras import execute_values, Json
from dotenv import load_dotenv
from faker import Faker

# ============================================================
# CONFIG
# ============================================================
load_dotenv()

N_USERS = 10000
SIM_MONTHS = 12
SIM_DAYS = SIM_MONTHS * 30
SIM_END = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
SIM_START = SIM_END - timedelta(days=SIM_DAYS)

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
RNG = np.random.default_rng(RANDOM_SEED)

fake = Faker()
Faker.seed(RANDOM_SEED)

COUNTRIES = [
    "United States", "United Kingdom", "India", "Brazil", "Germany",
    "Canada", "Australia", "France", "Mexico", "Spain", "Nigeria",
    "Indonesia", "Japan", "South Korea", "Italy",
]
COUNTRY_WEIGHTS = [0.22, 0.10, 0.14, 0.08, 0.06, 0.05, 0.04, 0.05,
                   0.05, 0.04, 0.04, 0.04, 0.03, 0.03, 0.03]

DEVICE_TYPES = ["iOS", "Android", "Web"]
DEVICE_WEIGHTS = [0.45, 0.42, 0.13]

# Acquisition channels and their relative share of signups. Quality
# multipliers scale each user's engagement weight (session count target):
# organic/referral users tend to have higher intent (they sought the
# product out or were vouched for by a friend); paid_social/influencer
# users are lower-intent "spray and pray" acquisition, so they engage
# less per-capita even though they may be cheap to acquire in volume.
ACQUISITION_CHANNELS = ["organic", "paid_social", "referral", "influencer", "app_store_search"]
ACQUISITION_WEIGHTS = [0.40, 0.20, 0.15, 0.15, 0.10]
CHANNEL_QUALITY_MULTIPLIER = {
    "organic": 1.00,
    "referral": 1.15,
    "app_store_search": 1.05,
    "paid_social": 0.65,
    "influencer": 0.55,
}

# A user with no session in the trailing window is considered churned.
CHURN_WINDOW_DAYS = 45
# Among non-churned users, only the top points percentile converts to premium.
PREMIUM_POINTS_PERCENTILE = 0.75
PREMIUM_CONVERSION_PROB = 0.70

# ------------------------------------------------------------
# Experiment treatment effects. Assigning users to variants (Phase 1)
# without making the variant actually change behavior would make Phase
# 4's analysis engine find nothing to analyze -- these constants give
# each pre-built experiment a real, but modest and not artificially
# obvious, causal effect baked into the generated data, so the stats
# engine has something genuine to detect (or correctly fail to detect,
# if underpowered -- that's a real outcome too, not a bug).
#
#   - Push notification timing: ml_optimized sends get a session-count
#     multiplier on top of the channel-quality multiplier; morning is
#     the baseline, evening is slightly worse (notification fatigue
#     from a fixed evening slot competing with prime-time engagement
#     hours already in random_time_on_day's hour_weights).
#   - Personalized feed: treatment users get an explicit bonus session
#     injected at exactly day 7 (with some probability, not guaranteed,
#     so the effect has realistic variance rather than a suspiciously
#     clean split). This was NOT modeled by skewing the existing
#     session-timing distribution earlier -- that was tried first and
#     produced the WRONG sign: front-loading a user's FIXED session
#     count into the days right after signup necessarily pulls
#     probability mass AWAY from day 7+, which actively lowers "still
#     active by day 7" rather than raising it (caught by checking the
#     actual post-generation numbers, not assumed). An explicit
#     additive bonus session avoids that trap entirely.
#   - Onboarding steps: treatment users get a boosted impression-to-
#     interaction conversion probability, but ONLY on their first-ever
#     session -- modeling "a simpler onboarding flow gets a user to
#     their first action faster," not a permanent conversion-rate boost.
# ------------------------------------------------------------
PUSH_VARIANT_MULTIPLIER = {"morning": 1.00, "evening": 0.95, "ml_optimized": 1.18}
FEED_DECAY_DIVISOR = 2.2
FEED_TREATMENT_DAY7_BONUS_PROB = 0.45
ONBOARDING_TREATMENT_FIRST_SESSION_BOOST = 0.15  # additive, capped at 0.95

SPORTS = ["Football", "Basketball", "Cricket", "Soccer", "Baseball", "Tennis"]
WIDGET_TYPES = ["poll", "trivia", "prediction", "leaderboard"]
N_WIDGETS = 60  # spread across sports/types over the 12-month window

# Conversion rates differ slightly by widget_type — polls are one-tap,
# trivia/prediction require more thought, leaderboard is mostly passive viewing.
WIDGET_CONVERSION = {
    "poll":        {"impression_to_interaction": 0.45, "interaction_to_completion": 0.85},
    "trivia":      {"impression_to_interaction": 0.30, "interaction_to_completion": 0.55},
    "prediction":  {"impression_to_interaction": 0.32, "interaction_to_completion": 0.60},
    "leaderboard": {"impression_to_interaction": 0.20, "interaction_to_completion": 0.90},
}

POINTS_MAP = {"impression": 0, "interaction": 1, "completion": 5}


def widget_interaction_properties(widget_type: str) -> dict:
    """Free-form metadata attached to an 'interaction' event, varying by
    widget_type — the kind of thing a real event-properties bag holds
    (e.g. which poll option a user tapped, what score they predicted)."""
    if widget_type == "poll":
        return {"choice": random.choice(["A", "B", "C"])}
    if widget_type == "trivia":
        return {"answer_correct": random.random() < 0.6}
    if widget_type == "prediction":
        return {"predicted_score": random.randint(0, 5)}
    return {}

DB_URL = os.environ["DATABASE_URL"]


def get_conn():
    return psycopg2.connect(DB_URL)


def random_time_on_day(day: datetime, not_before: datetime | None = None) -> datetime:
    """Attach a random time-of-day to a date, weighted toward evenings
    (sports engagement skews toward evening/game-time hours).

    If not_before is given (used for a user's signup day, day_off=0 case),
    the resulting time is clamped to be >= not_before so we never generate
    a session that starts before the user's actual signup timestamp.
    """
    hour_weights = np.array([
        1, 1, 1, 1, 1, 1,      # 0-5 (night)
        2, 3, 4, 3, 3, 3,      # 6-11 (morning)
        4, 4, 5, 5, 5, 6,      # 12-17 (afternoon)
        9, 10, 10, 8, 6, 3,    # 18-23 (evening prime time)
    ], dtype=float)
    hour_weights /= hour_weights.sum()
    hour = RNG.choice(24, p=hour_weights)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    result = day.replace(hour=int(hour), minute=minute, second=second)
    if not_before is not None and result < not_before:
        remaining_seconds = int((day.replace(hour=23, minute=59, second=59) - not_before).total_seconds())
        if remaining_seconds <= 0:
            return not_before
        offset = random.randint(0, remaining_seconds)
        result = not_before + timedelta(seconds=offset)
    return result


def exponential_offsets_no_pileup(scale: float, n: int, max_val: int) -> np.ndarray:
    """
    Draw n values from an Exponential(scale) distribution, restricted to
    [0, max_val). Unlike np.clip (which piles up every overflow value onto
    the single boundary day — a visible artifact in any day-by-day chart),
    this resamples any value that overflows, preserving the natural shape
    of the distribution's tail instead of creating an artificial spike.
    """
    offsets = RNG.exponential(scale=scale, size=n)
    mask = offsets >= max_val
    attempts = 0
    while mask.any() and attempts < 50:
        offsets[mask] = RNG.exponential(scale=scale, size=int(mask.sum()))
        mask = offsets >= max_val
        attempts += 1
    # Extremely rare stragglers after 50 resamples: safe to clip, negligible count
    offsets = np.clip(offsets, 0, max_val - 1)
    return offsets.astype(int)


# ============================================================
# STEP 1: USERS
# ============================================================
def generate_signup_dates(n_users: int) -> list[datetime]:
    """Front-loaded signups: launch spike then exponential taper."""
    decay_scale = SIM_DAYS / 4
    day_offsets = exponential_offsets_no_pileup(decay_scale, n_users, SIM_DAYS)
    return [
        random_time_on_day(SIM_START + timedelta(days=int(off)))
        for off in day_offsets
    ]


def generate_users(n_users: int):
    signup_dates = generate_signup_dates(n_users)
    countries = RNG.choice(COUNTRIES, size=n_users, p=COUNTRY_WEIGHTS)
    devices = RNG.choice(DEVICE_TYPES, size=n_users, p=DEVICE_WEIGHTS)
    channels = RNG.choice(ACQUISITION_CHANNELS, size=n_users, p=ACQUISITION_WEIGHTS)
    return [
        (signup_dates[i], countries[i], devices[i], channels[i])
        for i in range(n_users)
    ]


# ============================================================
# STEP 2: ENGAGEMENT WEIGHT (power-law) PER USER
# ============================================================
def generate_engagement_weights(n_users: int, channels: np.ndarray, push_variants: np.ndarray) -> np.ndarray:
    """
    Returns a session-count target per user following a power-law-like
    curve: ~20% of users generate ~78% of total sessions.
    Calibrated via rank-transform of a Pareto draw, validated to hit
    realistic 80/20-ish engagement skew (see project notes / README).

    The base power-law curve is then scaled per-user by two independent
    multipliers: their acquisition channel's quality multiplier (so
    organic/referral users skew toward higher engagement than
    paid_social/influencer users), and their push-notification-timing
    experiment variant (the Experiment C treatment effect) — without
    breaking the underlying power-law shape.
    """
    weights = RNG.pareto(1.5, n_users) + 1
    ranks = (np.argsort(np.argsort(weights)) + 0.5) / n_users  # uniform 0..1
    exponent = 6
    min_sessions, max_sessions = 1, 250
    counts = (ranks ** exponent) * (max_sessions - min_sessions) + min_sessions

    channel_mult = np.array([CHANNEL_QUALITY_MULTIPLIER[c] for c in channels])
    push_mult = np.array([PUSH_VARIANT_MULTIPLIER[v] for v in push_variants])
    counts = counts * channel_mult * push_mult

    return np.clip(counts.astype(int), min_sessions, max_sessions)


# ============================================================
# STEP 3: WIDGETS
# ============================================================
def generate_widgets(n_widgets: int):
    widgets = []
    for i in range(n_widgets):
        widget_type = random.choice(WIDGET_TYPES)
        sport = random.choice(SPORTS)
        name = f"{sport} {widget_type.capitalize()} #{i+1}"
        launch_offset = random.randint(0, SIM_DAYS - 14)
        launch_date = SIM_START + timedelta(days=launch_offset)
        widgets.append((widget_type, name, sport, launch_date))
    return widgets


# ============================================================
# STEP 4: SESSIONS + WIDGET_EVENTS (generated together per user)
# ============================================================
def generate_sessions_and_events(users_with_ids, widgets_with_ids, assignments_by_user):
    """
    NOTE: session_id here is a temporary local counter (1..N) used only
    to link events to sessions before either is inserted. The real
    auto-generated session_id from Postgres is mapped back in main().

    assignments_by_user: {user_id: {experiment_name: variant}} — used
    to apply the Experiment A (feed personalization) and Experiment B
    (onboarding) treatment effects inline, since both affect WHEN/HOW
    a session/interaction happens, not just how many.
    """
    sessions = []
    event_rows = []

    channels = np.array([u[2] for u in users_with_ids])
    push_variants = np.array([
        assignments_by_user[u[0]]["Push Notification Timing"] for u in users_with_ids
    ])
    engagement_weights = generate_engagement_weights(len(users_with_ids), channels, push_variants)
    widget_launch = {w[0]: w[4] for w in widgets_with_ids}
    widget_type_map = {w[0]: w[1] for w in widgets_with_ids}

    session_id_counter = 1

    for idx, (user_id, signup_date, _channel) in enumerate(users_with_ids):
        n_sessions = int(engagement_weights[idx])

        active_days = max((SIM_END - signup_date).days, 1)
        if active_days <= 0:
            continue

        exp = assignments_by_user[user_id]
        feed_is_treatment = exp["Personalized Feed vs Chronological"] == "treatment"
        onboarding_is_treatment = exp["Onboarding Steps Reduction"] == "treatment"

        day_offsets = list(exponential_offsets_no_pileup(active_days / FEED_DECAY_DIVISOR, n_sessions, active_days))

        # Experiment A treatment effect: an explicit bonus session at
        # exactly day 7, applied with some probability (not guaranteed)
        # so the effect has realistic variance. Additive, not a
        # redistribution of existing sessions -- see the constant's
        # comment above for why redistribution produced the wrong sign.
        if feed_is_treatment and active_days > 7 and random.random() < FEED_TREATMENT_DAY7_BONUS_PROB:
            day_offsets.append(7)

        sorted_offsets = sorted(day_offsets)

        for session_idx, day_off in enumerate(sorted_offsets):
            is_first_session = (session_idx == 0)

            session_day = signup_date + timedelta(days=int(day_off))
            not_before = signup_date if day_off == 0 else None
            open_time = random_time_on_day(session_day, not_before=not_before)
            duration_min = max(1, int(RNG.exponential(scale=6)))
            close_time = open_time + timedelta(minutes=duration_min)

            platform = random.choices(DEVICE_TYPES, weights=DEVICE_WEIGHTS)[0]

            sessions.append((session_id_counter, user_id, open_time, close_time, platform))

            live_widgets = [wid for wid, launch in widget_launch.items() if launch <= open_time]
            if not live_widgets:
                session_id_counter += 1
                continue

            n_impressions = min(len(live_widgets), int(RNG.poisson(3)) + 1)
            chosen_widgets = random.sample(live_widgets, n_impressions)

            for widget_id in chosen_widgets:
                w_type = widget_type_map[widget_id]
                conv = WIDGET_CONVERSION[w_type]

                impression_to_interaction = conv["impression_to_interaction"]
                if is_first_session and onboarding_is_treatment:
                    # Experiment B treatment effect: a simpler onboarding
                    # flow gets a user to their first action faster, on
                    # their very first session only -- not a permanent
                    # conversion-rate change.
                    impression_to_interaction = min(impression_to_interaction + ONBOARDING_TREATMENT_FIRST_SESSION_BOOST, 0.95)

                impression_ts = open_time + timedelta(
                    seconds=random.randint(0, max(duration_min * 60 - 1, 1))
                )
                event_rows.append((widget_id, user_id, session_id_counter,
                                    "impression", impression_ts, POINTS_MAP["impression"], {}))

                if random.random() < impression_to_interaction:
                    interaction_ts = min(
                        impression_ts + timedelta(seconds=random.randint(1, 30)),
                        close_time,
                    )
                    event_rows.append((widget_id, user_id, session_id_counter,
                                        "interaction", interaction_ts, POINTS_MAP["interaction"],
                                        widget_interaction_properties(w_type)))

                    if random.random() < conv["interaction_to_completion"]:
                        completion_ts = min(
                            interaction_ts + timedelta(seconds=random.randint(1, 60)),
                            close_time,
                        )
                        event_rows.append((widget_id, user_id, session_id_counter,
                                            "completion", completion_ts, POINTS_MAP["completion"], {}))

            session_id_counter += 1

    return sessions, event_rows


# ============================================================
# STEP 5: USER_POINTS (rolled up from completed events)
# ============================================================
def generate_user_points(user_ids, event_rows):
    """Aggregate points per user and assign standard competition rank
    (ties share a rank, e.g. 1,2,2,4 — matches SQL RANK() semantics)."""
    totals = {uid: 0 for uid in user_ids}
    for (_, user_id, _, _, _, points, _properties) in event_rows:
        totals[user_id] += points

    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    rows = []
    rank = 0
    last_points = None
    for i, (uid, pts) in enumerate(ranked):
        if pts != last_points:
            rank = i + 1
            last_points = pts
        rows.append((uid, pts, rank, SIM_END))
    return rows


# ============================================================
# STEP 6: BADGES (awarded based on simple thresholds)
# ============================================================
def generate_badges(user_points_rows):
    badges = []
    for (uid, total_points, rank, _) in user_points_rows:
        earned = []
        if total_points > 0:
            earned.append("First Steps")
        if total_points >= 100:
            earned.append("Top 100 Fan" if rank <= 100 else "Century Club")
        if total_points >= 500:
            earned.append("Super Fan")
        for badge_name in earned:
            earned_date = SIM_START + timedelta(days=random.randint(1, SIM_DAYS - 1))
            badges.append((uid, badge_name, earned_date))
    return badges


# ============================================================
# STEP 7: USER_SEGMENT (churned / premium / free, computed post-hoc)
# ============================================================
def generate_user_segments(user_ids, sessions, user_points_rows):
    """
    Segment is derived from actual simulated behavior, not assigned
    up front, since "is this user premium/churned" is a function of
    what they did, not who they are at signup:
      - churned: no session in the trailing CHURN_WINDOW_DAYS of the
        simulation window (a user who never had a session at all also
        counts as churned).
      - premium: not churned, AND in the top points percentile, AND
        clears a random conversion check (not every highly-engaged
        user pays — this avoids a deterministic points-to-premium cliff).
      - free: everyone else.
    """
    last_session = {}
    for (_, user_id, open_time, _close, _platform) in sessions:
        if user_id not in last_session or open_time > last_session[user_id]:
            last_session[user_id] = open_time

    points_by_user = {uid: pts for (uid, pts, _rank, _ts) in user_points_rows}
    points_values = sorted(points_by_user.values())
    if points_values:
        cutoff_idx = int(len(points_values) * PREMIUM_POINTS_PERCENTILE)
        cutoff_idx = min(cutoff_idx, len(points_values) - 1)
        premium_points_cutoff = points_values[cutoff_idx]
    else:
        premium_points_cutoff = 0

    churn_cutoff = SIM_END - timedelta(days=CHURN_WINDOW_DAYS)

    rows = []
    for uid in user_ids:
        last_seen = last_session.get(uid)
        is_churned = last_seen is None or last_seen < churn_cutoff
        if is_churned:
            segment = "churned"
        elif points_by_user.get(uid, 0) >= premium_points_cutoff and random.random() < PREMIUM_CONVERSION_PROB:
            segment = "premium"
        else:
            segment = "free"
        rows.append((uid, segment))
    return rows


# ============================================================
# STEP 8: EXPERIMENTS (pre-built A/B tests, baked into generation
# so Phase 4's experimentation engine has ready-made data)
# ============================================================
EXPERIMENTS = [
    {
        "name": "Personalized Feed vs Chronological",
        "hypothesis": "A personalized content/widget feed increases Day-7 retention vs a chronological feed.",
        "metric": "day_7_retention",
        "variants": ["control", "treatment"],
        "variant_weights": [0.5, 0.5],
    },
    {
        "name": "Onboarding Steps Reduction",
        "hypothesis": "Reducing onboarding from 5 steps to 2 steps increases signup-to-first-engagement conversion.",
        "metric": "signup_to_first_engagement_conversion",
        "variants": ["control", "treatment"],
        "variant_weights": [0.5, 0.5],
    },
    {
        "name": "Push Notification Timing",
        "hypothesis": "ML-optimized push notification timing increases session frequency vs fixed morning/evening sends.",
        "metric": "session_frequency",
        "variants": ["morning", "evening", "ml_optimized"],
        "variant_weights": [1 / 3, 1 / 3, 1 / 3],
    },
]


def generate_experiment_assignments(user_ids, experiment_rows):
    """
    Deterministic hash-based assignment: a user's variant is a stable
    function of (user_id, experiment_id), not a fresh random draw.
    This is what real experimentation platforms do — it guarantees a
    user sees the same variant on every visit without needing to store
    a sticky cookie/session flag, and it's reproducible across reruns.
    """
    assignments = []
    for (experiment_id, exp_def) in zip(
        [row[0] for row in experiment_rows], EXPERIMENTS
    ):
        variants = exp_def["variants"]
        weights = exp_def["variant_weights"]
        cum_weights = np.cumsum(weights)
        for uid in user_ids:
            # hashlib (not Python's built-in hash()) because hash() is
            # salted per-process via PYTHONHASHSEED — it would assign
            # different variants to the same user on every rerun.
            digest = hashlib.md5(f"{uid}:{experiment_id}".encode()).hexdigest()
            bucket = (int(digest, 16) % 10_000) / 10_000
            variant_idx = int(np.searchsorted(cum_weights, bucket))
            variant_idx = min(variant_idx, len(variants) - 1)
            variant = variants[variant_idx]
            assigned_at = SIM_START + timedelta(days=random.randint(0, max(SIM_DAYS - 1, 0)))
            assignments.append((uid, experiment_id, variant, assigned_at))
    return assignments


# ============================================================
# MAIN
# ============================================================
def main():
    conn = get_conn()
    cur = conn.cursor()

    print("Truncating existing data...")
    cur.execute("""
        TRUNCATE experiment_assignments, experiments, badges, user_points,
                 widget_events, sessions, widgets, users
        RESTART IDENTITY CASCADE;
    """)
    conn.commit()

    print(f"Simulation window: {SIM_START.date()} -> {SIM_END.date()} ({SIM_DAYS} days)")

    # --- USERS ---
    print(f"Generating {N_USERS} users...")
    users = generate_users(N_USERS)
    inserted_users = execute_values(
        cur,
        "INSERT INTO users (signup_date, country, device_type, acquisition_channel) VALUES %s "
        "RETURNING user_id, signup_date",
        users,
        page_size=1000,
        fetch=True,
    )  # fetch=True is REQUIRED so execute_values accumulates RETURNING rows
       # across ALL pages, not just the last page's cursor state.
    conn.commit()
    print(f"  -> {len(inserted_users)} users inserted")

    # --- WIDGETS ---
    print(f"Generating {N_WIDGETS} widgets...")
    widgets = generate_widgets(N_WIDGETS)
    inserted_widgets = execute_values(
        cur,
        "INSERT INTO widgets (widget_type, name, sport, launch_date) VALUES %s "
        "RETURNING widget_id, widget_type, launch_date",
        widgets,
        page_size=1000,
        fetch=True,
    )
    conn.commit()
    print(f"  -> {len(inserted_widgets)} widgets inserted")

    widgets_with_ids = [(w[0], w[1], None, None, w[2]) for w in inserted_widgets]
    # inserted_users preserves input order (single bulk INSERT...VALUES, no
    # ORDER BY), so zipping positionally with the original `users` list to
    # recover acquisition_channel is safe here.
    users_with_ids = [(inserted_users[i][0], inserted_users[i][1], users[i][3])
                       for i in range(len(inserted_users))]
    user_ids = [u[0] for u in users_with_ids]

    # --- EXPERIMENTS + EXPERIMENT_ASSIGNMENTS ---
    # Generated BEFORE sessions/events, not after: the feed-personalization
    # and onboarding treatment effects need each user's variant assignment
    # available while sessions/events are being generated (see
    # generate_sessions_and_events), not as a label applied after the fact.
    print(f"Seeding {len(EXPERIMENTS)} experiments...")
    experiment_insert_rows = [
        (exp["name"], exp["hypothesis"], exp["metric"], SIM_START,
         SIM_START + timedelta(days=30), "completed")
        for exp in EXPERIMENTS
    ]
    inserted_experiments = execute_values(
        cur,
        """INSERT INTO experiments
           (experiment_name, hypothesis, metric, start_date, end_date, status)
           VALUES %s RETURNING experiment_id""",
        experiment_insert_rows,
        page_size=100,
        fetch=True,
    )
    conn.commit()
    print(f"  -> {len(inserted_experiments)} experiments inserted")

    print("Assigning users to experiment variants (deterministic hash-based)...")
    assignment_rows = generate_experiment_assignments(user_ids, inserted_experiments)
    execute_values(
        cur,
        """INSERT INTO experiment_assignments
           (user_id, experiment_id, variant, assigned_at) VALUES %s""",
        assignment_rows,
        page_size=2000,
    )
    conn.commit()
    print(f"  -> {len(assignment_rows)} experiment_assignments inserted")

    experiment_id_to_name = {inserted_experiments[i][0]: EXPERIMENTS[i]["name"] for i in range(len(EXPERIMENTS))}
    assignments_by_user = {uid: {} for uid in user_ids}
    for (uid, exp_id, variant, _assigned_at) in assignment_rows:
        assignments_by_user[uid][experiment_id_to_name[exp_id]] = variant

    # --- SESSIONS + WIDGET_EVENTS ---
    print("Generating sessions and widget events (this is the big one)...")
    sessions, event_rows = generate_sessions_and_events(users_with_ids, widgets_with_ids, assignments_by_user)
    print(f"  -> {len(sessions)} sessions, {len(event_rows)} widget_events generated")

    print("Inserting sessions...")
    sessions_no_id = [(s[1], s[2], s[3], s[4]) for s in sessions]
    real_session_ids_rows = execute_values(
        cur,
        "INSERT INTO sessions (user_id, app_open_time, app_close_time, platform) VALUES %s "
        "RETURNING session_id",
        sessions_no_id,
        page_size=2000,
        fetch=True,
    )
    real_session_ids = [r[0] for r in real_session_ids_rows]
    conn.commit()
    print(f"  -> {len(real_session_ids)} sessions inserted")

    temp_to_real = {sessions[i][0]: real_session_ids[i] for i in range(len(sessions))}

    # --- WIDGET_EVENTS (chunked with retry/reconnect) ---
    print("Inserting widget_events (batched, with retry on connection drop)...")
    events_final = [
        (e[0], e[1], temp_to_real[e[2]], e[3], e[4], e[5], Json(e[6]))
        for e in event_rows
    ]

    CHUNK_SIZE = 2000
    total_inserted = 0
    i = 0
    while i < len(events_final):
        chunk = events_final[i:i + CHUNK_SIZE]
        for attempt in range(3):
            try:
                execute_values(
                    cur,
                    """INSERT INTO widget_events
                       (widget_id, user_id, session_id, event_type, event_timestamp, points_earned, properties)
                       VALUES %s""",
                    chunk,
                    page_size=CHUNK_SIZE,
                )
                conn.commit()
                total_inserted += len(chunk)
                break
            except psycopg2.OperationalError as e:
                print(f"    connection dropped on chunk {i}-{i+len(chunk)}, "
                      f"attempt {attempt+1}/3: {e}")
                try:
                    conn.close()
                except Exception:
                    pass
                conn = get_conn()
                cur = conn.cursor()
                if attempt == 2:
                    raise
        i += CHUNK_SIZE
        if (i // CHUNK_SIZE) % 20 == 0:
            print(f"    ... {total_inserted}/{len(events_final)} widget_events inserted so far")

    print(f"  -> {total_inserted} widget_events inserted")

    # --- USER_POINTS ---
    print("Rolling up user_points...")
    user_points_rows = generate_user_points(user_ids, events_final)
    execute_values(
        cur,
        "INSERT INTO user_points (user_id, total_points, current_rank, last_updated) VALUES %s",
        user_points_rows,
        page_size=2000,
    )
    conn.commit()
    print(f"  -> {len(user_points_rows)} user_points rows inserted")

    # --- BADGES ---
    print("Generating badges...")
    badges = generate_badges(user_points_rows)
    if badges:
        execute_values(
            cur,
            "INSERT INTO badges (user_id, badge_name, earned_date) VALUES %s",
            badges,
            page_size=2000,
        )
        conn.commit()
    print(f"  -> {len(badges)} badges inserted")

    # --- USER_SEGMENT (post-hoc, derived from actual session/points behavior) ---
    print("Computing user_segment (free/premium/churned)...")
    segment_rows = generate_user_segments(user_ids, sessions, user_points_rows)
    execute_values(
        cur,
        """UPDATE users SET user_segment = data.segment
           FROM (VALUES %s) AS data (user_id, segment)
           WHERE users.user_id = data.user_id""",
        segment_rows,
        page_size=2000,
    )
    conn.commit()
    seg_counts = {}
    for (_uid, seg) in segment_rows:
        seg_counts[seg] = seg_counts.get(seg, 0) + 1
    print(f"  -> segments: {seg_counts}")

    cur.close()
    conn.close()
    print("\n Data generation complete.")

if __name__ == "__main__":
    main()