"""Generate a fresh read-only fragment from previously derived narrow synthetic views."""
import re
from pathlib import Path
import sys
from run_vf1 import ROOT, canonical, check
import json


def build(batch, filename):
    check(batch.parent.resolve()==(ROOT/'docs/vf1-results').resolve(),'Invalid batch root')
    check(re.fullmatch(r'dashboard(?:-r[0-9]+)?\.html',filename),'Invalid viewer filename')
    payload=json.loads((batch/'viewer-data.json').read_bytes())
    check(payload['version']=='vf1-viewer-1.0.0','Unexpected view version')
    for label, view in zip(('a','b'),payload['reports'],strict=True):
        check(view==json.loads((batch/label/'view.json').read_bytes()),'View differs from derived record')
    data=canonical(payload).decode('utf-8').replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    template=(ROOT/'spikes/vf1/viewer.html').read_text(encoding='utf-8')
    with (batch/filename).open('xb') as stream:
        stream.write(template.replace('/*VF1_DATA*/null',data).encode('utf-8'))


if __name__=='__main__':
    build(ROOT/'docs/vf1-results'/sys.argv[1],sys.argv[2])
