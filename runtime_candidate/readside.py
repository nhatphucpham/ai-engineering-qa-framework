"""Current project/run reads and serialized release of the exact buffered result."""
import ast
from contextlib import contextmanager
import re

from .blobs import MAX_BLOB_BYTES, descriptor
from .common import VERSION, Error, canonical, digest, exact, require, strict_json
from .lineage import report_lineage
from .publication import _projection


PRIVATE_ORIGINS = frozenset(('vf1-execution-record', 'vf1-coverage-policy'))


def _events(app, run, after):
    require(type(after) is int and after >= 0)
    watermark = run['sequence']
    require(after <= watermark, 'E_RESYNC_REQUIRED')
    rows = app.conn.execute('''SELECT sequence,event,data FROM rt_events WHERE project=%s AND run_id=%s
        AND sequence>%s ORDER BY sequence LIMIT 64''', (run['project'], run['id'], after)).fetchall()
    expected = range(after + 1, min(watermark, after + 64) + 1)
    require([r['sequence'] for r in rows] == list(expected), 'E_RESYNC_REQUIRED')
    return {'events': [{'id': r['sequence'], 'event': r['event'], 'data': r['data']} for r in rows]}


def _source_row(app, run, aid):
    resolver = getattr(app, 'source_record', None)
    if resolver is None:
        row = app.conn.execute('''SELECT id,revision,classification,ref FROM rt_sources
            WHERE project=%s AND snapshot=%s AND id=%s''', (run['project'], run['snapshot'], aid)).fetchone()
    else:
        row = resolver(run, aid)
    require(row is not None and row['id'] == aid, 'E_DENIED')
    return row


def _public_source(app, run, manifest, allowed, aid):
    require(aid not in PRIVATE_ORIGINS and aid in manifest['sourceIds'] and aid in allowed, 'E_DENIED')
    row = _source_row(app, run, aid)
    require(row['classification'] == 'safe_source', 'E_DENIED')
    raw = app.blobs.get(row['ref'])
    require(len(raw) <= 32768, 'E_BUDGET')
    return {'artifactId': aid, 'revision': row['revision'], **row['ref'],
            'classification': 'safe_source', 'text': raw.decode('utf-8')}


def _registered_inputs(app, run, bundle, manifest, allowed, published):
    sources, references = {}, {}
    for artifact in bundle['artifacts']:
        if artifact['projectId'] != run['project']:
            continue
        aid = artifact['id']
        require(aid not in sources, 'E_INTEGRITY')
        if aid not in manifest['sourceIds']:
            require(manifest.get('mode') == 'executed_fixture' and aid in PRIVATE_ORIGINS
                    and callable(getattr(app, 'source_record', None)), 'E_DENIED')
        row = _source_row(app, run, aid)
        require((row['ref']['sha256'], row['revision']) == (artifact['sha256'], artifact['revision']), 'E_INTEGRITY')
        if aid in PRIVATE_ORIGINS:
            require(row['classification'] == 'restricted', 'E_DENIED')
        raw = app.blobs.get(row['ref'])
        sources[aid] = (raw, row['classification'], row['revision'])
        if row['classification'] == 'safe_source':
            require(aid in allowed, 'E_DENIED')
            references[aid] = {'artifactId': aid, 'revision': row['revision'], 'sha256': artifact['sha256']}
    projection = report_lineage(bundle, sources)
    frozen = manifest['reportProjection']
    require(projection['sourceIds'] == frozen['sourceIds'] == manifest['reportSourceIds'] and references, 'E_DENIED')
    late_bound = sources.keys() - set(manifest['sourceIds'])
    if late_bound:
        require(late_bound == PRIVATE_ORIGINS and frozen['profile'] == 'all_target_sources_safe_v1'
                and published is not None, 'E_DENIED')
    else:
        require(projection == frozen, 'E_DENIED')
    if published is not None:
        require(projection == published, 'E_DENIED')
    return sources, references, projection['profile']


def _locator(value, raw):
    # A location may contain arbitrary historic free text. Only publish a checked position.
    if not isinstance(value, str):
        return None
    lines = raw.decode('utf-8').splitlines()
    if re.fullmatch(r'AC-[0-9]{1,4}', value):
        if any(re.search(r'(?<![A-Za-z0-9_-])' + value + r'(?![A-Za-z0-9_-])', line) for line in lines):
            return value
    span = re.fullmatch(r'L([1-9][0-9]{0,5})(?:-L([1-9][0-9]{0,5}))?', value)
    if span:
        first, last = int(span[1]), int(span[2] or span[1])
        if first <= last <= len(lines) and last - first < 40:
            return value
    return None


