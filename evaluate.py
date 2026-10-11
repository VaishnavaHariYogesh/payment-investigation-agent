"""Compare one saved live report with the synthetic answer key."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).parent


def evaluate(payload, answer_key):
    report = payload['report']
    payment = report['target_type'] == 'payment'
    key = 'record_id' if payment else 'invoice_id'
    cases = answer_key['payment_cases'] if payment else answer_key['invoice_cases']
    expected = next((case for case in cases if case[key] == report['target_id']), None)
    if expected is None:
        raise ValueError('No labeled answer-key case for this target.')
    required = set(expected['expected_findings'])
    actual = set(report['findings'])
    missing = sorted(required - actual)
    additional_supported = set()
    # An ambiguous payment also leaves its candidate invoices unallocated.
    # Accept that contextual finding only when the actual calculations prove it.
    if payment and 'ambiguous_match' in required and 'unresolved_allocation' in actual:
        candidates = set(expected.get('related_invoice_ids', []))
        unresolved = {entry['result'].get('invoice_id') for entry in payload['tool_trace']
                      if entry['tool'] == 'calculate_balance'
                      and isinstance(entry['result'], dict)
                      and 'final_balance_usd' in entry['result']
                      and entry['result']['final_balance_usd'] is None
                      and report['target_id'] in entry['result'].get('unresolved_candidate_record_ids', [])}
        if (len(candidates) > 1 and candidates <= unresolved
                and report['final_balance_usd'] is None and report['requires_review'] is True):
            additional_supported.add('unresolved_allocation')
    extra = sorted(actual - required - additional_supported)
    sources = {item['source_id'] for item in report['evidence']}
    trace_sources = set()
    from agent import source_ids
    for call in payload['tool_trace']:
        trace_sources.update(source_ids(call['result']))
    unsupported_sources = sorted(sources - trace_sources - {'POLICY'})
    missing_invoices = sorted(set(expected.get('related_invoice_ids', [])) - set(report['related_invoice_ids']))
    if 'invoice_balance_usd' in expected:
        balance_correct = report['final_balance_usd'] == expected['invoice_balance_usd']
    elif 'outstanding_usd' in expected:
        balance_correct = report['final_balance_usd'] == expected['outstanding_usd']
    elif 'overpayment_usd' in expected:
        balance_correct = report['final_balance_usd'] == -expected['overpayment_usd']
    elif 'ambiguous_match' in required or 'unmatched_payment' in required or 'unresolved_allocation' in required:
        balance_correct = report['final_balance_usd'] is None
    elif 'duplicate_record' in required:
        balance_correct = report['final_balance_usd'] == 0
    else:
        balance_correct = None
    review_correct = not expected.get('requires_review', False) or report['requires_review'] is True
    passed = not (missing or extra or unsupported_sources or missing_invoices) and balance_correct is not False and review_correct
    return {'target_id': report['target_id'], 'labels_match': not missing and not extra,
            'missing_findings': missing, 'extra_findings': extra,
            'additional_supported_findings': sorted(additional_supported),
            'unsupported_evidence_ids': unsupported_sources,
            'missing_related_invoice_ids': missing_invoices,
            'balance_correct': balance_correct, 'required_review_flag_present': review_correct,
            'automated_case_check_passed': passed,
            'manual_check': 'Read the explanation and confirm its factual claims against the tool trace. IDs and labels alone do not prove correct reasoning.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('report_path', help='For example reports/P002.json')
    args = parser.parse_args()
    payload = json.loads(Path(args.report_path).read_text())
    if payload.get('mode') != 'live_model':
        parser.error('This evaluator expects a saved live model report.')
    answer_key = json.loads((ROOT / 'evaluation/answer_key.json').read_text())
    result = evaluate(payload, answer_key)
    print(json.dumps(result, indent=2))
    if not result['automated_case_check_passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
