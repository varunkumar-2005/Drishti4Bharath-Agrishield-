"""
Agent 5 — Advisory Generator
Calls Amazon Bedrock (Claude Sonnet / Nova Lite) to generate
dynamic, data-driven advisories for farmers, policymakers,
consumers, and traders — based on ML predictions + trade data.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import boto3

logger = logging.getLogger("agroshield.agent5")

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
BEDROCK_MODEL = os.getenv("BEDROCK_MODEL", "amazon.nova-lite-v1:0")
FALLBACK_MODEL = os.getenv("BEDROCK_FALLBACK_MODEL", "amazon.nova-lite-v1:0")
MAX_TOKENS = 2000


class AdvisoryGenerator:
    def __init__(self):
        self._client = None
        self._init_client()

    def _init_client(self):
        try:
            self._client = boto3.client(
                "bedrock-runtime",
                region_name=AWS_REGION,
            )
            logger.info("Bedrock client initialised (model: %s)", BEDROCK_MODEL)
        except Exception as exc:
            logger.warning("Bedrock client init failed: %s", exc)

    async def generate(
        self,
        headline: str,
        structured_event: Dict[str, Any],
        prediction: Dict[str, Any],
        impact: Dict[str, Any],
        country_stats: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate stakeholder-specific advisories via Bedrock LLM."""

        prompt = self._build_prompt(
            headline, structured_event, prediction, impact, country_stats
        )

        raw_text = None
        model_used = "none"

        if self._client:
            # Try primary model
            for model_id in [BEDROCK_MODEL, FALLBACK_MODEL]:
                try:
                    raw_text = self._invoke_bedrock(model_id, prompt)
                    model_used = model_id
                    break
                except Exception as exc:
                    logger.warning("Bedrock model %s failed: %s", model_id, exc)

        if not raw_text:
            logger.info("Using rule-based advisory fallback")
            raw_text = self._rule_based_advisory(structured_event, prediction, impact)
            model_used = "rule_based"

        advisory = self._parse_advisory(raw_text)
        advisory.update({
            "advisory_id": str(uuid.uuid4())[:12],
            "headline": headline,
            "event_type": structured_event.get("event_type"),
            "primary_country": structured_event.get("primary_country"),
            "risk_label": prediction.get("risk_label"),
            "risk_score": prediction.get("risk_score"),
            "affected_commodities": impact.get("affected_commodities", []),
            "affected_states": impact.get("affected_states", []),
            "farmers_at_risk_millions": impact.get("farmers_at_risk_millions", 0),
            "revenue_at_risk_usd": impact.get("revenue_at_risk_usd", 0),
            "model_used": model_used,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        })
        return advisory

    def _build_prompt(
        self,
        headline: str,
        event: Dict,
        prediction: Dict,
        impact: Dict,
        country_stats: Dict,
    ) -> str:
        commodities = ", ".join(impact.get("affected_commodities", [])[:5]) or "agricultural commodities"
        states = ", ".join(impact.get("affected_states", [])[:5]) or "major agri states"
        primary_effects = "\n".join(f"- {e}" for e in impact.get("primary_effects", []))
        cascading = "\n".join(f"- {e}" for e in impact.get("cascading_effects", []))
        price_impacts = json.dumps(impact.get("price_impacts", []), indent=2)
        timeline = json.dumps(impact.get("timeline", []), indent=2)

        return f"""You are AgroShield, an expert geopolitical agricultural trade intelligence system for India.

GEOPOLITICAL EVENT:
Headline: {headline}
Country: {event.get("primary_country", "UNKNOWN")}
Event Type: {event.get("event_type", "GENERAL")}
Severity: {event.get("severity_pct", 30)}%
Goldstein Score: {event.get("estimated_goldstein", -2.0)}
Tone: {event.get("avg_tone", 0.0)}

ML RISK PREDICTION:
Risk Level: {prediction.get("risk_label")} ({prediction.get("risk_score")}/100)
Confidence: {round(prediction.get("confidence", 0) * 100, 1)}%
Probabilities: {json.dumps(prediction.get("probabilities", {}))}
Model: {prediction.get("model", "rule_based")}

TRADE DATA (from India bilateral trade dataset):
Affected Commodities: {commodities}
Affected States: {states}
Trade Share: {impact.get("trade_share_pct", 0)}% of India agri trade
Trade Type: {impact.get("trade_type", "EXPORT")}
Revenue at Risk: ${round(impact.get("revenue_at_risk_usd", 0) / 1_000_000, 1)}M
Farmers at Risk: {impact.get("farmers_at_risk_millions", 0)}M farmers

PRIMARY EFFECTS:
{primary_effects}

CASCADING EFFECTS:
{cascading}

PRICE IMPACTS:
{price_impacts}

TIMELINE:
{timeline}

COUNTRY TRADE STATS (historical averages from dataset):
Trade Share: {round(float(country_stats.get("Trade_Share", 0)) * 100, 2)}%
Avg Goldstein: {country_stats.get("Avg_Goldstein", 0)}
Shock Intensity: {country_stats.get("Shock_Intensity", 0)}
Top Commodities: {", ".join(country_stats.get("top_commodities", [])[:4])}

TASK: Generate specific, actionable advisories for FOUR stakeholder groups based on the above real data.
DO NOT be generic. Reference specific commodities, states, farmers, dollar values, and timelines above.
Respond in JSON format exactly like this:

{{
  "policy_makers": {{
    "immediate_72h": "Specific action for policymakers in 0–72 hours using real data above",
    "week_1_4": "Specific week 1-4 policy action",
    "medium_term": "1-3 month strategic policy recommendation"
  }},
  "farmers": {{
    "immediate_action": "Specific action for farmers in the affected states/crops",
    "crop_advisory": "Specific crop planning recommendation with percentages and crop names",
    "opportunity": "Any opportunity farmers can exploit"
  }},
  "consumers": {{
    "price_alert": "Specific price impact on household items with estimated change",
    "advisory": "What consumers should do",
    "outlook_30d": "Price outlook for next 30 days"
  }},
  "traders": {{
    "immediate": "Urgent action for commodity traders",
    "rerouting": "Trade rerouting or hedging strategy",
    "opportunity": "Any trading opportunity"
  }},
  "summary": "2-sentence summary of the overall situation and its impact on India"
}}"""

    def _invoke_bedrock(self, model_id: str, prompt: str) -> str:
        """Invoke Amazon Bedrock with model-specific payload format."""
        if "anthropic" in model_id:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": MAX_TOKENS,
                "messages": [{"role": "user", "content": prompt}],
            })
        elif "amazon.nova" in model_id:
            body = json.dumps({
                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                "inferenceConfig": {"maxTokens": MAX_TOKENS, "temperature": 0.3},
            })
        else:
            body = json.dumps({
                "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
                "max_tokens_to_sample": MAX_TOKENS,
                "temperature": 0.3,
            })

        response = self._client.invoke_model(
            modelId=model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(response["body"].read())

        # Extract text from various response formats
        if "content" in result:
            return result["content"][0]["text"]
        if "output" in result and "message" in result["output"]:
            content = result["output"]["message"]["content"]
            if isinstance(content, list):
                return content[0].get("text", "")
        if "completion" in result:
            return result["completion"]
        return json.dumps(result)

    def _parse_advisory(self, raw_text: str) -> Dict[str, Any]:
        """Parse JSON advisory from LLM output."""
        try:
            # Extract JSON block
            start = raw_text.find("{")
            end = raw_text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(raw_text[start:end])
        except Exception:
            pass
        # Return raw text wrapped
        return {
            "policy_makers": {
                "immediate_72h": raw_text[:500],
                "week_1_4": "See full advisory text.",
                "medium_term": "See full advisory text.",
            },
            "farmers": {"immediate_action": "", "crop_advisory": "", "opportunity": ""},
            "consumers": {"price_alert": "", "advisory": "", "outlook_30d": ""},
            "traders": {"immediate": "", "rerouting": "", "opportunity": ""},
            "summary": raw_text[:300],
        }

    def _rule_based_advisory(
        self,
        event: Dict,
        prediction: Dict,
        impact: Dict,
    ) -> str:
        """Deterministic fallback advisory when Bedrock is unavailable."""
        country = event.get("primary_country", "the affected country")
        etype = event.get("event_type", "GENERAL")
        risk = prediction.get("risk_label", "MEDIUM")
        score = prediction.get("risk_score", 50)
        commodities = impact.get("affected_commodities", ["agricultural commodities"])
        states = impact.get("affected_states", ["major agri states"])
        rev = round(impact.get("revenue_at_risk_usd", 0) / 1_000_000, 1)
        farmers = impact.get("farmers_at_risk_millions", 0)
        c_str = ", ".join(commodities[:3])
        s_str = ", ".join(states[:3])
        trade_type = impact.get("trade_type", "EXPORT")

        if etype in ("TARIFF", "SANCTION"):
            pm_immediate = (f"Activate buffer stock protocol for {c_str} in {s_str} within 72 hours. "
                            f"Initiate WTO dispute panel notice against {country}. "
                            f"Pre-position procurement teams in affected districts. "
                            f"${rev}M revenue at risk — emergency MSP procurement may be needed.")
            farmer_action = (f"Do NOT sell {commodities[0] if commodities else 'crop'} at current mandi price — "
                             f"hold stock 30–45 days. Reduce sowing of {commodities[0]} by 15–20% next season. "
                             f"Register for PM-AASHA scheme for price support. {farmers}M farmers in {s_str} affected.")
            consumer_alert = (f"{c_str} prices may {'fall 8–15%' if trade_type == 'EXPORT' else 'rise 10–18%'} "
                              f"over next 6 weeks. Edible oil prices may rise due to INR pressure from trade deficit.")
            trader_action = (f"Reroute {commodities[0]} exports away from {country}. "
                             f"Target ASEAN and GCC corridors. Avoid forward contracts with {country} buyers until resolved.")
        elif etype == "CONFLICT":
            pm_immediate = (f"Authorize Strategic Petroleum Reserve drawdown to contain diesel price surge. "
                            f"Issue shipping route advisory for {c_str} exporters. "
                            f"Activate food security emergency protocol — {risk} risk, score {score}/100.")
            farmer_action = (f"Expect diesel and fertilizer costs to rise 12–20% due to conflict in {country} region. "
                             f"Plan accordingly for next sowing season. Affected: {c_str} farmers in {s_str}.")
            consumer_alert = (f"Edible oil and fuel prices may rise 15–25% if conflict persists over 2 weeks. "
                              f"Stock 1 month supply of essential cooking oil as precaution.")
            trader_action = (f"Activate alternative shipping routes — avoid {country} corridor. "
                             f"Reroute {c_str} shipments via alternative lanes immediately.")
        else:
            pm_immediate = (f"Monitor {country} situation closely. {risk} risk detected for India's {c_str} trade. "
                            f"Alert state agriculture departments in {s_str}.")
            farmer_action = f"Stay updated on {c_str} market prices. Consult local APMC before selling."
            consumer_alert = f"Minor price fluctuations possible for {c_str}. No immediate action needed."
            trader_action = f"Review {country} trade contracts. Consider hedging {c_str} positions."

        return json.dumps({
            "policy_makers": {
                "immediate_72h": pm_immediate,
                "week_1_4": f"Engage diplomatic channels with {country}. Fast-track CEPA with alternative partners. Issue export incentives for {c_str} to ASEAN/Africa.",
                "medium_term": f"Develop 90-day trade diversification plan. Commission APEDA report on {country} dependency. Review MSP for {c_str}.",
            },
            "farmers": {
                "immediate_action": farmer_action,
                "crop_advisory": f"Shift 15–20% acreage from high-risk {commodities[0] if commodities else 'crop'} to lower-risk alternatives with stable domestic demand.",
                "opportunity": "Explore FPO (Farmer Producer Organization) membership for collective bargaining and direct export.",
            },
            "consumers": {
                "price_alert": consumer_alert,
                "advisory": "No panic buying needed. Government buffer stocks are adequate.",
                "outlook_30d": f"Prices stable for 30 days. Monitor {c_str} prices at local market.",
            },
            "traders": {
                "immediate": trader_action,
                "rerouting": f"Explore Vietnam, Indonesia, Nigeria, and Kenya as alternative destinations for {c_str}.",
                "opportunity": "Currency depreciation may improve competitiveness for other Indian agri exports.",
            },
            "summary": (f"{risk} geopolitical risk from {country} {etype.lower()} event. "
                        f"${rev}M trade exposure, {farmers}M farmers in {s_str} potentially affected by {c_str} disruption.")
        })
