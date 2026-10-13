import unittest
from unittest.mock import patch

from agent import DEFAULT_MODEL
from batch import run_batch
from tools import PaymentTools


def fake_result(needs_review=False):
    return {"report": {"requires_review": needs_review}}


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.tools = PaymentTools()
        self.client = object()

    @patch("batch.investigate")
    def test_missing_record_does_not_stop_batch(self, mock_investigate):
        mock_investigate.side_effect = [
            fake_result(),
            fake_result(True)
        ]

        summary = run_batch(
            self.client, self.tools, ["P002", "P999", "P003"]
        )

        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["succeeded"], 2)
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["requires_review_count"], 1)
        self.assertEqual(
            summary["results"][1]["error_type"], "ValueError"
        )
        self.assertEqual(summary["results"][2]["status"], "success")

        called_ids = [
            call.args[3]
            for call in mock_investigate.call_args_list
        ]
        self.assertEqual(called_ids, ["P002", "P003"])

    @patch("batch.investigate")
    def test_investigation_failure_does_not_stop_batch(self, mock_investigate):
        mock_investigate.side_effect = [
            fake_result(),
            RuntimeError("Simulated investigation failure"),
            fake_result()
        ]

        summary = run_batch(
            self.client, self.tools, ["P002", "P003", "P004"]
        )

        self.assertEqual(summary["succeeded"], 2)
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(
            summary["results"][1]["error_type"], "RuntimeError"
        )
        self.assertEqual(summary["results"][2]["target_id"], "P004")
        self.assertEqual(summary["results"][2]["status"], "success")
        self.assertEqual(mock_investigate.call_count, 3)

    @patch("batch.investigate")
    def test_invoice_batch_uses_invoice_mode(self, mock_investigate):
        mock_investigate.return_value = fake_result()

        summary = run_batch(
            self.client, self.tools, ["I002"], target_type="invoice"
        )

        self.assertEqual(summary["succeeded"], 1)
        mock_investigate.assert_called_once_with(
            self.client, self.tools, "invoice", "I002",
            model=DEFAULT_MODEL, verbose=False
        )


if __name__ == "__main__":
    unittest.main()