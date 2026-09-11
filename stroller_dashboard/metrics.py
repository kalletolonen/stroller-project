"""Simple activity metrics from track points."""

from __future__ import annotations

import math
from dataclasses import dataclass

from stroller_dashboard.gpx_loader import Activity, TrackPoint

EARTH_RADIUS_M = 6_371_000


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


@dataclass
class ActivityStats:
    distance_km: float
    duration_s: float | None
    avg_hr: float | None
    avg_cad: float | None
    point_count: int

    @property
    def pace_min_per_km(self) -> float | None:
        if self.duration_s is None or self.distance_km <= 0:
            return None
        return (self.duration_s / 60) / self.distance_km


def compute_stats(activity: Activity) -> ActivityStats:
    points = activity.points
    distance_m = 0.0
    for i in range(1, len(points)):
        a, b = points[i - 1], points[i]
        distance_m += haversine_m(a.lat, a.lon, b.lat, b.lon)

    duration_s: float | None = None
    if points and points[0].time and points[-1].time:
        duration_s = (points[-1].time - points[0].time).total_seconds()

    hrs = [p.hr for p in points if p.hr is not None]
    cads = [p.cad for p in points if p.cad is not None and p.cad > 0]

    return ActivityStats(
        distance_km=distance_m / 1000,
        duration_s=duration_s,
        avg_hr=sum(hrs) / len(hrs) if hrs else None,
        avg_cad=sum(cads) / len(cads) if cads else None,
        point_count=len(points),
    )
