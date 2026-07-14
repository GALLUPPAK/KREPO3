# National AI Hub for MNCH — Punjab Mapping (S-22620) Dashboard

Story-style Streamlit + Plotly analytics dashboard for Gallup Pakistan / GPDA, built for
the S-22620 MNCH study (Emergency Delivery Pathway / Normal Delivery Pathway).

- **20 pages, 400+ charts** — every select-one, select-multiple and numeric question in
  the XLSForm gets its own chart automatically, organised into the Three Delays framework
  (recognition → journey → facility care) plus a full Digital Readiness chapter.
- **Fully data-driven.** Nothing about specific questions is hardcoded — the app reads
  `data/form.xlsx` (the XLSForm) to know what questions exist, their choice labels, and
  which module/page each belongs to.
- **EDP/NDP aware.** Where the Emergency and Normal pathways ask the "same" question
  under two different SurveyCTO variable names, the app automatically merges them into
  a single chart using each respondent's `protocol`.
- **Respondent data stays private.** The CSV of actual interviews is never committed to
  GitHub — it's pulled at runtime from a **private Hugging Face dataset**, using a token
  stored only in Streamlit Cloud's encrypted secrets.

## 1. Put the respondent data in a private Hugging Face dataset

1. Create a free account at [huggingface.co](https://huggingface.co) if you don't have one.
2. **New → Dataset** → give it a name (e.g. `s22620-mnch-data`) → set visibility to
   **Private**.
3. Upload your latest `survey_data.csv` export to that dataset repo (drag-and-drop in
   the web UI, or `huggingface-cli upload`).
4. **Settings → Access Tokens → New token** → type **Read**, scoped to this dataset repo
   only (fine-grained tokens let you restrict it to just this one repo). Copy the token
   (starts `hf_...`) — you won't see it again.

That's it for setup. From now on, **daily refresh = re-upload `survey_data.csv` to that
same HF dataset repo, overwriting the old file.** No GitHub push, no redeploy — the app
re-checks Hugging Face every 5 minutes.

## 2. Push the code (not the data) to GitHub

`data/survey_data.csv` is already in `.gitignore` so a normal `git add .` will never
pick it up. `data/form.xlsx` (the questionnaire structure — no respondent data) is fine
to commit and ships with the app as a fallback.

```bash
cd mnch_dashboard
git init
git add .
git commit -m "MNCH S-22620 dashboard"
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

## 3. Deploy on Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) → **New app** → point it at
   your repo, branch `main`, main file `app.py`.
2. Before (or after) deploying, open **Settings → Secrets** on the app and paste:
   ```toml
   [huggingface]
   repo_id       = "your-username/s22620-mnch-data"
   data_filename = "survey_data.csv"
   token         = "hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
   ```
   (See `.streamlit/secrets.toml.example` for the full template, including the optional
   live SurveyCTO block.)
3. Deploy. The sidebar's **"📡 Data source"** panel defaults to **"🔒 Private Hugging
   Face dataset"** — it will pull from your HF repo automatically using the token above.
   Nobody viewing the deployed app (or the public GitHub repo) can see your token or the
   raw data file — Streamlit secrets are encrypted and never exposed to the browser.

## 4. Daily data refresh

Just re-upload `survey_data.csv` to the private HF dataset repo, overwriting the
previous file. The app re-checks Hugging Face every 5 minutes and picks up the change —
no code change, no GitHub push, no redeploy.

If you'd rather pull straight from SurveyCTO instead of via Hugging Face, add a
`[surveycto]` block to secrets and switch the sidebar source to **"📶 Live SurveyCTO
server"** — see `.streamlit/secrets.toml.example`.

## 5. Project structure

```
app.py             — main Streamlit app: pages, sidebar, KPIs, narrative text
data_utils.py       — XLSForm parsing, choice-label maps, EDP/NDP coalescing, HF download
charts.py           — generic Plotly chart builders (bar, histogram, donut, map, gauge)
data/form.xlsx       — the SurveyCTO XLSForm (survey/choices/settings) — safe to commit
data/survey_data.csv — LOCAL DEV ONLY copy of respondent data — gitignored, not pushed
requirements.txt
.streamlit/config.toml            — Gallup Pakistan navy/red theme
.streamlit/secrets.toml.example   — template for HF + SurveyCTO credentials
```

## 6. Local testing

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # fill in real values
streamlit run app.py
```

Locally, `.streamlit/secrets.toml` is also gitignored, so your real token never risks
being committed by accident.

## Notes on interpreting this data

Fieldwork is in progress — the current data has 44 completed interviews (34 NDP, 10
EDP) across 8 Punjab districts. Several late-questionnaire modules (referral journey,
postnatal follow-up, costing) will fill in as more interviews are completed; charts for
those questions simply won't appear until at least one respondent has answered — they
start rendering automatically as new data arrives, no code change required. Treat all
percentages as descriptive of the current sample, not yet a statistically powered
estimate for Punjab as a whole.

