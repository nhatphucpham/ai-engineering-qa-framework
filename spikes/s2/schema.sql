-- Experiment model v1, not the production domain schema or RBAC.
CREATE TABLE runs (
    id text PRIMARY KEY,
    occurrence text NOT NULL UNIQUE,
    state text NOT NULL CHECK (state IN ('queued','checking','completed','cancelled')),
    version bigint NOT NULL,
    attempt bigint NOT NULL,
    fence bigint NOT NULL,
    expires timestamptz,
    cleanup_ok boolean NOT NULL DEFAULT true,
    policy_ok boolean NOT NULL DEFAULT true,
    bundle bytea NOT NULL,
    assessment bytea NOT NULL,
    bundle_sha text NOT NULL,
    assessment_sha text NOT NULL,
    report_id text UNIQUE,
    queued_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK ((state = 'completed') = (report_id IS NOT NULL))
);
CREATE TABLE claims (
    run_id text PRIMARY KEY REFERENCES runs(id),
    attempt bigint NOT NULL,
    fence bigint NOT NULL,
    backend integer NOT NULL,
    process integer NOT NULL
);
CREATE TABLE receipts (
    run_id text PRIMARY KEY REFERENCES runs(id),
    attempt bigint NOT NULL,
    fence bigint NOT NULL,
    version bigint NOT NULL,
    package_sha text NOT NULL
);
CREATE TABLE reports (
    id text PRIMARY KEY,
    run_id text NOT NULL UNIQUE REFERENCES runs(id),
    package bytea NOT NULL,
    package_sha text NOT NULL,
    package_length bigint NOT NULL,
    report_sha text NOT NULL
);
ALTER TABLE runs ADD CONSTRAINT report_ref FOREIGN KEY(report_id) REFERENCES reports(id) DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE outbox (
    id text PRIMARY KEY,
    run_id text NOT NULL UNIQUE REFERENCES runs(id),
    report_id text NOT NULL REFERENCES reports(id),
    sequence bigint NOT NULL,
    run_version bigint NOT NULL,
    acked boolean NOT NULL DEFAULT false,
    UNIQUE(run_id, sequence)
);
