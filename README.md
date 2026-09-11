# stroller-project

Explore Garmin GPX runs and compare stroller vs non-stroller activities.

## Map dashboard

Requires `gpx_files.zip` in the repo root (GPX files inside the archive). Runs whose filename starts with `str_` are treated as stroller runs.

```bash
pip install -r requirements.txt
streamlit run stroller_dashboard/app.py
```

## Track-point feature matrix

For stroller inference we use **only GPX track points** (`<trkpt>`): raw fields plus values computed from consecutive points in the same activity. Track metadata (`name`, `type`, `desc`) is not used as features.

| Column | Source |
|--------|--------|
| `lat`, `lon`, `ele_m`, `hr`, `cad` | Each track point |
| `cad_is_zero` | `cad == 0` |
| `elapsed_s` | `time` minus first point time in that activity |
| `dt_s`, `segment_distance_m`, `speed_m_s`, `pace_min_per_km` | Previous → current point |
| `delta_ele_m`, `grade_pct`, `bearing_deg`, `delta_bearing_deg` | Previous → current point |

`is_stroller` is the label (from `str_` filename when loading); `activity_id` and `point_index` are for grouping/splits, not model inputs.

```bash
python3 scripts/export_point_features.py -o data/point_features.csv
```