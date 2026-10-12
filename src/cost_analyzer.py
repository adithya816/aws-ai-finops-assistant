import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "sample_costs.csv"
REPORT_FILE = ROOT / "reports" / "cost_report.json"


def detect_anomalies(df, multiplier=2.0, minimum_increase=1.0):
    required = {"date", "service", "cost"}

    if not required.issubset(df.columns):
        raise ValueError("CSV must contain date, service, and cost columns")

    data = df.copy()
    data["date"] = pd.to_datetime(data["date"], errors="raise")
    data["cost"] = pd.to_numeric(data["cost"], errors="raise")

    if data.empty:
        return []

    if data["cost"].isna().any() or (data["cost"] < 0).any():
        raise ValueError("Cost values must be non-negative numbers")

    findings = []

    for service, group in data.groupby("service"):
        group = group.sort_values("date").reset_index(drop=True)

        # Compare each day with the previous seven available observations.
        for index in range(3, len(group)):
            history = group.loc[max(0, index - 7):index - 1, "cost"]
            current = float(group.loc[index, "cost"])
            baseline = float(history.mean())
            increase = current - baseline

            if (
                baseline > 0
                and current > baseline * multiplier
                and increase >= minimum_increase
            ):
                findings.append({
                    "date": group.loc[index, "date"].strftime("%Y-%m-%d"),
                    "service": service,
                    "current_cost": round(current, 2),
                    "average_previous_cost": round(baseline, 2),
                    "increase": round(increase, 2),
                    "message": (
                        f"{service} spending is unusually high. "
                        "Review recent usage and resources."
                    ),
                })

    return findings


def main():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Sample data not found: {DATA_FILE}")

    df = pd.read_csv(DATA_FILE)
    findings = detect_anomalies(df)

    report = {
        "source": "sample",
        "currency": "USD",
        "total_cost": round(float(df["cost"].sum()), 2),
        "services_analyzed": sorted(df["service"].unique().tolist()),
        "anomalies_detected": len(findings),
        "findings": findings,
        "note": "This report uses fictional sample data, not live AWS billing.",
    }

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    print(f"\nReport saved to: {REPORT_FILE}")


if __name__ == "__main__":
    main()
