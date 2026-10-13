"""Offline protocol tests with scripted responses, not live model evaluations."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agent import investigate
from evaluate import evaluate
from tools import PaymentTools

def call(name, arguments, call_id):
    return SimpleNamespace(type='function_call', name=name,
                           arguments=json.dumps(arguments), call_id=call_id)


def response(output=None, report=None, status='completed'):
    return SimpleNamespace(output=output or [], output_text=json.dumps(report) if report else '',
                           status=status, usage=None)

def example_report():
    return {'target_type': 'payment', 'target_id': 'P002', 'findings': ['overpayment'],
            'related_payment_ids': ['P002'], 'related_invoice_ids': ['I002'],
            'evidence': [{'source_id': 'P002', 'explanation': 'Payment is $120.'},
                         {'source_id': 'I002', 'explanation': 'Invoice is $100.'}],
            'explanation': 'Morgan paid $20 more than the invoice amount.',
            'final_balance_usd': -20, 'requires_review': False}

class ScriptedClient:
    def __init__(self, scripted_responses):
        self.script = iter(scripted_responses)
        self.requests = []
        self.responses = self

    def create(self, **request):
        self.requests.append(copy.deepcopy(request))
        return next(self.script)

def happy_script(report=None):
    return [
        response([call('get_payment', {'record_id': 'P002'}, 'call_1')]),
        response([call('get_invoice', {'invoice_id': 'I002'}, 'call_2'),
                  call('get_customer', {'customer_id': 'C002'}, 'call_3'),
                  call('calculate_balance', {'invoice_id': 'I002'}, 'call_4')]),
        response(report=report or example_report()),
    ]

class AgentProtocolTests(unittest.TestCase):
    def test_loop_returns_actual_tool_results_to_client(self):
        client = ScriptedClient(happy_script())
        result = investigate(client, PaymentTools(), 'payment', 'P002', verbose=False)
        self.assertEqual(len(result['tool_trace']), 4)
        outputs = [x for x in client.requests[1]['input'] if isinstance(x, dict) and x.get('type') == 'function_call_output']
        self.assertEqual(json.loads(outputs[0]['output'])['amount_usd'], 120)
        self.assertEqual(outputs[0]['call_id'], 'call_1')
        self.assertNotIn('payment_cases', client.requests[0]['instructions'])

    def test_multiple_calls_in_one_response(self):
        result = investigate(ScriptedClient(happy_script()), PaymentTools(), 'payment', 'P002', verbose=False)
        self.assertEqual(result['tool_trace'][-1]['result']['final_balance_usd'], -20)

    def test_rejects_unsupported_evidence(self):
        report = example_report()
        report['evidence'][0]['source_id'] = 'MADE_UP'
        with self.assertRaisesRegex(ValueError, 'no tool retrieved'):
            investigate(ScriptedClient(happy_script(report)), PaymentTools(), 'payment', 'P002', verbose=False)

    def test_rejects_incomplete_response(self):
        with self.assertRaisesRegex(RuntimeError, 'not completed'):
            investigate(ScriptedClient([response(status='incomplete')]), PaymentTools(), 'payment', 'P002', verbose=False)

    def test_enforces_round_limit(self):
        script = [response([call('get_payment', {'record_id': 'P002'}, str(n))]) for n in range(2)]
        with patch('agent.MAX_ROUNDS', 2), self.assertRaisesRegex(RuntimeError, 'round limit'):
            investigate(ScriptedClient(script), PaymentTools(), 'payment', 'P002', verbose=False)

    def test_unknown_tool_returns_error_then_can_recover(self):
        client = ScriptedClient([response([call('delete_payment', {'record_id': 'P002'}, 'bad')])] + happy_script())
        result = investigate(client, PaymentTools(), 'payment', 'P002', verbose=False)
        self.assertIn('error', result['tool_trace'][0]['result'])
        self.assertEqual(result['report']['findings'], ['overpayment'])

    def test_evaluator_detects_wrong_amount_despite_correct_label(self):
        result = investigate(ScriptedClient(happy_script()), PaymentTools(), 'payment', 'P002', verbose=False)
        key = json.loads((Path(__file__).parent / 'evaluation/answer_key.json').read_text())
        self.assertTrue(evaluate(result, key)['automated_case_check_passed'])
        result['report']['final_balance_usd'] = -999
        self.assertFalse(evaluate(result, key)['automated_case_check_passed'])
        
    def test_missing_target_payment_id_is_repaired(self):
        report = example_report()
        report['related_payment_ids'] = []

        script = happy_script(report) + [
            response(report=example_report())
        ]

        result = investigate(
            ScriptedClient(script), PaymentTools(),
            'payment', 'P002', verbose=False
        )

        self.assertEqual(result['report_repairs'], 1)
        self.assertIn(
            'P002', result['report']['related_payment_ids']
        )

    

if __name__ == '__main__':
    unittest.main()