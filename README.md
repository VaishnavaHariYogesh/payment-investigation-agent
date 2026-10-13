# Payment Investigation Agent

This project is based on a real payment problem at my dad's workplace. Some payments are too high or too low, some use the wrong fee category, and others are hard to match to the right invoice.

I built this program to look through payment records, investigate what happened, and explain its findings with evidence. I implemented it using Python, the OpenAI API, and read-only tools, with ChatGPT/Codex guidance throughout development.

The data in this project is made up. I haven't used any real customer or workplace records.

## What it does

You give the program a payment or invoice ID. It looks up the relevant records and returns a JSON report with its findings, the balance, supporting record IDs, and whether the case needs human review.

It handles cases such as:

- Overpayments and underpayments
- Payments using the wrong fee category
- The same payment being imported more than once
- Split payments toward one invoice
- Missing invoice references or more than one possible invoice match
- Valid payments made by parents or sponsors

`agent.py` investigates one record. `batch.py` runs several investigations one by one and saves a combined summary. If one record fails, the batch continues with the others.

The tools only read records and calculate balances. The program doesn't issue refunds or change accounts.

## How it works

1. I enter a payment or invoice ID.
2. The model chooses which tools it needs.
3. The Python tools retrieve the records and calculate the balance.
4. The model uses those results to explain its findings.
5. Python checks the report's references and required calculations. Some validation failures trigger a request for a corrected report.
6. I can check the saved report against the answer key using `evaluate.py`.

The calculations happen in Python. The model decides what to look up and explains the results.

For example, P002 is a $120 payment toward a $100 invoice. The balance is `100 - 120 = -20`, so the report should identify a $20 overpayment. P003 is an $80 payment toward a $100 invoice, leaving $20 outstanding.

## The data

The dataset has 12 customers, 13 invoices, and 14 imported payment records. The counts differ because one customer can have several invoices, an invoice can have several payments or none, and a payment can be imported twice.

It uses fictional registration policies, whole-dollar USD amounts, and a reporting date of October 7, 2026. Duplicate imports are counted once in the payment total.

## My work and AI assistance

I implemented this program with ChatGPT/Codex guidance. The business problem and project idea came from me. I described the cases it needed to handle, chose to use fictional data, and worked through the implementation from both the business and technical sides.

As I developed it, I used guidance to connect the components, understand the logic, apply changes, and test whether the program behaved as expected. That included the investigation agent, evaluator, batch processing, report validation, and automated test setup.

ChatGPT/Codex helped with design suggestions, explanations, code suggestions and examples, the synthetic dataset and answer key, the agent prompt, tests, and debugging. Some code and test examples were AI-generated and incorporated into the project. I used that assistance while implementing and extending the program.

| My work | ChatGPT/Codex's guidance |
| --- | --- |
| Identified the business problem and defined the payment cases and project scope. | Helped translate those requirements into a program structure and synthetic test data. |
| Implemented and connected the agent and evaluator with guidance, working through how records, tools, reports, and checks fit together. | Guided the structure and integration, provided code examples and the agent prompt, and explained unfamiliar concepts. |
| Implemented `batch.py` with ChatGPT/Codex guidance, including the processing loop, per-record failure handling, report saving, and batch summary. Tested it with offline cases and live investigations. | Helped me work through the batch design, error handling, code examples, and tests. |
| Configured GitHub Actions to run the test suite automatically, with guidance. | Explained the workflow and provided configuration examples and setup guidance. |
| Examined results with assistance, applied the report-validation fix, and added its regression test. | Helped identify the missing payment ID, explain the validation gap, and develop the fix and test. |

This project is an opportunity for me to learn how to turn a business problem into a working program through guided implementation, testing, and debugging. I can explain how the current components work, and I want to build on that experience with new features. This README was also written and edited with AI assistance.

## Testing and checking results

There are currently **24 offline automated tests**:

- `test_tools.py` checks record lookups and payment calculations, including duplicates, split payments, and uncertain matches.
- `test_agent.py` uses simulated model responses to check the tool-calling flow, report validation, repair requests, and evaluation behavior.
- `test_batch.py` checks that a missing record or failed investigation doesn't stop the batch. It also checks summary counts and invoice mode.

