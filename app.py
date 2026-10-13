
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# --------------------------------------------------
# Paths and configuration
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"

COST_FILE = REPORTS / "aws_daily_costs.csv"
ALERT_FILE = REPORTS / "cost_alerts.json"
RECOMMENDATION_FILE = REPORTS / "cost_recommendations.json"
SERVICE_FILE = ROOT / "october-costs.json"

AWS_REGION = "us-east-1"

st.set_page_config(
    page_title="AWS FinOps Assistant",
    page_icon="☁️",
    layout="wide",
)

# --------------------------------------------------
# Helper functions
# --------------------------------------------------

def run_script(script):
    """Run one project script and return its result."""
    return subprocess.run(
        [sys.executable, str(ROOT / script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )


def refresh_service_costs():
    """Fetch current-month AWS service costs."""
    today = date.today()
    start_date = today.replace(day=1).isoformat()
    end_date = today.isoformat()  # AWS end date is exclusive

    command = [
        "aws",
        "ce",
        "get-cost-and-usage",
        "--region",
        AWS_REGION,
        "--time-period",
        f"Start={start_date},End={end_date}",
        "--granularity",
        "MONTHLY",
        "--metrics",
        "UnblendedCost",
        "--group-by",
        "Type=DIMENSION,Key=SERVICE",
        "--output",
        "json",
    ]

    result = subprocess.run(
        command,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr or result.stdout or "AWS Cost Explorer request failed."
        )

    report = json.loads(result.stdout)
    SERVICE_FILE.write_text(
        json.dumps(report, indent=4),
        encoding="utf-8",
    )


def load_json(path):
    """Load a JSON report if it exists."""
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


# --------------------------------------------------
# Dashboard header
# --------------------------------------------------

st.title("☁️ AI-Powered AWS FinOps Assistant")
st.caption(
    "AWS cost monitoring, alerts, and optimization recommendations"
)

st.sidebar.header("Dashboard")
st.sidebar.write("Data source: AWS Cost Explorer")
st.sidebar.write(f"AWS region: {AWS_REGION}")
st.sidebar.write("Currency: USD")

# --------------------------------------------------
# Refresh button
# --------------------------------------------------

if st.sidebar.button("🔄 Refresh AWS Costs", type="primary"):
    scripts = [
        "src/aws_cost_fetcher.py",
        "src/analyze_aws_costs.py",
        "src/cost_alert.py",
        "src/cost_recommender.py",
    ]

    try:
        with st.spinner("Fetching and analyzing AWS costs..."):
            for script in scripts:
                result = run_script(script)

                if result.returncode != 0:
                    details = result.stderr or result.stdout
                    raise RuntimeError(
                        f"Script failed: {script}\n{details}"
                    )

            refresh_service_costs()

        st.sidebar.success("AWS cost data refreshed.")
        st.rerun()

    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        st.sidebar.error("Refresh failed.")
        st.error(str(exc))

# --------------------------------------------------
# Daily cost data
# --------------------------------------------------

st.subheader("Daily AWS Cost Summary")

if not COST_FILE.exists():
    st.warning(
        "Daily cost data is missing. Use Refresh AWS Costs "
        "or run src/aws_cost_fetcher.py."
    )
    st.stop()

try:
    df = pd.read_csv(COST_FILE)

    if not {"date", "cost_usd"}.issubset(df.columns):
        st.error("The daily cost CSV must contain date and cost_usd columns.")
        st.stop()

    df["date"] = pd.to_datetime(df["date"], errors="raise")
    df["cost_usd"] = pd.to_numeric(df["cost_usd"], errors="raise")

    if df.empty:
        st.warning("The daily cost CSV contains no records.")
        st.stop()

    if not df["cost_usd"].map(lambda value: pd.notna(value)).all():
        st.error("Invalid cost values were found in the CSV.")
        st.stop()

    if (df["cost_usd"] < -0.000001).any():
        st.error(
            "Unexpected negative daily costs were found. "
            "Check the original AWS Cost Explorer data."
        )
        st.stop()

except (OSError, ValueError, KeyError) as exc:
    st.error(f"Could not read daily cost data: {exc}")
    st.stop()

df = df.sort_values("date")
total_cost = df["cost_usd"].sum()
average_cost = df["cost_usd"].mean()
highest_cost = df["cost_usd"].max()

col1, col2, col3 = st.columns(3)

col1.metric("Total recorded cost", f"${total_cost:.10f}")
col2.metric("Average daily cost", f"${average_cost:.10f}")
col3.metric("Highest daily cost", f"${highest_cost:.10f}")

st.caption(
    "These metrics show recorded daily data, not necessarily your final bill. "
    "AWS billing data can be delayed or estimated."
)

# --------------------------------------------------
# Daily trend chart
# --------------------------------------------------

st.subheader("Daily AWS Cost Trend")

daily_fig = px.line(
    df,
    x="date",
    y="cost_usd",
    markers=True,
    title="Daily recorded AWS cost",
    labels={
        "date": "Date",
        "cost_usd": "Cost (USD)",
    },
)

st.plotly_chart(
    service_fig,
    use_container_width=True,
    key="aws_service_cost_chart",
)

# --------------------------------------------------
# Daily records table
# --------------------------------------------------

st.subheader("Daily Cost Records")

daily_display = df.sort_values("date", ascending=False).copy()
daily_display["date"] = daily_display["date"].dt.strftime("%Y-%m-%d")
daily_display["cost_usd"] = daily_display["cost_usd"].map(
    lambda value: f"${value:.10f}"
)

st.dataframe(
    daily_display,
    width="stretch",
    hide_index=True,
)

# --------------------------------------------------
# Service-level cost breakdown
# --------------------------------------------------

st.subheader("AWS Service Cost Breakdown")

service_report = load_json(SERVICE_FILE)

if service_report is None:
    st.info(
        "No service-level report found. Click Refresh AWS Costs "
        "to fetch service costs."
    )
else:
    try:
        periods = service_report.get("ResultsByTime", [])
        groups = periods[0].get("Groups", []) if periods else []

        service_rows = []

        for item in groups:
            service_name = item["Keys"][0]
            amount = float(
                item["Metrics"]["UnblendedCost"]["Amount"]
            )

            service_rows.append(
                {
                    "AWS Service": service_name,
                    "Cost (USD)": amount,
                }
            )

        service_df = pd.DataFrame(
            service_rows,
            columns=["AWS Service", "Cost (USD)"],
        )

        if not service_df.empty:
            start = periods[0]["TimePeriod"]["Start"]
            end = periods[0]["TimePeriod"]["End"]

            st.caption(
                f"Period: {start} to {end} (end date exclusive). "
                "Negative amounts may represent credits or adjustments. "
                "Values may be estimated."
            )

            service_df = service_df.sort_values(
                "Cost (USD)",
                ascending=False,
            )

            st.dataframe(
                service_df.style.format(
                    {"Cost (USD)": "${:.10f}"}
                ),
                width="stretch",
                hide_index=True,
            )

            service_fig = px.bar(
                service_df,
                x="AWS Service",
                y="Cost (USD)",
                title="AWS Cost by Service",
                labels={"Cost (USD)": "Cost (USD)"},
            )

            service_fig.update_yaxes(tickformat=".10f")
            service_fig.update_layout(xaxis_tickangle=-35)

            st.plotly_chart(service_fig, width="stretch")

            net_cost = service_df["Cost (USD)"].sum()
            st.metric("Net service cost (USD)", f"${net_cost:.10f}")

            st.caption(
                "The net is the sum of reported service amounts. "
                "Verify credits, adjustments, and final charges in AWS Billing."
            )
        else:
            st.info("AWS returned no service-level records for this period.")

    except (ValueError, KeyError, IndexError, TypeError) as exc:
        st.error(f"Could not display service costs: {exc}")
    except OSError as exc:
        st.error(f"Could not read the service report: {exc}")

# --------------------------------------------------
# Alerts and recommendations
# --------------------------------------------------

left, right = st.columns(2)

with left:
    st.subheader("Cost Alerts")

    try:
        alert_report = load_json(ALERT_FILE)

        if alert_report is None:
            st.info("No alert report found. Refresh AWS Costs to generate one.")
        else:
            alert_count = alert_report.get("alerts_detected", 0)
            st.metric("Alerts detected", alert_count)
            st.json(alert_report.get("alerts", []))

    except (OSError, ValueError, TypeError) as exc:
        st.error(f"Could not read the alert report: {exc}")

with right:
    st.subheader("Optimization Recommendations")

    try:
        recommendation_report = load_json(RECOMMENDATION_FILE)

        if recommendation_report is None:
            st.info(
                "No recommendation report found. "
                "Refresh AWS Costs to generate one."
            )
        else:
            average = recommendation_report.get(
                "average_daily_cost_usd", 0
            )

            st.write("Average daily cost:", f"${float(average):.10f}")

            for item in recommendation_report.get("recommendations", []):
                st.markdown(
                    f"**Priority:** {item.get('priority', 'Review')}"
                )
                st.write(item.get("finding", ""))
                st.write(item.get("recommendation", ""))
                st.divider()

            st.caption(recommendation_report.get("note", ""))

    except (OSError, ValueError, TypeError) as exc:
        st.error(f"Could not read recommendations: {exc}")

# --------------------------------------------------
# Footer
# --------------------------------------------------

st.caption(
    "This project uses rule-based recommendations, not a trained AI model. "
    "Savings are not estimated without resource-level usage and pricing data. "
    "Verify final charges in AWS Billing."
)

