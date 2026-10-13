import csv
import json
import os
from pathlib import Path

import boto3

ROOT = Path(__file__).resolve().parents[1]
COST_FILE = ROOT / "reports" / "aws_daily_costs.csv"
REPORT_FILE = ROOT / "reports" / "cost_alerts.json"

DAILY_COST_LIMIT_USD = 1.00
AWS_REGION = "us-east-1"
SNS_TOPIC_ARN = os.environ.get("FINOPS_SNS_TOPIC_ARN", "")


def main():
    if not COST_FILE.exists():
        raise FileNotFoundError(
            "Cost data not found. Run src/aws_cost_fetcher.py first."
        )

    alerts = []
    days_checked = 0

    with COST_FILE.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        if not {"date", "cost_usd"}.issubset(reader.fieldnames or []):
            raise ValueError("CSV must contain date and cost_usd columns")

        for row in reader:
            days_checked += 1
            cost = float(row["cost_usd"])

            if cost > DAILY_COST_LIMIT_USD:
                alerts.append({
                    "date": row["date"],
                    "cost_usd": round(cost, 6),
                    "limit_usd": DAILY_COST_LIMIT_USD,
                    "message": "Daily AWS cost exceeded the configured limit."
                })

    report = {
        "source": "AWS Cost Explorer",
        "daily_limit_usd": DAILY_COST_LIMIT_USD,
        "days_checked": days_checked,
        "alerts_detected": len(alerts),
        "alerts": alerts,
        "note": "AWS billing data may be delayed or estimated."
    }

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if alerts:
        if not SNS_TOPIC_ARN:
            raise RuntimeError(
                "Set FINOPS_SNS_TOPIC_ARN to your SNS topic ARN before sending alerts."
            )

        sns = boto3.client("sns", region_name=AWS_REGION)
        message = json.dumps(report, indent=2)

        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject="AWS FinOps: Daily Cost Limit Exceeded",
            Message=message,
        )

        print("WARNING: AWS daily cost limit exceeded!")
        print("Email alert published to the SNS topic.")
    else:
        print("No daily cost alerts. Spending is within the configured limit.")
        print("No email was sent.")

    print(json.dumps(report, indent=2))
    print(f"\nAlert report saved to: {REPORT_FILE}")


if __name__ == "__main__":
    main()
