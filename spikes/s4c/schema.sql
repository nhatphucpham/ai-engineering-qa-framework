CREATE TABLE launch_identity(version text PRIMARY KEY CHECK(version='s4-c-1.0.0'));
INSERT INTO launch_identity VALUES('s4-c-1.0.0');
CREATE TABLE launch_jobs(
 id text PRIMARY KEY,
 project text NOT NULL,
 run_id text NOT NULL,
 assignment_id text NOT NULL UNIQUE REFERENCES b_assignments(id),
 attempt bigint NOT NULL,
 fence bigint NOT NULL,
 helper_generation text NOT NULL,
 state text NOT NULL CHECK(state IN ('prepared','consumed','cleaned')),
 container_id text,
 CHECK(state!='prepared' OR container_id IS NULL)
);
CREATE UNIQUE INDEX launch_one_unresolved ON launch_jobs(project,run_id) WHERE state!='cleaned';
