
import csv
import json

import pytest

from src import cost_recommender


def write_cost_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["date", "cost_usd"])
        writer.writerows(rows)


def test_generates_recommendation_for_low_costs(tmp_path, monkeypatch):
    cost_file = tmp_path / "costs.csv"
    report_file = tmp_path / "recommendations.json"

    write_cost_csv(
        cost_file,
        [
            ["2026-10-10", "0.25"],
            ["2026-10-11", "0.30"],
        ],
    )

    monkeypatch.setattr(cost_recommender, "COST_FILE", cost_file)
    monkeypatch.setattr(cost_recommender, "OUTPUT_FILE", report_file)

    cost_recommender.generate_recommendations()

    report = json.loads(report_file.read_text(encoding="utf-8"))

    assert report["days_analyzed"] == 2
    assert report["total_cost_usd"] == 0.55
    assert len(report["recommendations"]) == 1


def test_rejects_large_negative_cost(tmp_path, monkeypatch):
    cost_file = tmp_path / "costs.csv"
    report_file = tmp_path / "recommendations.json"

    write_cost_csv(
        cost_file,
        [["2026-10-10", "-5.00"]],
    )

    monkeypatch.setattr(cost_recommender, "COST_FILE", cost_file)
    monkeypatch.setattr(cost_recommender, "OUTPUT_FILE", report_file)

    with pytest.raises(ValueError, match="Unexpected negative cost"):
        cost_recommender.generate_recommendations()


def test_rejects_empty_csv_data(tmp_path, monkeypatch):
    cost_file = tmp_path / "costs.csv"
    report_file = tmp_path / "recommendations.json"

    write_cost_csv(cost_file, [])

    monkeypatch.setattr(cost_recommender, "COST_FILE", cost_file)
    monkeypatch.setattr(cost_recommender, "OUTPUT_FILE", report_file)

    with pytest.raises(ValueError, match="No daily cost records"):
        cost_recommender.generate_recommendations()

