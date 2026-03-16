"""
train.py — Standalone script to train and save the investment scoring ML classifier.
IMPORTANT: Run this script locally BEFORE executing docker-compose up.
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import xgboost as xgb
import joblib

RANDOM_STATE = 42
N_SAMPLES = 500


def generate_synthetic_dataset(n: int = N_SAMPLES) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_STATE)

    revenue_growth_pct = rng.normal(loc=12.0, scale=15.0, size=n)
    ebitda_margin = rng.normal(loc=18.0, scale=8.0, size=n)
    debt_to_equity = rng.exponential(scale=0.8, size=n)
    market_size_bn = rng.uniform(1.0, 50.0, size=n)
    founding_year = rng.integers(1985, 2023, size=n)
    team_size = rng.integers(10, 1000, size=n)

    df = pd.DataFrame(
        {
            "revenue_growth_pct": revenue_growth_pct,
            "ebitda_margin": ebitda_margin,
            "debt_to_equity": debt_to_equity,
            "market_size_bn": market_size_bn,
            "founding_year": founding_year,
            "team_size": team_size,
        }
    )

    # Derive labels based on composite scoring rules
    score = (
        (df["revenue_growth_pct"] > 15).astype(int) * 2
        + (df["ebitda_margin"] > 20).astype(int) * 2
        + (df["debt_to_equity"] < 0.5).astype(int)
        + (df["market_size_bn"] > 10).astype(int)
        + (df["team_size"] > 100).astype(int)
        + rng.integers(0, 2, size=n)  # small stochastic noise
    )

    # Map composite score to 3-class label: 0=Pass, 1=Consider, 2=Strong Buy
    labels = pd.cut(score, bins=[-1, 2, 4, 10], labels=[0, 1, 2]).astype(int)
    df["label"] = labels

    return df


def train_and_save():
    print("Generating synthetic dataset …")
    df = generate_synthetic_dataset()

    feature_cols = [
        "revenue_growth_pct",
        "ebitda_margin",
        "debt_to_equity",
        "market_size_bn",
        "founding_year",
        "team_size",
    ]
    X = df[feature_cols]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )

    print(f"Training on {len(X_train)} samples, evaluating on {len(X_test)} samples …")

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="mlogloss",
        random_state=RANDOM_STATE,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    print(f"\nOverall Accuracy: {acc:.4f}")
    print("\nClassification Report:")
    print(
        classification_report(
            y_test,
            y_pred,
            target_names=["Pass", "Consider", "Strong Buy"],
        )
    )

    joblib.dump(model, "model.pkl")
    print("\nModel saved to model.pkl")


if __name__ == "__main__":
    train_and_save()
