#!/usr/bin/env python3
"""Export track-point feature matrix CSV from gpx_files.zip."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from stroller_dashboard.gpx_loader import DEFAULT_ZIP
from stroller_dashboard.point_features import (
    META_COLUMNS,
    POINT_FEATURE_COLUMNS,
    write_point_matrix_csv,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export one row per GPX track point (features from trkpt stream only)."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("data/point_features.csv"),
        help="Output CSV path",
    )
    parser.add_argument(
        "--zip",
        type=Path,
        default=DEFAULT_ZIP,
        help="Path to gpx_files.zip",
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    n = write_point_matrix_csv(args.output, args.zip)
    print(f"Wrote {n} rows to {args.output}")
    print(f"Feature columns ({len(POINT_FEATURE_COLUMNS)}): {', '.join(POINT_FEATURE_COLUMNS)}")
    print(f"Meta/label columns: {', '.join(META_COLUMNS)}")


if __name__ == "__main__":
    main()
