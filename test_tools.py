"""Regression cases for matching and arithmetic. No model is needed."""
import copy
import unittest
from tools import PaymentTools

class ToolTests(unittest.TestCase):
    def setUp(self):
        self.tools = PaymentTools()

    def test_overpayment(self):
        self.assertEqual(self.tools.calculate_balance('I002')['final_balance_usd'], -20)

    def test_underpayment(self):
        self.assertEqual(self.tools.calculate_balance('I003')['final_balance_usd'], 20)

    def test_duplicate_import_is_not_a_second_payment(self):
        result = self.tools.calculate_balance('I006')
        self.assertEqual(result['counted_paid_usd'], 100)
        self.assertEqual(result['final_balance_usd'], 0)
        self.assertEqual(result['duplicate_record_ids'], ['P007'])

    def test_split_payments_are_combined(self):
        result = self.tools.calculate_balance('I010')
        self.assertEqual(result['counted_record_ids'], ['P010', 'P011'])
        self.assertEqual(result['final_balance_usd'], 0)

    def test_parent_and_sponsor_are_valid(self):
        for invoice_id in ['I005', 'I011']:
            self.assertEqual(self.tools.calculate_balance(invoice_id)['final_balance_usd'], 0)

    def test_missing_reference_with_single_candidate(self):
        result = self.tools.calculate_balance('I007')
        self.assertEqual(result['inferred_record_ids'], ['P008'])
        self.assertEqual(result['final_balance_usd'], 0)

    def test_ambiguous_payment_is_not_guessed_or_called_unpaid(self):
        for invoice_id in ['I008', 'I009']:
            result = self.tools.calculate_balance(invoice_id)
            self.assertIsNone(result['final_balance_usd'])
            self.assertEqual(result['unresolved_candidate_record_ids'], ['P009'])

    def test_unpaid_invoice(self):
        self.assertEqual(self.tools.calculate_balance('I012')['final_balance_usd'], 100)

    def test_unknown_customer(self):
        self.assertIn('error', self.tools.get_customer('C999'))

    def test_category_mismatch_remains_visible_in_sources(self):
        self.assertEqual(self.tools.get_payment('P004')['fee_category'], 'child')
        self.assertEqual(self.tools.get_customer('C004')['age_group'], 'adult')
        self.assertEqual(self.tools.calculate_balance('I004')['final_balance_usd'], 50)

    def test_new_future_payment_does_not_change_snapshot(self):
        data = copy.deepcopy(self.tools.data)
        payment = dict(data['payments'][0], record_id='NEW', transaction_id='NEW', payment_date='2026-10-08')
        data['payments'].append(payment)
        self.assertEqual(PaymentTools(data).calculate_balance('I001')['final_balance_usd'], 0)

    def test_new_conflicting_duplicate_needs_review(self):
        data = copy.deepcopy(self.tools.data)
        data['payments'][6]['amount_usd'] = 999
        result = PaymentTools(data).calculate_balance('I006')
        self.assertIsNone(result['final_balance_usd'])
        self.assertEqual(result['counted_paid_usd'], 0)
        self.assertEqual(set(result['conflicting_record_ids']), {'P006', 'P007'})

    def test_invalid_tool_arguments_are_reported(self):
        self.assertIn('error', self.tools.call('get_payment', {'record_id': 5}))
        self.assertIn('error', self.tools.call('delete_payment', {'record_id': 'P002'}))

if __name__ == '__main__':
    unittest.main()