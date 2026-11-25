"""Local child-process observation only; never imports/starts application services."""
import sys
from pathlib import Path
from .common import canonical, parse, Rejected
from .harness import Harness


def main():
    root = Path(sys.argv[1])
    offer = parse((root / 'probe-offer.json').read_bytes())
    harness = Harness(root)
    replay = harness.replay(offer)
    state = harness.inspect()['attempts'][offer['attemptId']]
    try:
        harness.emit(offer, state['handle'], now=0)
    except Rejected as exc:
        emit = exc.code
    else:
        emit = 'unexpected_emit'
    print(canonical({'replay': replay, 'emit': emit, 'calls': state['calls'],
                     'reservation': state['reservation']}).decode('utf-8'))


if __name__ == '__main__':
    main()
