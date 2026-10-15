"""Read-only functions the investigation agent can choose to call."""
import json
from pathlib import Path

DATA_PATH = Path(__file__).parent / 'inputs' / 'payment_data.json'

class PaymentTools:
    def __init__(self, data=None):
        if data is None:
            with DATA_PATH.open() as file:
                data = json.load(file)
        self.data = data

    def get_payment(self, record_id):
        for payment in self.data['payments']:
            if payment['record_id'] == record_id:
                return payment
        return {'error': 'Payment record not found', 'record_id': record_id}

    def get_customer(self, customer_id):
        for customer in self.data['customers']:
            if customer['customer_id'] == customer_id:
                return customer
        return {'error': 'Customer not found', 'customer_id': customer_id}

    def get_invoice(self, invoice_id):
        for invoice in self.data['invoices']:
            if invoice['invoice_id'] == invoice_id:
                return invoice
        return {'error': 'Invoice not found', 'invoice_id': invoice_id}

    def find_invoices(self, customer_id):
        return [invoice for invoice in self.data['invoices']
                if invoice['beneficiary_customer_id'] == customer_id]

    def find_payments(self, customer_id):
        return [payment for payment in self.data['payments']
                if payment['beneficiary_customer_id'] == customer_id
                and payment['payment_date'] <= self.data['as_of_date']]

    def calculate_balance(self, invoice_id):
        """Do arithmetic in Python, preserving uncertain matches and duplicates."""
        invoice = self.get_invoice(invoice_id)
        if 'error' in invoice:
            return invoice
        customer_id = invoice['beneficiary_customer_id']
        customer_invoices = self.find_invoices(customer_id)
        customer_payments = self.find_payments(customer_id)
        confirmed = []
        inferred_ids = []
        unresolved_ids = []
        invalid_reference_ids = []
        for payment in customer_payments:
            reference = payment['invoice_reference']
            if reference == invoice_id:
                confirmed.append(payment)
            elif reference and 'error' in self.get_invoice(reference):
                invalid_reference_ids.append(payment['record_id'])
            elif not reference and len(customer_invoices) == 1:
                confirmed.append(payment)
                inferred_ids.append(payment['record_id'])
            elif not reference:
                unresolved_ids.append(payment['record_id'])

        # A repeated transaction ID can be a duplicate import. If its details
        # conflict anywhere in the dataset, exclude that transaction for review.
        source_transactions = {}
        conflicts = set()
        for payment in self.data['payments']:
            if payment['payment_date'] > self.data['as_of_date']:
                continue
            transaction_id = payment['transaction_id']
            details = {key: value for key, value in payment.items() if key != 'record_id'}
            if transaction_id in source_transactions and source_transactions[transaction_id] != details:
                conflicts.add(transaction_id)
            source_transactions[transaction_id] = details

        unique_payments = {}
        duplicates = []
        excluded = []
        for payment in confirmed:
            transaction_id = payment['transaction_id']
            if transaction_id in conflicts:
                excluded.append(payment['record_id'])
            elif transaction_id in unique_payments:
                duplicates.append(payment['record_id'])
            else:
                unique_payments[transaction_id] = payment

        paid = sum(payment['amount_usd'] for payment in unique_payments.values())
        balance = invoice['amount_due_usd'] - paid
        certain = not (unresolved_ids or invalid_reference_ids or excluded)
        return {
            'invoice_id': invoice_id,
            'as_of_date': self.data['as_of_date'],
            'currency': 'USD',
            'amount_due_usd': invoice['amount_due_usd'],
            'counted_paid_usd': paid,
            'counted_record_ids': [p['record_id'] for p in unique_payments.values()],
            'inferred_record_ids': inferred_ids,
            'duplicate_record_ids': duplicates,
            'unresolved_candidate_record_ids': unresolved_ids,
            'invalid_reference_record_ids': invalid_reference_ids,
            'conflicting_record_ids': excluded,
            'balance_after_counted_payments_usd': balance,
            'final_balance_usd': balance if certain else None,
            'balance_meaning': 'Positive means outstanding; negative means excess paid. Null final balance means allocation is unresolved.',
        }

    def call(self, name, arguments):
        """Allow only our named tools and one expected string argument."""
        expected = {spec[0]: spec[1] for spec in TOOL_SPECS}
        if name not in expected:
            return {'error': 'Unknown tool'}
        key = expected[name]
        if not isinstance(arguments, dict) or set(arguments) != {key}:
            return {'error': 'Tool requires exactly one argument: ' + key}
        if not isinstance(arguments[key], str) or not arguments[key].strip():
            return {'error': key + ' must be a nonempty string'}
        return getattr(self, name)(arguments[key])

TOOL_SPECS = [
    ('get_payment', 'record_id', 'Retrieve one imported payment record by P-prefixed record ID.'),
    ('get_customer', 'customer_id', 'Retrieve the registered beneficiary and their authoritative age group. Not-found is evidence of an unknown customer.'),
    ('get_invoice', 'invoice_id', 'Retrieve an invoice and its expected fee, beneficiary, and due date.'),
    ('find_invoices', 'customer_id', 'Retrieve all invoices for a beneficiary, including multiple possible matches.'),
    ('find_payments', 'customer_id', 'Retrieve all payment records for a beneficiary through the dataset reporting date; includes duplicate imports and split payments.'),
    ('calculate_balance', 'invoice_id', 'Calculate an invoice balance with duplicate source transactions counted once, split payments summed, and uncertain allocations left unresolved. This calculates evidence; it does not decide a financial resolution.'),
]

TOOL_DEFINITIONS = [
    {'type': 'function', 'name': name, 'description': description, 'strict': True,
     'parameters': {'type': 'object', 'properties': {key: {'type': 'string'}},
                    'required': [key], 'additionalProperties': False}}
    for name, key, description in TOOL_SPECS
]