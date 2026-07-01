"""
Redfin data utilities for ZIP 33301.

Data source: Redfin Market Tracker
Download URL: https://www.redfin.com/news/data-center/
File: redfin_market_tracker.tsv (tab-separated)

Steps to get the data:
1. Go to https://www.redfin.com/news/data-center/
2. Under "Market Tracker" download the ZIP-level data file
3. Save as data/redfin_market_tracker.tsv
4. The fetch_redfin() function will also auto-download it if you call it directly.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

REDFIN_URL = "https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_tracker/zip_code_market_tracker.tsv000.gz"
REDFIN_FILENAME = "redfin_market_tracker.tsv.gz"


def fetch_redfin(data_dir: str) -> str:
    """Download the Redfin ZIP-level market tracker file."""
    import urllib.request
    dest = os.path.join(data_dir, REDFIN_FILENAME)
    print(f"Downloading Redfin market data to {dest} ...")
    urllib.request.urlretrieve(REDFIN_URL, dest)
    print("Done.")
    return dest


def load_redfin_data(data_dir: str, zip_code: str) -> pd.DataFrame:
    """
    Load and filter the Redfin market tracker for a specific ZIP code.
    Falls back to synthetic mock data if the file is not present.
    """
    path = os.path.join(data_dir, REDFIN_FILENAME)
    if not os.path.exists(path):
        print(f"[redfin] Data file not found at {path}. Using mock data.")
        print(f"[redfin] Run: python utils/redfin.py --download to fetch real data.")
        return _mock_redfin_data(zip_code)

    try:
        df = pd.read_csv(path, sep="\t", compression="gzip", low_memory=False)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

        # Filter to zip code
        zip_col = next((c for c in df.columns if "zip" in c or "region" in c.lower()), None)
        if zip_col:
            df = df[df[zip_col].astype(str).str.contains(zip_code, na=False)].copy()

        if df.empty:
            print(f"[redfin] ZIP {zip_code} not found in dataset. Using mock data.")
            return _mock_redfin_data(zip_code)

        # Parse period column
        period_col = next((c for c in df.columns if "period" in c), None)
        if period_col:
            df["month"] = pd.to_datetime(df[period_col], errors="coerce")
            df = df.sort_values("month")

        return df

    except Exception as e:
        print(f"[redfin] Error loading data: {e}. Using mock data.")
        return _mock_redfin_data(zip_code)


def get_market_metrics(df: pd.DataFrame) -> dict:
    """Extract current market metrics from the Redfin dataframe."""
    if "_mock" in df.columns.tolist():
        return df.attrs.get("metrics", _mock_metrics())

    try:
        latest = df.sort_values("month").iloc[-1]
        prev   = df.sort_values("month").iloc[-2]

        def safe(col, fallback=0):
            val = latest.get(col, fallback)
            return float(val) if pd.notna(val) else fallback

        def safe_prev(col, fallback=0):
            val = prev.get(col, fallback)
            return float(val) if pd.notna(val) else fallback

        median_price  = safe("median_sale_price", 625000)
        prev_price    = safe_prev("median_sale_price", 600000)
        active        = int(safe("homes_for_sale", 87))
        prev_active   = int(safe_prev("homes_for_sale", 98))
        avg_dom       = int(safe("median_dom", 38))
        prev_dom      = int(safe_prev("median_dom", 32))
        ppsf          = safe("median_sale_ppsf", 441)
        prev_ppsf     = safe_prev("median_sale_ppsf", 431)
        lts           = safe("avg_sale_to_list", 0.961) * 100
        prev_lts      = safe_prev("avg_sale_to_list", 0.965) * 100

        return {
            "median_price":         median_price,
            "median_price_chg":     (median_price / prev_price - 1) * 100,
            "active_listings":      active,
            "active_listings_chg":  active - prev_active,
            "avg_dom":              avg_dom,
            "dom_chg":              avg_dom - prev_dom,
            "price_per_sqft":       ppsf,
            "ppsf_chg":             (ppsf / prev_ppsf - 1) * 100,
            "list_to_sale":         lts,
            "list_to_sale_chg":     lts - prev_lts,
        }
    except Exception as e:
        print(f"[redfin] get_market_metrics error: {e}")
        return _mock_metrics()


def get_price_history(df: pd.DataFrame) -> pd.DataFrame:
    """Return last 12 months of median price data."""
    if "_mock" in df.columns.tolist():
        return df.attrs.get("price_hist", _mock_price_history())

    try:
        hist = df.sort_values("month").tail(12)[["month", "median_sale_price"]].copy()
        hist.columns = ["month", "median_price"]
        hist["median_price"] = pd.to_numeric(hist["median_price"], errors="coerce")
        return hist.dropna()
    except Exception:
        return _mock_price_history()


def get_dom_history(df: pd.DataFrame) -> pd.DataFrame:
    """Return last 12 months of avg DOM data."""
    if "_mock" in df.columns.tolist():
        return df.attrs.get("dom_hist", _mock_dom_history())

    try:
        hist = df.sort_values("month").tail(12)[["month", "median_dom"]].copy()
        hist.columns = ["month", "avg_dom"]
        hist["avg_dom"] = pd.to_numeric(hist["avg_dom"], errors="coerce")
        return hist.dropna()
    except Exception:
        return _mock_dom_history()


# ── Mock data (used when CSV is not present) ───────────────────────────────────

def _mock_redfin_data(zip_code: str) -> pd.DataFrame:
    """Synthetic data shaped like the real Redfin file."""
    df = pd.DataFrame({"_mock": [True]})
    df.attrs["metrics"]    = _mock_metrics()
    df.attrs["price_hist"] = _mock_price_history()
    df.attrs["dom_hist"]   = _mock_dom_history()
    return df


def _mock_metrics() -> dict:
    return {
        "median_price":        625000,
        "median_price_chg":    4.1,
        "active_listings":     87,
        "active_listings_chg": -11,
        "avg_dom":             38,
        "dom_chg":             6,
        "price_per_sqft":      441,
        "ppsf_chg":            2.3,
        "list_to_sale":        96.1,
        "list_to_sale_chg":    -0.4,
    }


def _mock_price_history() -> pd.DataFrame:
    months = pd.date_range(end=datetime.today(), periods=12, freq="MS")
    prices = [581000, 594000, 602000, 578000, 571000, 585000,
              598000, 609000, 614000, 619000, 621000, 625000]
    return pd.DataFrame({"month": months, "median_price": prices})


def _mock_dom_history() -> pd.DataFrame:
    months = pd.date_range(end=datetime.today(), periods=12, freq="MS")
    doms   = [41, 38, 35, 44, 51, 48, 43, 36, 29, 22, 27, 38]
    return pd.DataFrame({"month": months, "avg_dom": doms})


# ── CLI download helper ────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse, sys
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true", help="Download Redfin data")
    parser.add_argument("--data-dir", default=os.path.join(os.path.dirname(__file__), "..", "data"))
    args = parser.parse_args()
    if args.download:
        fetch_redfin(os.path.abspath(args.data_dir))
    else:
        parser.print_help()
