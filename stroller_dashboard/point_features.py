"""Track-point feature matrix (one row per GPX trkpt).

Features use only per-point fields (lat, lon, ele, time, hr, cad) and values
derived from consecutive points within the same activity. Track-level metadata
(name, type, desc) and zip filenames are not feature columns.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from stroller_dashboard.gpx_loader import Activity, TrackPoint, load_activities_from_zip
from stroller_dashboard.metrics import haversine_m

# Model inputs: track-point stream only (no activity metadata).
POINT_FEATURE_COLUMNS: tuple[str, ...] = (
    "lat",
    "lon",
    "ele_m",
    "hr",
    "cad",
    "cad_is_zero",
    "elapsed_s",
    "dt_s",
    "segment_distance_m",
    "speed_m_s",
    "pace_min_per_km",
    "delta_ele_m",
    "grade_pct",
    "bearing_deg",
    "delta_bearing_deg",
)

# Grouping / supervision (not part of X).
META_COLUMNS: tuple[str, ...] = (
    "activity_id",
    "point_index",
    "time_utc",
    "is_stroller",
)


def _bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlon) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(
        dlon
    )
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def _delta_bearing(a: float, b: float) -> float:
    d = (b - a + 180) % 360 - 180
    return d


@dataclass(frozen=True)
class PointFeatureRow:
    activity_id: str
    point_index: int
    time_utc: datetime | None
    is_stroller: bool
    lat: float
    lon: float
    ele_m: float | None
    hr: int | None
    cad: int | None
    cad_is_zero: bool | None
    elapsed_s: float | None
    dt_s: float | None
    segment_distance_m: float | None
    speed_m_s: float | None
    pace_min_per_km: float | None
    delta_ele_m: float | None
    grade_pct: float | None
    bearing_deg: float | None
    delta_bearing_deg: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "activity_id": self.activity_id,
            "point_index": self.point_index,
            "time_utc": self.time_utc.isoformat() if self.time_utc else "",
            "is_stroller": self.is_stroller,
            "lat": self.lat,
            "lon": self.lon,
            "ele_m": self.ele_m,
            "hr": self.hr,
            "cad": self.cad,
            "cad_is_zero": self.cad_is_zero,
            "elapsed_s": self.elapsed_s,
            "dt_s": self.dt_s,
            "segment_distance_m": self.segment_distance_m,
            "speed_m_s": self.speed_m_s,
            "pace_min_per_km": self.pace_min_per_km,
            "delta_ele_m": self.delta_ele_m,
            "grade_pct": self.grade_pct,
            "bearing_deg": self.bearing_deg,
            "delta_bearing_deg": self.delta_bearing_deg,
        }


def build_point_rows(activity: Activity) -> list[PointFeatureRow]:
    points = activity.points
    if not points:
        return []

    t0 = points[0].time
    rows: list[PointFeatureRow] = []
    prev_bearing: float | None = None

    for i, pt in enumerate(points):
        elapsed_s: float | None = None
        if t0 and pt.time:
            elapsed_s = (pt.time - t0).total_seconds()

        cad_is_zero: bool | None = None
        if pt.cad is not None:
            cad_is_zero = pt.cad == 0

        if i == 0:
            rows.append(
                PointFeatureRow(
                    activity_id=activity.activity_id,
                    point_index=i,
                    time_utc=pt.time,
                    is_stroller=activity.is_stroller,
                    lat=pt.lat,
                    lon=pt.lon,
                    ele_m=pt.ele,
                    hr=pt.hr,
                    cad=pt.cad,
                    cad_is_zero=cad_is_zero,
                    elapsed_s=elapsed_s,
                    dt_s=None,
                    segment_distance_m=None,
                    speed_m_s=None,
                    pace_min_per_km=None,
                    delta_ele_m=None,
                    grade_pct=None,
                    bearing_deg=None,
                    delta_bearing_deg=None,
                )
            )
            continue

        prev = points[i - 1]
        dt_s: float | None = None
        if prev.time and pt.time:
            dt_s = (pt.time - prev.time).total_seconds()

        seg_m = haversine_m(prev.lat, prev.lon, pt.lat, pt.lon)
        speed_m_s: float | None = None
        pace: float | None = None
        if dt_s and dt_s > 0:
            speed_m_s = seg_m / dt_s
            if seg_m > 0:
                pace = (dt_s / 60) / (seg_m / 1000)

        delta_ele: float | None = None
        grade: float | None = None
        if prev.ele is not None and pt.ele is not None:
            delta_ele = pt.ele - prev.ele
            if seg_m > 0:
                grade = 100 * delta_ele / seg_m

        bearing = _bearing_deg(prev.lat, prev.lon, pt.lat, pt.lon)
        delta_br = (
            _delta_bearing(prev_bearing, bearing) if prev_bearing is not None else None
        )
        prev_bearing = bearing

        rows.append(
            PointFeatureRow(
                activity_id=activity.activity_id,
                point_index=i,
                time_utc=pt.time,
                is_stroller=activity.is_stroller,
                lat=pt.lat,
                lon=pt.lon,
                ele_m=pt.ele,
                hr=pt.hr,
                cad=pt.cad,
                cad_is_zero=cad_is_zero,
                elapsed_s=elapsed_s,
                dt_s=dt_s,
                segment_distance_m=seg_m,
                speed_m_s=speed_m_s,
                pace_min_per_km=pace,
                delta_ele_m=delta_ele,
                grade_pct=grade,
                bearing_deg=bearing,
                delta_bearing_deg=delta_br,
            )
        )

    return rows


def build_point_matrix(
    activities: Iterable[Activity],
) -> list[PointFeatureRow]:
    rows: list[PointFeatureRow] = []
    for activity in activities:
        rows.extend(build_point_rows(activity))
    return rows


def write_point_matrix_csv(path: Path, zip_path: Path | None = None) -> int:
    activities = load_activities_from_zip(zip_path)
    rows = build_point_matrix(activities)
    fieldnames = list(META_COLUMNS) + list(POINT_FEATURE_COLUMNS)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_dict())
    return len(rows)
