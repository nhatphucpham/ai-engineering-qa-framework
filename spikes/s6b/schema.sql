CREATE TABLE model_identity(version text PRIMARY KEY);
INSERT INTO model_identity VALUES('s6b-1.0.0');
CREATE TABLE control(id integer PRIMARY KEY CHECK(id=1),bootstrapped boolean NOT NULL DEFAULT false,
    dummy_hash text NOT NULL,serial bigint NOT NULL DEFAULT 0,login_count integer NOT NULL DEFAULT 0,
    login_window timestamptz NOT NULL DEFAULT clock_timestamp());
CREATE TABLE accounts(id text PRIMARY KEY,password_hash text NOT NULL,enabled boolean NOT NULL DEFAULT true,
    admin boolean NOT NULL DEFAULT false,must_change boolean NOT NULL DEFAULT true,epoch bigint NOT NULL DEFAULT 1);
CREATE TABLE login_buckets(bucket text PRIMARY KEY,attempts integer NOT NULL,window_start timestamptz NOT NULL);
CREATE TABLE families(id text PRIMARY KEY,user_id text NOT NULL REFERENCES accounts(id),epoch bigint NOT NULL,
    generation bigint NOT NULL,revoked boolean NOT NULL DEFAULT false,expires timestamptz NOT NULL);
CREATE TABLE access_tokens(digest text PRIMARY KEY,family text NOT NULL REFERENCES families(id),generation bigint NOT NULL,
    expires timestamptz NOT NULL);
CREATE TABLE refresh_tokens(digest text PRIMARY KEY,family text NOT NULL REFERENCES families(id),generation bigint NOT NULL,
    expires timestamptz NOT NULL,used boolean NOT NULL DEFAULT false,UNIQUE(family,generation));
CREATE TABLE projects(id text PRIMARY KEY,enabled boolean NOT NULL DEFAULT true);
CREATE TABLE members(project text NOT NULL REFERENCES projects(id),user_id text NOT NULL REFERENCES accounts(id),
    role text NOT NULL CHECK(role IN('Owner','Runner','Viewer')),PRIMARY KEY(project,user_id));
CREATE UNIQUE INDEX one_owner ON members(project) WHERE role='Owner';
CREATE TABLE grants(id text PRIMARY KEY,user_id text NOT NULL REFERENCES accounts(id),project text NOT NULL REFERENCES projects(id),
    epoch bigint NOT NULL,actions jsonb NOT NULL);
CREATE TABLE qa_runs(id text PRIMARY KEY,project text NOT NULL REFERENCES projects(id),initiator text NOT NULL REFERENCES accounts(id),
    state text NOT NULL CHECK(state IN('queued','cancelled')),version bigint NOT NULL DEFAULT 1);
CREATE TABLE audit(sequence bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,user_id text,operation text NOT NULL);
