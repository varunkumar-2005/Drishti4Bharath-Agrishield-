"""
Agent 3 — Risk Predictor
Uses the trained XGBoost model (loaded from S3) or a calibrated rule-based
fallback to predict risk level (LOW / MEDIUM / HIGH / CRITICAL) and score.
"""

import logging
import os
import pickle
import io
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("agroshield.agent3")

S3_BUCKET = os.getenv("S3_BUCKET", "agroshield-trade-data")
MODEL_KEY = os.getenv("MODEL_KEY", "model-artifacts/risk_model.pkl")
ENCODERS_KEY = os.getenv("ENCODERS_KEY", "model-artifacts/encoders.pkl")
FEATURES_KEY = os.getenv("FEATURES_KEY", "model-artifacts/feature_columns.pkl")

RISK_LABELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

# Feature columns expected by the XGBoost model (matching training)
DEFAULT_FEATURE_COLUMNS = [
    "Shock_Intensity", "Avg_Goldstein", "Avg_Tone", "Total_Mentions",
    "Total_Sources", "Conflict_Event_Count", "Protest_Event_Count",
    "Trade_Shock_Count", "Sanction_Threat_Count", "Incoming_Shock_Count",
    "Outgoing_Shock_Count", "Net_Hostility", "Conflict_Density",
    "Protest_Density", "Trade_Shock_Density", "Trade_Share",
    "Effective_Shock", "Conflict_Exposure", "Protest_Exposure",
    "Trade_Shock_Exposure", "Incoming_Shock_Exposure", "Outgoing_Shock_Exposure",
    "Net_Hostility_Exposure", "MoM_Change_Value", "Rolling_3M_Volatility",
    "Shock_Intensity_Lag1", "Shock_Intensity_Lag2",
    "Trade_Share_Lag1", "Trade_Share_Lag2",
    "Lagged_Effective_Shock_1", "Lagged_Effective_Shock_2",
]


