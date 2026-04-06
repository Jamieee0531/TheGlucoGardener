-- ═══════════════════════════════════════════════════════════════════
-- GlucoGardener — PostgreSQL Schema (Unified)
-- 目标数据库：华为云 PostgreSQL
-- 执行方式：psql -h <host> -U <user> -d glucogardener -f schema.sql
-- ═══════════════════════════════════════════════════════════════════

-- updated_at 自动维护触发器（替代 MySQL ON UPDATE CURRENT_TIMESTAMP）
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ─────────────────────────────────────────────────────────────────
-- 用户配置层
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    user_id              VARCHAR(36)    PRIMARY KEY,
    name                 VARCHAR(100),
    birth_year           INT,
    gender               VARCHAR(10)    CHECK (gender IN ('male', 'female', 'other')),
    waist_cm             NUMERIC(5,1),
    weight_kg            NUMERIC(5,1),
    height_cm            NUMERIC(5,1),
    avatar               VARCHAR(20)    DEFAULT 'avatar_1',
    language             VARCHAR(10)    DEFAULT 'English',
    onboarding_completed BOOLEAN        DEFAULT FALSE,
    conditions           TEXT[]         DEFAULT '{}',
    medications          TEXT[]         DEFAULT '{}',
    preferences          JSONB          DEFAULT '{}',
    created_at           TIMESTAMPTZ    DEFAULT NOW(),
    updated_at           TIMESTAMPTZ    DEFAULT NOW()
    -- BMI 不存储，应用层计算: weight_kg / (height_cm/100)^2
);
CREATE OR REPLACE TRIGGER users_set_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


CREATE TABLE IF NOT EXISTS user_weekly_patterns (
    id            BIGSERIAL      PRIMARY KEY,
    user_id       VARCHAR(36)    NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    day_of_week   SMALLINT       NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),  -- 0=Monday
    start_time    TIME           NOT NULL,
    end_time      TIME           NOT NULL,
    activity_type VARCHAR(50)    NOT NULL CHECK (activity_type IN ('resistance_training', 'cardio', 'hiit'))
);
CREATE INDEX IF NOT EXISTS idx_pattern_user ON user_weekly_patterns (user_id, day_of_week);


CREATE TABLE IF NOT EXISTS user_known_places (
    id          BIGSERIAL      PRIMARY KEY,
    user_id     VARCHAR(36)    NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    place_name  VARCHAR(100),
    place_type  VARCHAR(50),   -- 'home', 'gym', 'office'
    gps_lat     NUMERIC(10,7),
    gps_lng     NUMERIC(10,7)
);
CREATE INDEX IF NOT EXISTS idx_places_user ON user_known_places (user_id);


CREATE TABLE IF NOT EXISTS user_emergency_contacts (
    id           BIGSERIAL      PRIMARY KEY,
    user_id      VARCHAR(36)    NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    contact_name VARCHAR(100)   NOT NULL,
    phone_number VARCHAR(20)    NOT NULL,
    relationship VARCHAR(50),
    notify_on    JSONB          NOT NULL DEFAULT '[]'
    -- allowed values: "hard_low_glucose", "hard_high_hr", "data_gap"
);
CREATE INDEX IF NOT EXISTS idx_contacts_user ON user_emergency_contacts (user_id);


CREATE TABLE IF NOT EXISTS user_friends (
    id         BIGSERIAL      PRIMARY KEY,
    user_id    VARCHAR(36)    NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    friend_id  VARCHAR(36)    NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ    DEFAULT NOW(),
    UNIQUE (user_id, friend_id)
);


-- ─────────────────────────────────────────────────────────────────
-- 数据摄入层（传感器原始数据）
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS user_cgm_log (
    id          BIGSERIAL      PRIMARY KEY,
    user_id     VARCHAR(36)    NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    recorded_at TIMESTAMPTZ    NOT NULL,
    glucose     NUMERIC(5,2)   NOT NULL,  -- mmol/L
    source      VARCHAR(20)    DEFAULT 'manual'  -- 'cgm' | 'manual'
);
CREATE INDEX IF NOT EXISTS idx_cgm_user_time ON user_cgm_log (user_id, recorded_at DESC);


CREATE TABLE IF NOT EXISTS user_hr_log (
    id          BIGSERIAL      PRIMARY KEY,
    user_id     VARCHAR(36)    NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    recorded_at TIMESTAMPTZ    NOT NULL,
    heart_rate  INT            NOT NULL,  -- bpm
    gps_lat     NUMERIC(10,7),
    gps_lng     NUMERIC(10,7)
);
CREATE INDEX IF NOT EXISTS idx_hr_user_time ON user_hr_log (user_id, recorded_at DESC);


