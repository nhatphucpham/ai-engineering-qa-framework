CREATE TABLE d_lifecycle (
 job_id text PRIMARY KEY REFERENCES launch_jobs(id), project text NOT NULL, run_id text NOT NULL,
 state text NOT NULL CHECK(state IN ('active','cancelling','completing','cancelled','completed','failed_cleanup_unconfirmed')),
 request_id text UNIQUE, deadline timestamptz, incident_open boolean NOT NULL DEFAULT false,
 acked boolean NOT NULL DEFAULT false
);
CREATE UNIQUE INDEX d_run ON d_lifecycle(project,run_id);
CREATE FUNCTION d_no_queued_cancel() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.state='cancelled' AND (EXISTS(SELECT 1 FROM d_lifecycle WHERE project=OLD.project AND run_id=OLD.id) OR EXISTS(SELECT 1 FROM launch_jobs WHERE project=OLD.project AND run_id=OLD.id AND state!='cleaned')) THEN
   RAISE EXCEPTION 'active lifecycle owns cancellation';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER d_cancel_guard BEFORE UPDATE OF state ON app_runs FOR EACH ROW EXECUTE FUNCTION d_no_queued_cancel();
CREATE FUNCTION d_no_new_launch() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM d_lifecycle WHERE project=NEW.project AND run_id=NEW.run_id) THEN
   RAISE EXCEPTION 'lifecycle does not permit retry';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER d_launch_guard BEFORE INSERT ON launch_jobs FOR EACH ROW EXECUTE FUNCTION d_no_new_launch();
