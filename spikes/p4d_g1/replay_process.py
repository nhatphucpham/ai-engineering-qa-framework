"""New process reopens committed state, replays receive and loses start response."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'spikes/s2')]
from runtime_candidate.common import strict_json, require, VERSION, Error
from runtime_candidate.application import Application
from .ingress import Ingress


def main():
    context = strict_json(Path(sys.argv[1]).read_bytes())
    app = Application(context['schema'], Path(context['root']))
    try:
        if context.get('mode') == 'incident':
            # Operator SQL observation is not an ordinary API read or recovery.
            for table, expected in context['expectedCounts'].items():
                require(table in ('g1_receipts', 'g1_bindings', 'g1_pages', 'rt_intakes', 'rt_runs', 'rt_events', 'rt_receipts'))
                require(app.conn.execute('SELECT count(*) AS n FROM ' + table + ' WHERE project=%s', (context['project'],)).fetchone()['n'] == expected)
            try:
                app.dispatch('project_read', context['access'], {'version': VERSION, 'project': context['project']})
            except Error as exc:
                require(exc.code == 'E_UNRESOLVED')
            else:
                raise Error('E_INTEGRITY')
            return 0
        ingress = Ingress(app)
        received = ingress.receive(context['access'], context['page'])
        require(received['cursor'] == 1)
        intake = ingress.guarded(context['access'], context['page']['project'], context['binding'], 'intake')
        ingress.guarded(context['access'], context['page']['project'], context['binding'], 'start', intake['intakeId'])
        # Process exits without saving completion marker. Both API transactions committed.
    finally:
        app.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
