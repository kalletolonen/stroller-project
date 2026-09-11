# stroller-project

Explore Garmin GPX runs and compare stroller vs non-stroller activities.

## Map dashboard

Requires `gpx_files.zip` in the repo root (GPX files inside the archive). Runs whose filename starts with `str_` are treated as stroller runs.

```bash
pip install -r requirements.txt
streamlit run stroller_dashboard/app.py
```