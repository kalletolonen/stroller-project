"""Per-activity stroller classification from track-point features."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from stroller_dashboard.gpx_loader import load_activities_from_zip
from stroller_dashboard.point_features import (
    POINT_FEATURE_COLUMNS,
    PointFeatureRow,
    build_point_matrix,
)

STAT_SUFFIXES = ("mean", "std", "min", "max", "median")


@dataclass(frozen=True)
class ActivityFeatureSet:
    activity_ids: list[str]
    y: np.ndarray
    X: np.ndarray
    feature_names: list[str]
    groups: np.ndarray


def _row_to_feature_dict(row: PointFeatureRow) -> dict[str, float | None]:
    d = row.to_dict()
    out: dict[str, float | None] = {}
    for col in POINT_FEATURE_COLUMNS:
        val = d.get(col)
        if col == "cad_is_zero":
            out[col] = None if val is None or val == "" else float(bool(val))
        elif val is None or val == "":
            out[col] = None
        else:
            out[col] = float(val)
    return out


def aggregate_points_to_activities(
    rows: Iterable[PointFeatureRow],
    *,
    include_geo: bool = True,
) -> ActivityFeatureSet:
    columns = list(POINT_FEATURE_COLUMNS)
    if not include_geo:
        columns = [c for c in columns if c not in ("lat", "lon")]

    by_activity: dict[str, list[dict[str, float | None]]] = defaultdict(list)
    labels: dict[str, bool] = {}

    for row in rows:
        labels[row.activity_id] = row.is_stroller
        by_activity[row.activity_id].append(_row_to_feature_dict(row))

    feature_names: list[str] = []
    for col in columns:
        for suffix in STAT_SUFFIXES:
            feature_names.append(f"{col}_{suffix}")

    activity_ids = sorted(by_activity.keys())
    X_rows: list[list[float]] = []
    y: list[int] = []

    for act_id in activity_ids:
        points = by_activity[act_id]
        y.append(int(labels[act_id]))
        feats: list[float] = []
        for col in columns:
            vals = np.array(
                [p[col] for p in points if p[col] is not None],
                dtype=float,
            )
            if vals.size == 0:
                stats = [0.0] * len(STAT_SUFFIXES)
            else:
                stats = [
                    float(np.mean(vals)),
                    float(np.std(vals)),
                    float(np.min(vals)),
                    float(np.max(vals)),
                    float(np.median(vals)),
                ]
            feats.extend(stats)
        X_rows.append(feats)

    X = np.array(X_rows, dtype=float)
    groups = np.array(activity_ids)
    return ActivityFeatureSet(
        activity_ids=activity_ids,
        y=np.array(y, dtype=int),
        X=X,
        feature_names=feature_names,
        groups=groups,
    )


def load_activity_feature_set(
    zip_path=None,
    *,
    include_geo: bool = True,
) -> ActivityFeatureSet:
    activities = load_activities_from_zip(zip_path)
    rows = build_point_matrix(activities)
    return aggregate_points_to_activities(rows, include_geo=include_geo)