CREATE TABLE IF NOT EXISTS user_exercise_log (
    id              BIGSERIAL      PRIMARY KEY,
    user_id         VARCHAR(36)    NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    exercise_type   VARCHAR(50)    NOT NULL CHECK (exercise_type IN ('resistance_training', 'cardio', 'hiit', 'walking')),
    started_at      TIMESTAMPTZ    NOT NULL,
    ended_at        TIMESTAMPTZ    NOT NULL,
    avg_heart_rate  INT,
    calories_burned NUMERIC(7,1)
    -- duration_minutes 不存储，应用层计算: EXTRACT(EPOCH FROM (ended_at - started_at))/60
);
CREATE INDEX IF NOT EXISTS idx_ex_user_time ON user_exercise_log (user_id, started_at DESC);


-- ─────────────────────────────────────────────────────────────────
-- Chatbot 写入层
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS user_emotion_log (
    id            BIGSERIAL      PRIMARY KEY,
    user_id       VARCHAR(36)    NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    recorded_at   TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    user_input    TEXT           NOT NULL,
    emotion_label VARCHAR(50)    NOT NULL,
    source        VARCHAR(50)    DEFAULT 'meralion'
);
CREATE INDEX IF NOT EXISTS idx_emotion_log_user ON user_emotion_log (user_id, recorded_at DESC);


CREATE TABLE IF NOT EXISTS user_emotion_summary (
    id              BIGSERIAL      PRIMARY KEY,
    user_id         VARCHAR(36)    NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    summary_date    DATE           NOT NULL,
    summary_text    TEXT           NOT NULL,
    primary_emotion VARCHAR(50),
    UNIQUE (user_id, summary_date)
);
CREATE INDEX IF NOT EXISTS idx_summary_user ON user_emotion_summary (user_id, summary_date DESC);


