-- S2-C additions in a fresh namespace only, preserving S2-A/B tables and history.
CREATE TABLE capacity_identity(version text PRIMARY KEY);
INSERT INTO capacity_identity VALUES ('s2c-1.0.0');
CREATE TABLE scheduler(id integer PRIMARY KEY CHECK(id=1),global_cap integer NOT NULL CHECK(global_cap>0),turn bigint NOT NULL);
INSERT INTO scheduler VALUES(1,3,0);
CREATE TABLE projects(project_id text PRIMARY KEY,cap integer NOT NULL CHECK(cap>0),last_served bigint NOT NULL DEFAULT 0);
ALTER TABLE runs ADD COLUMN project_id text REFERENCES projects(project_id);
CREATE TABLE admissions(
    turn bigint PRIMARY KEY,
    run_id text NOT NULL,
    attempt bigint NOT NULL,
    project_id text NOT NULL REFERENCES projects(project_id),
    eligible jsonb NOT NULL,
    occupancy jsonb NOT NULL,
    global_cap integer NOT NULL,
    project_cap integer NOT NULL,
    queue_age_ms numeric NOT NULL,
    backend integer NOT NULL,
    process integer NOT NULL,
    UNIQUE(run_id,attempt),
    FOREIGN KEY(run_id,attempt) REFERENCES claims(run_id,attempt)
);
