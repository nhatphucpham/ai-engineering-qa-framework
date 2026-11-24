"""Bounded candidate-only maintenance wait; retained spike helpers remain unchanged."""
import subprocess
import time

from .common import require


def stop_database():
    from local import BIN, command, read_config
    config = read_config(False)
    begin = time.monotonic()
    # Larger preserved campaigns have thousands of files to fsync. Do not disable
    # durability, force-kill a checkpoint, change PG settings or reuse the old40s cap.
    subprocess.run([str(BIN / 'pg_ctl.exe'), '-D', config['data'], '-m', 'fast', '-t', '240', '-w', 'stop'],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=260,
                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    try:
        command('pg_ctl', '-D', config['data'], 'status')
    except subprocess.CalledProcessError as exc:
        require(exc.returncode == 3, 'E_UNRESOLVED')
    else:
        require(False, 'E_UNRESOLVED')
    return {'mode': 'fast', 'pgCtlWaitBudgetSeconds': 240, 'outerBudgetSeconds': 260,
            'elapsedSeconds': time.monotonic() - begin, 'statusCode': 3}
