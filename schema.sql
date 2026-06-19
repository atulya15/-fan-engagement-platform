-- ============================================================
-- Fan Engagement Platform — Schema
-- Simulates a sports/media gamification product (polls, trivia,
-- predictions, leaderboards) similar to LiveLike's widget suite.
-- ============================================================

-- Drop tables if rerunning (order matters due to FK constraints)
DROP TABLE IF EXISTS badges CASCADE;
DROP TABLE IF EXISTS user_points CASCADE;
DROP TABLE IF EXISTS widget_events CASCADE;
DROP TABLE IF EXISTS widgets CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ============================================================
-- users: core fan accounts
-- ============================================================
CREATE TABLE users (
    user_id       SERIAL PRIMARY KEY,
    signup_date   TIMESTAMPTZ NOT NULL,
    country       VARCHAR(100) NOT NULL,
    device_type   VARCHAR(20) NOT NULL CHECK (device_type IN ('iOS', 'Android', 'Web'))
);

-- ============================================================
-- sessions: each time a user opens the app
-- ============================================================
CREATE TABLE sessions (
    session_id      SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    app_open_time   TIMESTAMPTZ NOT NULL,
    app_close_time  TIMESTAMPTZ,
    platform        VARCHAR(20) NOT NULL CHECK (platform IN ('iOS', 'Android', 'Web')),
    CHECK (app_close_time IS NULL OR app_close_time >= app_open_time)
);

-- ============================================================
-- widgets: the gamification products themselves
-- ============================================================
CREATE TABLE widgets (
    widget_id     SERIAL PRIMARY KEY,
    widget_type   VARCHAR(20) NOT NULL CHECK (widget_type IN ('poll', 'trivia', 'prediction', 'leaderboard')),
    name          VARCHAR(150) NOT NULL,
    sport         VARCHAR(50) NOT NULL,
    launch_date   TIMESTAMPTZ NOT NULL
);

-- ============================================================
-- widget_events: every impression/interaction/completion
-- This is the core engagement fact table.
-- ============================================================
CREATE TABLE widget_events (
    event_id          BIGSERIAL PRIMARY KEY,
    widget_id         INTEGER NOT NULL REFERENCES widgets(widget_id) ON DELETE CASCADE,
    user_id           INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    session_id        INTEGER NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    event_type        VARCHAR(20) NOT NULL CHECK (event_type IN ('impression', 'interaction', 'completion')),
    event_timestamp   TIMESTAMPTZ NOT NULL,
    points_earned     INTEGER NOT NULL DEFAULT 0 CHECK (points_earned >= 0)
);

-- ============================================================
-- user_points: rolled-up leaderboard state per user
-- ============================================================
CREATE TABLE user_points (
    user_id        INTEGER PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    total_points   INTEGER NOT NULL DEFAULT 0,
    current_rank   INTEGER,
    last_updated   TIMESTAMPTZ NOT NULL
);

-- ============================================================
-- badges: achievement unlocks per user
-- ============================================================
CREATE TABLE badges (
    badge_id     SERIAL PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    badge_name   VARCHAR(100) NOT NULL,
    earned_date  TIMESTAMPTZ NOT NULL
);

-- ============================================================
-- Indexes — these matter once widget_events has hundreds of
-- thousands of rows and we start running DAU/WAU/retention queries
-- ============================================================
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_open_time ON sessions(app_open_time);

CREATE INDEX idx_widget_events_user_id ON widget_events(user_id);
CREATE INDEX idx_widget_events_widget_id ON widget_events(widget_id);
CREATE INDEX idx_widget_events_session_id ON widget_events(session_id);
CREATE INDEX idx_widget_events_timestamp ON widget_events(event_timestamp);
CREATE INDEX idx_widget_events_type ON widget_events(event_type);

CREATE INDEX idx_badges_user_id ON badges(user_id);