CREATE TABLE model_identity(version text PRIMARY KEY);
INSERT INTO model_identity VALUES('s6a-1.0.0');
CREATE TABLE projects(id text PRIMARY KEY,enabled boolean NOT NULL DEFAULT true);
CREATE TABLE heads(project text NOT NULL REFERENCES projects(id),ref text NOT NULL,version bigint NOT NULL,
    epoch bigint NOT NULL,enabled boolean NOT NULL DEFAULT true,PRIMARY KEY(project,ref));
CREATE TABLE key_identity(key_id text PRIMARY KEY,key_tag bytea NOT NULL UNIQUE);
CREATE TABLE nonce_history(key_id text NOT NULL REFERENCES key_identity(key_id),nonce bytea NOT NULL,
    PRIMARY KEY(key_id,nonce),CHECK(octet_length(nonce)=12));
CREATE TABLE encrypted_versions(
    project text NOT NULL,ref text NOT NULL,version bigint NOT NULL,kind text NOT NULL,
    key_id text NOT NULL,wrap_nonce bytea NOT NULL,wrapped_key bytea NOT NULL,
    data_nonce bytea NOT NULL,ciphertext bytea NOT NULL,wrapping_revision bigint NOT NULL DEFAULT 1,
    PRIMARY KEY(project,ref,version),UNIQUE(key_id,wrap_nonce),
    FOREIGN KEY(key_id,wrap_nonce) REFERENCES nonce_history(key_id,nonce),
    FOREIGN KEY(project,ref) REFERENCES heads(project,ref),
    CHECK(kind IN ('secret','quarantine')),CHECK(octet_length(wrap_nonce)=12),
    CHECK(octet_length(data_nonce)=12),CHECK(octet_length(wrapped_key)=48)
);
CREATE TABLE audit(sequence bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project text NOT NULL,ref text NOT NULL,version bigint NOT NULL,epoch bigint NOT NULL,
    operation text NOT NULL CHECK(operation IN ('write','rewrap','revoke','quarantine')));
