-- Migration 114: Workspace AI Reviewer Hybrid Mode, Model Binding, and Revocable Governance.

CREATE TABLE IF NOT EXISTS workspace_review_policies (
    workspace_id            TEXT PRIMARY KEY REFERENCES workspaces(id) ON DELETE CASCADE,
    inherit_system_default  BOOLEAN NOT NULL DEFAULT TRUE,
    mode                    TEXT NOT NULL DEFAULT 'manual_only'
                            CHECK (mode IN ('manual_only', 'fallback_advisory', 'panel_advisory', 'consensus_automatic')),
    minimum_success         INTEGER NOT NULL DEFAULT 1,
    accept_rule             JSONB NOT NULL DEFAULT '{}',
    reject_rule             JSONB NOT NULL DEFAULT '{}',
    policy_version          INTEGER NOT NULL DEFAULT 1,
    updated_by              TEXT REFERENCES users(id) ON DELETE SET NULL,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS workspace_model_bindings (
    id                      TEXT PRIMARY KEY,
    workspace_id            TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    model_account_id        TEXT NOT NULL REFERENCES user_ai_keys(id) ON DELETE CASCADE,
    source_scope            TEXT NOT NULL CHECK (source_scope IN ('system', 'user')),
    offered_by              TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    allowed_usages          TEXT[] NOT NULL DEFAULT '{}',
    billing_owner           TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consent_status          TEXT NOT NULL DEFAULT 'pending'
                            CHECK (consent_status IN ('pending', 'approved', 'rejected')),
    approval_status         TEXT NOT NULL DEFAULT 'pending'
                            CHECK (approval_status IN ('pending', 'approved', 'rejected')),
    status                  TEXT NOT NULL DEFAULT 'active'
                            CHECK (status IN ('offered', 'active', 'paused', 'revoked', 'unavailable', 'disabled_by_admin')),
    priority                INTEGER NOT NULL DEFAULT 0,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at              TIMESTAMPTZ,
    UNIQUE (workspace_id, model_account_id)
);

CREATE TABLE IF NOT EXISTS review_policy_members (
    policy_id               TEXT NOT NULL REFERENCES workspace_review_policies(workspace_id) ON DELETE CASCADE,
    binding_id              TEXT NOT NULL REFERENCES workspace_model_bindings(id) ON DELETE CASCADE,
    priority                INTEGER NOT NULL DEFAULT 0,
    is_required             BOOLEAN NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (policy_id, binding_id)
);

CREATE TABLE IF NOT EXISTS review_runs (
    id                      TEXT PRIMARY KEY,
    review_item_id          TEXT NOT NULL REFERENCES review_queue(id) ON DELETE CASCADE,
    effective_policy_snapshot JSONB NOT NULL DEFAULT '{}',
    policy_version          INTEGER NOT NULL,
    execution_mode          TEXT NOT NULL,
    quorum_rules            JSONB NOT NULL DEFAULT '{}',
    run_status              TEXT NOT NULL CHECK (run_status IN ('running', 'completed', 'partial', 'inconclusive', 'failed')),
    final_action            TEXT NOT NULL CHECK (final_action IN ('advice_only', 'auto_accept', 'auto_reject', 'escalate_manual')),
    summary                 JSONB NOT NULL DEFAULT '{}',
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at             TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS review_attempts (
    id                      TEXT PRIMARY KEY,
    run_id                  TEXT NOT NULL REFERENCES review_runs(id) ON DELETE CASCADE,
    binding_id              TEXT REFERENCES workspace_model_bindings(id) ON DELETE SET NULL,
    status                  TEXT NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'timed_out', 'skipped_after_success', 'skipped_by_policy', 'cancelled_before_start', 'discarded_after_revocation')),
    provider                TEXT NOT NULL,
    model                   TEXT NOT NULL,
    model_version           TEXT,
    decision                TEXT CHECK (decision IN ('accept', 'reject', 'comment')),
    confidence              NUMERIC(4,3),
    reasoning               TEXT,
    error_category          TEXT,
    sanitized_error         TEXT,
    started_at              TIMESTAMPTZ,
    finished_at             TIMESTAMPTZ,
    prompt_tokens           INTEGER,
    completion_tokens       INTEGER,
    cost                    NUMERIC(10,6)
);

CREATE INDEX IF NOT EXISTS idx_workspace_model_bindings_ws
    ON workspace_model_bindings(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_review_runs_item
    ON review_runs(review_item_id);
CREATE INDEX IF NOT EXISTS idx_review_attempts_run
    ON review_attempts(run_id);
CREATE INDEX IF NOT EXISTS idx_review_policy_members_policy
    ON review_policy_members(policy_id);
