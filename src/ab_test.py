"""Statistics, data access and chart helpers for the email campaign A/B test.

Every notebook imports from here, so each test and metric is defined once.
"""

import os
from getpass import getpass
from pathlib import Path
from urllib.parse import quote_plus

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sqlalchemy import create_engine, text
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import confint_proportions_2indep, proportions_ztest

REPO_ROOT = Path(__file__).resolve().parents[1]
FIGURES_DIR = REPO_ROOT / "reports" / "figures"

TREATMENTS = ["Mens", "Womens"]
CONTROL = "Control"

# Pre-specified in docs/analysis_plan.md
ALPHA = 0.05
SRM_THRESHOLD = 0.001
SMD_THRESHOLD = 0.1
MIN_SEGMENT_SIZE = 1_000
SEGMENTS = ["past_purchase", "recency_band", "history_segment", "channel", "area", "customer_type"]
BOOTSTRAP_SEED = 42
N_BOOTSTRAP = 10_000


# ---------------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------------
_password_cache = {}


def get_engine(database: str | None = "marketing_analytics"):
    """SQLAlchemy engine for MySQL (database=None connects to the server only).

    Credentials come from environment variables, or are asked for once at run time,
    so they never appear in code or notebook outputs.
    ANALYTICS_DB_URL can point to another database (used for testing).
    """
    url = os.getenv("ANALYTICS_DB_URL")
    if url:
        return create_engine(url)
    user = os.getenv("MYSQL_USER", "root")
    if user not in _password_cache:
        _password_cache[user] = os.getenv("MYSQL_PASSWORD") or getpass(f"MySQL password for {user}: ")
    host = os.getenv("MYSQL_HOST", "localhost:3306")
    return create_engine(f"mysql+pymysql://{user}:{quote_plus(_password_cache[user])}@{host}/{database or ''}")


def run_sql_file(engine, path) -> list:
    """Run every statement in a .sql file on one connection; return SELECT results as DataFrames."""
    sql = "\n".join(line.split("--")[0] for line in Path(path).read_text().splitlines())
    results = []
    with engine.begin() as conn:
        for statement in (s.strip() for s in sql.split(";")):
            if not statement:
                continue
            if statement.upper().startswith("SELECT"):
                results.append(pd.read_sql(text(statement), conn))
            else:
                conn.execute(text(statement))
    return results


def load_clean(engine) -> pd.DataFrame:
    """Analysis-ready data from the email_test_clean view (see sql/03_clean_view.sql)."""
    df = pd.read_sql("SELECT * FROM email_test_clean", engine)
    df["spend"] = df["spend"].astype(float)
    df["history"] = df["history"].astype(float)
    return df


def save_tables(tables: dict, engine) -> None:
    """Write result tables to the database, replacing earlier runs."""
    for name, frame in tables.items():
        frame.to_sql(name, engine, if_exists="replace", index=False)
        print(f"{name:<28} {len(frame):>3} rows saved")


# ---------------------------------------------------------------------------
# Validity checks
# ---------------------------------------------------------------------------
def srm_check(df: pd.DataFrame) -> dict:
    """Sample ratio mismatch: are group sizes consistent with equal thirds?"""
    observed = df["test_group"].value_counts().sort_index()
    expected = [len(df) / len(observed)] * len(observed)
    chi2, p_value = stats.chisquare(observed, expected)
    return {"observed": observed, "chi2": chi2, "p_value": p_value,
            "passed": p_value >= SRM_THRESHOLD}


def covariate_balance(df: pd.DataFrame) -> pd.DataFrame:
    """Standardised mean difference of each pre-campaign feature, treatment vs control."""
    features = pd.get_dummies(
        df[["recency", "history", "past_purchase", "customer_type", "area", "channel"]],
        columns=["past_purchase", "customer_type", "area", "channel"], dtype=int,
    )
    control = features[df["test_group"] == CONTROL]
    smd = {}
    for group in TREATMENTS:
        treated = features[df["test_group"] == group]
        pooled_sd = ((treated.var() + control.var()) / 2) ** 0.5
        smd[group] = (treated.mean() - control.mean()) / pooled_sd
    balance = pd.DataFrame(smd)
    balance["max_abs_smd"] = balance.abs().max(axis=1)
    return balance.sort_values("max_abs_smd", ascending=False)


# ---------------------------------------------------------------------------
# Main results
# ---------------------------------------------------------------------------
def group_summary(df: pd.DataFrame) -> pd.DataFrame:
    """KPI tree by group: revenue per customer = conversion rate x spend per buyer."""
    summary = df.groupby("test_group").agg(
        customers=("customer_id", "count"),
        visit_rate=("visit", "mean"),
        conversion_rate=("conversion", "mean"),
        revenue_per_customer=("spend", "mean"),
    )
    summary["spend_per_buyer"] = df[df["conversion"] == 1].groupby("test_group")["spend"].mean()
    summary[["visit_rate", "conversion_rate"]] *= 100
    return summary


def bootstrap_diff_ci(treated, control, rng, n_boot=N_BOOTSTRAP):
    """95% CI for the difference in means, by resampling customers with replacement."""
    t, c = np.asarray(treated), np.asarray(control)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        diffs[i] = rng.choice(t, t.size).mean() - rng.choice(c, c.size).mean()
    return np.percentile(diffs, [2.5, 97.5])


