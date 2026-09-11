#!/usr/bin/env python3
"""Leave-one-run-out CV for stroller vs non-stroller (small dataset)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from stroller_dashboard.gpx_loader import DEFAULT_ZIP
from stroller_dashboard.ml_activity import load_activity_feature_set


def _eval_model(name: str, pipeline: Pipeline, X, y, groups, activity_ids) -> None:
    logo = LeaveOneGroupOut()
    preds = np.zeros(len(y), dtype=int)
    prob = np.zeros(len(y), dtype=float)

    for train_idx, test_idx in logo.split(X, y, groups=groups):
        pipeline.fit(X[train_idx], y[train_idx])
        preds[test_idx] = pipeline.predict(X[test_idx])
        if hasattr(pipeline, "predict_proba"):
            prob[test_idx] = pipeline.predict_proba(X[test_idx])[:, 1]
        else:
            prob[test_idx] = float(preds[test_idx])

    acc = accuracy_score(y, preds)
    cm = confusion_matrix(y, preds, labels=[0, 1])
    majority = max(y.mean(), 1 - y.mean())
    print(f"\n=== {name} (leave-one-run-out) ===")
    print(f"Runs: {len(y)}  (stroller={y.sum()}, non-stroller={len(y) - y.sum()})")
    print(f"Accuracy: {acc:.1%}  ({int(acc * len(y))}/{len(y)} runs correct)")
    print(f"Majority-class baseline: {majority:.1%}")
    print("Confusion matrix [rows=true 0/1, cols=pred 0/1]:")
    print(cm)
    print("\nPer-run predictions:")
    print(f"{'activity_id':<28} {'true':>6} {'pred':>6} {'p(stroller)':>12}")
    for act_id, yt, yp, p in zip(activity_ids, y, preds, prob):
        label = "str" if yt else "run"
        pred = "str" if yp else "run"
        ok = "ok" if yt == yp else "MISS"
        print(f"{act_id:<28} {label:>6} {pred:>6} {p:>11.2%}  {ok}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Classify stroller vs non-stroller runs using aggregated track-point features."
    )
    parser.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    parser.add_argument(
        "--no-geo",
        action="store_true",
        help="Drop lat/lon from aggregation (pace/HR/cad dynamics only)",
    )
    args = parser.parse_args()

    feature_sets = [
        (True, "with lat/lon"),
        (False, "no lat/lon (dynamics)"),
    ]
    if args.no_geo:
        feature_sets = [feature_sets[1]]

    for include_geo, tag in feature_sets:
        print(f"\n{'#' * 60}\nFeature set: {tag}\n{'#' * 60}")
        data = load_activity_feature_set(args.zip, include_geo=include_geo)
        X, y, groups, activity_ids = data.X, data.y, data.groups, data.activity_ids

        log_reg = Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=2000,
                        class_weight="balanced",
                        random_state=0,
                    ),
                ),
            ]
        )
        rf = RandomForestClassifier(
            n_estimators=200,
            max_depth=4,
            min_samples_leaf=2,
            class_weight="balanced_subsample",
            random_state=0,
        )

        _eval_model("Logistic regression", log_reg, X, y, groups, activity_ids)
        _eval_model("Random forest", rf, X, y, groups, activity_ids)

    if not args.no_geo and len(feature_sets) > 1:
        print(
            "\nCompared both feature sets above. Use --no-geo to run dynamics-only."
        )


if __name__ == "__main__":
    main()
