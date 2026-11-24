"""Synthetic read/release checks using immutable HC1 bytes and a recording store."""
from contextlib import contextmanager
from copy import deepcopy
import unittest
import json
from pathlib import Path

from .blobs import descriptor
from .common import VERSION, Error, canonical, digest, require, sha
from .fixture_import import load_hc1
from .lineage import report_lineage
from .publication import prepare
from .readside import read_locked, release_unit
from .readside import _source_links


class Blobs:
    def __init__(self):
        self.rows = {}

    def put(self, raw):
        ref = descriptor(raw)
        self.rows[ref['sha256']] = raw
        return ref

    def get(self, ref):
        raw = self.rows[ref['sha256']]
        require(descriptor(raw) == ref, 'E_INTEGRITY')
        return raw


class Rows:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return next(iter(self.rows), None)


class Fixture:
    def __init__(self, data, publication):
        self.blobs, self.store, self.conn = Blobs(), self, self
        self.project = data['project']
        self.scope = {'project': self.project, 'run_id': data['run_id']}
        self.runrow = dict(project=self.project, id=data['run_id'], snapshot='snapshotA', state='completed',
                           version=6, sequence=2, attempt=1, incident=False)
        self.actor = dict(id='viewer', admin=False, access_expires=1, family_expires=1)
        self.live = True
        self.locked = False
        self.visible = True
        self.runrows = [self.runrow]
        self.events = [dict(sequence=i, event='run_state', data={'stateVersion': i}) for i in (1, 2)]
        self.configrow = {'config_version': 2, 'policy_version': 2, 'payload': {'sourceIds': sorted(data['sources'])}}
        self.sources = {(self.project, 'snapshotA', aid): {'id': aid, 'revision': revision,
                         'classification': classification, 'ref': self.blobs.put(raw)}
                        for aid, (raw, classification, revision) in data['sources'].items()}
        projection = report_lineage(data['bundle'], data['sources'])
        self.snapshotrow = {'manifest': {'sourceIds': sorted(data['sources']),
                                        'reportProjection': projection, 'reportSourceIds': projection['sourceIds']}}
        self.report = {'report_id': publication.view['reportId'], 'private_ref': self.blobs.put(publication.private_bytes),
                       'view_ref': self.blobs.put(publication.view_bytes), 'lineage': deepcopy(publication.lineage),
                       'bundle_digest': digest(data['bundle']), 'assessment_digest': digest(data['assessment'])}

    @contextmanager
    def unit(self, token):
        require(token == 'dummy-user', 'E_AUTH')
        self.locked = True
        try:
            yield self.actor, []
        finally:
            self.locked = False

    def config(self, actor, project, action):
        require(self.visible and actor == self.actor and project == self.project, 'E_DENIED')
        return self.configrow, 'Viewer'

    def snapshot(self, project, snapshot):
        require(project == self.project and snapshot == self.runrow['snapshot'], 'E_DENIED')
        return self.snapshotrow

    def run(self, project, run_id):
        require((project, run_id) == (self.project, self.runrow['id']), 'E_DENIED')
        return self.runrow

    def execute(self, query, params):
        if 'FROM rt_sources' in query:
            return Rows([self.sources[params]] if params in self.sources else [])
        if 'FROM rt_reports' in query:
            return Rows([self.report] if params == (self.project, self.runrow['id']) else [])
        if 'FROM rt_events' in query:
            return Rows([r for r in self.events if r['sequence'] > params[2]][:64])
        if 'FROM rt_projects' in query:
            return Rows([{'project': self.project}] if self.visible else [])
        if 'FROM rt_runs' in query:
            return Rows(self.runrows)
        if 'clock_timestamp()' in query:
            return Rows([{'live': self.live}])
        raise AssertionError(query)

    def read(self, op, **p):
        return read_locked(self, op, self.actor, p)

    def release(self, op, result, **p):
        return release_unit(self, op, 'dummy-user', dict(p, version=VERSION), result)


class ReadsideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_hc1('a', include_canaries=True)
        cls.pub = prepare(cls.data['bundle'], cls.data['assessment'],
                          expected_bundle_digest=digest(cls.data['bundle']),
                          expected_assessment_digest=digest(cls.data['assessment']),
                          run_id=cls.data['run_id'], report_id='report_' + cls.data['run_id'])

    def setUp(self):
        self.app = Fixture(self.data, self.pub)
        self.scope = self.app.scope

    def test_report_links_reach_registered_requirement_and_checks(self):
        response = self.app.read('report_read', **self.scope)
        export = self.app.read('report_export', **self.scope)
        self.assertEqual(self.pub.view, response['view'])
        self.assertEqual(export['sourceLinks'], response['sourceLinks'])
        self.assertEqual(digest(response['sourceLinks']), response['sourceLinksSha256'])
        self.assertEqual(digest(export['manifest']), export['manifestSha256'])
        for group in response['sourceLinks']:
            self.assertIn(group['criterionId'], self.pub.lineage['criteria'])
            for kind in ('requirement', 'comparison'):
                link = next(entry for entry in group['links'] if entry['kind'] == kind)
                source = self.app.read('source_read', **self.scope, artifact_id=link['artifactId'])
                self.assertEqual(link['sha256'], sha(source['text'].encode('utf-8')))
                self.assertEqual(link['revision'], source['revision'])
                self.assertTrue(link['locator'].startswith(('AC-', 'L')))
        for label in ('vf1-execution-record', 'vf1-coverage-policy', 'fixture-taint-canary', 'fixture-raw-canary'):
            self.assertNotIn(label.encode(), canonical(export))
            with self.assertRaisesRegex(Error, 'E_DENIED'):
                self.app.read('source_read', **self.scope, artifact_id=label)

    def test_evidence_alias_resolves_its_own_observed_check_independent_of_order(self):
        report = self.app.read('report_read', **self.scope)
        # Start from the returned view, then follow each alias through its own check link.
        criterion = next(c for c in report['view']['criteria']
                         if self.pub.lineage['criteria'][c['criterionId']] == 'AC-02')
        group = next(g for g in report['sourceLinks'] if g['criterionId'] == criterion['criterionId'])
        outcomes = {e['id']: e['outcome'] for e in report['view']['sources']}
        expected = {('artifact-6', 'L41-L46', 'pass', 'test_ui_select_from_first_page'),
                    ('artifact-7', 'L8-L12', 'fail', 'test_reset_from_third_page'),
                    ('artifact-8', 'L8-L17', 'fail', 'test_reset_with_recorded_api_call')}
        observed = set()
        for alias in reversed(criterion['evidenceIds']):
            check, = [link for link in group['links'] if link.get('evidenceId') == alias
                      and link['kind'] == 'check_definition']
            self.assertIn({'kind': 'evidence', 'reason': 'restricted', 'evidenceId': alias}, group['links'])
            source = self.app.read('source_read', **self.scope, artifact_id=check['artifactId'])
            number = int(check['locator'].split('-')[0][1:])
            first_line = source['text'].splitlines()[number - 1].strip()
            name = first_line.removeprefix('def ').split('(')[0]
            observed.add((check['artifactId'], check['locator'], outcomes[alias], name))
        self.assertEqual(observed, expected)

    def _record_completed_effect(self):
        app = self.app
        origins = ('vf1-execution-record', 'vf1-coverage-policy')
        manifest = app.snapshotrow['manifest']
        app.report['projection'] = deepcopy(manifest['reportProjection'])
        manifest['mode'] = 'executed_fixture'
        manifest['sourceIds'] = [aid for aid in manifest['sourceIds'] if aid not in origins]
        manifest['reportProjection'] = {'profile': 'all_target_sources_safe_v1',
                                        'sourceIds': list(manifest['reportSourceIds'])}
        observed = {aid: app.sources.pop((app.project, 'snapshotA', aid)) for aid in origins}
        def resolved(run, aid):
            self.assertIs(run, app.runrow)
            if aid in observed:
                return observed[aid]
            return app.sources.get((run['project'], run['snapshot'], aid))
        app.source_record = resolved
        return observed

    def test_completed_effect_validates_private_origins_without_changing_intake(self):
        observed = self._record_completed_effect()
        frozen = canonical(self.app.snapshotrow)
        for op in ('report_read', 'report_export'):
            report = self.app.read(op, **self.scope)
            self.assertEqual(report['view'], self.pub.view)
            self.assertTrue(all(any(link['kind'] == 'check_definition' for link in group['links'])
                                for group in report['sourceLinks']))
            for aid in observed:
                self.assertNotIn(aid.encode(), canonical(report))
        self.assertEqual(canonical(self.app.snapshotrow), frozen)
        # Even an overly broad current sourceIds list cannot expose either private origin.
        for aid in observed:
            self.assertIn(aid, self.app.configrow['payload']['sourceIds'])
            with self.assertRaisesRegex(Error, 'E_DENIED'):
                self.app.read('source_read', **self.scope, artifact_id=aid)

    def test_completed_effect_requires_both_publication_and_original_safe_source_pins(self):
        self._record_completed_effect()
        published = self.app.report.pop('projection')
        with self.assertRaisesRegex(Error, 'E_DENIED'):
            self.app.read('report_read', **self.scope)
        self.app.report['projection'] = dict(published, executionDigest='0' * 64)
        with self.assertRaisesRegex(Error, 'E_DENIED'):
            self.app.read('report_export', **self.scope)
        self.app.report['projection'] = published
        self.app.snapshotrow['manifest']['sourceIds'].remove('artifact-1')
        with self.assertRaisesRegex(Error, 'E_DENIED'):
            self.app.read('report_export', **self.scope)

    def test_completed_effect_rejects_changed_bytes_classification_and_wrong_mode(self):
        observed = self._record_completed_effect()
        origin = observed['vf1-execution-record']
        ref = origin['ref']
        origin['ref'] = self.app.blobs.put(b'other synthetic execution')
        with self.assertRaisesRegex(Error, 'E_INTEGRITY'):
            self.app.read('report_read', **self.scope)
        origin['ref'] = ref
        origin['classification'] = 'safe_source'
        with self.assertRaisesRegex(Error, 'E_DENIED'):
            self.app.read('report_read', **self.scope)
        origin['classification'] = 'restricted'
        self.app.snapshotrow['manifest']['mode'] = 'imported'
        with self.assertRaisesRegex(Error, 'E_DENIED'):
            self.app.read('report_read', **self.scope)

    def test_safe_source_policy_removed_and_taint_deny_ordinary_report(self):
        self.app.configrow['payload']['sourceIds'].remove('artifact-6')
        with self.assertRaisesRegex(Error, 'E_DENIED'):
            self.app.read('report_read', **self.scope)
        self.app.configrow['payload']['sourceIds'].append('artifact-6')
        for classification in ('raw_secret', 'tainted'):
            self.app.sources[(self.app.project, 'snapshotA', 'artifact-6')]['classification'] = classification
            with self.assertRaisesRegex(Error, 'E_DENIED'):
                self.app.read('report_export', **self.scope)

    def test_private_package_and_projection_must_match_held_rows(self):
        self.app.snapshotrow['manifest']['reportProjection']['sourceIds'] = ['artifact-1']
        with self.assertRaisesRegex(Error, 'E_DENIED'):
            self.app.read('report_read', **self.scope)
        self.app.report['lineage']['criteria']['criterion-1'] = 'AC-02'
        with self.assertRaisesRegex(Error, 'E_INTEGRITY'):
            self.app.read('report_read', **self.scope)

    def test_source_rejects_identical_id_from_other_snapshot(self):
        self.app.runrow['snapshot'] = 'snapshotB'
        with self.assertRaisesRegex(Error, 'E_DENIED'):
            self.app.read('source_read', **self.scope, artifact_id='artifact-1')

    def test_buffered_metadata_must_remain_authorized(self):
        projects = self.app.read('project_list')
        self.app.visible = False
        with self.assertRaisesRegex(Error, 'E_STALE'), self.app.release('project_list', projects):
            self.fail('stale listing released')
        self.app.visible = True
        project = self.app.read('project_read', project=self.app.project)
        self.app.configrow['config_version'] += 1
        with self.assertRaisesRegex(Error, 'E_STALE'), self.app.release('project_read', project, project=self.app.project):
            self.fail('stale configuration released')
        runs = self.app.read('run_list', project=self.app.project)
        self.app.runrows = []
        with self.assertRaisesRegex(Error, 'E_STALE'), self.app.release('run_list', runs, project=self.app.project):
            self.fail('stale run metadata released')

    def test_exact_event_page_accepts_only_new_tail_under_lock(self):
        query = dict(self.scope, after=0)
        page = self.app.read('events', **query)
        self.app.runrow['sequence'] = 3
        self.app.events.append(dict(sequence=3, event='report_ready', data={'stateVersion': 6}))
        with self.app.release('events', page, **query):
            self.assertTrue(self.app.locked)
        self.assertFalse(self.app.locked)
        self.app.events[1] = dict(sequence=2, event='run_state', data={'stateVersion': 100})
        with self.assertRaisesRegex(Error, 'E_STALE'), self.app.release('events', page, **query):
            self.fail('changed event released')
        self.app.events.pop()
        with self.assertRaisesRegex(Error, 'E_RESYNC_REQUIRED'):
            self.app.read('events', **dict(self.scope, after=2))

    def test_gaps_in_event_page_and_cursor_ahead(self):
        self.app.events[1]['sequence'] = 3
        for cursor in (0, 10):
            with self.assertRaisesRegex(Error, 'E_RESYNC_REQUIRED'):
                self.app.read('events', **self.scope, after=cursor)

    def test_clock_checked_after_projection_before_write(self):
        response = self.app.read('session_read')
        self.app.live = False
        with self.assertRaisesRegex(Error, 'E_AUTH'), self.app.release('session_read', response):
            self.fail('expired session released')


class FreshProducerLineageTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).parent / 'fixtures/fresh-lineage-f2.json'
        raw = path.read_bytes()
        self.assertEqual(sha(raw), '6b51c24d673b2128006d737aeb319df451d90716711d5b78cd80d1943e4ba560')
        fixture = json.loads(raw)
        self.package = fixture['package']
        bundle, assessment = self.package['payloads']['bundle'], self.package['payloads']['assessment']
        self.assertEqual(digest(self.package), fixture['origin']['packageSha256'])
        self.assertEqual(digest(fixture['executionRecord']), fixture['job']['executionSha256'])
        artifacts = {a['id']: a for a in bundle['artifacts']}
        self.sources = {a['id']: (a['text'].encode(), 'safe_source', artifacts[a['id']]['revision'])
                        for a in fixture['job']['artifacts']}
        self.sources.update({
            'vf1-execution-record': (canonical(fixture['executionRecord']), 'restricted', artifacts['vf1-execution-record']['revision']),
            'vf1-coverage-policy': (canonical(fixture['job']), 'restricted', artifacts['vf1-coverage-policy']['revision'])})
        run = bundle['runs'][0]
        self.publication = prepare(bundle, assessment, expected_bundle_digest=digest(bundle),
                                   expected_assessment_digest=digest(assessment), run_id=run['id'],
                                   report_id=self.package['target']['reportId'])
        self.assertEqual(self.publication.private_bytes, canonical(self.package))
        class FreshFixture(Fixture):
            def source_record(inner, current, aid):
                return inner.sources.get((current['project'], current['snapshot'], aid))
        self.app = FreshFixture({'project': run['projectId'], 'run_id': run['id'], 'bundle': bundle,
                                 'assessment': assessment, 'sources': self.sources}, self.publication)
        safe = sorted(aid for aid, (_, classification, _) in self.sources.items() if classification == 'safe_source')
        self.app.snapshotrow['manifest'].update(mode='executed_fixture', sourceIds=safe,
            reportProjection={'profile': 'all_target_sources_safe_v1', 'sourceIds': safe})
        self.app.configrow['payload']['sourceIds'] = safe
        self.app.report['projection'] = report_lineage(bundle, self.sources)

    def test_actual_producer_link_survives_different_assessor_comparison_source(self):
        prepared = self.package['payloads']['prepared']['report']['content']
        self.assertNotIn('artifact-7', {a['id'] for a in prepared['artifacts']})
        report = self.app.read('report_read', **self.app.scope)
        links = [link for group in report['sourceLinks'] for link in group['links']]
        self.assertTrue(any(link.get('artifactId') == 'artifact-7' and link['kind'] == 'check_definition' for link in links))
        source = self.app.read('source_read', **self.app.scope, artifact_id='artifact-7')
        self.assertEqual(source['text'].encode(), self.sources['artifact-7'][0])

    def test_producer_still_requires_current_source_permission(self):
        self.app.configrow['payload']['sourceIds'].remove('artifact-7')
        with self.assertRaisesRegex(Error, 'E_DENIED'):
            self.app.read('report_read', **self.app.scope)

    def test_producer_cannot_cross_target_task(self):
        package = deepcopy(self.package)
        next(a for a in package['payloads']['bundle']['artifacts'] if a['id'] == 'artifact-7')['taskRef'] = 'otherTask'
        refs = {aid: {'artifactId': aid, 'revision': revision, 'sha256': sha(raw)}
                for aid, (raw, classification, revision) in self.sources.items() if classification == 'safe_source'}
        with self.assertRaisesRegex(Error, 'E_INTEGRITY'):
            _source_links(self.publication.view, self.publication.lineage, package, self.sources, refs,
                          'vf1_fixed_outcome_metadata_v1')


if __name__ == '__main__':
    unittest.main()