def spend(df, group):
    return df.loc[df["test_group"] == group, "spend"]


def primary_results(df: pd.DataFrame, rng) -> pd.DataFrame:
    """H1, H2: revenue per customer vs control (Welch's t-test, bootstrap CI, Holm)."""
    control = spend(df, CONTROL)
    rows = []
    for group in TREATMENTS:
        treated = spend(df, group)
        lift = treated.mean() - control.mean()
        _, p = stats.ttest_ind(treated, control, equal_var=False)
        ci_low, ci_high = bootstrap_diff_ci(treated, control, rng)
        rows.append({"group": group, "control_$": control.mean(), "treated_$": treated.mean(),
                     "lift_$": lift, "lift_%": lift / control.mean() * 100,
                     "ci_low_$": ci_low, "ci_high_$": ci_high, "p_value": p})
    results = pd.DataFrame(rows)
    results["p_holm"] = multipletests(results["p_value"], method="holm")[1]
    results["success"] = (results["p_holm"] < ALPHA) & (results["ci_low_$"] > 0)
    return results


def secondary_results(df: pd.DataFrame) -> pd.DataFrame:
    """Conversion and visit rates vs control (two-proportion z-test, Holm within metric)."""
    rows = []
    for metric in ["conversion", "visit"]:
        c = df.loc[df["test_group"] == CONTROL, metric]
        for group in TREATMENTS:
            t = df.loc[df["test_group"] == group, metric]
            _, p = proportions_ztest([t.sum(), c.sum()], [t.size, c.size])
            ci_low, ci_high = confint_proportions_2indep(t.sum(), t.size, c.sum(), c.size, compare="diff")
            rows.append({"metric": metric, "group": group,
                         "control_%": c.mean() * 100, "treated_%": t.mean() * 100,
                         "lift_pp": (t.mean() - c.mean()) * 100,
                         "ci_low_pp": ci_low * 100, "ci_high_pp": ci_high * 100, "p_value": p})
    results = pd.DataFrame(rows)
    results["p_holm"] = results.groupby("metric")["p_value"].transform(
        lambda p: multipletests(p, method="holm")[1])
    return results


def mens_vs_womens(df: pd.DataFrame, rng) -> pd.DataFrame:
    """H3 (exploratory): direct comparison of the two emails."""
    mens, womens = spend(df, "Mens"), spend(df, "Womens")
    _, p = stats.ttest_ind(mens, womens, equal_var=False)
    ci_low, ci_high = bootstrap_diff_ci(mens, womens, rng)
    return pd.DataFrame([{"comparison": "Mens minus Womens", "diff_$": mens.mean() - womens.mean(),
                          "ci_low_$": ci_low, "ci_high_$": ci_high, "p_value": p}])


# ---------------------------------------------------------------------------
# Segments and targeting
# ---------------------------------------------------------------------------
def segment_lifts(df: pd.DataFrame, segments=SEGMENTS, min_size=MIN_SEGMENT_SIZE) -> pd.DataFrame:
    """Revenue lift by segment with a normal-approximation 95% CI (exploratory)."""
    rows = []
    for segment in segments:
        for value, sub in df.groupby(segment):
            control = spend(sub, CONTROL)
            for group in TREATMENTS:
                treated = spend(sub, group)
                if min(len(treated), len(control)) < min_size:
                    continue
                lift = treated.mean() - control.mean()
                se = np.sqrt(treated.var() / len(treated) + control.var() / len(control))
                rows.append({"segment": segment, "value": value, "email": group,
                             "n_per_group": min(len(treated), len(control)),
                             "control_$": control.mean(), "lift_$": lift,
                             "ci_low_$": lift - 1.96 * se, "ci_high_$": lift + 1.96 * se})
    results = pd.DataFrame(rows)
    results["ci_above_0"] = results["ci_low_$"] > 0
    return results


POLICIES = {
    "A: Mens email to all":   {"Mens only": "Mens",   "Both": "Mens",   "Womens only": "Mens"},
    "B: Womens email to all": {"Mens only": "Womens", "Both": "Womens", "Womens only": "Womens"},
    "C: Match past purchase": {"Mens only": "Mens",   "Both": "Mens",   "Womens only": "Womens"},
}


def policy_comparison(df: pd.DataFrame, seg_results: pd.DataFrame) -> pd.DataFrame:
    """Expected incremental revenue per 1,000 customers for each targeting rule."""
    lift = seg_results[seg_results["segment"] == "past_purchase"].pivot(
        index="value", columns="email", values="lift_$")
    share = df["past_purchase"].value_counts(normalize=True)
    rows = []
    for name, rule in POLICIES.items():
        per_customer = sum(share[seg] * lift.loc[seg, email] for seg, email in rule.items())
        rows.append({"policy": name, "incremental_$_per_1000_customers": per_customer * 1000})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
COLORS = {"Control": "#b8b7b2", "Mens": "#2a78d6", "Womens": "#eb6834"}


def apply_chart_style() -> None:
    plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False,
                         "axes.titleweight": "bold", "axes.titlelocation": "left",
                         "font.size": 10, "figure.dpi": 110})


def save_figure(fig, filename: str) -> Path:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURES_DIR / filename
    fig.savefig(path, dpi=150, bbox_inches="tight")
    return path
