"""
Freddie Mac Primary Mortgage Market Survey (PMMS) utilities.

Data source: Freddie Mac PMMS
Download URL: https://www.freddiemac.com/pmms/docs/historicalweeklydata.xlsx
Published: every Thursday

The fetch_freddie() function will auto-download the Excel file.
Alternatively, download manually and save as data/freddie_pmms.xlsx
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime

FREDDIE_URL      = "https://www.freddiemac.com/pmms/docs/historicalweeklydata.xlsx"
FREDDIE_FILENAME = "freddie_pmms.xlsx"


def fetch_freddie(data_dir: str) -> str:
    """Download the Freddie Mac PMMS Excel file."""
    import urllib.request
    dest = os.path.join(data_dir, FREDDIE_FILENAME)
    print(f"Downloading Freddie Mac PMMS data to {dest} ...")
    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(FREDDIE_URL, headers=headers)
    with urllib.request.urlopen(req) as response:
        with open(dest, "wb") as f:
            f.write(response.read())
    print("Done.")
    return dest


def load_freddie_rates(data_dir: str) -> pd.DataFrame:
    """
    Load Freddie Mac PMMS data.
    Falls back to synthetic mock data if the file is not present.
    """
    path = os.path.join(data_dir, FREDDIE_FILENAME)
    if not os.path.exists(path):
        print(f"[freddie] Data file not found at {path}. Using mock data.")
        print(f"[freddie] Run: python utils/freddie.py --download to fetch real data.")
        return _mock_freddie_data()

    try:
        # Freddie Mac Excel has a specific layout -- rates start on row 6
        df = pd.read_excel(path, sheet_name=0, header=None, skiprows=5)

        # Column layout: Date | 30-yr rate | 30-yr pts | 15-yr rate | 15-yr pts | ...
        df = df.iloc[:, :6].copy()
        df.columns = ["week", "rate_30yr", "pts_30yr", "rate_15yr", "pts_15yr", "rate_arm"]
        df["week"] = pd.to_datetime(df["week"], errors="coerce")
        df = df.dropna(subset=["week", "rate_30yr"])
        df["rate_30yr"] = pd.to_numeric(df["rate_30yr"], errors="coerce")
        df["rate_15yr"] = pd.to_numeric(df["rate_15yr"], errors="coerce")
        df["rate_arm"]  = pd.to_numeric(df["rate_arm"],  errors="coerce")

        # Approximate FHA as 30yr - 0.33
        df["rate_fha"] = df["rate_30yr"] - 0.33

        return df.sort_values("week")

    except Exception as e:
        print(f"[freddie] Error loading data: {e}. Using mock data.")
        return _mock_freddie_data()


def get_latest_rates(df: pd.DataFrame) -> dict:
    """Return the most recent week's rates and week-over-week changes."""
    if "_mock" in df.columns.tolist():
        return df.attrs.get("latest_rates", _mock_latest_rates())

    try:
        latest = df.iloc[-1]
        prev   = df.iloc[-2]

        def r(col):
            v = latest.get(col)
            return float(v) if pd.notna(v) else 0.0

        def chg(col):
            v1 = latest.get(col)
            v2 = prev.get(col)
            if pd.notna(v1) and pd.notna(v2):
                return float(v1) - float(v2)
            return 0.0

        return {
            "rate_30yr": r("rate_30yr"),
            "rate_15yr": r("rate_15yr"),
            "rate_arm":  r("rate_arm"),
            "rate_fha":  r("rate_fha"),
            "chg_30yr":  chg("rate_30yr"),
            "chg_15yr":  chg("rate_15yr"),
            "chg_arm":   chg("rate_arm"),
            "chg_fha":   chg("rate_fha"),
            "as_of":     str(latest["week"].date()),
        }
    except Exception as e:
        print(f"[freddie] get_latest_rates error: {e}")
        return _mock_latest_rates()


def get_rate_history(df: pd.DataFrame, weeks: int = 52) -> pd.DataFrame:
    """Return the last N weeks of rate history."""
    if "_mock" in df.columns.tolist():
        return df.attrs.get("rate_hist", _mock_rate_history())

    try:
        hist = df.tail(weeks)[["week", "rate_30yr", "rate_15yr", "rate_arm", "rate_fha"]].copy()
        return hist
    except Exception:
        return _mock_rate_history()


# ── Mock data ──────────────────────────────────────────────────────────────────

def _mock_freddie_data() -> pd.DataFrame:
    df = pd.DataFrame({"_mock": [True]})
    df.attrs["latest_rates"] = _mock_latest_rates()
    df.attrs["rate_hist"]    = _mock_rate_history()
    return df


def _mock_latest_rates() -> dict:
    return {
        "rate_30yr": 6.82, "rate_15yr": 6.14,
        "rate_arm":  6.31, "rate_fha":  6.49,
        "chg_30yr": -0.11, "chg_15yr": -0.09,
        "chg_arm":   0.04, "chg_fha":  -0.07,
        "as_of": datetime.today().strftime("%Y-%m-%d"),
    }


def _mock_rate_history() -> pd.DataFrame:
    weeks = pd.date_range(end=datetime.today(), periods=52, freq="W-THU")
    base_30 = np.linspace(7.31, 6.82, 52) + np.random.normal(0, 0.03, 52)
    base_15 = base_30 - 0.65 + np.random.normal(0, 0.02, 52)
    base_arm = base_30 - 0.5 + np.random.normal(0, 0.02, 52)
    return pd.DataFrame({
        "week":      weeks,
        "rate_30yr": np.round(base_30, 2),
        "rate_15yr": np.round(base_15, 2),
        "rate_arm":  np.round(base_arm, 2),
        "rate_fha":  np.round(base_30 - 0.33, 2),
    })


# ── CLI download helper ────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true", help="Download Freddie Mac PMMS data")
    parser.add_argument("--data-dir", default=os.path.join(os.path.dirname(__file__), "..", "data"))
    args = parser.parse_args()
    if args.download:
        fetch_freddie(os.path.abspath(args.data_dir))
    else:
        parser.print_help()