CREATE TABLE IF NOT EXISTS user_food_log (
    id             BIGSERIAL      PRIMARY KEY,
    user_id        VARCHAR(36)    NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    recorded_at    TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    food_name      VARCHAR(100)   NOT NULL,
    meal_type      VARCHAR(10)    NOT NULL CHECK (meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')),
    gi_level       VARCHAR(10)    NOT NULL CHECK (gi_level IN ('high', 'medium', 'low')),
    total_calories NUMERIC(6,1)   NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_food_user_time ON user_food_log (user_id, recorded_at DESC);


-- Chatbot 长期记忆（新增）
CREATE TABLE IF NOT EXISTS user_facts (
    fact_id     UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     VARCHAR(36)    NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    content     TEXT           NOT NULL,
    category    VARCHAR(20)    NOT NULL CHECK (category IN ('social', 'lifestyle', 'emotion_trigger', 'event', 'preference')),
    confidence  NUMERIC(3,2)   DEFAULT 0.80,
    created_at  TIMESTAMPTZ    DEFAULT NOW(),
    expires_at  TIMESTAMPTZ,   -- NULL = 永久有效；event 类设具体时间
    source_date DATE
);
CREATE INDEX IF NOT EXISTS idx_facts_user ON user_facts (user_id, created_at DESC);


CREATE TABLE IF NOT EXISTS user_context (
    user_id        VARCHAR(36)    PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    health_context TEXT           DEFAULT '',  -- 稳定背景：家庭/习惯/情绪触发
    current_focus  TEXT           DEFAULT '',  -- 当前关注：近期焦虑/待处理事项
    long_term_bg   TEXT           DEFAULT '',  -- 基础背景：性格/长期模式
    updated_at     TIMESTAMPTZ    DEFAULT NOW()
);
CREATE OR REPLACE TRIGGER user_context_set_updated_at
    BEFORE UPDATE ON user_context
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


-- ─────────────────────────────────────────────────────────────────
-- Pipeline 聚合层
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS user_glucose_daily_stats (
    id             BIGSERIAL      PRIMARY KEY,
    user_id        VARCHAR(36)    NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    stat_date      DATE           NOT NULL,
    avg_glucose    NUMERIC(5,2),
    peak_glucose   NUMERIC(5,2),
    nadir_glucose  NUMERIC(5,2),
    glucose_sd     NUMERIC(5,2),
    tir_percent    NUMERIC(5,1),   -- 目标范围内 % [3.9, 10.0]
    tbr_percent    NUMERIC(5,1),   -- 低于范围 % < 3.9
    tar_percent    NUMERIC(5,1),   -- 高于范围 % > 10.0
    data_points    INT,
    is_realtime    BOOLEAN        DEFAULT FALSE,
    created_at     TIMESTAMPTZ    DEFAULT NOW(),
    updated_at     TIMESTAMPTZ    DEFAULT NOW(),
    UNIQUE (user_id, stat_date)
);
CREATE OR REPLACE TRIGGER daily_stats_set_updated_at
    BEFORE UPDATE ON user_glucose_daily_stats
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


CREATE TABLE IF NOT EXISTS user_glucose_weekly_profile (
    id                    BIGSERIAL      PRIMARY KEY,
    user_id               VARCHAR(36)    NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    profile_date          DATE           NOT NULL,  -- 窗口结束日
    window_start          DATE           NOT NULL,  -- profile_date - 6 天
    avg_glucose           NUMERIC(5,2),
    peak_glucose          NUMERIC(5,2),
    nadir_glucose         NUMERIC(5,2),
    glucose_sd            NUMERIC(5,2),
    cv_percent            NUMERIC(5,1),  -- SD/mean×100，< 36% 为稳定
    tir_percent           NUMERIC(5,1),
    tbr_percent           NUMERIC(5,1),
    tar_percent           NUMERIC(5,1),
    avg_delta_vs_prior_7d NUMERIC(5,2),  -- 负值=改善，正值=变差
    data_points           INT,
    coverage_percent      NUMERIC(5,1),  -- data_points / 1008 × 100
    created_at            TIMESTAMPTZ    DEFAULT NOW(),
    UNIQUE (user_id, profile_date)
);


-- ─────────────────────────────────────────────────────────────────
-- 任务与奖励层
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS dynamic_task_rule (
    rule_id           SERIAL         PRIMARY KEY,
    base_calorie      INT            NOT NULL DEFAULT 300,
    trigger_threshold NUMERIC(3,2)   DEFAULT 0.60,
    is_active         SMALLINT       DEFAULT 1  -- 1=active, 0=inactive
);


CREATE TABLE IF NOT EXISTS dynamic_task_log (
    task_id        BIGSERIAL      PRIMARY KEY,
    user_id        VARCHAR(36)    NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    task_content   TEXT           NOT NULL,
    created_at     TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    task_date      DATE,
    task_status    VARCHAR(18)    NOT NULL DEFAULT 'pending'
                                  CHECK (task_status IN ('pending', 'completed', 'expired', 'canceled')),
    target_lat     NUMERIC(10,8),
    target_lng     NUMERIC(10,8),
    completed_at   TIMESTAMPTZ,
    expired_at     TIMESTAMPTZ,
    reward_points  INT            DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_dynamic_task_user ON dynamic_task_log (user_id, created_at DESC);


CREATE TABLE IF NOT EXISTS routine_task_log (
    task_id        BIGSERIAL      PRIMARY KEY,
    user_id        VARCHAR(36)    NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    task_type      VARCHAR(50)    NOT NULL,  -- 'breakfast','lunch','dinner','weekly_waist','weekly_weight'
    period         VARCHAR(20)    NOT NULL,  -- e.g. '2026-03-13' 或 '2026-week9'
    task_status    VARCHAR(20)    NOT NULL DEFAULT 'pending'
                                  CHECK (task_status IN ('pending', 'completed', 'expired', 'canceled')),
    created_at     TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    completed_at   TIMESTAMPTZ,
    expired_at     TIMESTAMPTZ,
    reward_points  INT            DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_routine_task_user ON routine_task_log (user_id, created_at DESC);


CREATE TABLE IF NOT EXISTS reward_log (
    user_id             VARCHAR(36)  PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    total_points        INT          NOT NULL DEFAULT 0,
    accumulated_points  INT          NOT NULL DEFAULT 0,
    consumed_points     INT          NOT NULL DEFAULT 0,
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE OR REPLACE TRIGGER reward_log_set_updated_at
    BEFORE UPDATE ON reward_log
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


-- ─────────────────────────────────────────────────────────────────
-- 日志层
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS intervention_log (
    id             BIGSERIAL      PRIMARY KEY,
    user_id        VARCHAR(36)    NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    triggered_at   TIMESTAMPTZ    NOT NULL,
    trigger_type   VARCHAR(50),
    agent_decision TEXT,
    message_sent   TEXT,
    user_ack       BOOLEAN        DEFAULT FALSE,
    created_at     TIMESTAMPTZ    DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_intervention_user ON intervention_log (user_id, triggered_at DESC);


CREATE TABLE IF NOT EXISTS error_log (
    id          BIGSERIAL      PRIMARY KEY,
    service     VARCHAR(50),
    error_msg   TEXT,
    payload     TEXT,
    ts          TIMESTAMPTZ    DEFAULT NOW()
);


-- ─────────────────────────────────────────────────────────────────
-- Demo 用户（首次部署运行，已存在则跳过）
-- ─────────────────────────────────────────────────────────────────
INSERT INTO users (user_id, name, language, conditions, medications, preferences)
VALUES
    ('demo_en', 'Mr Tan',      'English', '{"Type 2 Diabetes"}',           '{"Metformin 1000mg"}',                 '{"diet":"halal"}'),
    ('demo_zh', '陈先生',       'Chinese', '{"Type 2 Diabetes","高血压"}',   '{"Metformin 500mg","Amlodipine 5mg"}', '{"diet":"低碳水"}'),
    ('demo_ms', 'Encik Ahmad', 'Malay',   '{"Type 2 Diabetes"}',           '{"Metformin 500mg"}',                  '{"diet":"halal"}'),
    ('demo_ta', 'Mr Kumar',    'Tamil',   '{"Type 2 Diabetes"}',           '{"Metformin 500mg"}',                  '{}')
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO reward_log (user_id) VALUES
    ('demo_en'), ('demo_zh'), ('demo_ms'), ('demo_ta')
ON CONFLICT (user_id) DO NOTHING;
