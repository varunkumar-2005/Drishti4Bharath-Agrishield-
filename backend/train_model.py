#!/usr/bin/env python3
"""
AgroShield XGBoost Risk Model Trainer
Run in Google Colab or locally with your trade_dataset.csv.

Usage:
    python train_model.py --csv data/trade_dataset.csv --out data/
"""

import argparse
import os
import pickle
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score

try:
    import xgboost as xgb
except ImportError:
    print("pip install xgboost")
    raise

# ── Feature columns ────────────────────────────────────────────────────────────
FEATURE_COLS = [
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

TARGET_COL = "risk_label"  # column name for risk classification target


def make_risk_label(df: pd.DataFrame) -> pd.Series:
    """
    If risk_label column is absent, derive it from Effective_Shock + Trade_Share.
    Adjust thresholds to match your dataset distribution.
    """
    if TARGET_COL in df.columns:
        return df[TARGET_COL]

    score = (
        df.get("Effective_Shock", 0) * 15 +
        df.get("Shock_Intensity", 0) * 10 +
        df.get("Trade_Share", 0) * 200 +
        df.get("Conflict_Exposure", 0) * 20 +
        df.get("Net_Hostility", 0).abs() * 5
    ).clip(0, 100)

    labels = pd.cut(score, bins=[-1, 30, 55, 75, 101],
                    labels=["LOW", "MEDIUM", "HIGH", "CRITICAL"])
    return labels


def train(csv_path: str, out_dir: str):
    print(f"Loading dataset: {csv_path}")
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]
    print(f"Shape: {df.shape}")

    # Build target
    df["_target"] = make_risk_label(df)
    df = df.dropna(subset=["_target"])

    # Encode target
    le = LabelEncoder()
    y = le.fit_transform(df["_target"])
    print(f"Classes: {le.classes_} | Distribution: {np.bincount(y)}")

    # Features
    available = [c for c in FEATURE_COLS if c in df.columns]
    X = df[available].fillna(0)
    print(f"Using {len(available)} features")

    # Train / test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42, stratify=y
    )

    # Train XGBoost
    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=7,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="mlogloss",
        n_jobs=-1,
        random_state=42,
    )
    model.fit(X_train, y_train,
              eval_set=[(X_test, y_test)],
              verbose=50)

    # Evaluate
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\nAccuracy: {acc:.4f}")
    print(classification_report(y_test, y_pred, target_names=le.classes_))

    # Save artifacts
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "risk_model.pkl"), "wb") as f:
        pickle.dump(model, f)
    with open(os.path.join(out_dir, "encoders.pkl"), "wb") as f:
        pickle.dump(le, f)
    with open(os.path.join(out_dir, "feature_columns.pkl"), "wb") as f:
        pickle.dump(available, f)

    print(f"\nArtifacts saved to {out_dir}/")
    print("  risk_model.pkl")
    print("  encoders.pkl")
    print("  feature_columns.pkl")
    print("\nUpload to S3: python setup_s3.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="data/trade_dataset.csv")
    parser.add_argument("--out", default="data")
    args = parser.parse_args()
    train(args.csv, args.out)
