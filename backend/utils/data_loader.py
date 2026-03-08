"""
DataLoader: reads trade_dataset.csv from S3 (or local fallback),
computes per-country and per-commodity stats used by agents.
"""

import io
import logging
import os
from collections import defaultdict
from typing import Any, Dict, List, Optional

import boto3
import numpy as np
import pandas as pd

logger = logging.getLogger("agroshield.data_loader")

S3_BUCKET = os.getenv("S3_BUCKET", "agroshield-trade-data")
S3_KEY = os.getenv("S3_KEY", "raw-data/trade_dataset.csv")
LOCAL_CSV = os.getenv("LOCAL_CSV", "data/trade_dataset.csv")


class DataLoader:
    def __init__(self):
        self.df: Optional[pd.DataFrame] = None
        self.country_stats: Dict[str, Any] = {}
        self.commodity_stats: Dict[str, Any] = {}
        self.global_stats: Dict[str, Any] = {}
        self.loaded = False

    async def load(self):
        """Load trade data from S3 or local CSV."""
        try:
            self.df = self._load_from_s3()
            logger.info("Loaded %d rows from S3", len(self.df))
        except Exception as exc:
            logger.warning("S3 load failed (%s), trying local CSV …", exc)
            try:
                self.df = pd.read_csv(LOCAL_CSV)
                logger.info("Loaded %d rows from local CSV", len(self.df))
            except Exception as local_exc:
                logger.error("Local CSV also failed: %s — using empty dataset", local_exc)
                self.df = pd.DataFrame()

        if not self.df.empty:
            self._compute_stats()
        self.loaded = True

    def _load_from_s3(self) -> pd.DataFrame:
        s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION", "ap-south-1"))
        obj = s3.get_object(Bucket=S3_BUCKET, Key=S3_KEY)
        return pd.read_csv(io.BytesIO(obj["Body"].read()))

    def _compute_stats(self):
        df = self.df.copy()

        # Normalise column names
        df.columns = [c.strip() for c in df.columns]

        # ── Country stats ──────────────────────────────────────────────────
        numeric_cols = [
            "Value_USD", "NetWeight_KG", "Unit_Price_USD_per_KG",
            "Shock_Intensity", "Avg_Goldstein", "Avg_Tone",
            "Trade_Share", "Effective_Shock", "MoM_Change_Value",
            "Rolling_3M_Volatility", "Net_Hostility", "Conflict_Density",
            "Trade_Shock_Density", "Incoming_Shock_Exposure",
            "Outgoing_Shock_Exposure", "Conflict_Exposure",
        ]
        existing_numeric = [c for c in numeric_cols if c in df.columns]

        for country, grp in df.groupby("Country"):
            top_commodities = (
                grp.groupby("Commodity")["Value_USD"].sum()
                .nlargest(5)
                .index.tolist()
                if "Commodity" in grp.columns else []
            )
            trade_type = (
                grp["Trade_Type"].mode()[0]
                if "Trade_Type" in grp.columns and not grp["Trade_Type"].empty
                else "EXPORT"
            )
            stats = {"top_commodities": top_commodities, "trade_type": trade_type}
            for col in existing_numeric:
                stats[col] = float(grp[col].mean()) if col in grp.columns else 0.0
            stats["total_trade_usd"] = float(grp["Value_USD"].sum()) if "Value_USD" in grp.columns else 0.0
            self.country_stats[str(country).upper()] = stats

        # ── Commodity stats ────────────────────────────────────────────────
        if "Commodity" in df.columns:
            for commodity, grp in df.groupby("Commodity"):
                top_countries = (
                    grp.groupby("Country")["Value_USD"].sum()
                    .nlargest(3)
                    .index.tolist()
                    if "Country" in grp.columns else []
                )
                hs4 = grp["HS4"].iloc[0] if "HS4" in grp.columns else ""
                self.commodity_stats[str(commodity)] = {
                    "top_countries": top_countries,
                    "hs4": str(hs4),
                    "avg_value_usd": float(grp["Value_USD"].mean()) if "Value_USD" in grp.columns else 0.0,
                    "total_value_usd": float(grp["Value_USD"].sum()) if "Value_USD" in grp.columns else 0.0,
                    "avg_shock": float(grp["Shock_Intensity"].mean()) if "Shock_Intensity" in grp.columns else 0.0,
                    "avg_mom_change": float(grp["MoM_Change_Value"].mean()) if "MoM_Change_Value" in grp.columns else 0.0,
                }

        # ── Global stats ───────────────────────────────────────────────────
        self.global_stats = {
            "total_rows": len(df),
            "total_countries": df["Country"].nunique() if "Country" in df.columns else 0,
            "total_commodities": df["Commodity"].nunique() if "Commodity" in df.columns else 0,
            "total_trade_usd": float(df["Value_USD"].sum()) if "Value_USD" in df.columns else 0.0,
            "avg_shock_intensity": float(df["Shock_Intensity"].mean()) if "Shock_Intensity" in df.columns else 0.0,
            "avg_goldstein": float(df["Avg_Goldstein"].mean()) if "Avg_Goldstein" in df.columns else 0.0,
            "years": sorted(df["Year"].unique().tolist()) if "Year" in df.columns else [],
        }
        logger.info("Stats computed: %d countries, %d commodities",
                    len(self.country_stats), len(self.commodity_stats))

    # ── Public accessors ───────────────────────────────────────────────────────
    def get_country_stats(self, country: str) -> Dict[str, Any]:
        key = country.upper()
        if key in self.country_stats:
            return self.country_stats[key]
        # Geographic proxy fallback
        proxy = self._find_proxy(key)
        if proxy:
            logger.info("Using proxy %s for %s", proxy, key)
            stats = dict(self.country_stats[proxy])
            stats["_proxy"] = proxy
            return stats
        return self._default_country_stats()

    def _find_proxy(self, country: str) -> Optional[str]:
        """Map unknown country to nearest geographic/economic proxy."""
        proxies = {
            "IRAN": ["UAE", "SAUDI ARABIA", "IRAQ"],
            "ISRAEL": ["UAE", "SAUDI ARABIA"],
            "RUSSIA": ["GERMANY", "UKRAINE"],
            "UKRAINE": ["RUSSIA", "GERMANY"],
            "NORTH KOREA": ["CHINA", "SOUTH KOREA"],
            "TAIWAN": ["CHINA", "JAPAN"],
            "VENEZUELA": ["BRAZIL", "COLOMBIA"],
            "SYRIA": ["TURKEY", "UAE"],
            "MYANMAR": ["BANGLADESH", "THAILAND"],
            "AFGHANISTAN": ["PAKISTAN", "IRAN"],
            "TURKEY": ["UAE", "GERMANY"],
        }
        for candidate_list in [proxies.get(country, [])]:
            for candidate in candidate_list:
                if candidate in self.country_stats:
                    return candidate
        # fallback: find any existing country
        if self.country_stats:
            return next(iter(self.country_stats))
        return None

    def _default_country_stats(self) -> Dict[str, Any]:
        return {
            "Trade_Share": 0.02,
            "Shock_Intensity": 1.0,
            "Avg_Goldstein": -2.0,
            "Avg_Tone": -2.0,
            "MoM_Change_Value": 0.0,
            "Rolling_3M_Volatility": 0.1,
            "Net_Hostility": 0.0,
            "Effective_Shock": 0.5,
            "Conflict_Exposure": 0.1,
            "total_trade_usd": 0.0,
            "top_commodities": [],
            "trade_type": "EXPORT",
        }

    def get_country_summary(self) -> List[Dict]:
        result = []
        for country, stats in self.country_stats.items():
            result.append({
                "country": country,
                "trade_share": round(stats.get("Trade_Share", 0), 4),
                "total_trade_usd": round(stats.get("total_trade_usd", 0), 2),
                "top_commodities": stats.get("top_commodities", [])[:3],
                "avg_shock": round(stats.get("Shock_Intensity", 0), 2),
                "avg_goldstein": round(stats.get("Avg_Goldstein", 0), 2),
                "trade_type": stats.get("trade_type", "EXPORT"),
            })
        return sorted(result, key=lambda x: -x["total_trade_usd"])

    def get_commodity_summary(self) -> List[Dict]:
        result = []
        for commodity, stats in self.commodity_stats.items():
            result.append({
                "commodity": commodity,
                "hs4": stats.get("hs4", ""),
                "top_countries": stats.get("top_countries", [])[:3],
                "total_value_usd": round(stats.get("total_value_usd", 0), 2),
                "avg_shock": round(stats.get("avg_shock", 0), 2),
                "avg_mom_change": round(stats.get("avg_mom_change", 0), 4),
            })
        return sorted(result, key=lambda x: -x["total_value_usd"])
