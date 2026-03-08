"""
Farmer Chat Assistant
Interactive crop and market guidance for farmers using Bedrock with fallback.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3

logger = logging.getLogger("agroshield.farmer_chat")

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
BEDROCK_MODEL = os.getenv("FARMER_CHAT_MODEL", os.getenv("BEDROCK_MODEL", "amazon.nova-lite-v1:0"))
MAX_TOKENS = int(os.getenv("FARMER_CHAT_MAX_TOKENS", "600"))


class FarmerChatAssistant:
    def __init__(self):
        self._client = None
        self._init_client()

    def _init_client(self):
        try:
            self._client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
            logger.info("Farmer chat client initialised (model: %s)", BEDROCK_MODEL)
        except Exception as exc:
            logger.warning("Farmer chat init failed: %s", exc)

    async def respond(
        self,
        question: str,
        state: Optional[str],
        crop: Optional[str],
        season: Optional[str],
        advisories: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        commodity_stats: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        prompt = self._build_prompt(
            question=question,
            state=state,
            crop=crop,
            season=season,
            advisories=advisories,
            events=events,
            commodity_stats=commodity_stats,
        )

        text = ""
        model_used = "rule_based"
        if self._client:
            try:
                text = self._invoke_bedrock(BEDROCK_MODEL, prompt)
                model_used = BEDROCK_MODEL
            except Exception as exc:
                logger.warning("Farmer chat Bedrock failed: %s", exc)

        if not text:
            text = self._fallback_response(question, state, crop, season, events)

        return {
            "answer": text,
            "model_used": model_used,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }

    def _build_prompt(
        self,
        question: str,
        state: Optional[str],
        crop: Optional[str],
        season: Optional[str],
        advisories: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        commodity_stats: List[Dict[str, Any]],
    ) -> str:
        latest_events = [
            {
                "headline": e.get("headline"),
                "risk_label": e.get("risk_label"),
                "affected_commodities": e.get("affected_commodities", []),
                "affected_states": e.get("impact_affected_states", []),
            }
            for e in events[:5]
        ]
        latest_adv = [
            {
                "risk_label": a.get("risk_label"),
                "farmers": a.get("farmers", {}),
                "affected_commodities": a.get("affected_commodities", []),
                "affected_states": a.get("affected_states", []),
            }
            for a in advisories[:3]
        ]

        return f"""You are an agriculture advisor for Indian farmers.
Give practical, short, clear recommendations with direct actions.

Farmer context:
- State: {state or "Not specified"}
- Crop: {crop or "Not specified"}
- Season: {season or "Not specified"}
- Question: {question}

Latest risk events:
{json.dumps(latest_events, ensure_ascii=False)}

Latest farmer advisories:
{json.dumps(latest_adv, ensure_ascii=False)}

Commodity stats snapshot:
{json.dumps(commodity_stats[:5], ensure_ascii=False)}

Return plain text with:
1) What to do this week
2) What to plant/avoid
3) Price and risk outlook (next 30 days)
4) One backup plan
"""

    def _invoke_bedrock(self, model_id: str, prompt: str) -> str:
        if "amazon.nova" in model_id:
            body = json.dumps({
                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                "inferenceConfig": {"maxTokens": MAX_TOKENS, "temperature": 0.2},
            })
        elif "anthropic" in model_id:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": MAX_TOKENS,
                "messages": [{"role": "user", "content": prompt}],
            })
        else:
            body = json.dumps({
                "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
                "max_tokens_to_sample": MAX_TOKENS,
                "temperature": 0.2,
            })

        response = self._client.invoke_model(
            modelId=model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(response["body"].read())

        if "output" in result and "message" in result["output"]:
            content = result["output"]["message"].get("content", [])
            if isinstance(content, list) and content:
                return content[0].get("text", "")
        if "content" in result and isinstance(result["content"], list) and result["content"]:
            return result["content"][0].get("text", "")
        if "completion" in result:
            return result["completion"]
        return json.dumps(result)

    def _fallback_response(
        self,
        question: str,
        state: Optional[str],
        crop: Optional[str],
        season: Optional[str],
        events: List[Dict[str, Any]],
    ) -> str:
        risk = "MEDIUM"
        if events:
            risk = events[0].get("risk_label", "MEDIUM")
        return (
            f"For {state or 'your region'} and {season or 'this season'}: "
            f"continue diversified cropping, avoid overexposure to one export-linked crop, "
            f"and monitor mandi prices weekly. For {crop or 'your crop'}, keep 20-30% output "
            f"for staggered selling. Current geopolitical risk is {risk}. "
            f"If volatility rises, shift part of acreage to pulses/coarse grains as backup."
        )
