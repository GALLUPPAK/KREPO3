# -*- coding: utf-8 -*-
"""
National AI Hub for MNCH — Punjab Mapping (Study S-22620)
Story-style Streamlit + Plotly analytics dashboard for Gallup Pakistan / GPDA.

DAILY DATA REFRESH:
  Just overwrite  data/survey_data.csv  in the GitHub repo with the latest
  SurveyCTO export (same column layout — new columns are fine too) and
  push. Streamlit Cloud redeploys automatically, and this app re-reads the
  file (cache is keyed on the file's modified-time, so a same-filename
  overwrite is picked up immediately — no code change needed, even if the
  number of rows or the set of columns grows).

  The sidebar "📡 Data source" panel also lets you upload a CSV ad hoc to
  preview a different export without touching the repo.
"""
import os
import pandas as pd
import streamlit as st

import data_utils as du
import charts as ch

# --------------------------------------------------------------------------
# PAGE CONFIG & BRANDING
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="MNCH Punjab Mapping | Gallup Pakistan",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

NAVY, RED, GOLD = ch.NAVY, ch.RED, ch.GOLD

st.markdown(f"""
<style>
.main {{ background-color:#f7f8fa; }}
h1,h2,h3 {{ color:{NAVY}; font-family:'Segoe UI',Arial,sans-serif; }}
[data-testid="stSidebar"] {{ background-color:{NAVY}; }}
[data-testid="stSidebar"] * {{ color:#fff !important; }}
[data-testid="stSidebar"] .stRadio label {{ font-size:0.92rem; }}
div.stButton>button {{ background-color:{RED}; color:white; border:none; }}
.kpi-card {{ background:white; border-radius:10px; padding:16px 18px; box-shadow:0 1px 4px rgba(0,0,0,0.08);
             border-left:5px solid {RED}; }}
.kpi-value {{ font-size:1.9rem; font-weight:700; color:{NAVY}; }}
.kpi-label {{ font-size:0.82rem; color:#5b7083; text-transform:uppercase; letter-spacing:0.03em; }}
.story-box {{ background:white; border-radius:10px; padding:18px 22px; margin-bottom:14px;
              border-left:5px solid {NAVY}; box-shadow:0 1px 4px rgba(0,0,0,0.06); }}
.module-divider {{ border-top:2px solid {GOLD}; margin:22px 0 14px 0; }}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------
# DATA LOADING (replace data/survey_data.csv in the repo, or upload a file to preview)
# --------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _load_form_cached(form_path):
    return du.load_form(form_path)


@st.cache_data(show_spinner=False)
def _load_csv_cached(path, mtime):
    return du.load_data(path)


def _hf_secrets_available() -> bool:
    try:
        hf = st.secrets["huggingface"]
        return "repo_id" in hf and _resolve_hf_token(hf) is not None
    except Exception:
        return False


def _resolve_hf_token(hf_secrets):
    """Prefer an explicit token in st.secrets; fall back to the BA_TKN environment
    variable, matching the convention already used on the gallupdb HF Spaces."""
    token = hf_secrets.get("token") if hf_secrets else None
    return token or os.environ.get("BA_TKN")


def _hf_filename(hf_secrets, base_filename: str) -> str:
    subfolder = hf_secrets.get("subfolder", "").strip("/")
    return f"{subfolder}/{base_filename}" if subfolder else base_filename


@st.cache_data(show_spinner="Pulling data from private Hugging Face dataset...", ttl=300)
def _hf_paths(repo_id, data_filename, form_filename, token):
    """Re-runs every 5 min (TTL) so an updated file pushed to the HF dataset is
    picked up without redeploying the app. hf_hub_download checks the remote
    ETag on each call, so an unchanged file is served from local cache instantly."""
    data_path = du.hf_download(repo_id, data_filename, token)
    form_path = du.hf_download(repo_id, form_filename, token) if form_filename else du.FORM_PATH_DEFAULT
    return data_path, form_path


def load_everything(source: str, uploaded_file):
    bundled_exists = os.path.exists(du.DATA_PATH_DEFAULT)
    form_path_to_use = du.FORM_PATH_DEFAULT

    if source == "hf":
        try:
            hf = st.secrets["huggingface"]
            token = _resolve_hf_token(hf)
            if not token:
                raise RuntimeError("No token found in secrets or the BA_TKN environment variable.")
            data_path, form_path_to_use = _hf_paths(
                hf["repo_id"],
                _hf_filename(hf, hf.get("data_filename", "survey_data.csv")),
                _hf_filename(hf, hf["form_filename"]) if hf.get("form_filename") else "",
                token,
            )
            source_note = f"Private Hugging Face dataset ({hf['repo_id']}) — refreshed every 5 min"
        except Exception as e:
            if bundled_exists:
                st.sidebar.warning(f"Hugging Face pull unavailable, showing bundled file instead. ({e})")
                data_path = du.DATA_PATH_DEFAULT
                source_note = "Bundled file (Hugging Face unavailable)"
            else:
                st.sidebar.error(f"Hugging Face pull failed and no bundled fallback file is present. ({e})")
                st.stop()
        mtime = os.path.getmtime(data_path)
        data_df = _load_csv_cached(data_path, mtime)
    elif source == "upload" and uploaded_file is not None:
        data_df = pd.read_csv(uploaded_file, low_memory=False)
        source_note = f"Uploaded file: {uploaded_file.name}"
    elif bundled_exists:
        mtime = os.path.getmtime(du.DATA_PATH_DEFAULT)
        data_df = _load_csv_cached(du.DATA_PATH_DEFAULT, mtime)
        source_note = "Bundled repo file data/survey_data.csv"
    else:
        st.sidebar.warning("No data file found. Upload a CSV to preview, or configure the "
                            "[huggingface] source in Settings → Secrets.")
        st.stop()

    catalogue, label_maps = _load_form_cached(form_path_to_use)
    uniq = du.get_unique_variables(catalogue)
    data_df = du.coalesce_pathway_columns(data_df, catalogue)
    return catalogue, label_maps, uniq, data_df, source_note


# --------------------------------------------------------------------------
# SIDEBAR
# --------------------------------------------------------------------------
st.sidebar.markdown("## National AI Hub for MNCH")
st.sidebar.caption("Punjab Mapping · Study S-22620 · Gallup Pakistan Digital Analytics")

with st.sidebar.expander("📡 Data source", expanded=False):
    hf_ready = _hf_secrets_available()
    source_options = (["hf"] if hf_ready else []) + ["repo", "upload"]
    source = st.radio(
        "Where should data come from?",
        options=source_options,
        format_func=lambda k: {
            "hf": "🔒 Private Hugging Face dataset",
            "repo": "📁 Bundled repo file (data/survey_data.csv)",
            "upload": "⬆️ Upload a file to preview",
        }[k],
        index=0,
    )
    uploaded = st.file_uploader("CSV to preview", type="csv") if source == "upload" else None

catalogue, label_maps, uniq_vars, data_raw, source_note = load_everything(source, uploaded)
st.sidebar.caption(f"📄 Source: {source_note}")
st.sidebar.caption(f"🕒 Last loaded: {pd.Timestamp.now().strftime('%d %b %Y, %H:%M')}")

PAGES = [
    ("overview", "📖 Story Overview"),
    ("fieldwork", "🗺️ Sample & Fieldwork"),
    ("wb", "👩 Woman's Profile"),
    ("ma", "💍 Marriage & Household"),
    ("cm", "👶 Birth History & Eligibility"),
    ("pt", "🧭 Pathway Typing"),
    ("mn", "🏥 Antenatal Care (ANC)"),
    ("pu", "📚 Health Literacy & Records"),
    ("delay1", "⏱️ Delay 1 — Recognition & Decision"),
    ("delay2", "🚗 Delay 2 — Journey to Facility"),
    ("delay3", "🏨 Delay 3 — Facility Arrival & Care"),
    ("ec_detail", "🚨 Emergency Complications Detail"),
    ("costing", "💰 Costing & Payments"),
    ("outcomes", "🍼 Outcomes & Newborn Care"),
    ("referral", "🔁 Referral Journey"),
    ("pnc", "🤱 Postnatal Care & Breastfeeding"),
    ("dr_access", "📱 Digital Readiness — Access"),
    ("dr_usage", "💳 Digital Readiness — Usage & Finance"),
    ("dr_trust", "🤝 Digital Readiness — Info, Trust & Tools"),
    ("quality", "✅ Data Quality & Interviewer Notes"),
]
st.sidebar.markdown("---")
page_key = st.sidebar.radio("Navigate", options=[p[0] for p in PAGES], format_func=lambda k: dict(PAGES)[k])

st.sidebar.markdown("---")
st.sidebar.markdown("### Filters")
district_map = label_maps.get("district", {})
if "district" in data_raw.columns:
    all_districts = sorted(data_raw["district"].dropna().unique().tolist(), key=lambda x: str(x))
    dist_labels = {d: district_map.get(str(d), str(d)) for d in all_districts}
    sel_districts = st.sidebar.multiselect(
        "District", options=all_districts, format_func=lambda d: dist_labels.get(d, d), default=[]
    )
else:
    sel_districts = []

protocols_present = sorted(data_raw["protocol"].dropna().unique().tolist()) if "protocol" in data_raw.columns else []
sel_protocols = st.sidebar.multiselect("Pathway (protocol)", options=protocols_present, default=[])

data = data_raw.copy()
if sel_districts:
    data = data[data["district"].isin(sel_districts)]
if sel_protocols:
    data = data[data["protocol"].isin(sel_protocols)]

st.sidebar.markdown("---")
st.sidebar.markdown(f"**{len(data)}** of **{len(data_raw)}** interviews shown")

st.sidebar.markdown("---")
st.sidebar.caption("Gallup Pakistan Digital Analytics (GPDA)")

# --------------------------------------------------------------------------
# HEADER
# --------------------------------------------------------------------------
st.markdown(f"<h1 style='margin-bottom:0'>National AI Hub for MNCH — Punjab Mapping</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='color:#5b7083;margin-top:2px'>Study S-22620 · Emergency &amp; Normal Delivery Pathways · "
            f"{dict(PAGES)[page_key]}</p>", unsafe_allow_html=True)

CHART_COUNTER = {"n": 0}


def render_chart(fig):
    if fig is not None:
        try:
            st.plotly_chart(fig, width="stretch")
        except TypeError:
            st.plotly_chart(fig, use_container_width=True)
        CHART_COUNTER["n"] += 1


def render_module_grid(module_keys, ncols=2, min_n=1):
    """Generic renderer: every select_one / select_multiple / numeric question
    in the given modules gets a chart automatically, driven purely by the
    XLSForm catalogue — this is what lets the dashboard 'self update' when
    tomorrow's data adds rows or the form gains new questions."""
    rows = uniq_vars[uniq_vars["module_key"].isin(module_keys)]
    cols = st.columns(ncols)
    i = 0
    for _, r in rows.iterrows():
        vk, qtype = r["var_key"], r["type"]
        title = ch._short_label(r["label"] or vk, 80)
        fig, n = None, 0
        if qtype == "select_one":
            mm = du.merged_label_map(r["list_names"], label_maps)
            fig, n = ch.bar_select_one_merged(data, vk, mm, title, min_n=min_n)
        elif qtype in ("integer", "decimal"):
            fig, n = ch.histogram_numeric(data, vk, title, min_n=max(3, min_n))
        elif qtype == "select_multiple":
            mm = du.merged_label_map(r["list_names"], label_maps)
            fig, n = ch.bar_select_multiple_merged(data, r["name_first"], mm, title, min_n=min_n)
        if fig is not None:
            with cols[i % ncols]:
                render_chart(fig)
            i += 1


def story(text):
    st.markdown(f"<div class='story-box'>{text}</div>", unsafe_allow_html=True)


def section(title):
    st.markdown(f"<div class='module-divider'></div>", unsafe_allow_html=True)
    st.subheader(title)


# --------------------------------------------------------------------------
# PAGE: STORY OVERVIEW
# --------------------------------------------------------------------------
if page_key == "overview":
    story("""
    <b>The story this dashboard tells</b> follows Punjab women through pregnancy, delivery and the postnatal
    period along the classic <b>Three Delays</b> framework used worldwide in maternal-health research:
    <b>Delay 1</b> — recognising danger and deciding to seek care; <b>Delay 2</b> — reaching a health facility;
    and <b>Delay 3</b> — receiving adequate care once there. The study routes each woman down one of two
    pathways depending on her recent pregnancy experience — the <b style='color:#e4002b'>Emergency Delivery
    Pathway (EDP)</b> for women who faced a complication, and the <b style='color:#002147'>Normal Delivery
    Pathway (NDP)</b> for women who did not — and layers on a full <b>Digital Readiness</b> module to map how
    ready women are for phone-based MNCH tools. Use the sidebar to move through each chapter of the story,
    filter by district or pathway, and — since fieldwork is still running — this page refreshes automatically
    every time the data file is replaced.
    """)

    n_total, n_edp, n_ndp = len(data), int((data.get("protocol") == "EDP").sum()), int((data.get("protocol") == "NDP").sum())
    n_dist = data["district"].nunique() if "district" in data.columns else 0
    avg_dur = pd.to_numeric(data.get("duration"), errors="coerce").mean() / 60 if "duration" in data.columns else None

    k1, k2, k3, k4, k5 = st.columns(5)
    for col, val, lab in zip(
        [k1, k2, k3, k4, k5],
        [n_total, n_edp, n_ndp, n_dist, f"{avg_dur:.0f} min" if avg_dur else "—"],
        ["Interviews completed", "Emergency pathway (EDP)", "Normal pathway (NDP)", "Districts covered", "Avg. interview length"],
    ):
        col.markdown(f"<div class='kpi-card'><div class='kpi-value'>{val}</div>"
                      f"<div class='kpi-label'>{lab}</div></div>", unsafe_allow_html=True)

    section("Pathway split & district coverage")
    c1, c2 = st.columns(2)
    with c1:
        if n_total:
            render_chart(ch.donut({"Emergency (EDP)": n_edp, "Normal (NDP)": n_ndp},
                                   "Delivery pathway split", colors=[RED, NAVY]))
    with c2:
        if "district" in data.columns and n_total:
            dc = data["district"].map(lambda d: district_map.get(str(d), str(d))).value_counts().sort_values()
            import plotly.graph_objects as go
            fig = go.Figure(go.Bar(x=dc.values, y=dc.index, orientation="h", marker_color=GOLD,
                                    text=dc.values, textposition="outside"))
            fig.update_layout(title="Interviews by district", **{k: v for k, v in ch.BASE_LAYOUT.items()})
            render_chart(fig)

    section("Fieldwork progress")
    c3, c4 = st.columns(2)
    with c3:
        render_chart(ch.timeline_submissions(data, "Interviews completed per day"))
    with c4:
        render_chart(ch.histogram_numeric(data, "duration", "Interview duration (seconds)", min_n=3)[0])

    m = ch.map_scatter(data, "Where interviews are happening (EDP = red, NDP = navy)")
    if m:
        section("Geographic footprint")
        render_chart(m)

# --------------------------------------------------------------------------
# GENERIC MODULE PAGES
# --------------------------------------------------------------------------
else:
    PAGE_CONFIG = {
        "fieldwork": (["grp_sc", "grp_wm", "group_EDP_main", "group_NDP_main"],
                      "Every interview starts with a screener that determines eligibility and routes the "
                      "respondent to EDP or NDP, followed by the household and participant identification panel."),
        "wb": (["grp_wb"],
               "Who are the women in this sample? Age, education, health coverage, residence and livelihood — "
               "the background variables that shape everything downstream, shown here combined across both pathways."),
        "ma": (["grp_ma"],
               "Marriage and household composition — age at marriage, household size, and decision-making "
               "structures that influence a woman's autonomy in seeking care."),
        "cm": (["grp_cm", "grp_cm2", "grp_cm3"],
               "Birth history and eligibility screening, including — for the emergency pathway — the specific "
               "complication details that routed the respondent into EDP."),
        "pt": (["grp_pt"],
               "The pathway-typing tool: the structured logic SurveyCTO used in the field to classify each "
               "respondent's most recent pregnancy experience."),
        "mn": (["grp_mn", "grp_mn_fr"],
               "Antenatal care (ANC) attendance, timing and content — plus, for the normal pathway, the "
               "friction points that kept some women from attending as often as recommended."),
        "pu": (["grp_pu", "grp_pr"],
               "How well women understood the care and information given to them, and how pregnancy-related "
               "records were kept and stored."),
        "delay1": (["grp_fr_a", "grp_ec", "grp_dl_e", "grp_dd"],
                   "<b>Delay 1 — Recognition &amp; the decision to seek care.</b> For EDP respondents: how the "
                   "danger sign was recognised, screened, and how long it took to decide to leave home. For NDP "
                   "respondents: the deliberate decision-making process behind choosing a delivery location."),
        "delay2": (["grp_jo", "grp_jo_e"],
                   "<b>Delay 2 — Reaching a facility.</b> Transport used, distance and time travelled, and "
                   "obstacles encountered en route — the second of the three classic delays."),
        "delay3": (["grp_fa", "grp_fa_e", "grp_fah", "grp_cs"],
                   "<b>Delay 3 — Receiving adequate care.</b> What happened on arrival: waiting times, care "
                   "experience, and — for home deliveries or planned caesareans — the alternative pathways taken."),
        "ec_detail": (["grp_ec_pph", "grp_ec_hdp", "grp_ec_sep", "grp_ec_obl", "grp_ec_ane", "grp_ec_ptb", "grp_ec_nns"],
                      "A closer look at each specific emergency complication type reported by EDP respondents — "
                      "postpartum haemorrhage, hypertensive disorders, sepsis, obstructed labour, severe anaemia, "
                      "preterm birth and neonatal sepsis."),
        "costing": (["grp_co", "grp_co_e"],
                    "What care actually cost families — official fees, informal payments, and how the costs of "
                    "an emergency compare with a normal delivery."),
        "outcomes": (["grp_oc", "grp_nb"],
                     "Maternal and newborn outcomes, and the immediate newborn care practices that followed "
                     "delivery."),
        "referral": (["grp_rf", "grp_rf_e"],
                     "The referral journey — when a woman was moved from one facility to another, and what that "
                     "additional journey involved."),
        "pnc": (["grp_pn", "grp_pn_fr", "grp_pnc_e", "grp_bf"],
                "Postnatal care visits and the friction that limits follow-up, plus breastfeeding initiation "
                "and practices."),
        "dr_access": (["grp_dr", "grp_dr_a", "grp_dr_b"],
                      "<b>Digital Readiness, chapter 1 — Access.</b> Phone ownership, physical access to a "
                      "device, and network connectivity: the basic preconditions for any digital MNCH tool."),
        "dr_usage": (["grp_dr_c", "grp_dr_d"],
                     "<b>Digital Readiness, chapter 2 — Usage &amp; Finance.</b> Digital competency and use of "
                     "digital financial services."),
        "dr_trust": (["grp_dr_e", "grp_dr_e2", "grp_dr_f", "grp_dr_g", "grp_dr_h"],
                     "<b>Digital Readiness, chapter 3 — Information, Trust &amp; Tools.</b> How women currently "
                     "use phones for health information, the barriers they face, how much they trust "
                     "phone-based health information, and their readiness for a future digital MNCH tool."),
        "quality": (["grp_ob", "grp_dr_ob"],
                    "Interviewer observations and fieldwork data-quality indicators — the checks that keep "
                    "this dashboard's numbers trustworthy as new data arrives daily."),
    }
    keys, narrative = PAGE_CONFIG[page_key]
    story(narrative)
    if page_key == "quality":
        c1, c2 = st.columns(2)
        with c1:
            render_chart(ch.histogram_numeric(data, "duration", "Interview duration (seconds)", min_n=3)[0])
        with c2:
            if "audio_comp" in data.columns:
                aud = data["audio_comp"].notna().sum()
                render_chart(ch.donut({"Audio captured": int(aud), "Missing": int(len(data) - aud)},
                                       "Audio audit completeness", colors=[NAVY, "#c9c9c9"]))
    render_module_grid(keys, ncols=2, min_n=1)

st.sidebar.markdown("---")
st.sidebar.caption(f"Charts rendered on this page: **{CHART_COUNTER['n']}**")
