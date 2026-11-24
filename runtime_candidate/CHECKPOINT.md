# Restricted operator checkpoint

This offline maintenance interface copies one synthetic application schema and the immutable bytes it references. It uses the retained Windows PostgreSQL tools and the live source Store. Ordinary clients have no backup, restore or activation route. The archive contains private inputs, account password hashes, hashed credentials, session state and internal reports. Keep the archive, roots and receipt in private operator custody.

## Create and verify a copy

Start with the marker-bound local cluster already running. The operator provides existing private parent directories under the repository’s `.cache/s6/m50`. Each archive path and restored root below must be absolute and unused. Each destination schema is a fresh `id_` plus 32 lowercase hexadecimal characters.

```python
from uuid import uuid4
from runtime_candidate.checkpoint import backup, restore

receipt = backup(source_store, archive_path)
# Retain this receipt in a trusted operator record independent of the archive.
result = restore(source_store, archive_path, checkpoint=receipt,
                 target_schema='id_' + uuid4().hex, target_root=maintenance_root)
```

The receipt contains `manifestSha256`, `authoritySha256`, `sourceSchema` and `blobCount`. Restore needs the separately held receipt **and** the source’s current, matching external witness and database control row. An archive owner cannot establish recency from its own manifest. Source loss or a changed authority nonce blocks restoration by this interface.

Backup holds the source identity transaction mutex, exports a PostgreSQL snapshot to a second local connection, and runs schema-scoped `pg_dump --inserts --no-owner --no-privileges`. It copies every distinct referenced source, snapshot, execution, assessment and report object after a byte-level read check. When a run has an executor observation, it also copies the original observation bytes (`rawRef`) and the canonical offered job (`jobRef`). Both references are required for each recorded observation. A run without an observation contributes neither. The sealed manifest binds the dump, all object lengths and hashes, the authority head, the logical rows of all 27 application/identity tables and the audit sequence. An interrupted backup cannot return a completed receipt. Accepted archives are limited to 32 MiB of SQL and 4,096 referenced objects totaling at most 128 MiB, with the blob store’s 8 MiB limit per object.

Restore verifies the receipt, source head, manifest, SQL and every blob before creating a destination. The fixed pg_dump dialect supports this schema and its single audit identity sequence. It remaps schema identifiers and the sequence’s generated `setval` reference while preserving SQL string values and comments. Unsupported dump syntax fails closed. The pinned local `psql` restores the verified dump in one transaction into a new schema. Each target blob goes through a fresh marker-bound BlobStore and is checked again. Restore compares the complete logical row and sequence fingerprint and all DB reference descriptors before recording `restore-basis.json`.

Default success returns `state=verified_maintenance`. The restored root has a basis record and no live authority witness. Normal application operations therefore fail their witness check. Source authority continues on the original store.

## Exclusive cutover

For an intentional switch, call `restore(..., activate=True)` with the receipt and a **new** schema/root. A previously verified destination remains untouched. Cutover requires a current source head and no in-flight or incident run. While still holding the source identity mutex the operation verifies the restored copy, advances its DB nonce, verifies the source head again, retires the source’s external witness and then writes the target’s fresh authority witness. Successful output includes `state=active_restore`, `retiredAuthoritySha256` and `targetAuthoritySha256`. Retain these pins with the external operator record. The original application can no longer obtain a valid witness.

Before source retirement, a failure can leave an unservable target directory/schema. An interruption between retirement and target activation leaves both stores unavailable. A lost acknowledgement after activation can leave the new target live. Treat ambiguous outcomes as incidents and inspect the independently held authority records before further action. The utility never drops a schema, restores over an existing root, or automatically re-enables either store.

## Verification boundary

Run `py -3 -B -m unittest runtime_candidate.test_checkpoint -v` from the repo root. The suite uses real temporary files and byte storage, including separate missing and corrupt original executor observations and offered jobs on both backup and restore. Its database and command boundaries are injected to exercise stale heads, substituted archives, occupied targets, remapping, maintenance mode, retirement order and interruption between witnesses. Actual PostgreSQL dump/restore, TLS reads after cutover, refusal by the retired source and persistence across restart are separate integration checks. This candidate assumes a trusted local OS, trusted source DDL and external receipt custody. Simultaneous loss or rollback of database and authority custody, power failure and production disaster recovery require separate evidence.
