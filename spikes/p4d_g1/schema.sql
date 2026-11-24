CREATE TABLE g1_control(version text PRIMARY KEY);
INSERT INTO g1_control VALUES('p4d-g1-1.0.0');
CREATE TABLE g1_streams(project text NOT NULL, id text NOT NULL, repo bigint NOT NULL, pr bigint NOT NULL,
    actor text NOT NULL, grant_id text NOT NULL, config integer NOT NULL, sources jsonb NOT NULL,
    cursor bigint NOT NULL DEFAULT 0, PRIMARY KEY(project,id), UNIQUE(project,repo,pr));
CREATE TABLE g1_proofs(project text NOT NULL, stream text NOT NULL, observation_digest text NOT NULL,
    plan jsonb NOT NULL, PRIMARY KEY(project,stream,observation_digest),
    FOREIGN KEY(project,stream) REFERENCES g1_streams(project,id));
CREATE TABLE g1_bindings(project text NOT NULL, id text NOT NULL, stream text NOT NULL,
    plan jsonb NOT NULL, quarantined boolean NOT NULL DEFAULT false, result jsonb,
    PRIMARY KEY(project,id));
CREATE UNIQUE INDEX g1_run_binding ON g1_bindings(project,(plan->>'run'));
CREATE TABLE g1_receipts(project text NOT NULL, stream text NOT NULL, id text NOT NULL,
    digest text NOT NULL, observation bytea NOT NULL, status text NOT NULL, reason text,
    binding text, PRIMARY KEY(project,stream,id));
CREATE TABLE g1_pages(project text NOT NULL, stream text NOT NULL, predecessor bigint NOT NULL,
    digest text NOT NULL, result jsonb NOT NULL, PRIMARY KEY(project,stream,predecessor));
