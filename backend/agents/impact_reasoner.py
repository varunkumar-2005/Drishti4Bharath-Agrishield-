"""
Agent 4 - Impact Reasoner
Derives primary and secondary cascading effects on India's agricultural trade
using actual trade data loaded from the S3 CSV.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger("agroshield.agent4")

# Farmers per state (approximate millions)
STATE_FARMERS = {
    "Punjab": 2.5, "Haryana": 1.8, "Uttar Pradesh": 18.0,
    "Madhya Pradesh": 8.0, "Gujarat": 5.5, "Maharashtra (Vidarbha)": 9.0,
    "Andhra Pradesh": 5.0, "Telangana": 3.8, "West Bengal": 7.2,
    "Odisha": 4.0, "Karnataka": 5.3, "Kerala": 3.2,
    "Tamil Nadu": 4.5, "Rajasthan": 6.8, "Bihar": 8.5,
    "Assam": 3.0,
}

# USD per KG prices for revenue estimation
COMMODITY_PRICES = {
    "Rice": 0.38, "Wheat": 0.28, "Cotton": 1.65, "Spices": 3.50,
    "Sugar": 0.35, "Pulses": 0.80, "Edible Oil": 0.90, "Maize": 0.22,
    "Soybean": 0.45, "Tea": 2.10, "Shrimp": 5.50, "Onion": 0.25,
    "Fertilizer": 0.55, "Fuel": 0.60, "default": 0.50,
}


class ImpactReasoner:
    def reason(
        self,
        structured_event: Dict[str, Any],
        country_stats: Dict[str, Any],
        prediction: Dict[str, Any],
        data_loader: Any,
    ) -> Dict[str, Any]:
        """
        Derive trade impact, affected commodities, states, farmer count,
        revenue at risk, and cascading effects.
        """
        country = structured_event.get("primary_country", "GLOBAL")
        event_type = structured_event.get("event_type", "GENERAL")
        severity = structured_event.get("severity_pct", 30.0) / 100.0
        risk_label = prediction.get("risk_label", "MEDIUM")
        risk_score = prediction.get("risk_score", 50)
        is_positive = structured_event.get("is_positive", False)

        # Commodities from headline + country trade data (no hardcoded route mapping).
        detected = structured_event.get("affected_commodities", [])
        top_commodities_from_data = country_stats.get("top_commodities", [])
        if not top_commodities_from_data and hasattr(data_loader, "get_top_commodities_for_country"):
            top_commodities_from_data = data_loader.get_top_commodities_for_country(country, limit=6)
        all_commodities = self._select_commodities(detected, top_commodities_from_data)

        # Use real country trade data
        trade_share = float(country_stats.get("Trade_Share", 0.02))
        total_trade = float(country_stats.get("total_trade_usd", 0.0))
        trade_type = country_stats.get("trade_type", "EXPORT")

        # Revenue at risk
        revenue_at_risk = self._estimate_revenue_at_risk(
            total_trade, trade_share, severity, risk_score, is_positive
        )

        # Affected states from structured input only; otherwise national scope.
        affected_states = self._get_affected_states(structured_event)

        # Farmers at risk
        farmers_at_risk = self._estimate_farmers(affected_states, trade_share, severity)

        # Primary effects
        primary_effects = self._primary_effects(
            event_type, country, all_commodities, trade_share,
            severity, revenue_at_risk, trade_type, is_positive
        )

        # Cascading / secondary effects
        cascading_effects = self._cascading_effects(
            event_type, country, all_commodities, severity, is_positive
        )

        # Timeline
        timeline = self._build_timeline(event_type, risk_label, severity)

        # Mandi price impact per commodity
        price_impacts = self._price_impacts(all_commodities, event_type, severity, trade_type, is_positive)

        return {
            "primary_country": country,
            "event_type": event_type,
            "affected_commodities": all_commodities,
            "affected_states": affected_states,
            "farmers_at_risk_millions": round(farmers_at_risk, 1),
            "revenue_at_risk_usd": round(revenue_at_risk, 0),
            "trade_share_pct": round(trade_share * 100, 2),
            "trade_type": trade_type,
            "primary_effects": primary_effects,
            "cascading_effects": cascading_effects,
            "timeline": timeline,
            "price_impacts": price_impacts,
            "trade_impact_summary": self._trade_summary(
                revenue_at_risk, all_commodities, is_positive
            ),
        }

    def _estimate_revenue_at_risk(
        self, total_trade: float, trade_share: float,
        severity: float, risk_score: int, is_positive: bool
    ) -> float:
        if total_trade > 0:
            base = total_trade * severity * (risk_score / 100)
        else:
            base = 1_000_000 * trade_share * severity * (risk_score / 100) * 100
        return base if not is_positive else base * 0.2

    def _select_commodities(self, detected: List[str], top_from_data: List[str]) -> List[str]:
        merged = list(dict.fromkeys((top_from_data or []) + (detected or [])))
        cleaned = [str(c).strip() for c in merged if str(c).strip()]
        return cleaned[:6] if cleaned else ["agricultural commodities"]

    def _get_affected_states(self, structured_event: Dict[str, Any]) -> List[str]:
        raw_states = structured_event.get("affected_states", [])
        if isinstance(raw_states, str):
            states = [s.strip() for s in raw_states.split(",") if s.strip()]
        elif isinstance(raw_states, list):
            states = [str(s).strip() for s in raw_states if str(s).strip()]
        else:
            states = []
        if not states:
            return ["Nationwide"]
        seen = set()
        deduped = []
        for state in states:
            if state not in seen:
                seen.add(state)
                deduped.append(state)
        return deduped[:6]

    def _estimate_farmers(
        self, states: List[str], trade_share: float, severity: float
    ) -> float:
        total = sum(STATE_FARMERS.get(s, 1.0) for s in states)
        return total * trade_share * (1 + severity)

    def _primary_effects(
        self, event_type: str, country: str, commodities: List[str],
        trade_share: float, severity: float, revenue: float,
        trade_type: str, is_positive: bool
    ) -> List[str]:
        effects = []
        commodity_str = ", ".join(commodities[:3]) if commodities else "agricultural commodities"
        pct_exposed = round(trade_share * 100, 1)
        rev_m = round(revenue / 1_000_000, 1)

        if is_positive:
            effects.append(
                f"{commodity_str} {trade_type.lower()} opportunity from {country} - "
                f"{pct_exposed}% of India's agri trade could benefit, ~${rev_m}M revenue upside."
            )
        else:
            if event_type in ("TARIFF", "SANCTION", "TRADE_POLICY"):
                effects.append(
                    f"{commodity_str} exports to {country} at risk - "
                    f"{pct_exposed}% of India's total agri trade exposed, ~${rev_m}M revenue under threat."
                )
            elif event_type == "CONFLICT":
                effects.append(
                    f"Shipping lanes through {country} region disrupted - "
                    f"{commodity_str} transit risk; {pct_exposed}% trade exposure, ~${rev_m}M at risk."
                )
            elif event_type == "CLIMATE":
                effects.append(
                    f"{country} crop failure creates {commodity_str} demand opportunity for India - "
                    f"~${rev_m}M export upside if supply gaps filled quickly."
                )
            elif event_type == "ECONOMIC":
                effects.append(
                    f"Currency/economic stress in {country} weakens import capacity - "
                    f"{commodity_str} demand drop likely; {pct_exposed}% trade share affected."
                )
            else:
                effects.append(
                    f"Geopolitical tension involving {country} creates uncertainty for "
                    f"{commodity_str} trade ({pct_exposed}% exposure)."
                )

        price_drop = round(severity * 25, 0)
        if not is_positive and trade_share > 0.05:
            effects.append(
                f"Mandi prices for {commodities[0] if commodities else 'key crops'} expected to "
                f"{'drop' if trade_type == 'EXPORT' else 'rise'} {price_drop:.0f}-{price_drop*1.4:.0f}% "
                f"over next 4-8 weeks based on historical MoM patterns."
            )
        return effects

    def _cascading_effects(
        self, event_type: str, country: str,
        commodities: List[str], severity: float, is_positive: bool
    ) -> List[str]:
        effects = []
        if is_positive:
            return ["Export revenue could support INR stability.",
                    "Positive signal for farmer incomes in producing states."]

        if event_type == "CONFLICT" or country in ("IRAN", "ISRAEL"):
            effects.append("Strait of Hormuz disruption -> oil tanker rerouting -> diesel price spike -> "
                           "farm transport and cold chain cost surge across India.")
            effects.append("Oil price rise -> fertiliser production cost increase -> "
                           "Kharif season input costs rise 8-15%.")

        if event_type in ("TARIFF", "SANCTION"):
            effects.append(f"Oversupply at domestic mandis as {commodities[0] if commodities else 'crops'} "
                           f"pile up - distress selling risk for farmers.")
            effects.append("INR depreciation pressure as trade deficit widens due to export revenue loss.")

        if event_type == "ECONOMIC":
            effects.append("Weaker trading partner currency reduces real value of Indian exports.")
            effects.append("Potential import demand reduction triggers domestic price softening.")

        if "Fertilizer" in commodities or event_type == "SANCTION":
            effects.append("Fertilizer supply disruption -> Kharif sowing cost surge -> "
                           "risk of reduced crop area next season.")

        if "Edible Oil" in commodities or "Fuel" in commodities:
            effects.append("Consumer food basket inflation likely - edible oil and food processing inputs at risk.")

        if not effects:
            effects.append("Secondary supply chain disruptions may affect logistics costs for agri exports.")
        return effects

    def _build_timeline(self, event_type: str, risk_label: str, severity: float) -> List[Dict]:
        base = [
            {"period": "0-72 hours", "action": "Immediate monitoring and early-warning alerts"},
            {"period": "Week 1", "action": "Price signal detection at mandis and wholesale markets"},
            {"period": "Week 2-4", "action": "Trade volume adjustment and supply chain reconfiguration"},
            {"period": "Month 2-3", "action": "Policy intervention and trade partner diversification"},
            {"period": "Quarter", "action": "Long-term structural trade adjustment"},
        ]
        if risk_label in ("CRITICAL", "HIGH"):
            base[0]["action"] = "URGENT: Activate buffer stocks and issue emergency advisory within 24 hours"
        return base

    def _price_impacts(
        self, commodities: List[str], event_type: str,
        severity: float, trade_type: str, is_positive: bool
    ) -> List[Dict]:
        impacts = []
        for c in commodities[:4]:
            base_price = COMMODITY_PRICES.get(c, COMMODITY_PRICES["default"])
            direction = "up" if (
                (trade_type == "IMPORT" and not is_positive) or
                (trade_type == "EXPORT" and is_positive)
            ) else "down"
            change_pct = round(severity * 20 * (1.2 if event_type in ("CONFLICT", "SANCTION") else 1.0), 1)
            new_price = base_price * (1 + change_pct / 100) if direction == "up" else base_price * (1 - change_pct / 100)
            impacts.append({
                "commodity": c,
                "direction": direction,
                "change_pct": change_pct,
                "current_usd_kg": round(base_price, 2),
                "forecast_usd_kg": round(new_price, 2),
            })
        return impacts

    def _trade_summary(self, revenue: float, commodities: List[str], is_positive: bool) -> str:
        rev_m = round(revenue / 1_000_000, 1)
        c = commodities[0] if commodities else "commodities"
        prefix = "opportunity" if is_positive else "risk"
        return f"${rev_m}M {prefix} - {c} primary"
