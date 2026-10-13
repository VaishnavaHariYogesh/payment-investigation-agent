import argparse
from datetime import datetime
from getpass import getpass
import json
import os
from pathlib import Path
from tools import PaymentTools
from agent import investigate, DEFAULT_MODEL


def run_batch(client, tools, target_ids, target_type="payment",
              model=DEFAULT_MODEL):
    if target_type not in ["payment", "invoice"]:
        raise ValueError("Target type must be payment or invoice.")

    results = []

    for target_id in target_ids:
        try:
            if target_type == "invoice":
                target = tools.get_invoice(target_id)
            else:
                target = tools.get_payment(target_id)

            if "error" in target:
                raise ValueError("Target record was not found.")

            investigation = investigate(
                client, tools, target_type, target_id,
                model=model, verbose=False
            )

            results.append({
                "target_id": target_id,
                "status": "success",
                "investigation": investigation
            })

        except Exception as error:
            results.append({
                "target_id": target_id,
                "status": "failed",
                "error_type": type(error).__name__
            })

    successful = [
        item for item in results
        if item["status"] == "success"
    ]

    return {
        "total": len(results),
        "succeeded": len(successful),
        "failed": len(results) - len(successful),
        "requires_review_count": sum(
            item["investigation"]["report"]["requires_review"]
            for item in successful
        ),
        "results": results
    }

def main():
    parser = argparse.ArgumentParser(
        description="Investigate multiple payments or invoices."
    )
    parser.add_argument(
        "target_ids", nargs="+", help="For example P002 P003"
    )
    parser.add_argument("--invoice", action="store_true")
    parser.add_argument(
        "--model",
        default=os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)
    )
    args = parser.parse_args()

    tools = PaymentTools()
    target_type = "invoice" if args.invoice else "payment"

    try:
        from openai import OpenAI
    except ImportError:
        parser.exit(
            1,
            "Install dependencies: "
            "python3 -m pip install -r requirements.txt\n"
        )

    key = os.environ.get("OPENAI_API_KEY") or getpass(
        "OpenAI API key (hidden): "
    )
    if not key.strip():
        parser.exit(1, "No API key entered.\n")

    client = OpenAI(
        api_key=key.strip(), max_retries=0, timeout=60
    )

    print(f"Investigating {len(args.target_ids)} records...")
    summary = run_batch(
        client, tools, args.target_ids, target_type, args.model
    )

    run_name = datetime.now().strftime("batch_%Y%m%d_%H%M%S_%f")
    report_dir = Path(__file__).parent / "reports" / run_name
    report_dir.mkdir(parents=True, exist_ok=False)

    for position, item in enumerate(summary["results"], start=1):
        if item["status"] == "success":
            filename = f"report_{position}.json"
            path = report_dir / filename
            path.write_text(
                json.dumps(item["investigation"], indent=2) + "\n"
            )
            item["report_file"] = filename

    summary_path = report_dir / "batch_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2) + "\n"
    )

    print("Completed:", summary["succeeded"])
    print("Failed:", summary["failed"])
    print(
        "Completed reports requiring review:",
        summary["requires_review_count"]
    )

    for item in summary["results"]:
        if item["status"] == "failed":
            print(
                item["target_id"], "failed:", item["error_type"]
            )

    print("Saved reports to:", report_dir)

    if summary["failed"]:
        parser.exit(1)


if __name__ == "__main__":
    main()