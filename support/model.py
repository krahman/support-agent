"""OpenRouter chat completions transport. Credentials never appear in errors."""
import json
import os
import socket
import ssl
import urllib.error
import urllib.request

DEFAULT_MODEL = 'openai/gpt-4o-mini'


class ModelError(Exception):
    pass


def reject_constant(value):
    raise ValueError('Nonfinite JSON value')


class OpenRouter:
    def __init__(self):
        self.key = os.environ.get('OPENROUTER_API_KEY', '').strip()
        self.name = os.environ.get('OPENROUTER_MODEL', DEFAULT_MODEL)
        if not self.key:
            raise ModelError('Set OPENROUTER_API_KEY in .env or the environment.')

    def complete(self, messages, tools=None):
        body = {'model': self.name, 'messages': messages,
                'max_tokens': 1400, 'temperature': 0}
        if tools:
            body.update(tools=tools,
                        tool_choice={'type': 'function', 'function': {'name': 'support_response'}},
                        parallel_tool_calls=False)
        request = urllib.request.Request(
            'https://openrouter.ai/api/v1/chat/completions',
            data=json.dumps(body).encode(),
            headers={'Authorization': 'Bearer ' + self.key,
                     'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                result = json.load(response)
            choice = result['choices'][0]
            message = choice['message']
            if not isinstance(message, dict):
                raise ValueError('Invalid message')
            if tools:
                calls = message.get('tool_calls', [])
                if choice.get('finish_reason') != 'tool_calls' or not isinstance(calls, list) or len(calls) != 1:
                    raise ValueError('Expected one complete tool proposal')
                function = calls[0]['function']
                if function.get('name') != 'support_response':
                    raise ValueError('Unexpected tool')
                proposal = json.loads(function['arguments'], parse_constant=reject_constant)
                if not isinstance(proposal, dict):
                    raise ValueError('Invalid proposal arguments')
                return {'tool_calls': [{'function': {'name': function['name'],
                                         'arguments': json.dumps(proposal, allow_nan=False)}}]}
            text = message.get('content')
            if choice.get('finish_reason') != 'stop' or not isinstance(text, str) or not text.strip() or message.get('tool_calls'):
                raise ValueError('Expected a complete text response')
            return {'content': text}
        except urllib.error.HTTPError as exc:
            raise ModelError(f'OpenRouter HTTP {exc.code}; check key, credits, and model access.') from None
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, socket.gaierror):
                raise ModelError('OpenRouter DNS lookup failed; check network access to openrouter.ai.') from None
            if isinstance(exc.reason, ssl.SSLError):
                raise ModelError('OpenRouter TLS verification failed; check local certificate configuration.') from None
            if isinstance(exc.reason, TimeoutError):
                raise ModelError('OpenRouter request timed out; try again when connectivity is restored.') from None
            raise ModelError('OpenRouter network connection failed; check outbound HTTPS access.') from None
        except TimeoutError:
            raise ModelError('OpenRouter request timed out; try again when connectivity is restored.') from None
        except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise ModelError('OpenRouter unavailable or returned an invalid response.') from None
