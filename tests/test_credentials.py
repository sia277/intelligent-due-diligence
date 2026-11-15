"""Offline tests: never load a real credential or send a request."""
import ast
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def functions_from(filename, names):
    tree = ast.parse((ROOT / filename).read_text())
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    return compile(ast.Module(body=nodes, type_ignores=[]), filename, 'exec')


class CredentialTests(unittest.TestCase):
    def test_environment_has_priority_without_touching_secrets(self):
        class NoSecrets:
            @property
            def secrets(self):
                raise AssertionError('should not access secrets')
        scope = {'os': os, 'st': NoSecrets()}
        exec(functions_from('streamlit_app.py', {'get_api_key'}), scope)
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': ' test-value '}, clear=True):
            self.assertEqual(scope['get_api_key'](), 'test-value')

    def test_secrets_fallback(self):
        scope = {'os': os, 'st': SimpleNamespace(secrets={'DEEPSEEK_API_KEY': ' test-value '})}
        exec(functions_from('streamlit_app.py', {'get_api_key'}), scope)
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(scope['get_api_key'](), 'test-value')

    def test_missing_secrets_file(self):
        class MissingSecrets:
            @property
            def secrets(self):
                raise FileNotFoundError('no config')
        scope = {'os': os, 'st': MissingSecrets()}
        exec(functions_from('streamlit_app.py', {'get_api_key'}), scope)
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(scope['get_api_key'](), '')

    def test_requests_are_blocked_without_key(self):
        for filename, argument in [('app.py', []), ('streamlit_app.py', 'question')]:
            with self.subTest(filename=filename):
                requests = Mock()
                scope = {'DEEPSEEK_API_KEY': '', 'requests': requests}
                exec(functions_from(filename, {'call_deepseek'}), scope)
                self.assertIn('未配置', scope['call_deepseek'](argument))
                requests.post.assert_not_called()

    def test_provider_errors_and_exceptions_are_not_echoed(self):
        for filename, argument in [('app.py', []), ('streamlit_app.py', 'question')]:
            with self.subTest(filename=filename):
                requests = Mock()
                scope = {'DEEPSEEK_API_KEY': 'test-value', 'requests': requests}
                exec(functions_from(filename, {'call_deepseek'}), scope)
                requests.post.return_value.json.return_value = {'error': {'message': 'sensitive-detail'}}
                self.assertNotIn('sensitive-detail', scope['call_deepseek'](argument))
                requests.post.side_effect = RuntimeError('sensitive-detail')
                self.assertNotIn('sensitive-detail', scope['call_deepseek'](argument))

    def test_success_response_is_preserved(self):
        for filename, argument in [('app.py', []), ('streamlit_app.py', 'question')]:
            requests = Mock()
            requests.post.return_value.json.return_value = {'choices': [{'message': {'content': 'answer'}}]}
            scope = {'DEEPSEEK_API_KEY': 'test-value', 'requests': requests}
            exec(functions_from(filename, {'call_deepseek'}), scope)
            self.assertEqual(scope['call_deepseek'](argument), 'answer')
            self.assertEqual(requests.post.call_args.kwargs['headers']['Authorization'], 'Bearer test-value')


if __name__ == '__main__':
    unittest.main()
