"""Offline grammar tests; no DB creation, transport or provider calls."""
from copy import deepcopy
import unittest

from runtime_candidate.common import Error
from .ingress import VERSION, observation, page

SHA_A, SHA_B = 'a' * 40, 'b' * 40


def webhook(delivery='d1', sha=SHA_A, repo=101, pr=7):
    return {'kind': 'webhook', 'body': {'repository': {'id': repo}, 'number': pr,
            'action': 'ready_for_review', 'pull_request': {'number': pr, 'head': {'sha': sha}}, 'delivery': delivery}}


def timeline(event=1, *, complete=True):
    return {'kind': 'timeline', 'body': {'repository': {'id': 101}, 'number': 7,
            'event': {'id': event, 'event': 'ready_for_review'}, 'historyComplete': complete}}


def snapshot(complete=True):
    return {'kind': 'snapshot', 'body': {'repository': {'id': 101}, 'number': 7,
            'head': {'sha': SHA_B}, 'draft': False, 'historyComplete': complete}}


def make_page(project, observations, expected=0):
    return {'version': VERSION, 'project': project, 'stream': 'main',
            'expected': expected, 'next': expected + 1, 'observations': observations}


class GrammarTests(unittest.TestCase):
    def test_receipts_derive_from_kind_transport_identity(self):
        self.assertEqual(observation(webhook())[0], 'webhook:d1')
        self.assertEqual(observation(timeline())[0], 'timeline:1')
        self.assertTrue(observation(snapshot())[0].startswith('snapshot:'))
        altered = webhook(); altered['id'] = 'callerAlias'
        with self.assertRaises(Error):
            observation(altered)

    def test_independent_subject_types(self):
        for path in ('number', 'nested', 'repo'):
            for value in (True, 1.0, 0, -1, 2**63):
                obs = webhook(pr=1)
                if path == 'number': obs['body']['number'] = value
                elif path == 'nested': obs['body']['pull_request']['number'] = value
                else: obs['body']['repository']['id'] = value
                with self.subTest(path=path, value=value), self.assertRaises(Error):
                    observation(obs)

    def test_history_and_kind_fields(self):
        self.assertEqual(observation(timeline(complete=False))[3], 'history_gap')
        self.assertEqual(observation(snapshot(False))[3], 'history_gap')
        for obs in (timeline(True), timeline(complete=1), snapshot(1), {'kind': 'unknown', 'body': {}}, webhook(sha='HEAD')):
            with self.assertRaises(Error):
                observation(obs)
        obs = webhook(); obs['body']['action'] = 'synchronize'
        with self.assertRaises(Error): observation(obs)

    def test_page_contract_and_bounds(self):
        valid = make_page('project', [webhook()])
        self.assertEqual(page(valid), valid)
        mutations = [{'version': 'p4d-g1-2.0.0'}, {'extra': True}, {'expected': True}, {'next': 3},
                     {'observations': []}, {'observations': [webhook()] * 65}]
        huge = webhook(); huge['body']['untrusted'] = 'x' * 65536
        mutations.append({'observations': [huge]})
        for fields in mutations:
            with self.subTest(fields=list(fields)), self.assertRaises(Error):
                page(dict(valid, **fields))

    def test_duplicate_bytes_and_conflict(self):
        obs = webhook(); changed = deepcopy(obs); changed['body']['untrusted'] = 'changed'
        page(make_page('project', [obs, obs]))
        with self.assertRaises(Error): page(make_page('project', [obs, changed]))


if __name__ == '__main__':
    unittest.main()
