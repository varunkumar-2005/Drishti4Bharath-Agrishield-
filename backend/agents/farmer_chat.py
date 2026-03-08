"""
Farmer Chat Assistant
Interactive crop and market guidance for farmers using Bedrock with fallback.
"""

import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3

logger = logging.getLogger("agroshield.farmer_chat")

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
BEDROCK_MODEL = os.getenv("FARMER_CHAT_MODEL", os.getenv("BEDROCK_MODEL", "amazon.nova-lite-v1:0"))
MAX_TOKENS = int(os.getenv("FARMER_CHAT_MAX_TOKENS", "600"))
MIN_QUESTION_CHARS = int(os.getenv("FARMER_CHAT_MIN_QUESTION_CHARS", "5"))
AGRI_INTENT_KEYWORDS = {
    "crop", "crops", "sow", "seed", "plant", "harvest", "mandi", "price", "prices",
    "fertilizer", "fertiliser", "pesticide", "irrigation", "kharif", "rabi", "season",
    "wheat", "rice", "cotton", "maize", "pulses", "soybean", "onion", "sugar",
    "acre", "yield", "farmer", "farming", "agri", "agriculture", "export", "import",
}
SMALL_TALK_TOKENS = {
    "hi", "hello", "hey", "i am human", "who are you", "how are you", "thanks", "thank you",
}


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
        trade_facts: Optional[List[Dict[str, Any]]] = None,
        crop_risk_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        clean_question = self._normalise_question(question)
        if self._is_low_signal_query(clean_question):
            return {
                "answer": self._clarification_response(state, crop, season),
                "model_used": "guardrail",
                "generated_at": datetime.utcnow().isoformat() + "Z",
            }

        intent = self._detect_intent(clean_question)
        if intent == "chat" and self._is_small_talk(clean_question):
            return {
                "answer": (
                    "Hello. I am your AgroShield assistant. "
                    "Ask me a specific farming question like: "
                    "'Is it safe to sow wheat in Karnataka this season?'"
                ),
                "model_used": "chat_guardrail",
                "generated_at": datetime.utcnow().isoformat() + "Z",
            }

        if intent == "chat":
            prompt = self._build_chat_prompt(clean_question, state, crop, season)
        else:
            response_style = self._detect_response_style(clean_question)
            prompt = self._build_agri_prompt(
                question=clean_question,
                state=state,
                crop=crop,
                season=season,
                advisories=advisories,
                events=events,
                commodity_stats=commodity_stats,
                trade_facts=trade_facts or [],
                crop_risk_context=crop_risk_context or {},
                response_style=response_style,
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
            text = (
                self._fallback_chat_response(clean_question, state, crop, season)
                if intent == "chat"
                else self._fallback_response(
                    clean_question,
                    state,
                    crop,
                    season,
                    events,
                    crop_risk_context or {},
                )
            )

        return {
            "answer": text,
            "model_used": model_used,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }

    def _build_agri_prompt(
        self,
        question: str,
        state: Optional[str],
        crop: Optional[str],
        season: Optional[str],
        advisories: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        commodity_stats: List[Dict[str, Any]],
        trade_facts: List[Dict[str, Any]],
        crop_risk_context: Dict[str, Any],
        response_style: str,
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
If the question is vague or missing intent, ask one concise clarifying question instead of generating full advice.
Do not fabricate location/crop details that were not provided.

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

Crop risk context from agent/model outputs (authoritative for crop risk):
{json.dumps(crop_risk_context, ensure_ascii=False)}

Trade facts (authoritative, use these for numeric claims):
{json.dumps(trade_facts[:5], ensure_ascii=False)}

Rules:
- Use numbers only if they exist in Trade facts above.
- Use crop risk labels and risk scores only from Crop risk context above.
- If asked about a crop and that crop appears in Crop risk context, explicitly state that crop's risk label and risk score.
- If trade facts are empty or insufficient, say "data unavailable for this crop/country" for numeric parts.
- Do not fabricate percentages, prices, or exposure values.
- Response style = {response_style}
- If response style is "structured", return exactly:
  1) What to do this week
  2) What to plant/avoid
  3) Price and risk outlook (next 30 days)
  4) One backup plan