class RiskPredictor:
    def __init__(self):
        self.model = None
        self.encoders = None
        self.feature_columns: List[str] = DEFAULT_FEATURE_COLUMNS
        self._load_model()

    def _load_model(self):
        """Try loading XGBoost model from S3, then local disk."""
        # Try S3
        try:
            import boto3
            s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION", "ap-south-1"))
            model_obj = s3.get_object(Bucket=S3_BUCKET, Key=MODEL_KEY)
            self.model = pickle.loads(model_obj["Body"].read())
            try:
                enc_obj = s3.get_object(Bucket=S3_BUCKET, Key=ENCODERS_KEY)
                self.encoders = pickle.loads(enc_obj["Body"].read())
                feat_obj = s3.get_object(Bucket=S3_BUCKET, Key=FEATURES_KEY)
                self.feature_columns = pickle.loads(feat_obj["Body"].read())
            except Exception:
                pass
            logger.info("XGBoost model loaded from S3")
            return
        except Exception as exc:
            logger.warning("S3 model load failed: %s", exc)

        # Try local
        local_model = os.path.join(os.path.dirname(__file__), "..", "data", "risk_model.pkl")
        if os.path.exists(local_model):
            try:
                with open(local_model, "rb") as f:
                    self.model = pickle.load(f)
                logger.info("XGBoost model loaded from local disk")
                return
            except Exception as exc:
                logger.warning("Local model load failed: %s", exc)

        logger.info("No XGBoost model found — using rule-based fallback")

    def predict(
        self,
        structured_event: Dict[str, Any],
        country_stats: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build feature vector from event + country stats, run prediction.
        Returns: risk_label, risk_score, confidence, probabilities, feature_vector
        """
        features = self._build_features(structured_event, country_stats)

        if self.model is not None:
            return self._ml_predict(features)
        else:
            return self._rule_based_predict(features, structured_event)

    def _build_features(
        self,
        event: Dict[str, Any],
        country_stats: Dict[str, Any],
    ) -> Dict[str, float]:
        """
        Combine event signals with country historical stats to build features
        matching the training dataset columns.
        """
        severity = event.get("severity_pct", 30.0) / 100.0  # normalise to [0,1]
        goldstein = event.get("estimated_goldstein", -2.0)
        avg_tone = event.get("avg_tone", 0.0)
        event_type = event.get("event_type", "GENERAL")

        # Shock multipliers per event type
        shock_multipliers = {
            "CONFLICT":      2.5,
            "SANCTION":      2.0,
            "TARIFF":        1.8,
            "TRADE_POLICY":  1.5,
            "CLIMATE":       1.3,
            "ECONOMIC":      1.2,
            "PROTEST":       1.1,
            "DIPLOMATIC":    0.5,
            "GENERAL":       1.0,
        }
        mult = shock_multipliers.get(event_type, 1.0)

        base_shock = float(country_stats.get("Shock_Intensity", 1.0))
        trade_share = float(country_stats.get("Trade_Share", 0.02))
        base_effective = float(country_stats.get("Effective_Shock", 0.5))
        base_hostility = float(country_stats.get("Net_Hostility", 0.0))
        conflict_exposure = float(country_stats.get("Conflict_Exposure", 0.1))

        # Apply event shock
        event_shock = base_shock * mult * (1.0 + severity)
        effective_shock = base_effective * mult * (1.0 + severity * 0.8)

        fv: Dict[str, float] = {
            "Shock_Intensity": event_shock,
            "Avg_Goldstein": goldstein,
            "Avg_Tone": avg_tone,
            "Total_Mentions": 100.0 * (1 + severity * 5),
            "Total_Sources": 20.0 * (1 + severity * 3),
            "Conflict_Event_Count": 5.0 * mult if event_type == "CONFLICT" else 0.0,
            "Protest_Event_Count": 3.0 if event_type == "PROTEST" else 0.0,
            "Trade_Shock_Count": 4.0 * mult if event_type in ("TARIFF", "SANCTION", "TRADE_POLICY") else 0.0,
            "Sanction_Threat_Count": 3.0 if event_type == "SANCTION" else 0.0,
            "Incoming_Shock_Count": 2.0 * severity,
            "Outgoing_Shock_Count": 2.0 * severity,
            "Net_Hostility": base_hostility + abs(goldstein) * 0.3,
            "Conflict_Density": 0.4 if event_type == "CONFLICT" else 0.1,
            "Protest_Density": 0.2 if event_type == "PROTEST" else 0.05,
            "Trade_Shock_Density": 0.5 * severity if event_type in ("TARIFF", "SANCTION") else 0.1,
            "Trade_Share": trade_share,
            "Effective_Shock": effective_shock,
            "Conflict_Exposure": conflict_exposure * (1.5 if event_type == "CONFLICT" else 1.0),
            "Protest_Exposure": 0.05,
            "Trade_Shock_Exposure": trade_share * severity * mult,
            "Incoming_Shock_Exposure": trade_share * 0.5 * severity,
            "Outgoing_Shock_Exposure": trade_share * 0.5 * severity,
            "Net_Hostility_Exposure": abs(goldstein) * trade_share,
            "MoM_Change_Value": float(country_stats.get("MoM_Change_Value", 0.0)) * (1 - severity * mult * 0.3),
            "Rolling_3M_Volatility": float(country_stats.get("Rolling_3M_Volatility", 0.1)) * mult,
            "Shock_Intensity_Lag1": base_shock,
            "Shock_Intensity_Lag2": base_shock * 0.8,
            "Trade_Share_Lag1": trade_share,
            "Trade_Share_Lag2": trade_share,
            "Lagged_Effective_Shock_1": base_effective,
            "Lagged_Effective_Shock_2": base_effective * 0.7,
        }
        return fv

    def _ml_predict(self, features: Dict[str, float]) -> Dict[str, Any]:
        try:
            cols = self.feature_columns if self.feature_columns else DEFAULT_FEATURE_COLUMNS
            X = np.array([[features.get(c, 0.0) for c in cols]])
            proba = self.model.predict_proba(X)[0]
            pred_class = int(np.argmax(proba))
            risk_label = RISK_LABELS[pred_class] if pred_class < len(RISK_LABELS) else "MEDIUM"
            confidence = float(proba[pred_class])
            risk_score = self._proba_to_score(proba)
            return {
                "risk_label": risk_label,
                "risk_score": risk_score,
                "confidence": round(confidence, 3),
                "probabilities": {
                    "LOW": round(float(proba[0]), 3) if len(proba) > 0 else 0,
                    "MEDIUM": round(float(proba[1]), 3) if len(proba) > 1 else 0,
                    "HIGH": round(float(proba[2]), 3) if len(proba) > 2 else 0,
                    "CRITICAL": round(float(proba[3]), 3) if len(proba) > 3 else 0,
                },
                "model": "xgboost",
                "features_used": features,
            }
        except Exception as exc:
            logger.error("ML predict failed: %s — falling back to rules", exc)
            return self._rule_based_predict(features, {})

    def _rule_based_predict(
        self,
        features: Dict[str, float],
        event: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Calibrated rule-based risk scoring."""
        shock = features.get("Effective_Shock", 0.5)
        goldstein = features.get("Avg_Goldstein", -2.0)
        trade_share = features.get("Trade_Share", 0.02)
        trade_shock_exposure = features.get("Trade_Shock_Exposure", 0.01)
        conflict_exposure = features.get("Conflict_Exposure", 0.1)

        # Weighted composite score
        score = (
            min(shock * 15, 35)
            + min(abs(goldstein) * 3.5, 25)
            + min(trade_share * 200, 20)
            + min(trade_shock_exposure * 300, 15)
            + min(conflict_exposure * 20, 5)
        )
        score = min(int(score), 100)

        if score >= 75:
            label = "CRITICAL"
            proba = {"LOW": 0.02, "MEDIUM": 0.05, "HIGH": 0.15, "CRITICAL": 0.78}
        elif score >= 55:
            label = "HIGH"
            proba = {"LOW": 0.05, "MEDIUM": 0.15, "HIGH": 0.65, "CRITICAL": 0.15}
        elif score >= 35:
            label = "MEDIUM"
            proba = {"LOW": 0.10, "MEDIUM": 0.65, "HIGH": 0.20, "CRITICAL": 0.05}
        else:
            label = "LOW"
            proba = {"LOW": 0.70, "MEDIUM": 0.20, "HIGH": 0.08, "CRITICAL": 0.02}

        return {
            "risk_label": label,
            "risk_score": score,
            "confidence": proba[label],
            "probabilities": proba,
            "model": "rule_based",
            "features_used": features,
        }

    def _proba_to_score(self, proba: np.ndarray) -> int:
        weights = [10, 40, 70, 95]
        score = sum(float(p) * w for p, w in zip(proba, weights[:len(proba)]))
        return min(int(score), 100)