Run them with:

```bash
python -m unittest discover -v
```

These tests don't call the live model or use API credit. GitHub Actions runs them on pushes and pull requests, and I can also start the workflow manually. They don't run as part of a live investigation.

`evaluate.py` checks a saved live report against the expected findings and balances in the answer key. The investigating model doesn't get access to that answer key.

### Problems we caught

While testing the implementation, I reviewed the reports with ChatGPT/Codex assistance and worked through several fixes:

- An overpayment report also used `matched`, even though that label is only for a fully paid case with no other finding.
- A duplicate-payment case needed the balance check to include all relevant payments for the invoice.
- The evaluator rejected an extra `unresolved_allocation` finding even though the tool results supported it for an ambiguous match.
- A live underpayment report passed the evaluator but left `related_payment_ids` empty. We added a check requiring the target payment ID and a test confirming that the agent requests and accepts a corrected report.

That last case is why I still check the explanations against the tool results. Passing the evaluator doesn't mean every sentence or every part of the report has been checked. A mismatch can also come from the checking rules, so the retrieved evidence matters when debugging.

## Files

| File or folder | What it's for |
| --- | --- |
| `inputs/payment_data.json` | Fictional customers, invoices, payments, and policies |
| `tools.py` | Record lookups, balance calculations, and tool definitions |
| `demo.py` | An example that runs without a model or API key |
| `agent.py` | One investigation, API integration, report checks, and saving |
| `batch.py` | Multiple investigations, failure handling, and a combined summary |
| `evaluate.py` | Checking a saved report against expected results |
| `evaluation/answer_key.json` | Expected results for the synthetic records |
| `test_tools.py` | Tests for lookups and calculations |
| `test_agent.py` | Tests for agent and evaluator behavior |
| `test_batch.py` | Tests for batch behavior |
| `.github/workflows/tests.yml` | Automatic test runs on GitHub |
| `reports/` | Saved investigation reports and batch results |
| `requirements.txt` | Python dependencies |
| `.gitignore` | Keeps local environments, credentials, and generated reports out of Git |

## Running the project

Use Python 3.10 or newer and open a terminal in the project folder.

### Set it up

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Try it without an API key

```bash
python demo.py
```

### Investigate one record

For a payment:

```bash
python agent.py P002
```

For an invoice:

```bash
python agent.py I012 --invoice
```

The program asks for an OpenAI API key with hidden input unless `OPENAI_API_KEY` is already set. It doesn't save the key. Live investigations use API credit; keep keys out of source code and GitHub.

A single-record report is saved under `reports/`, for example `reports/P002.json`.

### Investigate several records

For payments:

```bash
python batch.py P002 P003
```

For invoices:

```bash
python batch.py I002 I003 --invoice
```

The batch asks for the key once unless it's already set. It makes live API calls and uses API credit. Use `python batch.py --help` to see the arguments, including `--model`.

Each run makes a new folder under `reports/` with a timestamp in its name. It saves:

- An individual `report_<position>.json` for each completed investigation. The position follows the input order, so a failed record can leave a gap in the numbering.
- `batch_summary.json`, containing the individual results and counts for completed investigations, failures, and completed reports needing review. Successful entries include `report_file` so I can find the right saved report.

A missing record is marked as failed without investigating it. If an investigation raises an exception, the batch records the error type and moves on. If any record failed, the command exits with status 1 after saving the results.

A completed investigation means the agent returned a report that passed its validation. The payment can still have a discrepancy, and the report still needs checking. Failed investigations aren't included in the count of completed reports needing review.

### Check a saved report

```bash
python evaluate.py reports/P002.json
```

This reads the saved report and doesn't make another API call. For a batch report, use the path to its individual JSON file in the timestamped folder.

The test files aren't needed to run the investigation commands.

## What I want to work on next

- Add new synthetic cases beyond the examples used during development.
- Use what I learned from this implementation to design and build further improvements.
- Explore a separate decision-support agent that suggests possible next steps for human review.
- Later, explore how investigation and decision support could work together.

Right now, this is a prototype using a small synthetic dataset. I haven't tested large-scale processing or measured its performance at that scale.