- If response style is "direct", answer naturally like a real assistant in 4-8 lines focused on the user's exact question.
- For direct mode, do not force section headers unless user explicitly asks for sections.

Always end with a short line: "Supporting trade statistics used: ..."
"""

    def _build_chat_prompt(
        self,
        question: str,
        state: Optional[str],
        crop: Optional[str],
        season: Optional[str],
    ) -> str:
        return f"""You are AgroShield assistant.
Respond naturally like a helpful chat assistant in 2-5 lines.
Do not force structured farming advisory format unless the user asks about farming decisions.
If useful, ask one clarifying question.

Known context:
- State: {state or "Not specified"}
- Crop: {crop or "Not specified"}
- Season: {season or "Not specified"}

User message: {question}
"""

    def _normalise_question(self, question: str) -> str:
        return re.sub(r"\s+", " ", (question or "")).strip()

    def _is_low_signal_query(self, question: str) -> bool:
        if len(question) < MIN_QUESTION_CHARS:
            return True
        lowered = question.lower()
        low_signal_tokens = {
            "t", "ok", "okay", "hmm", "h", "hello", "hi", "test",
            "yes", "no", "k", "?", ".", "..", "...",
        }
        if lowered in low_signal_tokens:
            return True
        if len(re.findall(r"[a-zA-Z0-9]", lowered)) < 3:
            return True
        return False

    def _detect_intent(self, question: str) -> str:
        lowered = question.lower()
        if any(token in lowered for token in AGRI_INTENT_KEYWORDS):
            return "agri"
        return "chat"

    def _is_small_talk(self, question: str) -> bool:
        lowered = question.lower().strip()
        if lowered in SMALL_TALK_TOKENS:
            return True
        return len(lowered.split()) <= 4 and lowered in {"i am human", "i am a human", "just checking"}

    def _detect_response_style(self, question: str) -> str:
        q = question.lower()
        structured_markers = [
            "what to do this week",
            "what to plant",
            "plant/avoid",
            "price and risk outlook",
            "backup plan",
            "advisory",
            "plan for",
            "step by step",
        ]
        if any(marker in q for marker in structured_markers):
            return "structured"
        if q.count("?") >= 1 and len(q.split()) <= 25:
            return "direct"
        return "direct"

    def _clarification_response(
        self,
        state: Optional[str],
        crop: Optional[str],
        season: Optional[str],
    ) -> str:
        return (
            "Please ask a specific farming question so I can give useful advice. "
            "Example: 'Is it safe to sow wheat in Karnataka this Kharif, and what is the 30-day price outlook?' "
            f"Current context: state={state or 'not set'}, crop={crop or 'not set'}, season={season or 'not set'}."
        )

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
        crop_risk_context: Dict[str, Any],
    ) -> str:
        top = crop_risk_context.get("query_crop_risk")
        if not top:
            top_risks = crop_risk_context.get("top_crop_risks", [])
            top = top_risks[0] if top_risks else None
        risk = str((top or {}).get("risk_label") or (events[0].get("risk_label") if events else "MEDIUM"))
        score = (top or {}).get("risk_score")
        crop_name = (top or {}).get("crop") or crop or "your crop"
        risk_text = f"{risk}" + (f" ({score}/100)" if score is not None else "")
        return (
            f"For {state or 'your region'} and {season or 'this season'}: "
            f"continue diversified cropping, avoid overexposure to one export-linked crop, "
            f"and monitor mandi prices weekly. For {crop_name}, keep 20-30% output "
            f"for staggered selling. Current geopolitical risk is {risk_text}. "
            f"If volatility rises, shift part of acreage to pulses/coarse grains as backup."
        )

    def _fallback_chat_response(
        self,
        question: str,
        state: Optional[str],
        crop: Optional[str],
        season: Optional[str],
    ) -> str:
        return (
            "I can help with both general questions and farming guidance. "
            "If you want crop advice, include crop/state/season for better accuracy."
        )
