"""
DataLoader: reads trade_dataset.csv from S3 (or local fallback),
computes per-country and per-commodity stats used by agents.
"""

import io
import logging
import os
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional

import boto3
import numpy as np
import pandas as pd
from botocore.config import Config

logger = logging.getLogger("agroshield.data_loader")

S3_BUCKET = os.getenv("S3_BUCKET", "agroshield-trade-data")
S3_KEY = os.getenv("S3_KEY", "raw-data/trade_dataset.csv")
LOCAL_CSV = os.getenv("LOCAL_CSV", "data/trade_dataset.csv")
LOAD_FROM_S3 = os.getenv("LOAD_FROM_S3", "true").lower() == "true"
REQUIRE_S3_DATA = os.getenv("REQUIRE_S3_DATA", "false").lower() == "true"


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
            if LOAD_FROM_S3:
                self.df = self._load_from_s3()
                logger.info("Loaded %d rows from S3", len(self.df))
            else:
                raise RuntimeError("S3 loading disabled by LOAD_FROM_S3=false")
        except Exception as exc:
            if REQUIRE_S3_DATA:
                logger.error("S3 load failed and REQUIRE_S3_DATA=true: %s", exc)
                raise
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
        s3 = boto3.client(
            "s3",
            region_name=os.getenv("AWS_REGION", "ap-south-1"),
            config=Config(connect_timeout=3, read_timeout=8, retries={"max_attempts": 1}),
        )
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

    def get_trade_facts(
        self,
        crop: Optional[str] = None,
        country: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Get recent high-value trade facts for grounding LLM responses."""
        if self.df is None or self.df.empty:
            return []

        df = self.df.copy()
        if crop and "Commodity" in df.columns:
            crop_q = str(crop).strip()
            if crop_q:
                pattern = re.escape(crop_q)
                df = df[df["Commodity"].astype(str).str.contains(pattern, case=False, na=False)]

        if country and "Country" in df.columns:
            key = str(country).strip().upper()
            aliases = {
                "USA": ["USA", "UNITED STATES", "US", "U.S."],
                "UK": ["UK", "UNITED KINGDOM", "GREAT BRITAIN", "BRITAIN"],
                "UAE": ["UAE", "UNITED ARAB EMIRATES"],
                "EU": ["EU", "EUROPEAN UNION"],
            }
            candidates = aliases.get(key, [key])
            df = df[df["Country"].astype(str).str.upper().isin(candidates)]

        if df.empty:
            return []

        if "Year" in df.columns and "Month" in df.columns:
            df = df.sort_values(by=["Year", "Month"], ascending=[False, False])
        if "Value_USD" in df.columns:
            df = df.sort_values(by=["Value_USD"], ascending=False)

        keep_cols = [
            "Country", "Commodity", "Trade_Type", "Value_USD", "Trade_Share",
            "MoM_Change_Value", "Shock_Intensity", "Avg_Goldstein",
            "Avg_Tone", "Rolling_3M_Volatility", "Year", "Month",
        ]
        cols = [c for c in keep_cols if c in df.columns]
        out: List[Dict[str, Any]] = []
        for _, row in df.head(max(limit, 1))[cols].iterrows():
            item = {}
            for c in cols:
                v = row[c]
                if hasattr(v, "item"):
                    v = v.item()
                if isinstance(v, float):
                    if c in {"Trade_Share", "MoM_Change_Value", "Shock_Intensity", "Avg_Goldstein", "Avg_Tone", "Rolling_3M_Volatility"}:
                        v = round(v, 4)
                    else:
                        v = round(v, 2)
                item[c] = v
            out.append(item)
        return out

    def get_top_commodities_for_country(self, country: str, limit: int = 6) -> List[str]:
        """Return top traded commodities for a country from the raw dataset."""
        if self.df is None or self.df.empty or "Country" not in self.df.columns or "Commodity" not in self.df.columns:
            return []
        key = str(country).strip().upper()
        aliases = {
            "USA": ["USA", "UNITED STATES", "US", "U.S."],
            "UK": ["UK", "UNITED KINGDOM", "GREAT BRITAIN", "BRITAIN"],
            "UAE": ["UAE", "UNITED ARAB EMIRATES"],
            "EU": ["EU", "EUROPEAN UNION"],
            "SOUTH KOREA": ["SOUTH KOREA", "KOREA, REPUBLIC OF", "REPUBLIC OF KOREA"],
        }
        candidates = aliases.get(key, [key])
        upper_country = self.df["Country"].astype(str).str.upper()
        country_df = self.df[upper_country.isin(candidates)]
        if country_df.empty:
            return []
        if "Value_USD" in country_df.columns:
            ranked = country_df.groupby("Commodity")["Value_USD"].sum().sort_values(ascending=False)
        else:
            ranked = country_df["Commodity"].value_counts()
        return [str(c) for c in ranked.head(max(limit, 1)).index.tolist() if str(c).strip()]
