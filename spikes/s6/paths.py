"""No third-party imports: prerequisite failure remains reportable."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
CACHE=ROOT/'.cache/s6'
DEPS=CACHE/'deps'

class Blocked(Exception):
    def __init__(self,code='E_RESTRICTED'):
        self.code=code
        super().__init__(code)
