"""Load and parse GPX activities from the project zip archive."""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import gpxpy
import gpxpy.gpx

DEFAULT_ZIP = Path(__file__).resolve().parent.parent / "gpx_files.zip"
STROLLER_PREFIX = "str_"


@dataclass(frozen=True)
class TrackPoint:
    lat: float
    lon: float
    ele: float | None
    time: datetime | None
    hr: int | None
    cad: int | None


@dataclass
class Activity:
    activity_id: str
    filename: str
    name: str
    is_stroller: bool
    start_time: datetime | None
    points: list[TrackPoint]

    @property
    def label(self) -> str:
        tag = "Stroller" if self.is_stroller else "No stroller"
        if self.start_time:
            return f"{self.start_time.strftime('%Y-%m-%d %H:%M')} · {tag}"
        return f"{self.activity_id} · {tag}"


def _hr_cad_from_extensions(extensions) -> tuple[int | None, int | None]:
    if extensions is None:
        return None, None
    hr, cad = None, None
    for ext in extensions:
        for child in ext:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag == "hr" and child.text:
                hr = int(float(child.text))
            elif tag == "cad" and child.text:
                cad = int(float(child.text))
    return hr, cad


def parse_gpx_bytes(data: bytes, filename: str) -> Activity:
    gpx = gpxpy.parse(io.BytesIO(data))
    activity_id = Path(filename).stem
    if activity_id.startswith(STROLLER_PREFIX):
        activity_id = activity_id[len(STROLLER_PREFIX) :]

    name = "Unknown"
    start_time: datetime | None = None
    if gpx.tracks:
        name = gpx.tracks[0].name or name

    if gpx.time:
        start_time = gpx.time

    points: list[TrackPoint] = []
    for track in gpx.tracks:
        for segment in track.segments:
            for pt in segment.points:
                hr, cad = _hr_cad_from_extensions(pt.extensions)
                points.append(
                    TrackPoint(
                        lat=pt.latitude,
                        lon=pt.longitude,
                        ele=pt.elevation,
                        time=pt.time,
                        hr=hr,
                        cad=cad,
                    )
                )

    is_stroller = Path(filename).name.startswith(STROLLER_PREFIX)
    return Activity(
        activity_id=activity_id,
        filename=filename,
        name=name,
        is_stroller=is_stroller,
        start_time=start_time,
        points=points,
    )


def load_activities_from_zip(zip_path: Path | None = None) -> list[Activity]:
    path = zip_path or DEFAULT_ZIP
    if not path.is_file():
        raise FileNotFoundError(f"GPX archive not found: {path}")

    activities: list[Activity] = []
    with zipfile.ZipFile(path, "r") as zf:
        for name in sorted(zf.namelist()):
            if not name.lower().endswith(".gpx"):
                continue
            raw = zf.read(name)
            base = Path(name).name
            activities.append(parse_gpx_bytes(raw, base))

    activities.sort(
        key=lambda a: a.start_time or datetime.min,
        reverse=True,
    )
    return activities


def downsample_coords(
    points: list[TrackPoint], max_points: int = 800
) -> list[tuple[float, float]]:
    if len(points) <= max_points:
        return [(p.lat, p.lon) for p in points]
    step = max(1, len(points) // max_points)
    return [(points[i].lat, points[i].lon) for i in range(0, len(points), step)]