def _check_locations(sources, profile):
    if profile != 'vf1_fixed_outcome_metadata_v1':
        return {}
    # report_lineage already rebuilt this held job from registered bytes. Resolve the
    # producer's actual test artifact, independently of the assessor's chosen comparisons.
    job = strict_json(sources['vf1-coverage-policy'][0])
    definitions = {}
    checks = {}
    for observed in job['observations']:
        aid = observed['checkArtifactId']
        if aid not in definitions:
            raw, classification, _ = sources[aid]
            require(classification == 'safe_source', 'E_DENIED')
            try:
                module = ast.parse(raw)
            except (SyntaxError, ValueError):
                raise Error('E_INTEGRITY') from None
            methods = {}
            for cls in module.body:
                if isinstance(cls, ast.ClassDef):
                    for method in cls.body:
                        if isinstance(method, ast.FunctionDef):
                            name = cls.name + '.' + method.name
                            require(name not in methods, 'E_INTEGRITY')
                            methods[name] = (method.lineno, method.end_lineno)
            definitions[aid] = methods
        position = definitions[aid].get(observed['testId'])
        require(position is not None, 'E_INTEGRITY')
        start, end = position
        locator = f'L{start}-L{end}' if end - start < 40 else f'L{start}'
        checks[observed['id']] = (aid, locator)
    return checks


def _source_links(view, lineage, package, sources, references, profile):
    content = package['payloads']['prepared']['report']['content']
    target = package['target']
    scoped = {a['id'] for a in content['artifacts'] if (a['projectId'], a['taskRef']) ==
              (target['projectId'], target['taskRef'])}
    producer_scope = {a['id'] for a in package['payloads']['bundle']['artifacts']
                      if (a['projectId'], a['taskRef']) == (target['projectId'], target['taskRef'])}
    criteria = {row['criterion']['id']: row for row in content['criterionSources']}
    evidence = {row['evidence']['id']: row['evidence'] for row in content['evidenceSources']}
    checks = _check_locations(sources, profile)
    result = []
    for criterion in view['criteria']:
        alias = criterion['criterionId']
        row = criteria[lineage['criteria'][alias]]
        links = []

        def append(kind, aid, location=None, evidence_id=None):
            scope = producer_scope if kind == 'check_definition' else scoped
            require(aid in scope and aid in sources, 'E_INTEGRITY')
            if aid not in references:
                link = {'kind': kind, 'reason': 'restricted'}
            else:
                link = dict(references[aid], kind=kind)
                if location is not None:
                    locator = _locator(location, sources[aid][0])
                    if locator is None:
                        link['locatorStatus'] = 'unavailable'
                    else:
                        link['locator'] = locator
            if evidence_id is not None:
                link['evidenceId'] = evidence_id
            if link not in links:
                require(len(links) < 64, 'E_BUDGET')
                links.append(link)

        for claim in row['criterion']['claims']:
            append('requirement', claim['artifactId'], claim['locator'])
        if row['plan'] is not None:
            for kind, field in (('obligation', 'obligations'), ('comparison', 'comparisonContexts')):
                for entry in row['plan'][field]:
                    append(kind, entry['sourceArtifactId'], entry['locator'])
        for alias_id in criterion['evidenceIds'] + criterion['contextEvidenceIds']:
            original = lineage['evidence'][alias_id]
            source = evidence[original]['provenance']['sourceArtifactId']
            append('evidence', source, evidence_id=alias_id)
            if original in checks:
                aid, location = checks[original]
                append('check_definition', aid, location, alias_id)
        append('policy', content['scope']['policySourceArtifactId'])
        result.append({'criterionId': alias, 'links': links})
    return result


