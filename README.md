# National AI Hub for MNCH — Punjab Mapping (S-22620) Dashboard

Story-style Streamlit + Plotly analytics dashboard for Gallup Pakistan / GPDA, built for
the S-22620 MNCH study (Emergency Delivery Pathway / Normal Delivery Pathway).

- **20 pages, 400+ charts** — every select-one, select-multiple and numeric question in
  the XLSForm gets its own chart automatically, organised into the Three Delays framework
  (recognition → journey → facility care) plus a full Digital Readiness chapter.
- **Fully data-driven.** Nothing about specific questions is hardcoded — the app reads
  `data/form.xlsx` (the XLSForm) to know what questions exist, their choice labels, and
  which module/page each belongs to. Add rows to the data or new questions to the form
  and the dashboard adapts without a code change.
- **EDP/NDP aware.** Where the Emergency and Normal pathways ask the "same" question
  under two different SurveyCTO variable names (e.g. `wb1_age_EDP` / `wb1_age_NDP`), the
  app automatically merges them into a single chart using each respondent's `protocol`.

## 1. Deploy on Streamlit Community Cloud

1. Push this whole folder to a GitHub repo (public or private).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app** → point it at
   this repo, branch `main`, main file `app.py`.
3. Deploy. That's it — `requirements.txt` and `.streamlit/config.toml` handle the rest.

## 2. Daily data refresh (the simple way)

Every day, just **overwrite `data/survey_data.csv`** in the repo with the latest
SurveyCTO "wide" CSV export (same column layout — new columns are fine too) and push
to GitHub:

```bash
cp /path/to/latest/S-22620_MNCH_FINAL_WIDE.csv data/survey_data.csv
git add data/survey_data.csv
git commit -m "Data refresh $(date +%F)"
git push
```

Streamlit Cloud redeploys automatically on push, and the app's cache is keyed on the
file's modified-time, so the new numbers appear immediately — no code change needed,
even as the row count grows from 44 to 4,000.

If the XLSForm itself changes (new questions added), replace `data/form.xlsx` the same
way — new questions will get their own charts automatically.

## 3. Live SurveyCTO server (the automatic way)

Instead of manually replacing the CSV, you can pull live from the SurveyCTO API:

1. In the Streamlit Cloud app → **Settings → Secrets**, paste (see
   `.streamlit/secrets.toml.example` for the exact format):
   ```toml
   [surveycto]
   server   = "your-server-name"
   form_id  = "S-22620_MNCH_FINAL"
   username = "your-surveycto-username"
   password = "your-surveycto-password-or-api-key"
   ```
2. In the running app, open the sidebar **"📡 Data source"** panel and tick
   **"Live SurveyCTO server"**. Data refreshes from the API every 5 minutes.
3. If the live pull ever fails (bad credentials, server hiccup), the app automatically
   falls back to the bundled `data/survey_data.csv` and shows an error in the sidebar —
   it never crashes the dashboard.

You can also preview any other export ad hoc via the **file uploader** in the same
sidebar panel, without touching the repo file.

## 4. Project structure

```
app.py            — main Streamlit app: pages, sidebar, KPIs, narrative text
data_utils.py      — XLSForm parsing, choice-label maps, EDP/NDP coalescing engine
charts.py          — generic Plotly chart builders (bar, histogram, donut, map, gauge)
data/form.xlsx      — the SurveyCTO XLSForm (survey/choices/settings) — drives everything
data/survey_data.csv— the current data export (replace this file daily)
requirements.txt
.streamlit/config.toml           — Gallup Pakistan navy/red theme
.streamlit/secrets.toml.example  — template for live SurveyCTO credentials
```

## 5. Local testing

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Notes on interpreting this data

Fieldwork is in progress — the bundled export has 44 completed interviews (34 NDP, 10
EDP) across 8 Punjab districts. Several late-questionnaire modules (referral journey,
postnatal follow-up, costing) will fill in as more interviews are completed; charts for
those questions simply won't appear until at least one respondent has answered — they
will start rendering automatically as new data arrives, with no code change required.
Treat all percentages as descriptive of the current sample, not yet as a statistically
powered estimate for Punjab as a whole.
