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
  GitHub — it's pulled at runtime from a folder inside your existing private
  `gallupdb/codedb` Hugging Face dataset, before this link is shared with the client.

## 1. Put the data in a subfolder of your existing private HF dataset

1. Open [huggingface.co/datasets/gallupdb/codedb](https://huggingface.co/datasets/gallupdb/codedb)
   → **Files and versions**.
2. Create a folder for this project (e.g. `s22620-mnch/`) and upload `survey_data.csv`
   into it — either drag-and-drop in the web UI, or `huggingface-cli upload`.
   (`form.xlsx` doesn't need to go here — it's just the questionnaire structure with no
   respondent data, so it ships in the GitHub repo as usual.)
3. You'll need a read token for this dataset. Reuse whichever token/secret your other
   `gallupdb` Spaces already use (e.g. the one behind `BA_TKN`), or generate a new
   **read-only** token scoped to this repo under **Settings → Access Tokens**.

## 2. Configure Streamlit Cloud secrets

Streamlit Cloud reads secrets from **Settings → Secrets** on the app dashboard (this is
the Streamlit-Cloud equivalent of the `BA_TKN` Space secret you use elsewhere). Paste:

```toml
[huggingface]
repo_id       = "gallupdb/codedb"
subfolder     = "s22620-mnch"
data_filename = "survey_data.csv"
token         = "hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

If you'd rather not duplicate the token, you can instead set an environment variable
named `BA_TKN` in the app's advanced settings and omit `token` from the block above —
the app checks `st.secrets` first, then falls back to `os.environ["BA_TKN"]`, matching
the convention already used on your other `gallupdb` Spaces.

See `.streamlit/secrets.toml.example` for the full template (also usable locally by
copying it to `.streamlit/secrets.toml`, which is gitignored).

## 3. Deploy / redeploy

Push the code (not the data) to GitHub as usual — `data/survey_data.csv` is gitignored,
`data/form.xlsx` is not. On [share.streamlit.io](https://share.streamlit.io), point the
app at `app.py`. Once the `[huggingface]` secret above is set, the sidebar's **"📡 Data
source"** panel automatically defaults to **"🔒 Private Hugging Face dataset"** — nobody
viewing the deployed dashboard or the public GitHub repo can see the token or the raw
data file.

## 4. Daily data refresh

Re-upload `survey_data.csv` to the same `s22620-mnch/` folder in the `gallupdb/codedb`
dataset, overwriting the previous file. The app re-checks Hugging Face every 5 minutes
and picks up the change — no GitHub push, no redeploy.

## 5. Project structure

```
app.py                — main Streamlit app: pages, sidebar, KPIs, narrative text
data_utils.py           — XLSForm parsing, choice-label maps, EDP/NDP coalescing, HF download
charts.py               — generic Plotly chart builders (bar, histogram, donut, map, gauge)
data/form.xlsx           — the SurveyCTO XLSForm — safe to commit, no respondent data
data/survey_data.csv     — LOCAL DEV ONLY copy — gitignored, not pushed
requirements.txt
.streamlit/config.toml            — Gallup Pakistan navy/red theme
.streamlit/secrets.toml.example   — template for the [huggingface] secret block
```

## 6. Local testing

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # fill in real values
streamlit run app.py
```

## Notes on interpreting this data

Fieldwork is in progress — the current data has 44 completed interviews (34 NDP, 10
EDP) across 8 Punjab districts. Several late-questionnaire modules (referral journey,
postnatal follow-up, costing) will fill in as more interviews are completed; charts for
those questions simply won't appear until at least one respondent has answered — they
start rendering automatically as new data arrives, no code change required. Treat all
percentages as descriptive of the current sample, not yet a statistically powered
estimate for Punjab as a whole.

A couple of fields (`ob7`, the `dr_e2_1` family) currently show a few responses labeled
`"Unlisted code (0)"` — raw values in the export that fall outside the choice list
defined in the XLSForm, most likely a SurveyCTO skip-logic default leaking through.
Worth flagging to whoever manages the form.
