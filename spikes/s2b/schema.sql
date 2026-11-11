-- Additive model in a fresh S2-B namespace only. Never migrate S2-A schema.
CREATE TABLE model_identity (version text PRIMARY KEY);
INSERT INTO model_identity VALUES ('s2b-1.0.0');
ALTER TABLE runs DROP CONSTRAINT runs_state_check;
ALTER TABLE runs ADD CHECK (state IN ('queued','checking','recovering','cancelling','completed','cancelled','failed'));
ALTER TABLE runs ADD COLUMN max_attempts integer NOT NULL DEFAULT 2 CHECK (max_attempts > 0);
ALTER TABLE runs ADD COLUMN stop_reason text;
ALTER TABLE runs ADD COLUMN terminal_reason text;
ALTER TABLE runs ADD COLUMN cleanup_request text;
ALTER TABLE runs ADD COLUMN cleanup_deadline timestamptz;
ALTER TABLE claims DROP CONSTRAINT claims_pkey;
ALTER TABLE claims ADD PRIMARY KEY(run_id, attempt);
ALTER TABLE receipts DROP CONSTRAINT receipts_pkey;
ALTER TABLE receipts ADD PRIMARY KEY(run_id, attempt);
CREATE TABLE attempt_inputs (
    run_id text NOT NULL REFERENCES runs(id),
    attempt bigint NOT NULL,
    fence bigint NOT NULL,
    bundle bytea NOT NULL,
    bundle_sha text NOT NULL,
    assessment bytea NOT NULL,
    assessment_sha text NOT NULL,
    PRIMARY KEY(run_id,attempt)
);
CREATE TABLE cleanup_requests (
    id text PRIMARY KEY,
    run_id text NOT NULL REFERENCES runs(id),
    attempt bigint NOT NULL,
    fence bigint NOT NULL,
    status text NOT NULL CHECK(status IN ('pending','acked')),
    observation bytea,
    UNIQUE(run_id,attempt)
);
ALTER TABLE runs ADD FOREIGN KEY(cleanup_request) REFERENCES cleanup_requests(id);
CREATE TABLE incidents (
    request_id text PRIMARY KEY REFERENCES cleanup_requests(id),
    reason text NOT NULL,
    resolved boolean NOT NULL DEFAULT false
);
