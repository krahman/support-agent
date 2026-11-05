"""Run: python3 main.py --customer C001 --message 'What is your return policy?'"""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

from support.agent import respond
from support.config import load_env
from support.model import ModelError, OpenRouter
from support.store import Store


class ScriptedClient:
    """Explicit eval-only model double; never selected as a live-mode fallback."""
    def __init__(self, path):
        self.proposal = json.loads(Path(path).read_text())

    def complete(self, messages, tools=None):
        return {'tool_calls': [{'function': {'name': 'support_response',
                                           'arguments': json.dumps(self.proposal)}}]}


def main():
    parser = argparse.ArgumentParser(description='Thread & Harbor simulated apparel support')
    parser.add_argument('--customer', help='Customer ID or guest email')
    parser.add_argument('--message', help='Customer message')
    parser.add_argument('--db', help='SQLite state path (default SUPPORT_DB or state/support.db)')
    parser.add_argument('--check-model', action='store_true', help='Run a small live connectivity check')
    parser.add_argument('--scripted-response', help='EVAL ONLY: JSON proposal file; bypasses the model')
    args = parser.parse_args()
    load_env()
    if args.check_model:
        try:
            response = OpenRouter().complete([{'role': 'user', 'content': 'Reply OK.'}])
            if not response.get('content'):
                raise ModelError('Model returned empty content.')
            print(json.dumps({'model_check': 'passed'}))
            return 0
        except ModelError as exc:
            print(json.dumps({'model_check': 'failed', 'error': str(exc)}))
            return 1
    if not args.customer or args.message is None:
        parser.error('--customer and --message are required')
    try:
        client = ScriptedClient(args.scripted_response) if args.scripted_response else None
        result = respond(Store(args.db), args.customer, args.message, client)
        if client:
            result['mode'] = 'scripted-eval'
        print(json.dumps(result, indent=2))
        return 1 if result.get('error') else 0
    except (OSError, sqlite3.Error, ValueError):
        print(json.dumps({'reply': 'Unable to access local state or configuration. Contact human support.',
                          'actions': [], 'error': 'local_configuration'}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
