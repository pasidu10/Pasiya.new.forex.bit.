-- Users table for Telegram bot users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    language TEXT DEFAULT 'en',
    is_active BOOLEAN DEFAULT TRUE,
    is_banned BOOLEAN DEFAULT FALSE,
    is_admin BOOLEAN DEFAULT FALSE,
    is_premium BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_interaction TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    referral_code TEXT,
    referred_by BIGINT,
    free_signals_used INTEGER DEFAULT 0,
    settings JSONB DEFAULT '{}'::jsonb
);

-- Signals table for trading signals
CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    market_type TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    entry_price REAL NOT NULL,
    stop_loss REAL,
    take_profit_1 REAL,
    take_profit_2 REAL,
    take_profit_3 REAL,
    risk_reward_ratio REAL,
    confidence_score REAL,
    indicators JSONB DEFAULT '{}'::jsonb,
    patterns JSONB DEFAULT '[]'::jsonb,
    analysis_notes TEXT,
    created_by BIGINT,
    is_auto BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    expired_at TIMESTAMP WITH TIME ZONE,
    hit_target INTEGER DEFAULT 0,
    closed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Alerts table for price alerts
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    symbol TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    target_price REAL NOT NULL,
    condition_type TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_triggered BOOLEAN DEFAULT FALSE,
    triggered_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Statistics table for daily tracking
CREATE TABLE IF NOT EXISTS statistics (
    id SERIAL PRIMARY KEY,
    date DATE UNIQUE NOT NULL,
    signals_generated INTEGER DEFAULT 0,
    signals_hit INTEGER DEFAULT 0,
    signals_missed INTEGER DEFAULT 0,
    total_users INTEGER DEFAULT 0,
    new_users INTEGER DEFAULT 0,
    premium_users INTEGER DEFAULT 0,
    premium_revenue REAL DEFAULT 0,
    messages_sent INTEGER DEFAULT 0,
    broadcasts_sent INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Bot settings table
CREATE TABLE IF NOT EXISTS bot_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Premium subscriptions table
CREATE TABLE IF NOT EXISTS premium_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    plan_type TEXT NOT NULL,
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    payment_amount REAL,
    payment_method TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Signal performance tracking table
CREATE TABLE IF NOT EXISTS signal_performance (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    price REAL,
    status TEXT,
    notes TEXT
);

-- Referrals table
CREATE TABLE IF NOT EXISTS referrals (
    id SERIAL PRIMARY KEY,
    referrer_id BIGINT NOT NULL,
    referral_code TEXT NOT NULL,
    referred_user_id BIGINT NOT NULL,
    reward_given BOOLEAN DEFAULT FALSE,
    reward_type TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_is_premium ON users(is_premium) WHERE is_premium = TRUE;
CREATE INDEX IF NOT EXISTS idx_signals_is_active ON signals(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol);
CREATE INDEX IF NOT EXISTS idx_signals_created_at ON signals(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_user_id ON alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_is_active ON alerts(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_statistics_date ON statistics(date DESC);
