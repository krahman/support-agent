import io
import json
import os
import socket
import ssl
import unittest
from unittest.mock import patch
import urllib.error

from support.agent import TOOLS
from support.model import DEFAULT_MODEL, ModelError, OpenRouter


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-placeholder', 'OPENROUTER_MODEL': 'test/model'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def complete_with(self, payload, tools=None):
        response = io.BytesIO(json.dumps(payload).encode())
        with patch('urllib.request.urlopen', return_value=response):
            return OpenRouter().complete([{'role': 'user', 'content': 'Hello'}], tools)

    def payload(self, arguments=None, name='support_response', finish='tool_calls'):
        return {'choices': [{'finish_reason': finish, 'message': {'tool_calls': [
            {'type': 'function', 'function': {'name': name, 'arguments': json.dumps(arguments if arguments is not None else {'kind': 'answer', 'reply': 'Hello'})}}
        ]}}]}

    def test_transport_contract(self):
        """Transport uses OpenRouter HTTPS, environment bearer auth, bounded timeout, and preserved system/history roles."""
        payload = {'choices': [{'finish_reason': 'stop', 'message': {'content': 'OK'}}]}
        messages = [{'role': 'system', 'content': 'Rules'}, {'role': 'system', 'content': 'Facts'},
                    {'role': 'user', 'content': 'Previous request'},
                    {'role': 'assistant', 'content': 'Previous reply'},
                    {'role': 'user', 'content': 'Hello'}]
        with patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(payload).encode())) as request:
            self.assertEqual(OpenRouter().complete(messages), {'content': 'OK'})
        sent = request.call_args.args[0]
        self.assertEqual(sent.full_url, 'https://openrouter.ai/api/v1/chat/completions')
        self.assertEqual(sent.get_header('Authorization'), 'Bearer test-placeholder')
        self.assertIsNone(sent.get_header('X-api-key'))
        body = json.loads(sent.data)
        self.assertEqual(body['messages'], messages)
        self.assertEqual(body['model'], 'test/model')
        self.assertNotIn('system', body)
        self.assertNotIn('thinking', body)
        self.assertEqual(request.call_args.kwargs['timeout'], 45)

    def test_tool_schema_and_proposal(self):
        """OpenRouter receives function schemas and forced single-tool selection; valid object arguments reach the agent."""
        proposal = {'kind': 'refund', 'reply': 'Proposing refund', 'order_id': 'O100', 'unit_ids': ['O100-1-1']}
        with patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(self.payload(proposal)).encode())) as request:
            result = OpenRouter().complete([{'role': 'user', 'content': 'Refund my tee'}], TOOLS)
        body = json.loads(request.call_args.args[0].data)
        self.assertEqual(body['tools'], TOOLS)
        self.assertEqual(body['tool_choice'], {'type': 'function', 'function': {'name': 'support_response'}})
        self.assertFalse(body['parallel_tool_calls'])
        self.assertEqual(json.loads(result['tool_calls'][0]['function']['arguments']), proposal)

    def test_http_error_redacted(self):
        """HTTP errors expose only status, not private provider error bodies."""
        error = urllib.error.HTTPError('https://openrouter.ai', 401, 'secret-provider-body', {}, None)
        with patch('urllib.request.urlopen', side_effect=error):
            with self.assertRaisesRegex(ModelError, 'OpenRouter HTTP 401') as result:
                OpenRouter().complete([])
        self.assertNotIn('secret-provider-body', str(result.exception))

    def test_network_error_redacted(self):
        """Generic connection errors never reveal private socket details."""
        with patch('urllib.request.urlopen', side_effect=urllib.error.URLError('private socket details')):
            with self.assertRaisesRegex(ModelError, 'network connection failed') as result:
                OpenRouter().complete([])
        self.assertNotIn('private socket', str(result.exception))

    def test_dns_tls_timeout_diagnostics(self):
        """DNS, TLS, and timeout failures are distinguishable without leaking raw error details."""
        for reason, expected in ((socket.gaierror(8, 'private DNS detail'), 'DNS lookup failed'),
                                 (ssl.SSLError('private TLS detail'), 'TLS verification failed'),
                                 (TimeoutError('private timeout detail'), 'timed out')):
            with patch('urllib.request.urlopen', side_effect=urllib.error.URLError(reason)):
                with self.assertRaisesRegex(ModelError, expected) as result:
                    OpenRouter().complete([])
                self.assertNotIn('private', str(result.exception))

    def test_invalid_provider_payload(self):
        """Malformed or empty provider responses cannot reach application dispatch."""
        for payload in ({'choices': []}, {'choices': [{'finish_reason': 'stop', 'message': None}]},
                        {'choices': [{'finish_reason': 'stop', 'message': {'content': ''}}]}):
            with self.assertRaises(ModelError):
                self.complete_with(payload)

    def test_truncated_tool_rejected(self):
        """A token-limited response never authorizes a tool action, even if arguments look complete."""
        with self.assertRaises(ModelError):
            self.complete_with(self.payload(finish='length'), TOOLS)

    def test_multiple_or_wrong_tools_rejected(self):
        """Multiple, unexpected, or non-object tool proposals are rejected."""
        multiple = self.payload()
        multiple['choices'][0]['message']['tool_calls'] *= 2
        for payload in (multiple, self.payload(name='refund_everyone'), self.payload(arguments='invalid'),
                        {'choices': [{'finish_reason': 'stop', 'message': {'content': 'Refunded!'}}]}):
            with self.assertRaises(ModelError):
                self.complete_with(payload, TOOLS)

    def test_nonfinite_tool_arguments_rejected(self):
        """Nonfinite JSON values cannot be forwarded as executable arguments."""
        with self.assertRaises(ModelError):
            self.complete_with(self.payload(arguments={'kind': 'refund', 'amount': float('nan')}), TOOLS)

    def test_default_and_missing_key(self):
        """OpenRouter default is configurable and missing credentials fail before network access."""
        with patch.dict(os.environ):
            os.environ.pop('OPENROUTER_MODEL', None)
            self.assertEqual(OpenRouter().name, DEFAULT_MODEL)
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': ''}):
            with patch('urllib.request.urlopen') as network:
                with self.assertRaisesRegex(ModelError, 'OPENROUTER_API_KEY'):
                    OpenRouter()
                network.assert_not_called()
