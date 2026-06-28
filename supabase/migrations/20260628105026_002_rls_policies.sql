-- Enable Row Level Security on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE statistics ENABLE ROW LEVEL SECURITY;
ALTER TABLE premium_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE signal_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE referrals ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_settings ENABLE ROW LEVEL SECURITY;

-- Users table policies (public read, service role has full access)
CREATE POLICY "users_select_all" ON users
    FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY "users_insert" ON users
    FOR INSERT TO anon, authenticated WITH CHECK (true);

CREATE POLICY "users_update" ON users
    FOR UPDATE TO anon, authenticated USING (true) WITH CHECK (true);

CREATE POLICY "users_service_full" ON users
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Signals table policies (public read for active signals)
CREATE POLICY "signals_select_all" ON signals
    FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY "signals_insert" ON signals
    FOR INSERT TO anon, authenticated WITH CHECK (true);

CREATE POLICY "signals_update" ON signals
    FOR UPDATE TO anon, authenticated USING (true) WITH CHECK (true);

CREATE POLICY "signals_service_full" ON signals
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Alerts table policies
CREATE POLICY "alerts_select_all" ON alerts
    FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY "alerts_insert" ON alerts
    FOR INSERT TO anon, authenticated WITH CHECK (true);

CREATE POLICY "alerts_update" ON alerts
    FOR UPDATE TO anon, authenticated USING (true) WITH CHECK (true);

CREATE POLICY "alerts_delete" ON alerts
    FOR DELETE TO anon, authenticated USING (true);

CREATE POLICY "alerts_service_full" ON alerts
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Bot settings policies (public read)
CREATE POLICY "settings_select" ON bot_settings
    FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY "settings_insert" ON bot_settings
    FOR INSERT TO anon, authenticated WITH CHECK (true);

CREATE POLICY "settings_update" ON bot_settings
    FOR UPDATE TO anon, authenticated USING (true) WITH CHECK (true);

CREATE POLICY "settings_service_full" ON bot_settings
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Statistics policies (public read)
CREATE POLICY "stats_select" ON statistics
    FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY "stats_insert" ON statistics
    FOR INSERT TO anon, authenticated WITH CHECK (true);

CREATE POLICY "stats_update" ON statistics
    FOR UPDATE TO anon, authenticated USING (true) WITH CHECK (true);

CREATE POLICY "stats_service_full" ON statistics
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Premium subscriptions policies
CREATE POLICY "premium_select" ON premium_subscriptions
    FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY "premium_insert" ON premium_subscriptions
    FOR INSERT TO anon, authenticated WITH CHECK (true);

CREATE POLICY "premium_update" ON premium_subscriptions
    FOR UPDATE TO anon, authenticated USING (true) WITH CHECK (true);

CREATE POLICY "premium_service_full" ON premium_subscriptions
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Referrals policies
CREATE POLICY "referrals_select" ON referrals
    FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY "referrals_insert" ON referrals
    FOR INSERT TO anon, authenticated WITH CHECK (true);

CREATE POLICY "referrals_service_full" ON referrals
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Signal performance policies
CREATE POLICY "sig_perf_select" ON signal_performance
    FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY "sig_perf_insert" ON signal_performance
    FOR INSERT TO anon, authenticated WITH CHECK (true);

CREATE POLICY "sig_perf_service_full" ON signal_performance
    FOR ALL TO service_role USING (true) WITH CHECK (true);
