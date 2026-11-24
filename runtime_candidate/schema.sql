CREATE TABLE rt_control(id integer PRIMARY KEY CHECK(id=1),version text NOT NULL,instance text NOT NULL,
    nonce text NOT NULL,global_capacity integer NOT NULL CHECK(global_capacity>0));
CREATE TABLE rt_projects(project text PRIMARY KEY REFERENCES projects(id),config_version integer NOT NULL,
    policy_version integer NOT NULL,enabled boolean NOT NULL DEFAULT true);
CREATE TABLE rt_configs(project text NOT NULL,version integer NOT NULL,policy_version integer NOT NULL,payload jsonb NOT NULL,
    PRIMARY KEY(project,version),FOREIGN KEY(project) REFERENCES rt_projects(project));
CREATE TABLE rt_sources(project text NOT NULL REFERENCES projects(id),snapshot text NOT NULL,id text NOT NULL,ref jsonb NOT NULL,
    classification text NOT NULL CHECK(classification IN('safe_source','restricted','raw_secret','tainted')),
    revision text NOT NULL,lineage jsonb NOT NULL,PRIMARY KEY(project,snapshot,id));
CREATE TABLE rt_snapshots(project text NOT NULL REFERENCES projects(id),id text NOT NULL,kind text NOT NULL,
    bundle_ref jsonb NOT NULL,bundle_digest text NOT NULL,candidate_digest text NOT NULL,input_digest text NOT NULL,
    manifest jsonb NOT NULL,PRIMARY KEY(project,id),CHECK(kind IN('repo_task','handoff')));
CREATE TABLE rt_grants(id text PRIMARY KEY,project text NOT NULL REFERENCES projects(id),user_id text NOT NULL REFERENCES accounts(id),
    user_epoch bigint NOT NULL,config_version integer NOT NULL,policy_version integer NOT NULL,actions jsonb NOT NULL,
    expires timestamptz NOT NULL,revoked boolean NOT NULL DEFAULT false);
CREATE TABLE rt_services(id text PRIMARY KEY,kind text NOT NULL CHECK(kind IN('scheduler','worker','collector','assessor')),
    epoch bigint NOT NULL,projects jsonb NOT NULL,enabled boolean NOT NULL DEFAULT true);
CREATE TABLE rt_credentials(digest text PRIMARY KEY,service text NOT NULL REFERENCES rt_services(id),epoch bigint NOT NULL,
    expires timestamptz NOT NULL);
CREATE TABLE rt_intakes(project text NOT NULL REFERENCES projects(id),id text NOT NULL,snapshot text NOT NULL,
    kind text NOT NULL,actor text NOT NULL REFERENCES accounts(id),PRIMARY KEY(project,id),
    FOREIGN KEY(project,snapshot) REFERENCES rt_snapshots(project,id));
CREATE TABLE rt_runs(project text NOT NULL REFERENCES projects(id),id text NOT NULL,snapshot text NOT NULL,
    owner text NOT NULL REFERENCES accounts(id),grant_id text NOT NULL REFERENCES rt_grants(id),user_epoch bigint NOT NULL,
    config_version integer NOT NULL,policy_version integer NOT NULL,state text NOT NULL,
    version integer NOT NULL DEFAULT 1,sequence integer NOT NULL DEFAULT 0,attempt integer NOT NULL DEFAULT 0,
    fence bigint NOT NULL DEFAULT 0,assignment text,worker text REFERENCES rt_services(id),worker_epoch bigint,
    claim_scheduler text,claim_scheduler_epoch bigint,claim_expected_version integer,delivery_count integer NOT NULL DEFAULT 0,
    lease_hash text,lease_expires timestamptz,run_deadline timestamptz,effect_nonce text,effect_state text,effect_witness jsonb,
    incident boolean NOT NULL DEFAULT false,cancel_requested boolean NOT NULL DEFAULT false,
    PRIMARY KEY(project,id),FOREIGN KEY(project,snapshot) REFERENCES rt_snapshots(project,id),
    CHECK(state IN('queued','collecting','awaiting_assessment','analyzing','stopping','cancelled','failed','completed','unresolved')));
CREATE TABLE rt_executions(project text NOT NULL,run_id text NOT NULL,assignment text NOT NULL,fence bigint NOT NULL,
    effect_nonce text NOT NULL,record_ref jsonb NOT NULL,record_digest text NOT NULL,cleanup jsonb NOT NULL,
    collector text NOT NULL REFERENCES rt_services(id),work_accepted boolean NOT NULL,PRIMARY KEY(project,run_id,assignment),
    FOREIGN KEY(project,run_id) REFERENCES rt_runs(project,id));
CREATE TABLE rt_assessments(project text NOT NULL,run_id text NOT NULL,assignment text NOT NULL,fence bigint NOT NULL,
    bundle_ref jsonb NOT NULL,assessment_ref jsonb NOT NULL,bundle_digest text NOT NULL,assessment_digest text NOT NULL,
    execution_digest text NOT NULL,assessor text NOT NULL REFERENCES rt_services(id),
    PRIMARY KEY(project,run_id,assignment),FOREIGN KEY(project,run_id,assignment) REFERENCES rt_executions(project,run_id,assignment));
CREATE TABLE rt_reports(project text NOT NULL,run_id text NOT NULL,report_id text NOT NULL,private_ref jsonb NOT NULL,
    view_ref jsonb NOT NULL,lineage jsonb NOT NULL,projection jsonb NOT NULL,bundle_digest text NOT NULL,assessment_digest text NOT NULL,
    PRIMARY KEY(project,run_id),UNIQUE(project,report_id),FOREIGN KEY(project,run_id) REFERENCES rt_runs(project,id));
CREATE TABLE rt_events(project text NOT NULL,run_id text NOT NULL,sequence integer NOT NULL,event text NOT NULL,
    data jsonb NOT NULL,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),PRIMARY KEY(project,run_id,sequence),
    FOREIGN KEY(project,run_id) REFERENCES rt_runs(project,id));
CREATE TABLE rt_receipts(actor text NOT NULL,project text NOT NULL,operation text NOT NULL,key text NOT NULL,
    payload_digest text NOT NULL,result jsonb NOT NULL,PRIMARY KEY(actor,project,key));
