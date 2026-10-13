import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
COST_FILE = ROOT / "reports" / "aws_daily_costs.csv"
REPORT_FILE = ROOT / "reports" / "aws_cost_report.json"


def main():
    if not COST_FILE.exists():
        raise FileNotFoundError(
            f"AWS cost data not found: {COST_FILE}. "
            "Run src/aws_cost_fetcher.py first."
        )

    df = pd.read_csv(COST_FILE)

    required = {"date", "cost_usd"}
    if not required.issubset(df.columns):
        raise ValueError("AWS CSV must contain date and cost_usd columns")

    df["date"] = pd.to_datetime(df["date"], errors="raise")
    df["cost_usd"] = pd.to_numeric(df["cost_usd"], errors="raise")

    if df.empty:
        raise ValueError("AWS cost CSV contains no records")

    if df["cost_usd"].isna().any():
        raise ValueError("AWS costs cannot contain missing values")

    # Cost Explorer can report tiny negative adjustments or credits.
    # Preserve them in the report instead of treating them as usage spikes.
    findings = []
    ordered = df.sort_values("date").reset_index(drop=True)

    for index in range(3, len(ordered)):
        history = ordered.loc[max(0, index - 7):index - 1, "cost_usd"]
        baseline = float(history.mean())
        current = float(ordered.loc[index, "cost_usd"])

        if baseline > 0 and current > baseline * 2 and current - baseline >= 1e-9:
            findings.append({
                "date": ordered.loc[index, "date"].strftime("%Y-%m-%d"),
                "current_cost_usd": round(current, 12),
                "previous_average_usd": round(baseline, 12),
                "increase_usd": round(current - baseline, 12),
                "message": "Review AWS usage and billing details.",
            })

    report = {
        "source": "AWS Cost Explorer",
        "metric": "UnblendedCost",
        "currency": "USD",
        "records_analyzed": len(ordered),
        "total_reported_cost_usd": round(float(ordered["cost_usd"].sum()), 12),
        "anomalies_detected": len(findings),
        "findings": findings,
        "note": (
            "Cost Explorer data may be delayed or estimated. "
            "Tiny values and negative adjustments should not be treated "
            "as confirmed usage spikes."
        ),
    }

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    print(f"\nReport saved to: {REPORT_FILE}")


if __name__ == "__main__":
    main()
