CREATE TABLE authority_identity(version text PRIMARY KEY);
INSERT INTO authority_identity VALUES('iap-b-1.0.0');
CREATE TABLE b_services(id text PRIMARY KEY,kind text NOT NULL CHECK(kind IN('scheduler','worker')),
    epoch bigint NOT NULL CHECK(epoch>0),enabled boolean NOT NULL,projects jsonb NOT NULL);
CREATE TABLE b_credentials(digest text PRIMARY KEY,service_id text NOT NULL REFERENCES b_services(id),
    epoch bigint NOT NULL,audience text NOT NULL,expires timestamptz NOT NULL,UNIQUE(service_id,epoch));
CREATE TABLE b_heads(project text NOT NULL,run_id text NOT NULL,attempt bigint NOT NULL CHECK(attempt>=0),
    fence bigint NOT NULL CHECK(fence>=0),PRIMARY KEY(project,run_id),
    FOREIGN KEY(project,run_id) REFERENCES app_runs(project,id));
CREATE TABLE b_assignments(id text PRIMARY KEY,project text NOT NULL,run_id text NOT NULL,
    attempt bigint NOT NULL,fence bigint NOT NULL,scheduler_id text NOT NULL REFERENCES b_services(id),
    scheduler_epoch bigint NOT NULL,worker_id text NOT NULL REFERENCES b_services(id),worker_epoch bigint NOT NULL,
    expires timestamptz NOT NULL,state text NOT NULL CHECK(state IN('active','retired')),
    UNIQUE(project,run_id,attempt),FOREIGN KEY(project,run_id) REFERENCES b_heads(project,run_id));
CREATE TABLE b_audit(sequence bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,actor_kind text,
    actor_id text,project text,run_id text,operation text NOT NULL,
    FOREIGN KEY(project,run_id) REFERENCES app_runs(project,id) DEFERRABLE INITIALLY DEFERRED);
