import boto3
import csv
from datetime import date, timedelta
from pathlib import Path


def fetch_daily_costs(days=7):
    client = boto3.client("ce", region_name="us-east-1")

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    response = client.get_cost_and_usage(
        TimePeriod={
            "Start": start_date.isoformat(),
            "End": end_date.isoformat(),
        },
        Granularity="DAILY",
        Metrics=["UnblendedCost"],
    )

    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "aws_daily_costs.csv"

    with output_file.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["date", "cost_usd"])

        for item in response["ResultsByTime"]:
            amount = item["Total"]["UnblendedCost"]["Amount"]
            writer.writerow([item["TimePeriod"]["Start"], amount])

    print(f"Saved daily AWS costs to {output_file}")
    print(f"Daily records: {len(response['ResultsByTime'])}")


if __name__ == "__main__":
    fetch_daily_costs()