def _report(app, op, run, config, snapshot):
    row = app.conn.execute('SELECT * FROM rt_reports WHERE project=%s AND run_id=%s',
                           (run['project'], run['id'])).fetchone()
    require(row is not None and run['state'] == 'completed', 'E_DENIED')
    package = strict_json(app.blobs.get(row['private_ref']), MAX_BLOB_BYTES)
    target = package['target']
    require((target['projectId'], target['runId'], target['reportId']) ==
            (run['project'], run['id'], row['report_id']), 'E_INTEGRITY')
    bundle = package['payloads']['bundle']
    require(digest(bundle) == row['bundle_digest'] and
            digest(package['payloads']['assessment']) == row['assessment_digest'], 'E_INTEGRITY')
    view = strict_json(app.blobs.get(row['view_ref']))
    expected_view, lineage = _projection(package)
    require(canonical(view) == canonical(expected_view) and lineage == row['lineage'], 'E_INTEGRITY')
    inputs, refs, profile = _registered_inputs(app, run, bundle, snapshot['manifest'],
                                              config['payload']['sourceIds'], row.get('projection'))
    links = _source_links(view, lineage, package, inputs, refs, profile)
    link_ref = descriptor(canonical(links))
    result = {'view': view, 'sourceLinks': links, 'sourceLinksSha256': link_ref['sha256']}
    if op == 'report_read':
        result.update(reportId=row['report_id'], viewSha256=row['view_ref']['sha256'])
        require(len(canonical(result)) <= 65536, 'E_BUDGET')
        return result
    manifest = {'version': VERSION, 'project': run['project'], 'runId': run['id'], 'reportId': row['report_id'],
                'configVersion': config['config_version'], 'policyVersion': config['policy_version'],
                'entries': [{'kind': 'report_view', **row['view_ref']}, {'kind': 'source_links', **link_ref}],
                'classification': 'target_scoped_derived_view'}
    result.update(manifest=manifest, manifestSha256=digest(manifest))
    require(len(canonical(result)) <= 65536, 'E_BUDGET')
    return result


def read_locked(app, operation, actor, p):
    from .contracts import READ_ACTION, safe_run
    require(operation in READ_ACTION, 'E_DENIED')
    require(actor is not None, 'E_AUTH')
    if operation == 'session_read':
        return {'user': actor['id'], 'isAdmin': actor['admin'], 'version': VERSION}
    if operation == 'project_list':
        rows = app.conn.execute('''SELECT p.project FROM rt_projects p JOIN projects q ON q.id=p.project
            JOIN rt_configs c ON (c.project,c.version)=(p.project,p.config_version)
            WHERE p.enabled AND q.enabled AND c.payload->'enabled' = 'true'::jsonb
            AND (%s OR EXISTS(SELECT 1 FROM members m WHERE m.project=p.project AND m.user_id=%s))
            ORDER BY p.project''', (actor['admin'], actor['id'])).fetchall()
        return {'projects': [r['project'] for r in rows]}
    config, _ = app.store.config(actor, p['project'], READ_ACTION[operation])
    if operation == 'project_read':
        return {'project': p['project'], 'configVersion': config['config_version'],
                'policyVersion': config['policy_version'], 'config': config['payload']}
    if operation == 'run_list':
        rows = app.conn.execute('SELECT * FROM rt_runs WHERE project=%s ORDER BY id LIMIT 100',
                                (p['project'],)).fetchall()
        return {'runs': [safe_run(row) for row in rows]}
    run = app.store.run(p['project'], p['run_id'])
    if operation == 'run_read':
        return safe_run(run)
    if operation == 'events':
        return _events(app, run, p['after'])
    snapshot = app.store.snapshot(p['project'], run['snapshot'])
    if operation == 'source_read':
        return _public_source(app, run, snapshot['manifest'], config['payload']['sourceIds'], p['artifact_id'])
    return _report(app, operation, run, config, snapshot)


@contextmanager
def release_unit(app, operation, token, body, result):
    from .contracts import FIELDS, READ_ACTION
    require(operation in READ_ACTION, 'E_DENIED')
    p = dict(body)
    require(p.pop('version', None) == VERSION, 'E_VERSION')
    exact(p, FIELDS[operation])
    try:
        with app.store.unit(token) as (actor, _):
            current = read_locked(app, operation, actor, p)
            if operation == 'events':
                # A committed tail may grow while the already-buffered page is being delivered.
                current = {'events': current['events'][:len(result['events'])]}
            require(canonical(current) == canonical(result), 'E_STALE')
            # Computing a large projection may take time even with policy changes serialized.
            live = app.conn.execute('SELECT %s>clock_timestamp() AND %s>clock_timestamp() AS live',
                                    (actor['access_expires'], actor['family_expires'])).fetchone()
            require(live['live'], 'E_AUTH')
            yield
    except Error:
        raise
