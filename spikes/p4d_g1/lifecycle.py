"""Independent cleanup even when startup, connection close or bookkeeping fails."""


def finish(evidence, *, attempted, close, pins, observe, stop):
    for stage, action in (('close', close), ('inputsAfter', pins)):
        try:
            value = action()
            if stage == 'inputsAfter':
                evidence['inputsAfter'] = value
                if value != evidence['inputsBefore']:
                    evidence['status'] = 'ERROR'
                    evidence['sourceMutation'] = True
        except Exception as exc:
            evidence['status'] = 'ERROR'
            evidence.setdefault('finalizationErrors', []).append({'stage': stage, 'type': type(exc).__name__})
    if not attempted:
        evidence['databaseStopped'] = None
        return
    try:
        status = observe()
        evidence['databaseAfterAttempt'] = status
        if status == 'RUNNING':
            evidence['databaseStopObservation'] = stop()
        elif status != 'STOPPED':
            raise RuntimeError('G1_UNKNOWN_DATABASE_STATUS')
        evidence['databaseFinalStatus'] = observe()
        if evidence['databaseFinalStatus'] != 'STOPPED':
            raise RuntimeError('G1_DATABASE_NOT_STOPPED')
        evidence['databaseStopped'] = True
    except Exception as exc:
        evidence['status'], evidence['databaseStopped'] = 'ERROR', False
        evidence.setdefault('finalizationErrors', []).append({'stage': 'databaseCleanup', 'type': type(exc).__name__})
