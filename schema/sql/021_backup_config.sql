CREATE TABLE IF NOT EXISTS system_config (
    key        TEXT PRIMARY KEY,
    value      JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO system_config (key, value) VALUES (
    'backup',
    '{"enabled": false, "path": "/backups", "interval_hours": 24, "keep_count": 7}'::jsonb
) ON CONFLICT DO NOTHING;
