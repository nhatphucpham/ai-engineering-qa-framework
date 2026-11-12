CREATE TABLE application_identity(version text PRIMARY KEY);
INSERT INTO application_identity VALUES('iap-a-1.0.0');
CREATE TABLE app_policies(project text PRIMARY KEY REFERENCES projects(id),epoch bigint NOT NULL CHECK(epoch>0),
    config_version bigint NOT NULL CHECK(config_version>0),enabled boolean NOT NULL,actions jsonb NOT NULL,
    max_queued integer NOT NULL CHECK(max_queued>0));
CREATE TABLE app_grants(id text PRIMARY KEY,user_id text NOT NULL REFERENCES accounts(id),
    project text NOT NULL REFERENCES projects(id),credential_epoch bigint NOT NULL,policy_epoch bigint NOT NULL,
    config_version bigint NOT NULL,actions jsonb NOT NULL,expires timestamptz NOT NULL,revoked boolean NOT NULL DEFAULT false);
CREATE TABLE app_runs(project text NOT NULL REFERENCES projects(id),id text NOT NULL,
    initiator text NOT NULL REFERENCES accounts(id),state text NOT NULL CHECK(state IN('queued','cancelled')),
    version bigint NOT NULL CHECK(version>0),policy_epoch bigint NOT NULL,config_version bigint NOT NULL,
    candidate_digest text NOT NULL,input_digest text NOT NULL,PRIMARY KEY(project,id));
CREATE TABLE app_delegations(project text NOT NULL,run_id text NOT NULL,user_id text NOT NULL REFERENCES accounts(id),
    grant_id text NOT NULL REFERENCES app_grants(id),credential_epoch bigint NOT NULL,
    policy_epoch bigint NOT NULL,config_version bigint NOT NULL,actions jsonb NOT NULL,expires timestamptz NOT NULL,
    PRIMARY KEY(project,run_id),FOREIGN KEY(project,run_id) REFERENCES app_runs(project,id));
CREATE TABLE app_receipts(user_id text NOT NULL REFERENCES accounts(id),project text NOT NULL REFERENCES projects(id),
    operation text NOT NULL CHECK(operation IN('start','cancel')),client_key text NOT NULL,payload_digest text NOT NULL,
    result jsonb NOT NULL,PRIMARY KEY(user_id,project,operation,client_key));
CREATE TABLE app_outbox(project text NOT NULL,run_id text NOT NULL,sequence integer NOT NULL,
    event text NOT NULL CHECK(event IN('queued','cancelled')),run_version bigint NOT NULL,
    PRIMARY KEY(project,run_id,sequence),FOREIGN KEY(project,run_id) REFERENCES app_runs(project,id));
CREATE TABLE app_audit(sequence bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,user_id text,
    project text,run_id text,operation text NOT NULL,
    FOREIGN KEY(project,run_id) REFERENCES app_runs(project,id) DEFERRABLE INITIALLY DEFERRED);
