"""
Agent 2 — Event Processor
Extracts structured fields (country, event_type, severity, commodities,
Goldstein score) from raw GDELT headlines using keyword matching + regex.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("agroshield.agent2")

# ── Event type detection ───────────────────────────────────────────────────────
EVENT_TYPES = {
    "TARIFF": ["tariff", "duty", "import tax", "customs levy", "trade tax"],
    "SANCTION": ["sanction", "embargo", "ban", "restrict", "blacklist", "block"],
    "CONFLICT": ["war", "conflict", "attack", "missile", "strike", "military",
                 "troops", "invasion", "bombing", "naval", "blockade", "battle"],
    "DIPLOMATIC": ["agreement", "deal", "treaty", "mou", "cepa", "summit",
                   "cooperation", "partnership", "negotiation", "accord"],
    "CLIMATE": ["drought", "flood", "cyclone", "storm", "monsoon", "heat wave",
                "crop failure", "harvest loss", "locust"],
    "PROTEST": ["protest", "strike", "demonstration", "riot", "unrest"],
    "TRADE_POLICY": ["export ban", "import ban", "quota", "subsidy", "dumping",
                     "anti-dumping", "countervailing", "free trade"],
    "ECONOMIC": ["recession", "inflation", "currency", "rupee", "dollar",
                 "exchange rate", "devaluation", "gdp", "fuel price", "oil price"],
}

# ── Country detection ──────────────────────────────────────────────────────────
COUNTRY_ALIASES = {
    "USA": ["usa", "united states", "us ", "america", "american", "washington",
            "white house", "biden", "trump", "ustr", "u.s."],
    "CHINA": ["china", "chinese", "beijing", "prc", "xi jinping"],
    "EU": ["eu", "europe", "european union", "brussels", "germany", "france",
           "netherlands", "belgium"],
    "UK": ["uk", "britain", "british", "london", "england"],
    "IRAN": ["iran", "iranian", "tehran", "irgc", "khamenei"],
    "ISRAEL": ["israel", "israeli", "tel aviv", "idf", "netanyahu"],
    "RUSSIA": ["russia", "russian", "moscow", "kremlin", "putin"],
    "UKRAINE": ["ukraine", "ukrainian", "kyiv", "zelenskyy"],
    "PAKISTAN": ["pakistan", "pakistani", "islamabad", "karachi"],
    "BANGLADESH": ["bangladesh", "bangladeshi", "dhaka"],
    "SRI LANKA": ["sri lanka", "colombo", "sinhala"],
    "SAUDI ARABIA": ["saudi", "saudi arabia", "riyadh", "aramco"],
    "UAE": ["uae", "dubai", "abu dhabi", "emirates"],
    "INDONESIA": ["indonesia", "indonesian", "jakarta"],
    "MALAYSIA": ["malaysia", "kuala lumpur"],
    "TURKEY": ["turkey", "turkish", "ankara", "erdogan"],
    "AFGHANISTAN": ["afghanistan", "afghan", "kabul", "taliban"],
    "MYANMAR": ["myanmar", "burma", "yangon"],
    "BRAZIL": ["brazil", "brazilian", "brasilia"],
    "ARGENTINA": ["argentina", "buenos aires"],
    "AUSTRALIA": ["australia", "australian", "canberra"],
    "VIETNAM": ["vietnam", "vietnamese", "hanoi", "ho chi minh"],
    "JAPAN": ["japan", "japanese", "tokyo"],
    "SOUTH KOREA": ["south korea", "seoul", "korean"],
    "NEPAL": ["nepal", "kathmandu"],
    "IRAQ": ["iraq", "baghdad", "iraqi"],
    "EGYPT": ["egypt", "cairo", "suez"],
    "G7": ["g7", "g-7"],
    "G20": ["g20", "g-20"],
}

# ── Commodity detection ────────────────────────────────────────────────────────
COMMODITY_KEYWORDS = {
    "Rice": ["rice", "basmati", "paddy", "parboiled rice"],
    "Wheat": ["wheat", "flour", "atta"],
    "Cotton": ["cotton", "cotton seed", "textile"],
    "Spices": ["spice", "chilli", "turmeric", "pepper", "cardamom", "ginger"],
    "Sugar": ["sugar", "sugarcane", "molasses"],
    "Pulses": ["pulse", "lentil", "dal", "tur", "moong", "chana"],
    "Edible Oil": ["palm oil", "soybean oil", "sunflower oil", "edible oil",
                   "vegetable oil", "mustard oil"],
    "Maize": ["maize", "corn"],
    "Soybean": ["soybean", "soya"],
    "Onion": ["onion"],
    "Tomato": ["tomato"],
    "Potato": ["potato"],
    "Tea": ["tea", "chai"],
    "Coffee": ["coffee"],
    "Shrimp": ["shrimp", "prawn", "seafood"],
    "Fertilizer": ["fertilizer", "fertiliser", "urea", "dap", "potash", "phosphate"],
    "Fuel": ["oil", "petroleum", "diesel", "crude", "fuel", "energy"],
}

# ── Goldstein scale per event type ────────────────────────────────────────────
GOLDSTEIN_MAP = {
    "TARIFF": -6.5,
    "SANCTION": -7.0,
    "CONFLICT": -8.5,
    "DIPLOMATIC": +3.5,
    "CLIMATE": -4.0,
    "PROTEST": -3.5,
    "TRADE_POLICY": -5.0,
    "ECONOMIC": -3.0,
}


class EventProcessor:
    def process(self, raw_article: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Turn a raw GDELT article into a structured event dict.
        Returns None if irrelevant to India agri trade.
        """
        title = raw_article.get("title", "")
        if not title:
            return None

        title_lower = title.lower()

        # Allow file-based structured hints to override regex extraction.
        event_type = self._coerce_event_type(raw_article.get("event_type")) or self._detect_event_type(title_lower)
        countries = self._coerce_countries(raw_article.get("primary_country")) or self._detect_countries(title_lower)
        severity = self._coerce_float(raw_article.get("severity_pct"))
        if severity is None:
            severity = self._extract_severity(title_lower)
        commodities = self._coerce_list(raw_article.get("affected_commodities")) or self._detect_commodities(title_lower)
        hint_goldstein = self._coerce_float(raw_article.get("estimated_goldstein"))
        goldstein = hint_goldstein if hint_goldstein is not None else self._estimate_goldstein(event_type, raw_article.get("avg_tone", 0.0))

        # Determine primary affected country
        primary_country = countries[0] if countries else "GLOBAL"

        return {
            "event_id": raw_article.get("event_id", ""),
            "headline": title,
            "url": raw_article.get("url", ""),
            "timestamp": raw_article.get("timestamp", ""),
            "primary_country": primary_country,
            "all_countries": countries,
            "event_type": event_type,
            "severity_pct": severity,
            "affected_commodities": commodities,
            "estimated_goldstein": goldstein,
            "avg_tone": raw_article.get("avg_tone", 0.0),
            "is_positive": goldstein > 0,
        }

    def _coerce_float(self, value: Any) -> Optional[float]:
        try:
            if value is None or value == "":
                return None
            return float(value)
        except Exception:
            return None

    def _coerce_list(self, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        text = str(value).strip()
        if not text:
            return []
        return [p.strip() for p in text.split(",") if p.strip()]

    def _coerce_event_type(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        etype = str(value).strip().upper()
        if not etype:
            return None
        return etype

    def _coerce_countries(self, value: Any) -> List[str]:
        if value is None:
            return []
        parts = self._coerce_list(value)
        return [p.upper() for p in parts]

    def _detect_event_type(self, text: str) -> str:
        for etype, keywords in EVENT_TYPES.items():
            if any(kw in text for kw in keywords):
                return etype
        return "GENERAL"

    def _detect_countries(self, text: str) -> List[str]:
        found = []
        for country, aliases in COUNTRY_ALIASES.items():
            if any(alias in text for alias in aliases):
                found.append(country)
        return found if found else ["GLOBAL"]

    def _extract_severity(self, text: str) -> float:
        """Extract percentage or numeric severity from headline."""
        # e.g. "50%", "50 percent", "$2 billion"
        pct_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|percent)", text)
        if pct_match:
            return min(float(pct_match.group(1)), 100.0)
        # Dollar amount (billion → scaled)
        bn_match = re.search(r"\$(\d+(?:\.\d+)?)\s*billion", text)
        if bn_match:
            return min(float(bn_match.group(1)) * 5, 100.0)
        mn_match = re.search(r"\$(\d+(?:\.\d+)?)\s*million", text)
        if mn_match:
            return min(float(mn_match.group(1)) / 20, 100.0)
        # Default severity by keywords
        if any(w in text for w in ["major", "massive", "critical", "severe", "total", "complete"]):
            return 75.0
        if any(w in text for w in ["significant", "large", "high", "sharp"]):
            return 50.0
        if any(w in text for w in ["minor", "small", "slight"]):
            return 15.0
        return 30.0  # default moderate

    def _detect_commodities(self, text: str) -> List[str]:
        found = []
        for commodity, keywords in COMMODITY_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                found.append(commodity)
        return found if found else []

    def _estimate_goldstein(self, event_type: str, avg_tone: float) -> float:
        base = GOLDSTEIN_MAP.get(event_type, -2.0)
        # Blend with GDELT tone (normalized from [-100,100] to [-10,10])
        tone_factor = avg_tone / 10.0
        return round((base * 0.7) + (tone_factor * 0.3), 2)
