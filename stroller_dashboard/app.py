"""Streamlit map dashboard for stroller vs non-stroller GPX runs."""

from __future__ import annotations

from pathlib import Path

import folium
import streamlit as st
from streamlit_folium import st_folium

from stroller_dashboard.gpx_loader import (
    DEFAULT_ZIP,
    downsample_coords,
    load_activities_from_zip,
)
from stroller_dashboard.metrics import compute_stats

STROLLER_COLOR = "#e67e22"
REGULAR_COLOR = "#2980b9"

st.set_page_config(
    page_title="Stroller runs · GPX map",
    page_icon="🗺️",
    layout="wide",
)

st.title("GPX run map")
st.caption(
    "Tracks come from `gpx_files.zip`. Files prefixed with `str_` are labeled stroller runs."
)


@st.cache_data(show_spinner="Loading GPX archive…")
def get_activities(zip_path: str):
    return load_activities_from_zip(Path(zip_path))


zip_path = st.sidebar.text_input("GPX zip path", value=str(DEFAULT_ZIP))

try:
    activities = get_activities(zip_path)
except FileNotFoundError as exc:
    st.error(str(exc))
    st.stop()

stroller_runs = [a for a in activities if a.is_stroller]
regular_runs = [a for a in activities if not a.is_stroller]

st.sidebar.markdown("### Filter")
show_stroller = st.sidebar.checkbox("Stroller runs", value=True)
show_regular = st.sidebar.checkbox("Non-stroller runs", value=True)

selected_ids: set[str] = set()
if show_stroller:
    selected_ids.update(a.activity_id for a in stroller_runs)
if show_regular:
    selected_ids.update(a.activity_id for a in regular_runs)

visible = [a for a in activities if a.activity_id in selected_ids]

if not visible:
    st.warning("No activities selected.")
    st.stop()

# Summary metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total activities", len(activities))
col2.metric("Stroller (labeled)", len(stroller_runs))
col3.metric("Non-stroller", len(regular_runs))
col4.metric("On map", len(visible))

# Build map centered on all visible points
all_lats: list[float] = []
all_lons: list[float] = []
for act in visible:
    for p in act.points:
        all_lats.append(p.lat)
        all_lons.append(p.lon)

center_lat = sum(all_lats) / len(all_lats)
center_lon = sum(all_lons) / len(all_lons)

m = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles="OpenStreetMap")

for act in visible:
    coords = downsample_coords(act.points)
    if len(coords) < 2:
        continue
    color = STROLLER_COLOR if act.is_stroller else REGULAR_COLOR
    stats = compute_stats(act)
    pace = stats.pace_min_per_km
    pace_str = f"{pace:.1f} min/km" if pace is not None else "—"
    hr_str = f"{stats.avg_hr:.0f} bpm" if stats.avg_hr is not None else "—"
    popup = (
        f"<b>{act.label}</b><br>"
        f"{act.name}<br>"
        f"Distance: {stats.distance_km:.2f} km<br>"
        f"Pace: {pace_str}<br>"
        f"Avg HR: {hr_str}<br>"
        f"Points: {stats.point_count}"
    )
    folium.PolyLine(
        locations=coords,
        color=color,
        weight=4,
        opacity=0.85,
        popup=folium.Popup(popup, max_width=280),
    ).add_to(m)

legend_html = f"""
<div style="position: fixed; bottom: 24px; left: 24px; z-index: 9999;
     background: white; padding: 10px 14px; border-radius: 8px;
     box-shadow: 0 2px 8px rgba(0,0,0,0.15); font-size: 14px;">
  <div><span style="color:{STROLLER_COLOR}; font-weight:bold;">━━</span> Stroller (str_ prefix)</div>
  <div><span style="color:{REGULAR_COLOR}; font-weight:bold;">━━</span> Non-stroller</div>
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

st_folium(m, width=None, height=520, returned_objects=[])

st.subheader("Activities")
rows = []
for act in activities:
    stats = compute_stats(act)
    pace = stats.pace_min_per_km
    rows.append(
        {
            "Stroller": act.is_stroller,
            "Start": act.start_time.strftime("%Y-%m-%d %H:%M")
            if act.start_time
            else "",
            "Name": act.name,
            "Distance (km)": round(stats.distance_km, 2),
            "Pace (min/km)": round(pace, 2) if pace is not None else None,
            "Avg HR": round(stats.avg_hr) if stats.avg_hr is not None else None,
            "Avg cadence": round(stats.avg_cad)
            if stats.avg_cad is not None
            else None,
            "File": act.filename,
        }
    )

st.dataframe(rows, use_container_width=True, hide_index=True)
