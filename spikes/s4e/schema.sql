CREATE TABLE e_identity(version text PRIMARY KEY CHECK(version='s4-e-1.0.0'));
INSERT INTO e_identity VALUES('s4-e-1.0.0');
CREATE TABLE e_jobs(
 id text PRIMARY KEY,
 project text NOT NULL,
 run_id text NOT NULL,
 assignment_id text NOT NULL UNIQUE REFERENCES b_assignments(id),
 attempt bigint NOT NULL,
 fence bigint NOT NULL,
 generation text NOT NULL,
 binding jsonb NOT NULL,
 state text NOT NULL CHECK(state IN ('prepared','consumed','unresolved','failed')),
 incident_open boolean NOT NULL DEFAULT false,
 epoch bigint NOT NULL DEFAULT 0,
 recovery_fence bigint NOT NULL,
 resource jsonb,
 cleanup_proof jsonb,
 UNIQUE(project,run_id)
);
