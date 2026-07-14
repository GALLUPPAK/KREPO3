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

## 1. Push everything to GitHub

```bash
cd mnch_dashboard
git init
git add .
git commit -m "MNCH S-22620 dashboard"
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

Both `data/form.xlsx` (the questionnaire structure) and `data/survey_data.csv` (the
current respondent data) are committed as normal files — nothing is excluded.

## 2. Deploy on Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) → **New app** → point it at
   your repo, branch `main`, main file `app.py`.
2. Deploy. `requirements.txt` and `.streamlit/config.toml` handle the rest — no secrets
   or credentials needed.

## 3. Daily data refresh

Every day, just **overwrite `data/survey_data.csv`** with the latest SurveyCTO "wide"
CSV export (same column layout — new columns are fine too):

```bash
cp /path/to/latest/S-22620_MNCH_FINAL_WIDE.csv data/survey_data.csv
git add data/survey_data.csv
git commit -m "Data refresh $(date +%F)"
git push
```

Or do it straight from the GitHub website: open the `data` folder in your repo →
**Add file → Upload files** → drag in the new `survey_data.csv` → commit. Either way,
Streamlit Cloud redeploys automatically on push, and the app's cache is keyed on the
file's modified-time, so the new numbers appear immediately.

If the XLSForm itself changes (new questions added), replace `data/form.xlsx` the same
way — new questions get their own charts automatically.

## 4. Preview a different file without touching the repo

Open the sidebar **"📡 Data source"** panel in the running app and switch to
**"⬆️ Upload a file to preview"** — pick any CSV with the same column layout. This is
just for a quick look; it doesn't change what's in the repo.

## 5. Project structure

```
app.py                — main Streamlit app: pages, sidebar, KPIs, narrative text
data_utils.py           — XLSForm parsing, choice-label maps, EDP/NDP coalescing engine
charts.py               — generic Plotly chart builders (bar, histogram, donut, map, gauge)
data/form.xlsx           — the SurveyCTO XLSForm (survey/choices/settings) — drives everything
data/survey_data.csv     — the current data export — replace this file to refresh
requirements.txt
.streamlit/config.toml   — Gallup Pakistan navy/red theme
```

## 6. Local testing

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Notes on interpreting this data

Fieldwork is in progress — the bundled export has 44 completed interviews (34 NDP, 10
EDP) across 8 Punjab districts. Several late-questionnaire modules (referral journey,
postnatal follow-up, costing) will fill in as more interviews are completed; charts for
those questions simply won't appear until at least one respondent has answered — they
start rendering automatically as new data arrives, no code change required. Treat all
percentages as descriptive of the current sample, not yet a statistically powered
estimate for Punjab as a whole.

A couple of fields (`ob7`, the `dr_e2_1` family) currently show a few responses labeled
`"Unlisted code (0)"` — these are raw values in the export that fall outside the choice
list defined in the XLSForm, most likely a SurveyCTO skip-logic default leaking through.
Worth flagging to whoever manages the form; the dashboard surfaces it honestly rather
than hiding it.
