import pandas as pd
import pytest

from src.cost_analyzer import detect_anomalies


def test_detects_high_cost():
    df = pd.DataFrame({
        "date": [
            "2026-10-01",
            "2026-10-02",
            "2026-10-03",
            "2026-10-04",
            "2026-10-05",
        ],
        "service": ["Amazon EC2"] * 5,
        "cost": [2.0, 2.1, 2.0, 2.2, 8.5],
    })

    findings = detect_anomalies(df)

    assert len(findings) == 1
    assert findings[0]["service"] == "Amazon EC2"
    assert findings[0]["current_cost"] == 8.5


def test_no_anomaly_for_stable_costs():
    df = pd.DataFrame({
        "date": [
            "2026-10-01",
            "2026-10-02",
            "2026-10-03",
            "2026-10-04",
            "2026-10-05",
        ],
        "service": ["Amazon S3"] * 5,
        "cost": [0.30, 0.31, 0.29, 0.32, 0.30],
    })

    assert detect_anomalies(df) == []


def test_rejects_missing_columns():
    df = pd.DataFrame({"date": ["2026-10-01"], "cost": [2.0]})

    with pytest.raises(ValueError):
        detect_anomalies(df)


def test_rejects_negative_costs():
    df = pd.DataFrame({
        "date": ["2026-10-01"],
        "service": ["Amazon EC2"],
        "cost": [-2.0],
    })

    with pytest.raises(ValueError):
        detect_anomalies(df)
