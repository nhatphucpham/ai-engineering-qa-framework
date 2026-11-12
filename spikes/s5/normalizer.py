"""Synthetic offline S5 model. Correlation assertion is a test seam, not a GitHub API."""
import re

SHA = re.compile(r"[0-9a-f]{40}\Z")


def token(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", value):
        raise ValueError("invalid scope")
    return value


def subject(repo_id, number):
    if type(repo_id) is not int or repo_id < 1 or type(number) is not int or number < 1:
        raise ValueError("invalid subject")
    return f"github:{repo_id}:pr:{number}"


def observe_webhook(payload, delivery):
    token(delivery)
    try:
        if payload["action"] != "ready_for_review":
            raise ValueError("unsupported action")
        pr = payload["pull_request"]
        subject(payload["repository"]["id"], pr["number"])
        if pr["number"] != payload["number"]:
            raise ValueError("subject mismatch")
        sub = subject(payload["repository"]["id"], payload["number"])
        sha = pr["head"]["sha"]
        if not isinstance(sha, str) or not SHA.fullmatch(sha):
            raise ValueError("invalid revision")
    except (KeyError, TypeError):
        raise ValueError("invalid webhook") from None
    return {"status": "unresolved", "subject": sub, "reason": "missing_common_occurrence", "delivery": delivery}


def observe_timeline(repo_id, number, event):
    sub = subject(repo_id, number)
    try:
        if event["event"] != "ready_for_review" or type(event["id"]) is not int or event["id"] < 1:
            raise ValueError("invalid timeline event")
    except (KeyError, TypeError):
        raise ValueError("invalid timeline event") from None
    return {"status": "unresolved", "subject": sub, "occurrence": f"timeline:{event['id']}", "reason": "missing_exact_event_revision"}


class Reconciler:
    """Test-only assertions are assumed proven; caller must establish provenance externally."""
    def __init__(self):
        self.bindings = {}
        self.intents = set()
        self.conflicts = set()

    def bind_test_assertion(self, project, repo_id, number, event_id, revision):
        project = token(project)
        sub = subject(repo_id, number)
        if type(event_id) is not int or event_id < 1 or not isinstance(revision, str) or not SHA.fullmatch(revision):
            raise ValueError("invalid assertion")
        occurrence = f"timeline:{event_id}"
        key = (project, sub, occurrence)
        if key in self.conflicts:
            return {"status": "quarantined"}
        previous = self.bindings.get(key)
        if previous is not None and previous != revision:
            self.conflicts.add(key)
            return {"status": "quarantined"}
        self.bindings[key] = revision
        normalized = f"{project}|pr_ready|{sub}|{occurrence}|{revision}"
        duplicate = normalized in self.intents
        self.intents.add(normalized)
        return {"status": "duplicate" if duplicate else "resolved", "normalizedKey": normalized}


def observe_snapshot(repo_id, pull, history_complete):
    """A current snapshot never supplies a historical transition, even with complete pages."""
    if type(history_complete) is not bool:
        raise ValueError("invalid history status")
    try:
        sub = subject(repo_id, pull["number"])
        if type(pull["draft"]) is not bool:
            raise ValueError("invalid draft")
    except (KeyError, TypeError):
        raise ValueError("invalid pull") from None
    return {"status": "unresolved", "subject": sub,
            "reason": "missing_transition" if history_complete else "history_gap"}
