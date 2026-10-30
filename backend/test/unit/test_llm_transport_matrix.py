"""Validate real client behavior with its network boundary mocked."""
from unittest.mock import patch
from django.test import SimpleTestCase
from backend.ollama import OllamaClient, OllamaResponseError
from backend.test.unit.llm_cases import cases, expand_cases

INVALID = [('null', None), ('boolean', True), ('number', 9), ('empty', ''), ('spaces', ' \n\t '), ('list', []), ('object', {})]


@expand_cases
class LlmTransportMatrixTests(SimpleTestCase):
    def setUp(self):
        self.client = OllamaClient(base_url='http://unused.invalid', model='test', embedding_model='embed',
                                   embedding_dimensions=3, request_timeout=1, health_timeout=1)
        patcher = patch.object(self.client, '_request')
        self.request = patcher.start()
        self.addCleanup(patcher.stop)

    @cases([(f'{role}_{label}', role, value) for role in ('system', 'user', 'assistant') for label, value in INVALID])
    def test_invalid_message_never_reaches_network(self, role, value):
        with self.assertRaises(ValueError):
            self.client.chat([{'role': role, 'content': value}])
        self.request.assert_not_called()

    @cases([('tool', 'tool'), ('developer', 'developer'), ('missing', None), ('uppercase', 'USER'), ('empty', '')])
    def test_invalid_role_never_reaches_network(self, role):
        with self.assertRaises(ValueError):
            self.client.chat([{'role': role, 'content': 'Film'}])
        self.request.assert_not_called()

    @cases(INVALID)
    def test_invalid_response_content(self, value):
        self.request.return_value = {'message': {'content': value}}
        with self.assertRaises(OllamaResponseError):
            self.client.chat([{'role': 'user', 'content': 'Film'}])

    @cases(INVALID)
    def test_invalid_embedding_input_never_reaches_network(self, value):
        with self.assertRaises(ValueError):
            self.client.embed([value])
        self.request.assert_not_called()

    @cases([(f'{position}_{label}', position, value) for position in range(3) for label, value in
            [('null', None), ('bool', True), ('string', '0.1'), ('nan', float('nan')), ('inf', float('inf')), ('negative_inf', -float('inf'))]])
    def test_invalid_embedding_coordinate(self, position, value):
        vector = [.1, .2, .3]
        vector[position] = value
        self.request.return_value = {'embeddings': [vector]}
        with self.assertRaises(OllamaResponseError):
            self.client.embed(['Film'])

    @cases([('missing', None), ('object', {}), ('empty', []), ('short', [[.1, .2]]),
            ('long', [[.1, .2, .3, .4]]), ('extra_vector', [[.1]*3, [.2]*3]), ('not_vector', [None])])
    def test_invalid_embedding_shape(self, value):
        self.request.return_value = {'embeddings': value}
        with self.assertRaises(OllamaResponseError):
            self.client.embed(['Film'])

    @cases([('zero', [0, 0, 0]), ('negative', [-1, -.5, 0]), ('mixed', [1, -.1, .3])])
    def test_finite_embedding_coordinates_are_preserved(self, vector):
        self.request.return_value = {'embeddings': [vector]}
        result = self.client.embed([' Film '])
        self.assertEqual(result.embeddings, (tuple(vector),))
        self.assertEqual(self.request.call_args.kwargs['payload']['input'], ['Film'])

    @cases([('schema', {'type': 'object'}), ('json', 'json'), ('plain', None)])
    def test_chat_preserves_format_and_disables_streaming(self, fmt):
        self.request.return_value = {'message': {'content': ' odpowiedź '}}
        result = self.client.chat([{'role': 'user', 'content': ' Film '}], response_format=fmt, options={'temperature': 0})
        payload = self.request.call_args.kwargs['payload']
        self.assertEqual(payload.get('format'), fmt)
        self.assertFalse(payload['stream'])
        self.assertEqual(payload['messages'], [{'role': 'user', 'content': 'Film'}])
        self.assertEqual(result.content, 'odpowiedź')
