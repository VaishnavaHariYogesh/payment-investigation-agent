# Payment Investigation Agent

A Python learning project that investigates payment discrepancies using an
OpenAI model and read-only Python tools.

The idea came from payment reconciliation problems at my dad's workplace:
payments can be too high, too low, assigned to the wrong fee category, or
difficult to match to an invoice. This prototype explores how an agent can
gather the relevant records and explain those discrepancies.

All records are fictional. No workplace or real customer data is used.

## What the program does

Given a payment or invoice ID, the agent can:

- Retrieve the customer, invoice, and payment records it needs.
- Identify overpayments, underpayments, and fee-category mismatches.
- Account for duplicate imports and payments made in installments.
- Investigate missing invoice references and ambiguous matches.
- Recognize valid payments made by parents or sponsors.
- Produce a JSON report with findings, supporting record IDs, a balance,
  and a flag for human review.

The current version investigates one record at a time. It does not issue refunds
or make changes to financial accounts.

## How it works

1. I provide a record ID to `agent.py`.
2. The model requests the tools it needs to investigate that record.
3. Functions in `tools.py` retrieve data and calculate balances.
4. The model uses those results to produce a structured investigation report.
5. Python checks the report's references and required calculations before saving it.
6. I can run `evaluate.py` to compare the saved report with the expected answer.

Python handles the balance calculations; the model chooses which tools to use
and explains the evidence.

For example, payment P002 is $120 against a $100 invoice. Its invoice balance
is −$20, meaning an overpayment of $20.

## Dataset

The synthetic dataset contains:

- 12 customers
- 13 invoices
- 14 imported payment records

These counts differ because a customer can have multiple invoices, an invoice
can have multiple payments or none, and a payment can be imported twice.
Duplicate imports are counted once when calculating the amount received.

The fixture uses fictional registration policies, whole-dollar USD amounts,
and a reporting date of October 7, 2026.

## My contributions and AI assistance

I developed this as an AI-assisted learning project. My goal is to understand
how the implementation works and become comfortable writing and extending this
kind of program myself.

| My contributions | ChatGPT/Codex assistance |
| --- | --- |
| Came up with the project idea and described the payment problems it should investigate. | Proposed the project structure and how the components could work together. |
| Chose to begin with investigation and use synthetic data. | Generated `payment_data.json` and `answer_key.json`. |
| Worked on `agent.py` and `evaluate.py` with guidance, working through the implementation to learn how to build an agent and evaluate its reports. | Provided implementation code, examples, and explanations for unfamiliar concepts and integrations. |
| Ran investigations, examined the results, and brought mismatches back for debugging. | Helped diagnose failures and generate or explain fixes. |
| Defined the project's scope and directed its development through requirements and feedback. | Generated the instructions prompt inside `investigate()` in `agent.py`, and suggested and helped implement the automated test files. |

Development included AI-generated starting code and guided implementation.
This README was also prepared with AI assistance.

## Why the test files exist

The tests check the Python program's behavior independently of a live API run.

- **`test_tools.py`** checks the lookups and balance calculations. For example,
  duplicate imports should not increase the total amount paid.
- **`test_agent.py`** checks report validation and agent behavior using simulated
  model responses. For example, a report should be rejected if it cites a record
  that no tool retrieved. It also includes checks for evaluation behavior.

These files help catch mistakes when the implementation changes. They do not
call the live model, cost API credit, or run automatically during an investigation.

**`evaluate.py` serves a different purpose:** it checks a particular saved
investigation report against the synthetic dataset's expected findings and
balances. The answer key is not available to the investigating model.

Neither test file is required to run the program.

## Debugging and evaluation

During development, some reports produced by `agent.py` did not match the
answers expected by `evaluate.py`. I used AI assistance to examine the reports,
tool results, and checking rules, then work through the necessary fixes.

Examples included:

- An overpayment report also used `matched`, although that label was defined
  for a fully paid case with no other finding.
- A duplicate-payment investigation needed invoice-wide balance evidence
  before it could correctly identify the duplicate.
- An ambiguous-payment report included a supported `unresolved_allocation`
  finding that the evaluator initially rejected.

These cases showed that a mismatch can come from the agent's behavior, unclear
label definitions, or an evaluation rule. Fixes should follow the retrieved
evidence rather than simply change an answer to make a test pass.

Passing automated checks does not establish that every sentence in a report is
correct. Explanations still need to be compared with the actual tool results.

## Files

| File or folder | Purpose |
| --- | --- |
| `inputs/payment_data.json` | Fictional customers, invoices, payments, and policies |
| `tools.py` | Record lookups, balance calculations, and tool definitions |
| `demo.py` | A manual example using the tools without a model or API key |
| `agent.py` | API integration, tool-calling loop, report validation, and saving |
| `evaluate.py` | Checks a saved report against expected results |
| `evaluation/answer_key.json` | Expected results for the synthetic records |
| `test_tools.py` | Automated tests for the Python tools |
| `test_agent.py` | Automated tests for agent and evaluation behavior |
| `reports/` | Generated investigation reports |
| `requirements.txt` | Python package dependencies |
| `.gitignore` | Excludes local environments, credentials, and generated reports from Git |

## Setup and commands

Use Python 3.10 or newer. Open a terminal in the project folder.

### Install dependencies

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Run the manual example

No API key is needed:

```bash
python demo.py
```

### Investigate a payment

```bash
python agent.py P002
```

The program prompts for an OpenAI API key with hidden input unless
`OPENAI_API_KEY` is already set. The key is not saved by the program.
Live investigations use API credit. Keep keys out of source code and GitHub.

The report is saved to `reports/P002.json`.

To investigate an invoice:

```bash
python agent.py I012 --invoice
```

### Evaluate a saved report

```bash
python evaluate.py reports/P002.json
```

This command uses the saved report and makes no API request.

### Run the automated tests

```bash
python -m unittest test_tools test_agent -v
```

## Future development

- Understand and modify each component while continuing to learn its implementation.
- Implement `batch.py` to investigate multiple records
  and produce a combined summary.
- Add fresh synthetic cases to check behavior beyond the development examples.
- Explore a separate decision-support agent that suggests what to do with each
  discrepancy, with human review.
- Later explore connecting investigation and decision support in one workflow.

The current prototype has been developed with a small synthetic dataset.
Large-scale processing and performance remain future work.
