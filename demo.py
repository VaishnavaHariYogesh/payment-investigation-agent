"""First learning step: run the tools manually, without a model or API key."""
import json
from tools import PaymentTools

def main():
    tools = PaymentTools()
    payment = tools.get_payment('P002')
    customer = tools.get_customer(payment['beneficiary_customer_id'])
    invoice = tools.get_invoice(payment['invoice_reference'])
    balance = tools.calculate_balance(invoice['invoice_id'])
    print('Manual tool demo (not an AI-agent run)')
    print('Customer:', customer['name'])
    print('Invoice:', invoice['invoice_id'])
    print('Amount owed: $' + str(balance['amount_due_usd']))
    print('Amount paid: $' + str(balance['counted_paid_usd']))
    print('Balance: $' + str(balance['final_balance_usd']))
    print('A negative balance means more money was paid than was owed.')
    print('\nCalculation evidence:')
    print(json.dumps(balance, indent=2))

if __name__ == '__main__':
    main()
