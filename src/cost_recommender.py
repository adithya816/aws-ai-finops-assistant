
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COST_FILE = ROOT / "reports" / "aws_daily_costs.csv"
OUTPUT_FILE = ROOT / "reports" / "cost_recommendations.json"

DAILY_COST_BENCHMARK_USD = 1.00
NEGATIVE_COST_TOLERANCE = 0.000001


def generate_recommendations():
    if not COST_FILE.exists():
        raise FileNotFoundError(
            "Cost data not found. Run src/aws_cost_fetcher.py first."
        )

    daily_costs = []

    with COST_FILE.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        if not {"date", "cost_usd"}.issubset(reader.fieldnames or []):
            raise ValueError(
                "CSV must contain date and cost_usd columns"
            )

        for row in reader:
            try:
                cost = float(row["cost_usd"])
            except (ValueError, TypeError):
                raise ValueError(
                    f"Invalid cost value for date {row.get('date')}"
                ) from None

            if cost < -NEGATIVE_COST_TOLERANCE:
                raise ValueError(
                    f"Unexpected negative cost on {row['date']}: {cost}"
                )

            # Treat tiny negative floating-point/billing values as zero.
            cost = max(cost, 0.0)

            daily_costs.append({
                "date": row["date"],
                "cost_usd": cost,
            })

    if not daily_costs:
        raise ValueError("No daily cost records found")

    total_cost = sum(item["cost_usd"] for item in daily_costs)
    average_cost = total_cost / len(daily_costs)

    recommendations = []

    if average_cost > DAILY_COST_BENCHMARK_USD:
        recommendations.append({
            "priority": "High",
            "finding": (
                "Average daily AWS cost exceeds the configured benchmark."
            ),
            "recommendation": (
                "Review the AWS Cost Explorer service breakdown. "
                "Identify expensive resources and check whether unused "
                "resources can be stopped or removed."
            ),
            "estimated_savings": None,
        })
    else:
        recommendations.append({
            "priority": "Review",
            "finding": (
                "Average daily cost is within the configured benchmark."
            ),
            "recommendation": (
                "Review service-level costs and verify that running "
                "resources are required. Check AWS Billing for accurate "
                "charges before making cost decisions."
            ),
            "estimated_savings": None,
        })

    report = {
        "project": "AI-Powered AWS FinOps Assistant",
        "data_source": "AWS Cost Explorer daily costs",
        "days_analyzed": len(daily_costs),
        "total_cost_usd": round(total_cost, 6),
        "average_daily_cost_usd": round(average_cost, 6),
        "daily_cost_benchmark_usd": DAILY_COST_BENCHMARK_USD,
        "recommendations": recommendations,
        "note": (
            "This is a rule-based recommendation engine, not a trained "
            "AI model. Tiny negative values within the configured "
            "tolerance are treated as zero. Savings are not estimated "
            "without resource-level usage and pricing data. AWS billing "
            "data may be delayed or estimated."
        ),
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2))
    print(f"\nRecommendations saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_recommendations()

