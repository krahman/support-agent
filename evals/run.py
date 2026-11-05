"""Preserve every run, including failures and interruption, without logging secrets."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest
import uuid

from support.config import ROOT, load_env
from support.model import DEFAULT_MODEL


def fingerprint():
    digest = hashlib.sha256()
    for folder in ('support', 'tests', 'evals', 'data'):
        for path in sorted((ROOT / folder).rglob('*')):
            if path.suffix in ('.py', '.json') and path.is_file():
                digest.update(str(path.relative_to(ROOT)).encode())
                digest.update(path.read_bytes())
    digest.update((ROOT / 'main.py').read_bytes())
    return digest.hexdigest()


class EvidenceResult(unittest.TextTestResult):
    def __init__(self, *args, report, save, **kwargs):
        super().__init__(*args, **kwargs)
        self.report, self.save = report, save

    def startTest(self, test):
        self.report['active_test'] = test.id()
        self.save()
        super().startTest(test)

    def record(self, test, status, error=None):
        observed = getattr(test, 'observed', {})
        if not observed and getattr(test, 'store', None):
            try:
                ledger = test.store.snapshot()['ledger']
                observed = {'ledger': ledger, 'ledger_total_cents': sum(r['amount_cents'] for r in ledger)}
            except Exception:
                observed = {'state_snapshot': 'unavailable'}
        case = {'id': test.id(), 'criteria': test.shortDescription() or test.id(),
                'status': status, 'steps': getattr(test, 'evidence', []),
                'observed': observed}
        if error:
            # Only assertions from fictional data; never provider response bodies.
            case['detail'] = self._exc_info_to_string(error, test)
        self.report['cases'].append(case)
        self.report['active_test'] = None
        self.save()

    def addSuccess(self, test):
        super().addSuccess(test)
        self.record(test, 'pass')

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.record(test, 'fail', err)

    def addError(self, test, err):
        super().addError(test, err)
        self.record(test, 'error', err)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.record(test, 'skip')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--pattern', default='test_*.py', help='Offline unittest filename filter')
    args = parser.parse_args()
    load_env()
    os.environ['SUPPORT_LIVE_EVAL'] = '1' if args.live else '0'
    os.environ['SUPPORT_TODAY'] = '2026-11-04'
    os.environ['SUPPORT_LOOKUP_FAIL'] = '0'
    folder = ROOT / 'eval_runs'
    folder.mkdir(exist_ok=True)
    path = folder / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + uuid.uuid4().hex[:8] + '.json')
    report = {'started_at': datetime.now(timezone.utc).isoformat(),
              'mode': 'live-openrouter' if args.live else 'offline-scripted-and-executor',
              'model': os.environ.get('OPENROUTER_MODEL', DEFAULT_MODEL) if args.live else None,
              'clock': '2026-11-04', 'source_sha256': fingerprint(),
              'status': 'running', 'cases': []}
    def save():
        # Redact known environment credentials, including accidental assertion traces.
        content = json.dumps(report, indent=2)
        for key in ('ANTHROPIC_API_KEY', 'OPENROUTER_API_KEY', 'OPENAI_API_KEY'):
            value = os.environ.get(key)
            if value:
                content = content.replace(value, '[REDACTED]')
        path.write_text(content + '\n')
    save()
    result = None
    try:
        suite = unittest.defaultTestLoader.discover(str(ROOT / ('evals/live' if args.live else 'tests')), pattern=args.pattern, top_level_dir=str(ROOT))
        runner = unittest.TextTestRunner(verbosity=2, resultclass=lambda *a, **kw: EvidenceResult(*a, report=report, save=save, **kw))
        result = runner.run(suite)
        report['status'] = 'passed' if result.wasSuccessful() else 'failed'
        report['summary'] = {'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped)}
    finally:
        if report['status'] == 'running':
            report['status'] = 'interrupted'
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        save()
        print('Evidence:', path.relative_to(ROOT))
    return 0 if result and result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
